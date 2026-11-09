import json
import tempfile
import unittest
from pathlib import Path

from precio_entorno.apify_export import adapt_export
from precio_entorno.importing import import_listings, usable_pin
from precio_entorno.store import Store


class ApifyExportTests(unittest.TestCase):
    def test_offline_adapter_preserves_contract_and_excludes_publisher_fields(self):
        sample = {
            'listingKey': 'zonaprop.com.ar:123', 'portal': 'zonaprop', 'country': 'AR',
            'operation': 'sale', 'propertyType': 'departamentos', 'postingType': 'PROPERTY',
            'locationHierarchy': ['Caballito', 'Capital Federal'],
            'url': 'https://www.zonaprop.com.ar/propiedades/demo-123.html?tracking=sample',
            'price': 100000, 'currency': 'USD', 'coveredAreaM2': 41, 'totalAreaM2': 50,
            'rooms': 2, 'postedAt': '2026-10-01', 'publisherPhone': 'example',
            'latitude': -34.62, 'longitude': -58.44,
        }
        rows = [sample, dict(sample, operation='rental'), dict(sample, locationHierarchy=['Flores']),
                dict(sample, postingType='DEVELOPMENT'), dict(sample, coveredAreaM2=None)]
        adapted = adapt_export(rows, '2026-11-07')
        self.assertEqual(len(adapted), 2)
        self.assertNotIn('publisherPhone', adapted[0])
        self.assertNotIn('?', adapted[0]['url'])
        self.assertEqual(adapted[0]['captured_at'], '2026-11-07T00:00:00')
        with tempfile.TemporaryDirectory() as temp:
            store = Store(Path(temp) / 'preview.sqlite3')
            report = import_listings(store, json.dumps(adapted).encode(), 'preview.json', 'zonaprop')
            self.assertEqual((report.added, report.discarded), (1, 1))
            self.assertFalse(usable_pin(store.listings()[0]))

    def test_adapter_enforces_pilot_size(self):
        with self.assertRaisesRegex(ValueError, '1 a 50'):
            adapt_export([{}] * 51, '2026-11-07')

