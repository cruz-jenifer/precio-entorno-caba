"""Pruebas del envío de alertas a Make, sin red."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from precio_entorno import inmobiliarias, make_webhook
from precio_entorno.actualizar import update
from precio_entorno.inmobiliarias import PoliteClient
from precio_entorno.store import Store
from test_actualizar import fake_site


class WebhookUrlTests(unittest.TestCase):
    def test_only_https_make_domains_are_accepted(self):
        with tempfile.TemporaryDirectory() as temp, patch.dict('os.environ', {}, clear=True):
            env = Path(temp) / '.env'
            self.assertIsNone(make_webhook.webhook_url(env))
            env.write_text('apify_api_x\nMAKE_WEBHOOK_URL="https://hook.us1.make.com/abc123"\n', encoding='utf-8')
            self.assertEqual(make_webhook.webhook_url(env), 'https://hook.us1.make.com/abc123')
            for bad in ('http://hook.us1.make.com/abc', 'https://example.com/hook', 'https://make.com.example.org/x'):
                with patch.dict('os.environ', {'MAKE_WEBHOOK_URL': bad}):
                    with self.assertRaisesRegex(ValueError, 'dominio de Make'):
                        make_webhook.webhook_url(env)


class SendTests(unittest.TestCase):
    def test_retries_once_and_reports_without_raising(self):
        calls = []

        def flaky(url, body):
            calls.append(body)
            if len(calls) == 1:
                raise TimeoutError
            return 200
        result = make_webhook.send('https://hook.eu1.make.com/x', {'a': 1}, post=flaky, sleep=lambda s: None)
        self.assertEqual(result, {'enviado': True, 'http': 200, 'intentos': 2})
        failed = make_webhook.send('https://hook.eu1.make.com/x', {}, post=lambda u, b: 500, sleep=lambda s: None)
        self.assertEqual((failed['enviado'], failed['error']), (False, 'HTTP 500'))

    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.dir = Path(temp.name)
        self.store = Store(self.dir / 'real.sqlite3')
        self.store.save_search('Caballito', 110000, 40, 2)
        self.client = PoliteClient(fetch=lambda url, params=None: (200, ''), pause_s=0, sleep=lambda s: None)
        self.sent = []

    def run_update(self, name, site, history=None):
        with patch.dict(inmobiliarias.SITES, {'ficticia': site}, clear=True):
            return update(self.store, self.dir / name, ['ficticia'], 10, client=self.client, echo=lambda line: None,
                          webhook='https://hook.us1.make.com/x', history=history,
                          post=lambda url, body: self.sent.append(body) or 200)

    def test_every_run_is_sent_and_alerts_only_once(self):
        first = self.run_update('c1', fake_site(['1', '2']))
        self.assertTrue(first['make']['enviado'])
        body, = self.sent
        self.assertEqual((body['tipo'], body['estado'], body['cantidad'], body['nuevos']), ('corrida', 'ok', 2, 2))
        self.assertEqual(set(body['alertas'][0]), set(make_webhook.ALERT_FIELDS))
        self.assertEqual((body['alertas'][0]['aviso'], body['alertas'][0]['superficie_m2']), ('ficticia:1', 45))
        self.assertEqual(body['sitios'], 'ficticia: completo')
        repeat = self.run_update('c2', fake_site(['1']))
        self.assertTrue(repeat['make']['enviado'])  # La corrida sin novedades también llega a Make...
        self.assertEqual((self.sent[1]['cantidad'], self.sent[1]['alertas'], self.sent[1]['busquedas']), (0, [], []))
        self.assertEqual(self.sent[1]['repetidos'], 1)  # ...y no repite alertas.

    def test_alerts_are_grouped_in_one_summary_per_search(self):
        self.store.save_search('Caballito', 110000, 30, 2)
        self.run_update('c1', fake_site(['1', '2']))
        body, = self.sent
        self.assertEqual(body['cantidad'], 4)  # Dos avisos × dos búsquedas: una fila por alerta.
        self.assertEqual([(g['busqueda'], g['cantidad']) for g in body['busquedas']], [(1, 2), (2, 2)])
        summary = body['busquedas'][0]
        self.assertEqual(summary['descripcion'], 'Caballito · hasta USD 110.000 · 40 m² o más · 2 ambientes')
        self.assertEqual(summary['asunto'], '2 avisos nuevos · Caballito · hasta USD 110.000 · 40 m² o más · 2 ambientes')
        self.assertEqual(summary['avisos'], ['ficticia:1', 'ficticia:2'])
        self.assertIn('Caballito · USD 100.000 · 45 m² · 2 amb.', summary['texto'])
        self.assertIn('<a href="https://example.invalid/1">Ver aviso</a>', summary['html'])

    def test_failed_run_is_reported_recorded_and_sent(self):
        def broken(client, captured_at, max_listings, known=frozenset()):
            raise KeyError('precio')
        history = self.dir / 'actualizaciones.jsonl'
        with patch('precio_entorno.actualizar.import_listings', side_effect=OSError('disco lleno')):
            entry = self.run_update('c1', fake_site(['1']), history=history)
        self.assertEqual((entry['estado'], entry['error']), ('error', 'OSError: disco lleno'))
        body, = self.sent
        self.assertEqual((body['estado'], body['error'], body['cantidad'], body['nuevos']),
                         ('error', 'OSError: disco lleno', 0, None))
        self.assertEqual(json.loads(history.read_text(encoding='utf-8'))['estado'], 'error')
        partial = self.run_update('c2', broken)  # Un sitio con error no frena la corrida: queda parcial.
        self.assertEqual(partial['estado'], 'parcial')
        self.assertEqual(self.sent[1]['sitios'], 'ficticia: error: \'precio\'')


class GroupTests(unittest.TestCase):
    def test_listing_text_is_escaped_and_only_web_links_are_kept(self):
        alert = {'busqueda': 9, 'aviso': 'x:1', 'barrio': '<b>Boedo</b>', 'precio': 900000, 'moneda': 'ARS',
                 'expensas_ars': 120000, 'superficie_m2': 38.5, 'ambientes': 2, 'url': 'javascript:alert(1)'}
        summary, = make_webhook.group([alert])
        self.assertEqual(summary['descripcion'], 'Búsqueda 9')  # Sin la búsqueda, solo el número.
        self.assertIn('&lt;b&gt;Boedo&lt;/b&gt; · ARS 900.000 · expensas ARS 120.000 · 38.5 m²', summary['html'])
        self.assertNotIn('javascript', summary['html'])
        self.assertEqual(summary['asunto'], '1 aviso nuevo · Búsqueda 9')
