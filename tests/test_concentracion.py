"""Radios, cobertura y persistencia con registros sintéticos independientes de los reales."""

import csv
import tempfile
import unittest
from pathlib import Path

from precio_entorno.concentracion import CrimeIndex, circle, distance_m

HEADER = ['id-mapa', 'fecha', 'franja', 'tipo', 'barrio', 'latitud', 'longitud', 'cantidad']
BBOX = (-58.54, -34.73, -58.32, -34.52)
PIN = {'id': 'prueba', 'latitude': -34.62, 'longitude': -58.44, 'location_accuracy_m': 50}


class ConcentracionTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)

    def file(self, name, rows):
        path = self.root / name
        with path.open('w', encoding='utf-8', newline='') as output:
            writer = csv.writer(output)
            writer.writerow(HEADER)
            writer.writerows(rows)
        return path

    def event(self, identifier, year=2024, month=1, hour=20, kind='Robo', count=1,
              lat=-34.62, lon=-58.44, barrio='CABALLITO'):
        return [identifier, f'{year}-{month:02d}-02', hour, kind, barrio, lat, lon, count]

    def test_exact_accumulative_radii_bands_weights_and_year_scoped_deduplication(self):
        rows = [self.event('a', hour=6, count=2, lat=-34.621),
                self.event('b', hour=19, kind='Hurto', count=3, lat=-34.623),
                self.event('c', hour=20, count=4, lat=-34.628, barrio='ALMAGRO'),
                self.event('d', hour=5, count=7, lat=-34.63),  # Fuera de 1.000 m.
                self.event('e', hour='NULL', kind='Hurto'),
                self.event('f', hour=1.5), self.event('a', count=99),
                self.event('a', year=2025, hour=0),
                self.event('vial', kind='Vialidad', count=100),
                self.event('invalid', count=-1), self.event('fraction', count=1.5),
                self.event('pin', lat=0, count=8)]
        index = CrimeIndex([self.file('delitos_2024.csv', rows)])
        result = index.analyze(BBOX, PIN)
        values = {(r['anio'], r['radio_m'], r['tipo']): r for r in result['resumen_radios']}
        self.assertEqual(values[2024, 250, 'robo']['diurno'], 2)
        self.assertEqual(values[2024, 250, 'robo']['sin_dato'], 1)
        self.assertEqual(values[2024, 250, 'hurto']['total'], 1)
        self.assertEqual(values[2024, 500, 'hurto']['total'], 4)
        self.assertEqual(values[2024, 1000, 'robo']['nocturno'], 4)
        self.assertEqual(values[2025, 250, 'robo']['nocturno'], 1)
        self.assertEqual(result['calidad']['duplicadas'], 1)
        self.assertEqual(result['calidad']['robos_hurtos_sin_pin'], 8)
        self.assertEqual(result['calidad']['descartadas'], 2)
        self.assertIsNotNone(result['revision_2025'])
        self.assertFalse(result['persistencia']['disponible'])
        self.assertEqual(len(result['fuentes'][0]['sha256']), 64)

    def persistent_rows(self, year):
        # Cobertura mensual observada por ciudad, sin inferirla de la zona del aviso.
        rows = [self.event(f'm{m}', year=year, month=m, kind='Vialidad') for m in range(1, 13)]
        rows += [self.event(f'low{i}', year=year, lat=-34.60, lon=-58.51 + i * .005) for i in range(10)]
        rows.append(self.event('hot', year=year, count=6))
        if year == 2024:
            rows.append(self.event('isolated', year=year, lat=-34.65, count=30))
        return rows

    def test_persistence_requires_repeated_high_concentration_and_comparable_years(self):
        paths = [self.file(f'delitos_{y}.csv', self.persistent_rows(y)) for y in (2024, 2025)]
        result = CrimeIndex(paths).analyze(BBOX, kind='robo', band='nocturno')
        persistent = [c for c in result['celdas'] if c['persistente']]
        self.assertEqual(len(persistent), 1)
        self.assertEqual(persistent[0]['anios_altos'], [2024, 2025])
        self.assertEqual(result['persistencia']['umbrales'], {2024: 5, 2025: 5})
        self.assertFalse(next(c for c in result['celdas'] if c['hechos'] == 30)['persistente'])
        # Ausencia en otro año es cero observado, no persistencia del evento aislado.
        filtered = CrimeIndex(paths).analyze(BBOX, year=2025, kind='hurto', band='diurno')
        self.assertEqual(filtered['celdas'], [])

    def test_partial_year_and_missing_location_do_not_produce_persistence_or_fake_radius(self):
        first = self.file('delitos_2024.csv', self.persistent_rows(2024))
        partial = self.file('delitos_2025.csv', [self.event('hot', year=2025, count=100)])
        index = CrimeIndex([first, partial])
        result = index.analyze(BBOX)
        self.assertFalse(result['persistencia']['disponible'])
        self.assertFalse(any(c['persistente'] for c in result['celdas']))
        self.assertEqual(result['resumen_radios'], [])
        for accuracy in (None, 101):
            self.assertFalse(index.analyze(BBOX, dict(PIN, location_accuracy_m=accuracy))['disponible'])
        with self.assertRaisesRegex(ValueError, 'año'):
            index.analyze(BBOX, year=2026)
        with self.assertRaises(ValueError):
            index.analyze(BBOX, radius=750)

    def test_filters_do_not_silently_include_unknown_hours_or_change_full_summary(self):
        path = self.file('delitos.csv', [self.event('n'), self.event('d', hour=6),
                                       self.event('h', kind='Hurto'), self.event('u', hour='NULL')])
        index = CrimeIndex([path])
        night = index.analyze(BBOX, PIN, kind='robo', band='nocturno', year=2024)
        unknown = index.analyze(BBOX, PIN, kind='robo', band='sin_dato', year=2024)
        all_events = index.analyze(BBOX, PIN, year=2024)
        self.assertEqual(sum(c['hechos'] for c in night['celdas']), 1)
        self.assertEqual(sum(c['hechos'] for c in unknown['celdas']), 1)
        self.assertEqual(sum(c['hechos'] for c in all_events['celdas']), 4)
        self.assertEqual(night['resumen_radios'], all_events['resumen_radios'])

    def test_geodesic_circle_and_distance_agree_at_all_three_boundaries(self):
        for radius in (250, 500, 1000):
            ring = circle(PIN['longitude'], PIN['latitude'], radius)['coordinates'][0]
            self.assertEqual(ring[0], ring[-1])
            for lon, lat in ring[:-1]:
                self.assertAlmostEqual(distance_m(PIN['longitude'], PIN['latitude'], lon, lat), radius, places=6)

    def test_official_field_aliases_and_invalid_sources(self):
        path = self.file('delitos.csv', [self.event('a')])
        text = path.read_text(encoding='utf-8').replace('franja,', 'franja_horaria,').replace('tipo,', 'tipo_delito,').replace('latitud,', 'lat,').replace('longitud,', 'long,')
        path.write_text(text, encoding='utf-8')
        self.assertEqual(len(CrimeIndex([path]).events), 1)
        path.write_text('fecha,tipo\n2024-01-01,Robo\n', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'faltan columnas'):
            CrimeIndex([path])


if __name__ == '__main__':
    unittest.main()
