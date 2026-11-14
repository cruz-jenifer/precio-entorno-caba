"""Pruebas de «Dónde comer» con respuestas grabadas de Google Places: nunca llaman a Google."""

import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import httpx
from fastapi.testclient import TestClient

from precio_entorno import entorno
from precio_entorno.api import create_app
from precio_entorno.lugares import CAMPOS, URL, ErrorLugares, Lugares, enlace_seguro

try:
    from test_entorno import ALMAGRO, build_sources
except ImportError:  # Ejecutado como tests.test_lugares
    from tests.test_entorno import ALMAGRO, build_sources

GEOMETRIA = {'type': 'Polygon', 'coordinates': [[[ALMAGRO[0], ALMAGRO[1]], [ALMAGRO[2], ALMAGRO[1]],
                                                 [ALMAGRO[2], ALMAGRO[3]], [ALMAGRO[0], ALMAGRO[3]],
                                                 [ALMAGRO[0], ALMAGRO[1]]]]}
BBOX = (-58.441, -34.621, -58.429, -34.609)


def lugar(pid, nombre, nota=None, resenas=None, lon=-58.435, lat=-34.615, precio=None,
          uri='https://maps.google.com/?cid=1'):
    datos = {'id': pid, 'displayName': {'text': nombre, 'languageCode': 'es'},
             'location': {'latitude': lat, 'longitude': lon}, 'googleMapsUri': uri}
    if nota is not None:
        datos['rating'] = nota
    if resenas is not None:
        datos['userRatingCount'] = resenas
    if precio:
        datos['priceLevel'] = precio
    return datos


PAGINA_1 = {'places': [
    lugar('a', 'Cantina A', 4.8, 300),
    lugar('b', 'Afuera B', 4.9, 900, lon=-58.45),
    lugar('c', 'Bodegón C', 4.8, 1000),
    lugar('d', 'Sin nota D'),
], 'nextPageToken': 'siguiente'}
PAGINA_2 = {'places': [
    lugar('a', 'Cantina A', 4.8, 300),
    lugar('e', 'Pizzería E', 4.46, 50, precio='PRICE_LEVEL_MODERATE', uri='javascript:alert(1)'),
]}


class Google:
    """Imita httpx.post con respuestas grabadas y guarda cada pedido."""

    def __init__(self, *respuestas):
        self.respuestas = list(respuestas)
        self.pedidos = []

    def __call__(self, url, json, timeout, headers):
        self.pedidos.append({'url': url, 'json': json, 'headers': headers})
        estado, cuerpo = self.respuestas.pop(0)
        return httpx.Response(estado, json=cuerpo, request=httpx.Request('POST', url))


class LugaresTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.registro = Path(self.temp.name) / 'consumo.sqlite3'

    def tearDown(self):
        self.temp.cleanup()

    def test_query_is_restricted_and_results_are_filtered_and_sorted(self):
        google = Google((200, PAGINA_1), (200, PAGINA_2))
        resultado = Lugares('clave', 10, self.registro, google).buscar('Almagro', GEOMETRIA, BBOX)
        primero, segundo = google.pedidos
        self.assertEqual(primero['url'], URL)
        self.assertEqual(primero['headers']['X-Goog-Api-Key'], 'clave')
        self.assertEqual(primero['headers']['X-Goog-FieldMask'], CAMPOS)
        self.assertIn('places.rating', CAMPOS)
        self.assertEqual(primero['json']['includedType'], 'restaurant')
        self.assertEqual(primero['json']['locationRestriction']['rectangle'],
                         {'low': {'latitude': -34.621, 'longitude': -58.441},
                          'high': {'latitude': -34.609, 'longitude': -58.429}})
        self.assertNotIn('pageToken', primero['json'])
        self.assertEqual(segundo['json']['pageToken'], 'siguiente')
        self.assertEqual([x['id'] for x in resultado['lugares']], ['c', 'a', 'e'])
        pizzeria = resultado['lugares'][2]
        self.assertEqual((pizzeria['nota'], pizzeria['precio'], pizzeria['enlace']), (4.5, '$$', None))
        self.assertEqual((resultado['devueltos'], resultado['en_barrio'], resultado['llamadas'], resultado['completa']),
                         (5, 3, 2, True))
        self.assertEqual(Lugares('clave', 10, self.registro).consumo()['llamadas'], 2)

    def test_monthly_cap_stops_calls_and_resets_next_month(self):
        mes = ['2026-11']
        google = Google((200, PAGINA_1), (200, PAGINA_2))
        lugares = Lugares('clave', 1, self.registro, google, mes=lambda: mes[0])
        resultado = lugares.buscar('Almagro', GEOMETRIA, BBOX)
        self.assertEqual((len(google.pedidos), resultado['completa']), (1, False))
        with self.assertRaises(ErrorLugares) as error:
            lugares.buscar('Almagro', GEOMETRIA, BBOX)
        self.assertEqual(error.exception.motivo, 'cupo')
        self.assertEqual(len(google.pedidos), 1)
        mes[0] = '2026-12'
        lugares.buscar('Almagro', GEOMETRIA, BBOX)
        self.assertEqual(len(google.pedidos), 2)

    def test_google_error_is_reported_and_still_counted(self):
        lugares = Lugares('clave', 10, self.registro, Google((403, {'error': {'status': 'PERMISSION_DENIED'}})))
        with self.assertRaises(ErrorLugares) as error:
            lugares.buscar('Almagro', GEOMETRIA, BBOX, 'cafes')
        self.assertEqual(error.exception.motivo, 'google')
        self.assertEqual(lugares.consumo()['llamadas'], 1)

    def test_failed_second_page_keeps_first_page(self):
        google = Google((200, PAGINA_1), (500, {}))
        resultado = Lugares('clave', 10, self.registro, google).buscar('Almagro', GEOMETRIA, BBOX)
        self.assertEqual(([x['id'] for x in resultado['lugares']], resultado['completa']), (['c', 'a'], False))

    def test_configuration_comes_from_env_file(self):
        env = Path(self.temp.name) / '.env'
        env.write_text('GOOGLE_MAPS_API_KEY="abc"\nPRECIO_ENTORNO_LUGARES_TOPE_MES=10\n', encoding='utf-8')
        limpio = {k: v for k, v in os.environ.items()
                  if k not in ('GOOGLE_MAPS_API_KEY', 'PRECIO_ENTORNO_LUGARES_TOPE_MES')}
        with mock.patch.dict(os.environ, limpio, clear=True):
            lugares = Lugares.from_env(self.temp.name, env)
            self.assertEqual((lugares.enabled, lugares.clave, lugares.tope), (True, 'abc', 10))
            env.write_text('GOOGLE_MAPS_API_KEY=abc\nPRECIO_ENTORNO_LUGARES_TOPE_MES=mucho\n', encoding='utf-8')
            self.assertFalse(Lugares.from_env(self.temp.name, env).enabled)
            env.write_text('', encoding='utf-8')
            self.assertFalse(Lugares.from_env(self.temp.name, env).enabled)

    def test_only_https_google_links_are_kept(self):
        self.assertEqual(enlace_seguro('https://maps.google.com/?cid=1'), 'https://maps.google.com/?cid=1')
        self.assertEqual(enlace_seguro('https://www.google.com/maps/place/x'), 'https://www.google.com/maps/place/x')
        for malo in ('http://maps.google.com/?cid=1', 'https://google.com.evil.example/', 'javascript:alert(1)', None):
            self.assertIsNone(enlace_seguro(malo))


class LugaresApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        root = Path(cls.temp.name)
        poi, raw = build_sources(root)
        entorno.convert(poi, raw, root / 'entorno')
        cls.root = root

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def client(self, lugares):
        return TestClient(create_app(demo_path=self.root / 'demo.sqlite3', real_path=self.root / 'real.sqlite3',
                                     entorno_dir=self.root / 'entorno', raw_dir=self.root, lugares=lugares))

    def test_live_places_only_with_real_data_and_key(self):
        google = Google((200, PAGINA_1), (200, PAGINA_2))
        client = self.client(Lugares('clave', 10, self.root / 'consumo.sqlite3', google))
        self.assertTrue(client.get('/api/estado', params={'modo': 'real'}).json()['lugares'])
        self.assertFalse(client.get('/api/estado', params={'modo': 'demo'}).json()['lugares'])
        demo = client.get('/api/barrios/Almagro/lugares', params={'modo': 'demo'}).json()
        self.assertEqual((demo['disponible'], demo['motivo']), (False, 'demo'))
        self.assertEqual(google.pedidos, [])
        datos = client.get('/api/barrios/Almagro/lugares', params={'tipo': 'restaurantes'}).json()
        self.assertTrue(datos['disponible'])
        self.assertEqual(datos['fuente'], 'Google Maps')
        self.assertEqual([x['nombre'] for x in datos['lugares']], ['Bodegón C', 'Cantina A', 'Pizzería E'])
        self.assertEqual(client.get('/api/barrios/Almagro/lugares', params={'tipo': 'pizzas'}).status_code, 422)
        self.assertEqual(client.get('/api/barrios/Narnia/lugares').status_code, 404)

    def test_missing_key_or_cap_is_reported_without_calling(self):
        client = self.client(Lugares('', 10, self.root / 'consumo.sqlite3'))
        self.assertFalse(client.get('/api/estado', params={'modo': 'real'}).json()['lugares'])
        datos = client.get('/api/barrios/Almagro/lugares').json()
        self.assertEqual((datos['disponible'], datos['motivo']), (False, 'config'))
        agotado = self.client(Lugares('clave', 1, self.root / 'agotado.sqlite3',
                                      Google((200, {'places': []}))))
        agotado.get('/api/barrios/Almagro/lugares')
        datos = agotado.get('/api/barrios/Almagro/lugares').json()
        self.assertEqual((datos['disponible'], datos['motivo']), (False, 'cupo'))


if __name__ == '__main__':
    unittest.main()
