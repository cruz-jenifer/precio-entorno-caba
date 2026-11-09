import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from precio_entorno.apify_client import ApifyClient
from precio_entorno.importing import import_listings
from precio_entorno.run_pilot import ACTOR, ACTOR_PATH, SOURCE, apify_token, main, pilot_plan, run_pilot
from precio_entorno.store import Store

FIXTURE = Path(__file__).resolve().parents[1] / 'data' / 'fixtures' / 'apify_zonaprop_prueba.json'


class PilotTests(unittest.TestCase):
    def test_dry_run_needs_no_token_or_network(self):
        with (patch('sys.argv', ['pilot', '--dry-run']),
              patch('precio_entorno.run_pilot.apify_token', side_effect=AssertionError),
              patch.object(ApifyClient, 'request', side_effect=AssertionError),
              redirect_stdout(io.StringIO()) as output):
            main()
        plan = json.loads(output.getvalue())
        self.assertEqual(plan['actor'], ACTOR)
        self.assertEqual([s['ubicacion'] for s in plan['busquedas']], ['caballito', 'almagro'])
        self.assertEqual(plan['candidatos_por_barrio'], 25)
        self.assertAlmostEqual(2 * plan['tope_busqueda_usd'] + 50 * plan['tope_detalle_usd'], 1)
        self.assertEqual(plan['detalle']['mode'], 'scrape-single')
        self.assertFalse(plan['detalle']['enableProxies'])

    def test_mocked_api_to_import_and_alerts(self):
        caballito = json.loads(FIXTURE.read_text(encoding='utf-8'))
        almagro = dict(caballito, barrio='Almagro', precio=115000,
                       url=caballito['url'].replace('12345678', '12345679'))
        other = dict(caballito, ambientes=3, url=caballito['url'].replace('12345678', '12345680'))
        datasets = [
            [{'url': caballito['url']}, {'url': caballito['url'] + '?test=1'}, {'url': other['url']}],
            [caballito], [other], [{'url': almagro['url']}], [almagro],
        ]
        responses = []
        for i, rows in enumerate(datasets):
            final = {'status': 'SUCCEEDED', 'usageTotalUsd': 0.01, 'defaultDatasetId': f'data{i}'}
            responses.extend([{'data': {'id': f'run{i}', 'status': 'READY'}},
                              {'data': final}, {'data': final}, rows])
        client = ApifyClient()
        with (tempfile.TemporaryDirectory() as temp,
              patch.object(client, 'request', side_effect=responses) as request,
              patch('precio_entorno.apify_client.sleep')):
            output = Path(temp) / 'pilot'
            stats = run_pilot(client, pilot_plan(), output)
            posts = [call for call in request.call_args_list if call.args[0] == f'{ACTOR_PATH}/runs']
            self.assertEqual([call.kwargs['params']['maxTotalChargeUsd'] for call in posts],
                             [0.05, 0.018, 0.018, 0.05, 0.018])
            self.assertEqual((stats['detalles_recibidos'], stats['comparables_con_barrio'],
                              stats['pines_utilizables'], stats['fuera_de_alcance']), (3, 2, 0, 1))
            self.assertNotIn('vendedor_email', (output / 'run1-crudo.json').read_text(encoding='utf-8'))
            log = json.loads((output / 'corridas.json').read_text(encoding='utf-8'))
            self.assertEqual((log[0]['run_id'], log[0]['costo_informado_usd']), ('run0', 0.01))
            with self.assertRaises(FileExistsError):
                run_pilot(client, pilot_plan(), output)

            store = Store(Path(temp) / 'real.sqlite3')
            store.save_search('Caballito', 110000, 40, 2)
            batch = (output / 'avisos.json').read_bytes()
            first = import_listings(store, batch, 'avisos.json', SOURCE)
            second = import_listings(store, batch, 'avisos.json', SOURCE)
            self.assertEqual((first.added, first.alerts, second.added, second.alerts), (2, 1, 0, 0))
            self.assertEqual(len(store.alerts()), 1)

    def test_failed_first_run_prevents_second_start(self):
        client = ApifyClient()
        with (tempfile.TemporaryDirectory() as temp,
              patch.object(client, 'request', return_value={'data': {'id': 'run1', 'status': 'READY'}}) as request,
              patch.object(client, 'wait', return_value={'status': 'FAILED', 'usageTotalUsd': 0.02})):
            output = Path(temp) / 'pilot'
            with self.assertRaisesRegex(RuntimeError, 'FAILED'):
                run_pilot(client, pilot_plan(), output)
            request.assert_called_once()
            log, = json.loads((output / 'corridas.json').read_text(encoding='utf-8'))
            self.assertEqual((log['run_id'], log['status'], log['costo_informado_usd']), ('run1', 'FAILED', 0.02))


    def test_env_tokens_select_one_account(self):
        with tempfile.TemporaryDirectory() as temp, patch.dict('os.environ', {}, clear=True):
            env = Path(temp) / '.env'
            env.write_text('# comentario\nAPIFY_TOKEN="apify_api_uno"\n', encoding='utf-8')
            self.assertEqual(apify_token(env=env), 'apify_api_uno')
            env.write_text('APIFY_TOKEN=\nOTRA=valor\n', encoding='utf-8')
            self.assertIsNone(apify_token(env=env))
            env.write_text('apify_api_uno\n\nAPIFY_TOKEN_2=apify_api_dos\napify_api_uno\nnota suelta\n',
                           encoding='utf-8')
            with self.assertRaisesRegex(ValueError, '2 cuentas'):
                apify_token(env=env)
            self.assertEqual([apify_token(n, env) for n in (1, 2)], ['apify_api_uno', 'apify_api_dos'])
            with self.assertRaisesRegex(ValueError, 'entre 1 y 2'):
                apify_token(3, env)
            with patch.dict('os.environ', {'APIFY_TOKEN': 'desde_entorno'}):
                self.assertEqual(apify_token(env=env), 'desde_entorno')

    def test_empty_search_stops_the_pilot(self):
        client = ApifyClient()
        final = {'status': 'SUCCEEDED', 'usageTotalUsd': 0.001, 'defaultDatasetId': 'data1'}
        responses = [{'data': {'id': 'run1', 'status': 'READY'}}, []]
        with (tempfile.TemporaryDirectory() as temp,
              patch.object(client, 'request', side_effect=responses) as request,
              patch.object(client, 'wait', return_value=final)):
            with self.assertRaisesRegex(RuntimeError, 'no devolvió enlaces'):
                run_pilot(client, pilot_plan(), Path(temp) / 'pilot')
            self.assertEqual(request.call_count, 2)
