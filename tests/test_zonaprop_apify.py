"""Pruebas del adaptador de Zonaprop (Apify) con resultados sintéticos y ficticios."""

import json
import tempfile
import unittest
from pathlib import Path

from precio_entorno.importing import parse_listings
from precio_entorno.inmobiliarias import CATALOG
from precio_entorno.zonaprop_apify import adapt, adapt_all, check_pricing, run

CAPTURED = '2026-11-08T12:00:00+00:00'


def location(name, label='BARRIO', parent=None):
    caba = {'name': 'Capital Federal', 'acronym': 'CABA', 'label': 'CIUDAD'}
    return {'name': name, 'label': label, 'parent': parent or caba}


def zp_item(pid, **extra):
    item = {
        'posting_id': str(pid), 'url': f'https://www.zonaprop.com.ar/propiedades/clasificado/ficticio-{pid}.html?x=1',
        'pricing': {'amount': 115000, 'currency': 'USD', 'operation': 'Venta'},
        'propertyDetails': {'type': 'Departamento'},
        'features': [{'feature': {'feature_id': 'CFT1'}, 'value': '3'},
                     {'feature': {'feature_id': 'CFT100'}, 'value': '80'},
                     {'feature': {'feature_id': 'CFT101'}, 'value': '73'},
                     {'feature': {'feature_id': 'CFT6'}, 'value': '$ 200.000'}],
        'location': {'posting_geolocation': {'geolocation': {'latitude': -34.619, 'longitude': -58.428}}},
        'contact': {'publisherId': 'P-1', 'logo': 'https://example.invalid/logo.png'},
        '_details': {'location': {'location': location('Caballito')},
                     'contact_info': {'contact_name': 'Anunciante Ficticio', 'emails': ['anunciante@example.invalid'],
                                      'phone': ['+54 11 0000-0000']}},
    }
    item.update(extra)
    return item


class FakeClient:
    def __init__(self, items, unit=0.001, usage=0.0):
        self.items, self.unit, self.usage, self.calls = items, unit, usage, []

    def request(self, path, params=None, payload=None):
        self.calls.append((path, params, payload))
        if path == 'users/me/limits':
            return {'data': {'current': {'monthlyUsageUsd': self.usage}}}
        if path.endswith('/runs'):
            return {'data': {'id': 'run1'}}
        if path.startswith('datasets/'):
            return self.items
        event = {'eventTieredPricingUsd': {'FREE': {'tieredEventPriceUsd': self.unit}}}
        return {'data': {'pricingInfos': [{'pricingModel': 'PAY_PER_EVENT', 'pricingPerEvent': {
            'actorChargeEvents': {'apify-default-dataset-item': event, 'fetch-detail': event}}}]}}

    def wait(self, run_id, max_seconds=0):
        return {'id': run_id, 'status': 'SUCCEEDED', 'defaultDatasetId': 'ds1', 'usageTotalUsd': 0.01}


class ZonapropTests(unittest.TestCase):
    def test_maps_contract_fields_without_contacts(self):
        listing, why = adapt(zp_item(1), CAPTURED, 'venta')
        self.assertIsNone(why)
        self.assertEqual(listing['listing_id'], 'zonaprop:1')
        self.assertEqual(listing['source'], CATALOG)
        self.assertEqual(listing['url'], 'https://www.zonaprop.com.ar/propiedades/clasificado/ficticio-1.html')
        self.assertEqual((listing['price'], listing['currency'], listing['rooms']), (115000, 'USD', 3))
        self.assertEqual((listing['covered_area_m2'], listing['total_area_m2'], listing['expenses']), (73, 80, 200000))
        self.assertEqual(listing['neighborhood'], 'Caballito')
        text = json.dumps(listing)
        for word in ('Anunciante', 'example.invalid', '0000-0000', 'P-1'):
            self.assertNotIn(word, text)

    def test_scope_and_neighborhoods(self):
        cases = [
            (zp_item(2, pricing={'amount': 900000, 'currency': 'ARS', 'operation': 'Alquiler'}), 'fuera_de_alcance'),
            (zp_item(3, propertyDetails={'type': 'Casa'}), 'fuera_de_alcance'),
            (zp_item(4, _details={'location': {'location': location('Lanús', parent={'name': 'GBA Sur'})}}),
             'fuera_de_caba'),
            (zp_item(5, url='https://otro.example/aviso'), 'sin_id_o_enlace'),
        ]
        for item, reason in cases:
            self.assertEqual(adapt(item, CAPTURED, 'venta'), (None, reason))
        sub = zp_item(6, _details={'location': {'location': location('Parque Rivadavia', 'SUBBARRIO')}})
        self.assertEqual(adapt(sub, CAPTURED, 'venta')[0]['neighborhood'], 'Caballito')
        pompeya = zp_item(16, _details={'location': {'location': location('Pompeya')}})
        self.assertEqual(adapt(pompeya, CAPTURED, 'venta')[0]['neighborhood'], 'Nueva Pompeya')
        nested = zp_item(7, _details={'location': {'location': location('Rincón Ficticio', 'SUBBARRIO',
                                                                         location('Almagro'))}})
        self.assertEqual(adapt(nested, CAPTURED, 'venta')[0]['neighborhood'], 'Almagro')

    def test_foreign_expenses_and_deduplication(self):
        item = zp_item(8)
        item['features'][3]['value'] = 'USD 150'
        listings, skipped = adapt_all([item, zp_item(8), zp_item(9)], CAPTURED, 'venta')
        self.assertEqual([x['listing_id'] for x in listings], ['zonaprop:8', 'zonaprop:9'])
        self.assertIsNone(listings[0]['expenses'])
        self.assertEqual(skipped, {})

    def test_imports_into_sale_catalog(self):
        listings, _ = adapt_all([zp_item(10), zp_item(11)], CAPTURED, 'venta')
        valid, report = parse_listings(json.dumps(listings).encode(), 'avisos.json', CATALOG)
        self.assertEqual(len(valid), 2)
        self.assertEqual(report.discarded, 0)

    def test_price_change_stops_before_running(self):
        with self.assertRaisesRegex(RuntimeError, 'tarifa'):
            check_pricing(FakeClient([], unit=0.01))

    def test_run_caps_spend_and_writes_only_contract_fields(self):
        client = FakeClient([zp_item(12), zp_item(13)])
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp) / 'captura'
            listings, log = run([(1, client)], out, ['Caballito'], 'venta', 2, 0.5)
            saved = (out / 'avisos.json').read_text(encoding='utf-8') + (out / 'registro.json').read_text(encoding='utf-8')
        self.assertEqual(len(listings), 2)
        runs = [c for c in client.calls if c[0].endswith('/runs')]
        self.assertEqual(runs[0][1]['maxTotalChargeUsd'], 0.5)
        self.assertEqual(runs[0][2]['location'], 'Caballito')
        self.assertNotIn('example.invalid', saved)
        self.assertEqual(log['corridas'][0]['avisos'], 2)

    def test_rotates_accounts_and_stops_without_balance(self):
        full, spare = FakeClient([zp_item(14)], usage=4.6), FakeClient([zp_item(15)], usage=1.0)
        with tempfile.TemporaryDirectory() as temp:
            _, log = run([(1, full), (2, spare)], Path(temp) / 'a', ['Caballito', 'Almagro'], 'venta', 1, 0.2)
        self.assertEqual([c['cuenta'] for c in log['corridas']], [2, 2])
        self.assertFalse([c for c in full.calls if c[0].endswith('/runs')])
        with tempfile.TemporaryDirectory() as temp:
            listings, log = run([(1, full)], Path(temp) / 'b', ['Caballito'], 'venta', 1, 0.2)
        self.assertEqual(listings, [])
        self.assertIn('Sin saldo', log['detenido'])


if __name__ == '__main__':
    unittest.main()
