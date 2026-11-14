"""Calidad de la ubicación publicada de los avisos y su punto en la API del mapa."""

import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from precio_entorno import entorno
from precio_entorno.api import create_app
from precio_entorno.store import Store
from precio_entorno.ubicacion import APROXIMADA, PUBLICADA, quality

try:
    from test_entorno import CABALLITO, build_sources
except ImportError:  # Ejecutado como tests.test_ubicacion
    from tests.test_entorno import CABALLITO, build_sources

WEST, SOUTH, EAST, NORTH = CABALLITO
SQUARE = {'type': 'Polygon', 'coordinates': [[[WEST, SOUTH], [EAST, SOUTH], [EAST, NORTH], [WEST, NORTH], [WEST, SOUTH]]]}


def north_of(meters):
    """Latitud a `meters` al norte del límite norte del barrio de prueba."""
    return NORTH + meters / 111_320


class QualityTests(unittest.TestCase):
    def test_points_are_classified_by_distance_to_their_neighborhood(self):
        self.assertEqual(quality(-58.445, -34.615, SQUARE), PUBLICADA)
        self.assertEqual(quality(-58.445, north_of(100), SQUARE), PUBLICADA)
        self.assertEqual(quality(-58.445, north_of(300), SQUARE), APROXIMADA)
        self.assertIsNone(quality(-58.445, north_of(2000), SQUARE))

    def test_missing_coordinates_or_geometry_give_no_point(self):
        self.assertIsNone(quality(None, -34.615, SQUARE))
        self.assertIsNone(quality(-58.445, None, SQUARE))
        self.assertIsNone(quality(-58.445, -34.615, None))

    def test_multipolygons_and_holes_are_respected(self):
        hole = [[-58.447, -34.617], [-58.443, -34.617], [-58.443, -34.613], [-58.447, -34.613], [-58.447, -34.617]]
        with_hole = {'type': 'MultiPolygon', 'coordinates': [[SQUARE['coordinates'][0], hole]]}
        # El centro del hueco queda a unos 220 m del borde del hueco: fuera del barrio, pero cerca.
        self.assertEqual(quality(-58.445, -34.615, with_hole), APROXIMADA)
        self.assertEqual(quality(-58.4495, -34.6195, with_hole), PUBLICADA)


class ApiPointTests(unittest.TestCase):
    def test_listings_carry_a_map_point_only_when_it_fits_their_neighborhood(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            poi, raw = build_sources(root)
            entorno.convert(poi, raw, root / 'entorno')
            store = Store(root / 'real.sqlite3')
            base = {'neighborhood': 'Caballito', 'price': 100_000, 'covered_area': 45, 'rooms': 2,
                    'captured_at': '2026-11-09', 'currency': 'USD', 'total_area_m2': None,
                    'location_accuracy_m': None, 'longitude': -58.445}
            listings = [dict(base, id='adentro', latitude=-34.615), dict(base, id='borde', latitude=north_of(100)),
                        dict(base, id='cerca', latitude=north_of(300)), dict(base, id='lejos', latitude=north_of(2000)),
                        dict(base, id='sin-coordenadas', latitude=None, longitude=None)]
            store.ingest([dict(l, url=f"https://example.invalid/{l['id']}") for l in listings], source='prueba')
            client = TestClient(create_app(real_path=store.path, demo_path=root / 'demo.sqlite3',
                                           raw_dir=root / 'raw', entorno_dir=root / 'entorno'))
            found = {a['id']: a for a in client.get('/api/barrios/Caballito/avisos', params={'modo': 'real'}).json()['avisos']}
            self.assertEqual({k: a['ubicacion'] for k, a in found.items()},
                             {'adentro': PUBLICADA, 'borde': PUBLICADA, 'cerca': APROXIMADA, 'lejos': None,
                              'sin-coordenadas': None})
            self.assertEqual((found['adentro']['lat'], found['adentro']['lon']), (-34.615, -58.445))
            # Sin un punto coherente no se envían coordenadas, y el cruce con delitos sigue exigiendo precisión.
            self.assertEqual((found['lejos']['lat'], found['lejos']['lon']), (None, None))
            self.assertFalse(any(a['pin_utilizable'] for a in found.values()))


if __name__ == '__main__':
    unittest.main()
