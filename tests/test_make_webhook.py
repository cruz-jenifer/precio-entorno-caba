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

    def test_update_sends_only_new_alerts_and_only_listing_fields(self):
        sent = []
        with tempfile.TemporaryDirectory() as temp:
            d = Path(temp)
            store = Store(d / 'real.sqlite3')
            store.save_search('Caballito', 110000, 40, 2)
            client = PoliteClient(fetch=lambda url, params=None: (200, ''), pause_s=0, sleep=lambda s: None)

            def run(name, ids):
                with patch.dict(inmobiliarias.SITES, {'ficticia': fake_site(ids)}, clear=True):
                    return update(store, d / name, ['ficticia'], 10, client=client, echo=lambda line: None,
                                  webhook='https://hook.us1.make.com/x',
                                  post=lambda url, body: sent.append(body) or 200)
            first = run('c1', ['1'])
            self.assertTrue(first['make']['enviado'])
            body, = sent
            self.assertEqual(body['cantidad'], 1)
            self.assertEqual(set(body['alertas'][0]), set(make_webhook.ALERT_FIELDS))
            self.assertEqual((body['alertas'][0]['aviso'], body['alertas'][0]['superficie_m2']), ('ficticia:1', 45))
            repeat = run('c2', ['1'])
            self.assertNotIn('make', repeat)  # Sin alertas nuevas no se envía nada.
            self.assertEqual(len(sent), 1)
            self.assertNotIn('example.invalid"', json.dumps(body).replace('https://example.invalid', ''))
