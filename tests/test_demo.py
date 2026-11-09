import tempfile
import unittest
from pathlib import Path

from precio_entorno.matching import compare_neighborhoods
from precio_entorno.store import Store


class DemoTests(unittest.TestCase):
    def test_alerts_match_filters_and_repeat_import_is_safe(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'demo.sqlite3'
            store = Store(path)
            self.assertTrue(store.save_search('Caballito', 110000, 40, 2))
            self.assertFalse(store.save_search('Caballito', 110000, 40, 2))
            batch = [
                dict(id='good', neighborhood='Caballito', price=110000, covered_area=40, rooms=2),
                dict(id='price', neighborhood='Caballito', price=110001, covered_area=40, rooms=2),
                dict(id='area', neighborhood='Caballito', price=100000, covered_area=39, rooms=2),
                dict(id='rooms', neighborhood='Caballito', price=100000, covered_area=40, rooms=1),
                dict(id='zone', neighborhood='Almagro', price=100000, covered_area=40, rooms=2),
            ]
            self.assertEqual(store.ingest(batch), (5, 1))
            reopened = Store(path)
            self.assertEqual(reopened.ingest(batch), (0, 0))
            self.assertEqual([alert['id'] for alert in reopened.alerts()], ['good'])

    def test_comparison_keeps_neighborhoods_without_matches(self):
        rows = [dict(neighborhood='Caballito', price=100000, covered_area=40, rooms=2),
                dict(neighborhood='Almagro', price=99000, covered_area=39, rooms=2)]
        result = compare_neighborhoods(rows, 100000, 40, 2)
        self.assertEqual([(row['Barrio'], row['Coincidencias']) for row in result],
                         [('Caballito', 1), ('Almagro', 0)])
