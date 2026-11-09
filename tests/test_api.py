"""Pruebas de la API de la interfaz web con bases temporales y capas sintéticas."""

import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from precio_entorno import entorno
from precio_entorno.api import create_app
from precio_entorno.importing import import_crimes
from precio_entorno.store import Store

try:
    from test_entorno import build_sources
except ImportError:  # Ejecutado como tests.test_api
    from tests.test_entorno import build_sources

CRIMES = (
    '"id-mapa","fecha","franja","tipo","barrio","latitud","longitud","cantidad"\n'
    '1,"2025-03-02",14,"Robo","CABALLITO","-34.6150","-58.4450",1\n'
    '2,"2025-03-05",9,"Hurto","CABALLITO","-34.6152","-58.4452",2\n'
    '3,"2025-04-01",20,"Robo","ALMAGRO","-34.6150","-58.4350",1\n'
).encode('utf-8')


class ApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        root = Path(cls.temp.name)
        poi, raw = build_sources(root)
        entorno.convert(poi, raw, root / 'entorno')
        cls.raw = root / 'raw'
        cls.raw.mkdir()
        cls.real = root / 'real.sqlite3'
        import_crimes(Store(cls.real), CRIMES, 'delitos.csv')
        (cls.raw / 'delitos.csv').write_bytes(CRIMES)
        cls.client = TestClient(create_app(demo_path=root / 'demo.sqlite3', real_path=cls.real,
                                           entorno_dir=root / 'entorno', raw_dir=cls.raw))

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def get(self, path, **params):
        response = self.client.get(path, params=params)
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()

    def test_demo_neighborhoods_count_matches_and_attach_environment(self):
        state = self.get('/api/estado')
        self.assertEqual((state['avisos'], state['delitos'], state['capas']), (6, None, True))
        rows = {r['barrio']: r for r in self.get('/api/barrios')['barrios']}
        self.assertEqual(len(rows), 48)
        self.assertEqual((rows['Almagro']['coincidencias'], rows['Almagro']['mediana']), (2, 100_000))
        self.assertEqual(rows['Caballito']['coincidencias'], 1)
        self.assertEqual(rows['Caballito']['entorno']['subte_lineas'], ['A'])
        self.assertIsNone(rows['Palermo']['entorno'])
        first = self.get('/api/barrios')['barrios'][0]
        self.assertEqual(first['barrio'], 'Almagro')

    def test_demo_listings_hide_links_and_follow_filters(self):
        listings = self.get('/api/barrios/Almagro/avisos')['avisos']
        self.assertEqual([a['precio'] for a in listings], [98_000, 102_000])
        self.assertTrue(all(a['enlace'] is None for a in listings))
        self.assertEqual(self.get('/api/barrios/Almagro/avisos', presupuesto=99_000)['avisos'][0]['id'], 'demo-003')

    def test_rooms_or_more_widens_matches(self):
        exact = sum(r['coincidencias'] for r in self.get('/api/barrios', ambientes=1, presupuesto=10**9)['barrios'])
        rows = self.get('/api/barrios', ambientes=1, presupuesto=10**9, superficie=1, ambientes_o_mas='true')['barrios']
        self.assertEqual(sum(r['coincidencias'] for r in rows), sum(r['avisos'] for r in rows))
        self.assertGreaterEqual(sum(r['coincidencias'] for r in rows), exact)

    def test_rentals_compare_in_the_chosen_currency(self):
        self.assertEqual(self.get('/api/estado', operacion='alquiler')['monedas'], ['ARS', 'USD'])
        rows = self.get('/api/barrios', operacion='alquiler', presupuesto=800_000, moneda='ARS')['barrios']
        self.assertGreater(sum(r['coincidencias'] for r in rows), 0)
        self.assertEqual(self.client.get('/api/barrios', params={'moneda': 'ARS'}).status_code, 422)

    def test_search_is_saved_once_and_validated(self):
        body = {'barrio': 'Villa Crespo', 'presupuesto': 120_000, 'superficie': 40, 'ambientes': 2}
        self.assertTrue(self.client.post('/api/busquedas', json=body).json()['creada'])
        self.assertFalse(self.client.post('/api/busquedas', json=body).json()['creada'])
        saved = self.get('/api/busquedas')['busquedas']
        self.assertIn('Villa Crespo', [s['barrio'] for s in saved])
        self.assertEqual(self.client.post('/api/busquedas', json=dict(body, barrio='Narnia')).status_code, 404)
        self.assertEqual(self.client.post('/api/busquedas', json=dict(body, ambientes=0)).status_code, 422)
        self.assertEqual(self.client.post('/api/busquedas', params={'operacion': 'alquiler'},
                                          json=dict(body, moneda='EUR')).status_code, 422)

    def test_email_subscription_goes_only_to_make(self):
        sent = []
        root = Path(self.temp.name)
        with tempfile.TemporaryDirectory() as temp:
            real = Path(temp) / 'real.sqlite3'
            client = TestClient(create_app(demo_path=root / 'demo.sqlite3', real_path=real,
                                           entorno_dir=root / 'entorno', raw_dir=self.raw,
                                           subscriptions_url='https://hook.us2.make.com/x',
                                           post=lambda url, body: sent.append(body) or 200))
            body = {'barrio': 'Boedo', 'presupuesto': 100_000, 'superficie': 35, 'ambientes': 2,
                    'email': 'persona@example.com', 'consentimiento': True}
            result = client.post('/api/busquedas', params={'modo': 'real'}, json=body).json()
            self.assertEqual(result, {'creada': True, 'correo': {'enviado': True}})
            alta, = sent
            self.assertEqual((alta['tipo'], alta['email']), ('alta', 'persona@example.com'))
            self.assertEqual({k: v for k, v in alta['busqueda'].items() if k != 'id'},
                             {'operacion': 'venta', 'barrio': 'Boedo', 'presupuesto': 100_000, 'moneda': 'USD',
                              'superficie': 35, 'ambientes': 2, 'ambientesOMas': False})
            self.assertGreaterEqual(len(alta['busqueda']['id']), 12)  # Aleatorio: sirve de clave para la baja.
            self.assertEqual(alta['descripcion'], 'Boedo · hasta USD 100.000 · 35 m² o más · 2 ambientes')
            self.assertNotIn(b'persona@example.com', real.read_bytes())  # El mail no queda en la base local.
            # Otra persona con los mismos filtros también se suscribe, con otro ID.
            again = client.post('/api/busquedas', params={'modo': 'real'}, json=dict(body, email='otra@example.com'))
            self.assertEqual(again.json(), {'creada': False, 'correo': {'enviado': True}})
            self.assertNotEqual(sent[1]['busqueda']['id'], alta['busqueda']['id'])
            bad = {'demo': ({'modo': 'demo'}, body), 'mail': ({'modo': 'real'}, dict(body, email='persona@')),
                   'consentimiento': ({'modo': 'real'}, dict(body, consentimiento=False))}
            for name, (params, payload) in bad.items():
                with self.subTest(name):
                    self.assertEqual(client.post('/api/busquedas', params=params, json=payload).status_code, 422)
            self.assertEqual(len(sent), 2)
            unset = TestClient(create_app(demo_path=root / 'demo.sqlite3', real_path=real, entorno_dir=root / 'entorno',
                                          raw_dir=self.raw, subscriptions_url=None))
            result = unset.post('/api/busquedas', params={'modo': 'real'}, json=body).json()
            self.assertFalse(result['correo']['enviado'])

    def test_map_layers_are_cut_to_the_neighborhood(self):
        shapes = self.get('/api/mapa/barrios')
        self.assertEqual({f['properties']['barrio'] for f in shapes['features']}, {'Caballito', 'Almagro'})
        layers = self.client.get('/api/mapa/capas', params=[('barrio', 'Caballito'), ('capas', 'subte'),
                                                             ('capas', 'ruido'), ('capas', 'salud')]).json()
        self.assertEqual(set(layers), {'subte', 'ruido', 'salud'})
        self.assertIn('Primera Junta', [f['properties']['name'] for f in layers['subte']['features']])
        cell = layers['ruido']['features'][0]
        self.assertEqual(cell['geometry']['type'], 'Polygon')
        self.assertEqual(cell['properties']['tipico'], 70)
        kinds = {f['properties']['kind'] for f in layers['salud']['features']}
        self.assertEqual(kinds, {'cesac', 'hospital'})
        bad = self.client.get('/api/mapa/capas', params={'barrio': 'Caballito', 'capas': 'bares'})
        self.assertEqual(bad.status_code, 422)

    def test_crimes_are_mapped_only_with_real_data_and_matching_file(self):
        demo = self.get('/api/delitos', barrio='Caballito', modo='demo')
        self.assertFalse(demo['disponible'])
        real = self.get('/api/delitos', barrio='Caballito', periodo='2025-03')
        self.assertTrue(real['disponible'])
        self.assertEqual((real['periodo'], real['maximo'], real['tipos']), ('2025-03', 3, {'Robo': 1, 'Hurto': 2}))
        self.assertEqual(real['periodos'], ['2025-04', '2025-03'])
        robos = self.get('/api/delitos', barrio='Caballito', periodo='2025-03', tipo='Robo')
        self.assertEqual(robos['maximo'], 1)

    def test_crimes_refuse_a_file_that_differs_from_the_loaded_one(self):
        with tempfile.TemporaryDirectory() as temp:
            other_raw = Path(temp)
            (other_raw / 'delitos.csv').write_bytes(CRIMES + b'4,"2025-03-09",1,"Robo","CABALLITO","-34.6","-58.44",1\n')
            app = create_app(real_path=self.real, entorno_dir=Path(self.temp.name) / 'entorno', raw_dir=other_raw,
                             demo_path=Path(temp) / 'demo.sqlite3')
            data = TestClient(app).get('/api/delitos', params={'barrio': 'Caballito'}).json()
            self.assertFalse(data['disponible'])
            self.assertIn('no es el mismo archivo', data['motivo'])

    def test_sources_and_page_are_served(self):
        self.assertEqual(len(self.get('/api/fuentes')['fuentes']), len(entorno.SOURCES))
        page = self.client.get('/')
        self.assertEqual(page.status_code, 200)
        self.assertIn('Precio y Entorno CABA', page.text)


if __name__ == '__main__':
    unittest.main()
