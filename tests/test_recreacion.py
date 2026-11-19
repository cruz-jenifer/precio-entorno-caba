"""Recreación: cines, teatros, museos y centros culturales de OpenStreetMap, con datos sintéticos."""

import json
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from precio_entorno import entorno, parecidos
from precio_entorno.api import create_app
from precio_entorno.store import Store

try:
    from test_entorno import build_sources
except ImportError:  # Ejecutado como tests.test_recreacion
    from tests.test_entorno import build_sources


def nodo(lon, lat, **tags):
    return {'type': 'node', 'lon': lon, 'lat': lat, 'tags': tags}


OVERPASS = {'elements': [
    nodo(-58.446, -34.6155, amenity='cinema', name='Cine Uno', **{'addr:street': 'Rivadavia', 'addr:housenumber': '5000'}),
    # El mismo cine cargado también como edificio: cuenta una sola vez.
    {'type': 'way', 'center': {'lon': -58.4462, 'lat': -34.6156}, 'tags': {'amenity': 'cinema', 'name': 'Cine Uno'}},
    nodo(-58.436, -34.612, amenity='theatre', name='Teatro Dos', phone='4444-5555'),
    {'type': 'way', 'center': {'lon': -58.434, 'lat': -34.613}, 'tags': {'tourism': 'museum', 'name': 'Museo Tres'}},
    nodo(-58.433, -34.614, amenity='planetarium', name='Planetario'),
    nodo(-58.437, -34.616, tourism='gallery', name='Galería Cuatro'),
    nodo(-58.444, -34.614, amenity='events_venue', name='Salón de Fiestas'),    # no es recreación cultural
    nodo(-58.443, -34.613, amenity='theatre'),                                  # sin nombre
    nodo(-58.20, -34.90, amenity='cinema', name='Cine de otra provincia'),
    {'type': 'relation', 'tags': {'amenity': 'theatre', 'name': 'Sin centro'}},
]}


class RecreacionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        root = Path(cls.temp.name)
        poi, raw = build_sources(root)
        cls.capture = root / 'raw-osm' / 'osm-recreacion-20261119' / 'recreacion.json'
        cls.capture.parent.mkdir(parents=True)
        cls.capture.write_text(json.dumps(OVERPASS), encoding='utf-8')
        cls.target = root / 'processed'
        cls.summary = entorno.convert(poi, raw, cls.target, recreation_path=cls.capture)
        store = Store(root / 'real.sqlite3')
        store.ingest([{'id': 'pin', 'neighborhood': 'Caballito', 'price': 100_000, 'covered_area': 45, 'rooms': 2,
                       'url': 'https://example.invalid/x', 'captured_at': '2026-11-19', 'currency': 'USD',
                       'total_area_m2': None, 'location_accuracy_m': None,
                       'latitude': -34.615, 'longitude': -58.445}], source='prueba')
        cls.client = TestClient(create_app(real_path=store.path, demo_path=root / 'demo.sqlite3',
                                           entorno_dir=cls.target))

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_latest_capture(self):
        self.assertEqual(entorno.latest_recreation(self.capture.parents[1]), self.capture)

    def test_counts_by_kind_and_barrio(self):
        self.assertEqual(self.summary['Caballito']['recreacion'], {'cine': 1, 'teatro': 0, 'museo': 0, 'cultural': 0})
        self.assertEqual(self.summary['Almagro']['recreacion'], {'cine': 0, 'teatro': 1, 'museo': 2, 'cultural': 1})

    def test_points_keep_name_kind_and_address_only(self):
        text = (self.target / 'puntos.json').read_text(encoding='utf-8')
        points = json.loads(text)['recreacion']
        self.assertEqual(len(points), 5)
        self.assertNotIn('4444', text)
        self.assertNotIn('Salón de Fiestas', text)
        cine = next(p for p in points if p['kind'] == 'cine')
        self.assertEqual(cine['tooltip'], 'Cine Uno · Cine · Rivadavia 5000')

    def test_map_layer_and_source(self):
        layer = self.client.get('/api/mapa/capas', params={'barrio': 'Almagro', 'capas': 'recreacion'}).json()['recreacion']
        self.assertTrue(layer['disponible'])
        kinds = {f['properties']['name']: f['properties']['kind'] for f in layer['features']}
        self.assertEqual(kinds['Teatro Dos'], 'teatro')
        self.assertEqual(kinds['Planetario'], 'museo')
        source = {s['capa']: s for s in self.client.get('/api/fuentes').json()['fuentes']}['recreacion']
        self.assertEqual(source['periodo'], 'Captura del 2026-11-19')
        self.assertIn('OpenStreetMap', source['licencia'])

    def test_listing_distance_to_nearest_place(self):
        aviso, = self.client.get('/api/barrios/Caballito/avisos',
                                 params={'modo': 'real', 'capas': 'recreacion'}).json()['avisos']
        cercano = aviso['cercania']['recreacion']
        self.assertEqual((cercano['nombre'], cercano['tipo']), ('Cine Uno', 'cine'))
        self.assertLess(cercano['m'], 150)

    def test_similar_barrios_use_density(self):
        valor = parecidos.valores(self.summary['Almagro'])['recreacion']
        self.assertAlmostEqual(valor, 4 / self.summary['Almagro']['area_ha'] * 100)
        self.assertIn('recreacion', parecidos.CAPAS)

    def test_without_capture_nothing_is_invented(self):
        with tempfile.TemporaryDirectory() as tmp:
            poi, raw = build_sources(Path(tmp))
            target = Path(tmp) / 'processed'
            summary = entorno.convert(poi, raw, target)
            self.assertNotIn('recreacion', summary['Caballito'])
            self.assertIsNone(parecidos.valores(summary['Caballito'])['recreacion'])
            layer = TestClient(create_app(entorno_dir=target)).get(
                '/api/mapa/capas', params={'barrio': 'Caballito', 'capas': 'recreacion'}).json()['recreacion']
            self.assertFalse(layer['disponible'])


if __name__ == '__main__':
    unittest.main()
