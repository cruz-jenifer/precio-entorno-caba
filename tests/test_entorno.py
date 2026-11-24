"""Pruebas de las capas de entorno por barrio y del mapa, con datos sintéticos."""

import json
import tempfile
import unittest
from pathlib import Path

from pyproj import Transformer

from precio_entorno import entorno, mapa

CABALLITO = (-58.45, -34.62, -58.44, -34.61)
ALMAGRO = (-58.44, -34.62, -58.43, -34.61)


def square(west, south, east, north):
    return [[[west, south], [east, south], [east, north], [west, north], [west, south]]]


def polygon(box, transform=None):
    ring = square(*box)[0]
    if transform:
        ring = [list(transform(x, y)) for x, y in ring]
    return {'type': 'Polygon', 'coordinates': [ring]}


def point(lon, lat, transform=None):
    x, y = transform(lon, lat) if transform else (lon, lat)
    return {'type': 'Point', 'coordinates': [x, y]}


def collection(*features):
    return {'type': 'FeatureCollection', 'features': [
        {'type': 'Feature', 'properties': props, 'geometry': geometry} for props, geometry in features]}


def write(path, data):
    path.write_text(json.dumps(data), encoding='utf-8')


def build_sources(root):
    poi, raw = root / 'poi', root / 'entorno'
    poi.mkdir()
    raw.mkdir()
    to_local = Transformer.from_crs('EPSG:4326', 'EPSG:9498', always_xy=True).transform
    to_gkba = Transformer.from_crs('EPSG:4326', entorno.GKBA, always_xy=True).transform
    write(raw / 'barrios.geojson', collection(
        ({'nombre': 'Caballito', 'comuna': 6, 'area_metro': 1_000_000}, polygon(CABALLITO)),
        ({'nombre': 'Almagro', 'comuna': 5, 'area_metro': 900_000}, polygon(ALMAGRO))))
    write(raw / 'estaciones_de_subte.geojson', collection(
        ({'estacion': 'Primera Junta', 'linea': 'A'}, point(-58.445, -34.615)),
        ({'estacion': 'Medrano', 'linea': 'B'}, point(-58.435, -34.615)),
        ({'estacion': 'Afuera', 'linea': 'C'}, point(-58.30, -34.615))))
    (raw / 'estaciones-accesibles.csv').write_text(
        'long;lat;linea;estacion;escaleras_mecanicas;ascensores\n-58,445;-34,615;A;PRIMERA JUNTA;2;2\n',
        encoding='utf-8')
    write(raw / 'centros_salud_nivel_1_cesac.geojson', collection(
        ({'nombre': 'CeSAC N° 99', 'direccion': 'Calle 1'}, point(-58.436, -34.614))))
    write(raw / 'riesgo-hidrico.geojson', collection(
        ({'m2': 1}, polygon((-58.45, -34.62, -58.445, -34.61), to_gkba))))
    write(raw / 'medicion_de_ruido_diurno.geojson', collection(
        ({'dba_low': '70', 'color': '132 0 168'}, polygon(CABALLITO)),
        ({'dba_low': '55', 'color': '230 152 0'}, polygon(ALMAGRO))))
    write(raw / 'medicion_de_ruido_nocturno.geojson', collection(
        ({'dba_low': '60', 'color': '255 0 0'}, polygon(CABALLITO))))
    write(poi / 'espacio_verde_publico.geojson', collection(
        ({'clasificac': 'PLAZA', 'nombre': 'Plaza Irlanda', 'area': 20_000},
         polygon((-58.448, -34.618, -58.446, -34.616))),
        ({'clasificac': 'CANTERO CENTRAL', 'area': 500}, polygon((-58.438, -34.618, -58.436, -34.616)))))
    write(poi / 'establecimientos_educativos.geojson', collection(
        ({'nam': 'Escuela 1', 'ges': 'Estatal', 'nen_mde': 'Nivel primario común'}, point(-58.447, -34.613, to_local)),
        ({'nam': 'Colegio 2', 'ges': 'Privada', 'nen_mde': 'Nivel secundario común'},
         point(-58.434, -34.613, to_local)),
        ({'nam': 'Adultos 3', 'ges': 'Estatal', 'nen_mde': 'Nivel primario de jóvenes y adultos'},
         point(-58.447, -34.612, to_local))))
    write(poi / 'hospitales.geojson', collection(
        ({'fna': 'Hospital Durand', 'esp': 'General'}, point(-58.443, -34.611, to_local))))
    return poi, raw


class EntornoTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        root = Path(cls.temp.name)
        poi, raw = build_sources(root)
        cls.target = root / 'out'
        cls.summary = entorno.convert(poi, raw, cls.target)
        cls.layers = entorno.load(cls.target)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_points_are_assigned_to_official_barrios(self):
        caballito, almagro = self.summary['Caballito'], self.summary['Almagro']
        self.assertEqual((caballito['subte_lineas'], almagro['subte_lineas']), (['A'], ['B']))
        self.assertEqual(caballito['escuelas']['primario'], {'Estatal': 1})
        self.assertEqual(almagro['escuelas']['secundario'], {'Privada': 1})
        self.assertEqual((caballito['cesac'], almagro['cesac']), (0, 1))
        self.assertEqual((caballito['hospitales'], almagro['hospitales']), (1, 0))
        stations = {s['name']: s for s in self.layers['puntos']['subte']}
        self.assertNotIn('Afuera', stations)
        self.assertIn('Ascensores informados: 2', stations['Primera Junta']['tooltip'])
        self.assertIsNone(stations['Medrano']['elevators'])

    def test_green_spaces_exclude_medians(self):
        self.assertEqual((self.summary['Caballito']['verdes_cantidad'], self.summary['Caballito']['verdes_ha']), (1, 2.0))
        self.assertEqual(self.summary['Almagro']['verdes_cantidad'], 0)

    def test_noise_uses_typical_level_per_cell_and_requires_coverage(self):
        caballito, almagro = self.summary['Caballito']['ruido'], self.summary['Almagro']['ruido']
        self.assertGreaterEqual(caballito['diurno']['celdas'], entorno.MIN_NOISE_CELLS)
        self.assertEqual(caballito['diurno']['alto'], 1.0)
        self.assertEqual(almagro['diurno']['alto'], 0.0)
        self.assertEqual(caballito['nocturno']['alto'], 0.0)
        self.assertIsNone(almagro['nocturno']['alto'])
        self.assertEqual(self.layers['ruido']['colores']['70'], [132, 0, 168])

    def test_flood_risk_is_reprojected_from_gauss_kruger(self):
        self.assertAlmostEqual(self.summary['Caballito']['riesgo_hidrico'], 0.5, delta=0.1)
        self.assertEqual(self.summary['Almagro']['riesgo_hidrico'], 0.0)

    def test_sources_record_digest_and_license(self):
        sources = {s['capa']: s for s in self.layers['fuentes']['fuentes']}
        self.assertEqual(len(sources['barrios']['sha256']), 64)
        self.assertTrue(sources['subte']['url'].startswith('https://cdn.buenosaires.gob.ar/'))
        self.assertIn('CC-BY 2.5 AR', sources['cesac']['licencia'])
        self.assertNotIn('gastronomia', sources)
        self.assertNotIn('gastronomia', self.summary['Almagro'])

    def test_comparison_columns_follow_preferences_without_a_score(self):
        self.assertEqual(entorno.comparison_columns(self.summary['Caballito'], []), {})
        row = entorno.comparison_columns(self.summary['Caballito'], ['Subte', 'Escuelas', 'Ruido'], 'primario')
        self.assertEqual(row['Líneas de subte'], 'A')
        self.assertEqual(row['Escuelas de nivel primario'], 1)
        self.assertEqual(row['Ruido ≥70 dBA de día (% de celdas relevadas)'], 100)
        self.assertNotIn('Puntaje', ' '.join(row))
        self.assertEqual(entorno.comparison_columns(None, ['Subte']), {})

    def test_map_builds_active_layers_with_legend(self):
        deck, legend = mapa.build(self.layers, 'Caballito', ['Subte', 'Ruido', 'Salud'], noise_period='diurno')
        labels = [label for _, label in legend]
        self.assertIn('70–75 dBA', labels)
        self.assertIn('Línea A', labels)
        self.assertIn('CeSAC', labels)
        kinds = [layer.type for layer in deck.layers]
        self.assertEqual(kinds.count('ScatterplotLayer'), 3)
        self.assertIn('ColumnLayer', kinds)
        empty, nothing = mapa.build(self.layers, 'Caballito', [])
        self.assertEqual([layer.type for layer in empty.layers], ['GeoJsonLayer'])
        self.assertEqual(nothing, [])


class UniversidadesTrenesTests(unittest.TestCase):
    def test_universities_keep_name_unit_and_address_but_not_contacts(self):
        rows = entorno.universities({'features': [
            {'geometry': {'type': 'Point', 'coordinates': [-58.4, -34.6]},
             'properties': {'nombre': 'Universidad Ficticia', 'unidad_aca': 'Facultad  de Pruebas', 'sede': None,
                            'dirreccion': 'Calle 123', 'telefono': '4000-0000', 'fax': '4000-0001', 'web': 'x.edu'}},
            {'geometry': {'type': 'LineString', 'coordinates': []}, 'properties': {'nombre': 'No es un punto'}}]})
        self.assertEqual(rows, [{'name': 'Universidad Ficticia', 'unit': 'Facultad de Pruebas', 'lon': -58.4, 'lat': -34.6,
                                 'tooltip': 'Universidad Ficticia · Facultad de Pruebas · Calle 123'}])
        self.assertNotIn('4000', json.dumps(rows))

    def test_train_stations_get_a_short_line_name_once_per_line(self):
        punto = lambda nombre, linea, lon: {'geometry': {'type': 'Point', 'coordinates': [lon, -34.6]},
                                            'properties': {'nombre': nombre, 'linea': linea, 'ramal': 'x'}}
        rows = entorno.train_stations({'features': [
            punto('Retiro', 'Mitre , F.C.G.B.M.', -58.37), punto('Retiro', 'Mitre , F.C.G.B.M.', -58.37),
            punto('Retiro', 'San Martin , F.C.G.S.M.', -58.375), punto('Sin línea', '', -58.4)]})
        self.assertEqual([(r['name'], r['line']) for r in rows], [('Retiro', 'Mitre'), ('Retiro', 'San Martín')])
        self.assertEqual(rows[1]['tooltip'], 'Estación Retiro · Línea San Martín')


class CrimeCellsTests(unittest.TestCase):
    def test_counts_registered_events_by_cell_month_and_kind(self):
        rows = [
            '"id-mapa","fecha","tipo","latitud","longitud","cantidad"',
            '1,"2025-03-02","Robo","-34.6150","-58.4450",1',
            '2,"2025-03-05","Robo","-34.6151","-58.4451",2',
            '3,"2025-03-09","Hurto","-34.6150","-58.4450",1',
            '4,"2025-04-01","Robo","-34.6150","-58.4450",5',
            '5,"2025-03-01","Robo","0","0",1',
            '6,"2025-03-01","Robo","-34.5800","-58.3900",1',
        ]
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'delitos.csv'
            path.write_text('\n'.join(rows) + '\n', encoding='utf-8')
            cells, kinds = entorno.crime_cells(path, '2025-03', bbox=(-58.46, -34.63, -58.43, -34.60))
            self.assertEqual(kinds, {'Robo': 3, 'Hurto': 1})
            self.assertEqual([c['hechos'] for c in cells], [4])
            robos, _ = entorno.crime_cells(path, '2025-03', kind='Robo', bbox=(-58.46, -34.63, -58.43, -34.60))
            self.assertEqual([c['hechos'] for c in robos], [3])


class GastronomiaOsmTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.poi, self.raw = build_sources(self.root)
        self.osm = self.root / 'raw' / 'osm-20261107'
        self.osm.mkdir(parents=True)
        lugares = {
            'restaurantes': [{'name': 'R1', 'lat': -34.615, 'lon': -58.435}, {'name': 'R2', 'lat': -34.615, 'lon': -58.445},
                             {'name': 'Afuera', 'lat': -34.615, 'lon': -58.30}, {'name': 'Sin punto'}],
            'cafes': [{'name': 'C1', 'latitude': -34.612, 'longitude': -58.432}],
            'bares': [],
        }
        for name, items in lugares.items():
            (self.osm / f'{name}.json').write_text(json.dumps(items), encoding='utf-8')
        self.write_runs(restaurantes=(4, 100))

    def tearDown(self):
        self.temp.cleanup()

    def write_runs(self, **runs):
        (self.osm / 'corridas.json').write_text(json.dumps(
            [{'nombre': n, 'puntos': p, 'max_items': m} for n, (p, m) in runs.items()]), encoding='utf-8')

    def test_counts_food_places_by_barrio_with_osm_source(self):
        self.assertEqual(entorno.latest_osm(self.root / 'raw'), self.osm)
        summary = entorno.convert(self.poi, self.raw, self.root / 'out', osm_dir=self.osm)
        self.assertEqual(summary['Almagro']['gastronomia'],
                         {'restaurantes': 1, 'cafes': 1, 'bares': 0, 'captura': '2026-11-07'})
        self.assertEqual(summary['Caballito']['gastronomia']['restaurantes'], 1)
        sources = {s['capa']: s for s in entorno.load(self.root / 'out')['fuentes']['fuentes']}
        self.assertIn('OpenStreetMap', sources['gastronomia']['licencia'])
        self.assertEqual(sources['gastronomia']['periodo'], 'Captura del 2026-11-07')

    def test_truncated_capture_is_not_used(self):
        self.write_runs(restaurantes=(100, 100))
        with self.assertWarns(UserWarning):
            summary = entorno.convert(self.poi, self.raw, self.root / 'out', osm_dir=self.osm)
        self.assertNotIn('gastronomia', summary['Almagro'])


if __name__ == '__main__':
    unittest.main()
