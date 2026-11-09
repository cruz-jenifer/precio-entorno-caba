"""Pruebas de las corridas de OpenStreetMap con un cliente de Apify simulado."""

import json
import tempfile
import unittest
from pathlib import Path

from precio_entorno.osm_apify import PLAN, cap_usd, check_plan, check_pricing, run_one, slim


class FakeClient:
    def __init__(self, rows, cost=0.05, status='SUCCEEDED', pricing=None):
        self.rows, self.cost, self.status, self.calls = rows, cost, status, []
        self.pricing = pricing or {'pricingModel': 'PAY_PER_EVENT', 'pricingPerEvent': {'actorChargeEvents': {
            'start': {'eventTieredPricingUsd': {'FREE': {'tieredEventPriceUsd': 0.005}}},
            'poi-extracted': {'eventTieredPricingUsd': {'FREE': {'tieredEventPriceUsd': 0.0008}}}}}}

    def request(self, path, params=None, payload=None):
        self.calls.append((path, params, payload))
        if path.endswith('/runs'):
            return {'data': {'id': 'run1', 'status': 'READY'}}
        if path.startswith('datasets/'):
            return self.rows
        return {'data': {'pricingInfos': [self.pricing]}}

    def wait(self, run_id, max_seconds=360):
        return {'status': self.status, 'defaultDatasetId': 'data1', 'usageTotalUsd': self.cost}


class OsmApifyTests(unittest.TestCase):
    def test_plan_fits_five_dollars_per_account(self):
        budget = check_plan(PLAN)
        self.assertEqual(sorted(budget), [1, 2, 3, 4])
        self.assertTrue(all(v <= 5 for v in budget.values()))
        self.assertLess(sum(budget.values()), 25)
        with self.assertRaisesRegex(ValueError, 'supera'):
            check_plan([(1, 'a', 'restaurants', 5000), (1, 'b', 'cafes', 2000)])

    def test_pricing_change_stops_before_running(self):
        check_pricing(FakeClient([]))
        expensive = FakeClient([], pricing={'pricingModel': 'PAY_PER_EVENT', 'pricingPerEvent': {'actorChargeEvents': {
            'start': {'eventPriceUsd': 0.005}, 'poi-extracted': {'eventPriceUsd': 0.002}}}})
        with self.assertRaisesRegex(RuntimeError, 'tarifa'):
            check_pricing(expensive)

    def test_run_keeps_only_place_fields_and_logs_cost(self):
        rows = [{'osmId': 1, 'osmType': 'node', 'name': 'Plaza', 'category': 'parks', 'latitude': -34.6,
                 'longitude': -58.4, 'phone': '+54 11 0000', 'website': 'https://example.invalid',
                 'email': 'x@example.invalid', 'extras': {'leisure': 'park', 'contact:phone': '1'}}]
        client = FakeClient(rows, cost=0.04)
        with tempfile.TemporaryDirectory() as temp:
            out, log = Path(temp), []
            points = run_one(client, 'parques', 'parks', 50, out, log, account=1)
            self.assertEqual(points, [{'osmId': 1, 'osmType': 'node', 'name': 'Plaza', 'category': 'parks',
                                       'latitude': -34.6, 'longitude': -58.4, 'leisure': 'park'}])
            saved = json.loads((out / 'corridas.json').read_text(encoding='utf-8'))
            self.assertEqual((saved[0]['costo_informado_usd'], saved[0]['puntos'], saved[0]['tope_usd']),
                             (0.04, 1, cap_usd(50)))
            _, params, payload = client.calls[0]
            self.assertEqual((params['maxTotalChargeUsd'], payload['maxItems']), (cap_usd(50), 50))

    def test_failed_or_overpriced_run_raises(self):
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaisesRegex(RuntimeError, 'FAILED'):
                run_one(FakeClient([], status='FAILED'), 'x', 'parks', 50, Path(temp), [], account=1)
            with self.assertRaisesRegex(RuntimeError, 'supera el tope'):
                run_one(FakeClient([], cost=9.0), 'y', 'parks', 50, Path(temp), [], account=1)

    def test_slim_drops_contacts(self):
        self.assertNotIn('phone', slim({'name': 'A', 'phone': '1', 'website': 'w', 'latitude': 1}))
