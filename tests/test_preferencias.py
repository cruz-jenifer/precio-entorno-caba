import sqlite3
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from pathlib import Path
from threading import Event

import httpx
from fastapi.testclient import TestClient

from precio_entorno.api import create_app
from precio_entorno.actor_alertas import parse_searches
from precio_entorno.make_webhook import subscription
from precio_entorno.preferencias import ErrorPreferencias, Interprete, RESERVA, reglas
from precio_entorno.store import Store


class PreferenciasTests(unittest.TestCase):
    def test_reglas_and_ambiguity(self):
        parsed = reglas('Comprar en Almagro, hasta 120 mil dólares, dos ambientes o más')
        self.assertEqual({c.clave: c.valor for c in parsed.campos}, {
            'operacion': 'venta', 'barrio': 'Almagro', 'moneda': 'USD',
            'presupuesto': '120000', 'ambientes': '2', 'ambientes_o_mas': 'true'})
        parsed = reglas('Hasta 120 mil, 50 metros totales, necesito balcón')
        self.assertEqual({d.campo for d in parsed.dudas}, {'moneda', 'superficie'})
        self.assertTrue(parsed.no_soportadas[0].obligatoria)

    def test_disabled_endpoint(self):
        def post(*args, **kwargs):
            self.fail('Hubo una llamada externa')
        client = TestClient(create_app(interprete=Interprete(secret='fake', post=post)))
        self.assertEqual(client.post('/api/preferencias/interpretar', json={'texto': 'Almagro'}).status_code, 503)
        self.assertEqual(client.post('/api/preferencias/interpretar', json={'texto': 'x'*2001}).status_code, 422)

    def test_privacy_and_reservation(self):
        with tempfile.TemporaryDirectory() as tmp:
            ledger = Path(tmp) / 'test.sqlite'
            entered, release = Event(), Event()

            def post(url, *, json, **kwargs):
                self.assertFalse(json['store'])
                self.assertNotIn('@', json['input'])
                self.assertNotIn('5555-1212', json['input'])
                entered.set()
                self.assertTrue(release.wait(5))
                raise httpx.ReadTimeout('fake timeout')

            service = Interprete(True, 'fake-secret', RESERVA, ledger, post)
            with self.assertRaisesRegex(ErrorPreferencias, 'credencial'):
                service.interpretar('Almagro API key: abc123')
            with ThreadPoolExecutor(max_workers=1) as pool:
                first = pool.submit(service.interpretar, 'Almagro, yo@example.invalid 5555-1212')
                try:
                    self.assertTrue(entered.wait(5))
                    another = Interprete(True, 'fake-secret', RESERVA, ledger, post)
                    with self.assertRaises(ErrorPreferencias) as over:
                        another.interpretar('Caballito')
                    self.assertEqual(over.exception.status, 429)
                finally:
                    release.set()
                with self.assertRaises(ErrorPreferencias) as timeout:
                    first.result()
                self.assertEqual(timeout.exception.status, 502)
            with self.assertRaisesRegex(ErrorPreferencias, 'presupuesto'):
                service.interpretar('Caballito')

    def test_invalid_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            def post(*args, **kwargs):
                return httpx.Response(200, request=httpx.Request('POST', 'https://example.invalid'),
                    json={'status': 'completed', 'usage': {'input_tokens': 100, 'output_tokens': 50},
                          'output': [{'type': 'message', 'content': [{'type': 'output_text', 'text':
                              '{"campos":[{"clave":"barrio","valor":"Palermo","evidencia":"inventada"}],'
                              '"dudas":[],"no_soportadas":[]}'}]}]})
            service = Interprete(True, 'fake-secret', RESERVA, Path(tmp) / 'test.sqlite', post)
            with self.assertRaisesRegex(ErrorPreferencias, 'No pudimos'):
                service.interpretar('Almagro')

    def test_minimum_reaches_actor_through_make_contract(self):
        payload = subscription('x', 'venta', {'barrio': 'Almagro', 'presupuesto': 120000,
            'superficie': 40, 'ambientes': 2, 'moneda': 'USD', 'ambientes_o_mas': True},
            'example@example.invalid', '2026-11-12')
        self.assertTrue(parse_searches([payload['busqueda']])[0]['or_more'])
        self.assertIn('2 ambientes o más', payload['descripcion'])

    def test_legacy_ids_and_alerts_survive_and_minimum_alerts_match(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'legacy.sqlite'
            with closing(sqlite3.connect(path)) as db:
                db.executescript("""
                    CREATE TABLE searches (id INTEGER PRIMARY KEY, neighborhood TEXT, budget INTEGER,
                        min_area INTEGER, rooms INTEGER, UNIQUE(neighborhood,budget,min_area,rooms));
                    CREATE TABLE alerts (search_id INTEGER REFERENCES searches(id),
                        listing_id TEXT REFERENCES listings(id), PRIMARY KEY(search_id,listing_id));
                    INSERT INTO searches VALUES (7, 'Almagro', 120000, 35, 2);
                    INSERT INTO alerts VALUES (7, 'anterior');
                """)
            store = Store(path)
            store.seed([dict(id='anterior', neighborhood='Almagro', price=110000, covered_area=50, rooms=2)])
            self.assertEqual(store.searches()[0]['id'], 7)
            self.assertEqual(store.searches()[0]['rooms_or_more'], 0)
            self.assertTrue(store.save_search('Almagro', 120000, 35, 2, 'USD', True))
            self.assertFalse(store.save_search('Almagro', 120000, 35, 2, 'USD', True))
            store.ingest([dict(id='nuevo', neighborhood='Almagro', price=110000, covered_area=50, rooms=3)])
            self.assertEqual([(a['search_id'], a['id']) for a in Store(path).alerts()],
                             [(7, 'anterior'), (8, 'nuevo')])
