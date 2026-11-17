"""Ciclovías, Ecobici y bibliotecas (etapa B del explorador de necesidades), con datos sintéticos."""

import json
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from precio_entorno import entorno
from precio_entorno.api import create_app
from precio_entorno.store import Store

try:
    from test_entorno import build_sources, collection, point, write
except ImportError:  # Ejecutado como tests.test_movilidad
    from tests.test_entorno import build_sources, collection, point, write

ECOBICI = ('﻿id,numero_de_estacion,nombre,direccion,barrio,comuna,emplazamiento,latitud,longitud\n'
           '1,1,PRIMERA JUNTA,Av. Rivadavia 5000,,,,-34.6155,-58.4452\n'
           '2,2,AFUERA,Otra provincia,,,,-34.90,-58.20\n'
           '3,3,SIN COORDENADAS,Calle,,,,,\n')


def add_sources(raw):
    files = {name: file for name, (file, *_) in entorno.MOVILIDAD.items()}
    write(raw / files['ciclovias'], collection(
        ({'nombre': 'RIVADAVIA', 'tipo': 'Ciclovías'},
         {'type': 'LineString', 'coordinates': [[-58.449, -34.6152], [-58.441, -34.6152]]}),
        ({'nombre': 'MEDRANO', 'tipo': 'Ciclovías mano única'},
         {'type': 'LineString', 'coordinates': [[-58.435, -34.619], [-58.435, -34.611]]}),
        ({'nombre': 'ROTA', 'tipo': 'Ciclovías'}, {'type': 'LineString', 'coordinates': [[-58.44, -34.61]]})))
    (raw / files['ecobici']).write_text(ECOBICI, encoding='utf-8')
    write(raw / files['bibliotecas'], collection(
        ({'nombre': 'Biblioteca Uno', 'tipo': 'Biblioteca Popular', 'dirreccion': 'Calle 1', 'telefono': '4444-5555',
          'email': 'privado@example.invalid'}, point(-58.436, -34.612))))


class MovilidadTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        root = Path(cls.temp.name)
        poi, raw = build_sources(root)
        add_sources(raw)
        cls.target = root / 'processed'
        cls.summary = entorno.convert(poi, raw, cls.target)
        store = Store(root / 'real.sqlite3')
        base = {'neighborhood': 'Caballito', 'price': 100_000, 'covered_area': 45, 'rooms': 2,
                'url': 'https://example.invalid/x', 'captured_at': '2026-11-17', 'currency': 'USD',
                'total_area_m2': None, 'location_accuracy_m': None}
        store.ingest([dict(base, id='pin', latitude=-34.615, longitude=-58.445)], source='prueba')
        cls.client = TestClient(create_app(real_path=store.path, demo_path=root / 'demo.sqlite3', entorno_dir=cls.target))

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_counts_per_barrio(self):
        caballito, almagro = self.summary['Caballito'], self.summary['Almagro']
        self.assertEqual((caballito['ecobici'], almagro['ecobici']), (1, 0))   # la de otra provincia se descarta
        self.assertEqual((caballito['bibliotecas'], almagro['bibliotecas']), (0, 1))
        self.assertAlmostEqual(caballito['ciclovias_km'], 0.7, delta=0.1)      # ~730 m de Rivadavia
        self.assertAlmostEqual(almagro['ciclovias_km'], 0.9, delta=0.1)        # ~890 m de Medrano

    def test_lanes_keep_only_what_the_source_says(self):
        lanes = json.loads((self.target / 'ciclovias.geojson').read_text(encoding='utf-8'))['features']
        self.assertEqual(len(lanes), 2)                                       # el tramo de un solo punto no entra
        self.assertEqual({f['properties']['kind'] for f in lanes}, {'Doble mano', 'Mano única'})

    def test_libraries_drop_contact_data(self):
        text = (self.target / 'puntos.json').read_text(encoding='utf-8')
        self.assertNotIn('4444', text)
        self.assertNotIn('privado@', text)
        self.assertIn('Biblioteca Uno · Biblioteca Popular · Calle 1', text)

    def test_map_layers_and_sources(self):
        params = [('barrio', 'Caballito'), ('capas', 'ciclovias'), ('capas', 'ecobici'), ('capas', 'bibliotecas')]
        layers = self.client.get('/api/mapa/capas', params=params).json()
        self.assertTrue(all(layers[k]['disponible'] for k in ('ciclovias', 'ecobici', 'bibliotecas')))
        self.assertEqual(layers['ecobici']['features'][0]['properties']['name'], 'Primera Junta')
        sources = {s['capa']: s for s in self.client.get('/api/fuentes').json()['fuentes']}
        self.assertIn('no informa si cada estación está operativa', sources['ecobici']['periodo'])
        self.assertTrue(sources['ciclovias']['url'].startswith(entorno.CDN))

    def test_listing_distances(self):
        params = [('modo', 'real'), ('capas', 'ciclovias'), ('capas', 'ecobici'), ('capas', 'bibliotecas')]
        aviso, = self.client.get('/api/barrios/Caballito/avisos', params=params).json()['avisos']
        cercania = aviso['cercania']
        self.assertEqual(cercania['ciclovia']['m'], 20)                       # 0,0002° al norte de la ciclovía
        self.assertEqual(cercania['ecobici']['m'], 60)
        self.assertGreater(cercania['biblioteca']['m'], 800)

    def test_without_the_files_nothing_is_invented(self):
        with tempfile.TemporaryDirectory() as tmp:
            poi, raw = build_sources(Path(tmp))
            target = Path(tmp) / 'processed'
            summary = entorno.convert(poi, raw, target)
            self.assertFalse({'ecobici', 'bibliotecas', 'ciclovias_km'} & set(summary['Caballito']))
            self.assertFalse((target / 'ciclovias.geojson').exists())
            client = TestClient(create_app(entorno_dir=target))
            layers = client.get('/api/mapa/capas', params=[('barrio', 'Caballito'), ('capas', 'ciclovias'),
                                                           ('capas', 'ecobici')]).json()
            self.assertFalse(layers['ciclovias']['disponible'] or layers['ecobici']['disponible'])


if __name__ == '__main__':
    unittest.main()
