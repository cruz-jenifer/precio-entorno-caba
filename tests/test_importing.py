import json
import tempfile
import unittest
from pathlib import Path

from precio_entorno.importing import import_crimes, import_listings, usable_pin
from precio_entorno.matching import compare_neighborhoods
from precio_entorno.store import Store

FIXTURES = Path(__file__).resolve().parents[1] / 'data' / 'fixtures'


class ImportTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.path = Path(temp.name) / 'real.sqlite3'
        self.store = Store(self.path)

    def test_removing_a_search_also_removes_its_alerts(self):
        self.store.save_search('Caballito', 110000, 40, 2)
        fixture = FIXTURES / 'avisos_prueba.csv'
        import_listings(self.store, fixture.read_bytes(), fixture.name, 'Catálogo de prueba')
        search_id = self.store.searches()[0]['id']
        self.assertTrue(self.store.alerts())
        self.assertTrue(self.store.delete_search(search_id))
        self.assertEqual((self.store.searches(), self.store.alerts()), ([], []))
        self.assertFalse(self.store.delete_search(search_id))

    def test_csv_validates_and_alerts_only_once(self):
        self.store.save_search('Caballito', 110000, 40, 2)
        fixture = FIXTURES / 'avisos_prueba.csv'
        args = fixture.read_bytes(), fixture.name, 'Catálogo de prueba'
        report = import_listings(self.store, *args)
        self.assertEqual((report.read, report.added, report.duplicates, report.discarded, report.alerts),
                         (5, 2, 1, 2, 1))
        self.assertEqual(report.missing['price'], 1)
        self.assertEqual(report.invalid['currency'], 1)
        reopened = Store(self.path)
        listings = reopened.listings()
        self.assertEqual(sum(map(usable_pin, listings)), 1)
        self.assertEqual(listings[0]['covered_area'], 42.5)
        self.assertEqual(listings[0]['total_area_m2'], 45)
        self.assertEqual(listings[0]['captured_at'], '2026-11-01T00:00:00')
        self.assertEqual(listings[0]['source'], 'catálogo de prueba')
        self.assertEqual(compare_neighborhoods(listings, 110000, 40, 2)[0]['Coincidencias'], 1)
        repeat = import_listings(reopened, *args)
        self.assertEqual((repeat.added, repeat.duplicates, repeat.alerts), (0, 3, 0))
        self.assertEqual([(a['id'], a['url']) for a in reopened.alerts()],
                         [('av-1', 'https://example.invalid/av-1')])
        demo = Store(self.path.with_name('demo.sqlite3'))
        self.assertEqual((demo.listings(), demo.searches(), demo.alerts()), ([], [], []))

    def test_json_preserves_coordinates_and_rejects_another_catalog(self):
        payload = json.dumps({'listings': [{
            'listing_id': 10, 'url': 'https://example.invalid/10', 'captured_at': '2026-11-01',
            'price': 105000, 'currency': 'USD', 'covered_area_m2': 42, 'rooms': 2,
            'neighborhood': 'Nunez', 'latitude': -34.55, 'longitude': -58.46,
        }]}).encode()
        self.assertEqual(import_listings(self.store, payload, 'avisos.json', 'A').added, 1)
        listing, = self.store.listings()
        self.assertEqual((listing['neighborhood'], listing['latitude']), ('Núñez', -34.55))
        self.assertFalse(usable_pin(listing))
        with self.assertRaisesRegex(ValueError, 'otro catálogo'):
            import_listings(self.store, payload.replace(b'example.invalid/10', b'example.invalid/20').replace(b': 10,', b': 20,'), 'avisos.json', 'B')
        self.assertEqual(len(self.store.listings()), 1)

    def test_building_fields_are_optional_and_validated(self):
        base = {'url': 'https://example.invalid/x', 'captured_at': '2026-11-09', 'price': 105000, 'currency': 'USD',
                'covered_area_m2': 42, 'rooms': 2, 'neighborhood': 'Caballito'}
        rows = [dict(base, listing_id='a', age_years=40, condition='A reciclar', garages=1, floor=3),
                dict(base, listing_id='b', antiguedad=0, estado='A estrenar', piso='0'),
                dict(base, listing_id='c', age_years=-1, condition='otro', garages=1.5, floor=200),
                dict(base, listing_id='d')]
        report = import_listings(self.store, json.dumps(rows).encode(), 'avisos.json', 'A')
        self.assertEqual((report.added, report.discarded), (4, 0))   # Un dato opcional inválido no descarta el aviso.
        self.assertEqual({k: report.invalid[k] for k in ('age_years', 'condition', 'garages', 'floor')},
                         {'age_years': 1, 'condition': 1, 'garages': 1, 'floor': 1})
        got = {l['id']: (l['age_years'], l['condition'], l['garages'], l['floor']) for l in self.store.listings()}
        self.assertEqual(got, {'a': (40, 'a reciclar', 1, 3), 'b': (0, 'a estrenar', None, 0),
                               'c': (None, None, None, None), 'd': (None, None, None, None)})

    def test_old_database_gets_building_columns(self):
        import sqlite3
        from contextlib import closing
        old = self.path.with_name('vieja.sqlite3')
        with closing(sqlite3.connect(old)) as db, db:
            db.execute('CREATE TABLE listing_details (listing_id TEXT PRIMARY KEY, source TEXT NOT NULL, url TEXT NOT NULL, '
                       'captured_at TEXT NOT NULL, currency TEXT NOT NULL, total_area_m2 REAL, latitude REAL, '
                       'longitude REAL, location_accuracy_m REAL)')
        Store(old)
        with closing(sqlite3.connect(old)) as db:
            columns = {row[1] for row in db.execute('PRAGMA table_info(listing_details)')}
        self.assertTrue({'expenses', 'age_years', 'condition', 'garages', 'floor'} <= columns)

    def test_implausible_prices_and_areas_are_discarded(self):
        base = dict(url='https://example.invalid/x', captured_at='2026-11-01', currency='USD',
                    rooms=2, neighborhood='Caballito')
        cases = {
            'ok': dict(price=105000, covered_area_m2='42,5'),
            'miles-punto': dict(price='105.000', covered_area_m2=45),
            'miles-coma': dict(price='105,000', covered_area_m2=45),
            'minimo': dict(price=1, covered_area_m2=1),
            'superficie-miles': dict(price=105000, covered_area_m2='4.500'),
            'precio-m2': dict(price=10000, covered_area_m2=200),
            'ambientes': dict(price=105000, covered_area_m2=45, rooms=45),
        }
        rows = [dict(base, listing_id=name, **values) for name, values in cases.items()]
        report = import_listings(self.store, json.dumps(rows).encode(), 'avisos.json', 'A')
        self.assertEqual((report.added, report.discarded), (1, 6))
        self.assertEqual([item['id'] for item in self.store.listings()], ['ok'])
        self.assertEqual(report.invalid['price'], 3)
        self.assertEqual(report.invalid['covered_area_m2'], 2)
        self.assertEqual(report.invalid['precio_m2'], 1)
        self.assertEqual(report.invalid['rooms'], 1)

    def test_crime_counts_coverage_and_reimport(self):
        fixture = FIXTURES / 'delitos_prueba.csv'
        args = fixture.read_bytes(), fixture.name
        report = import_crimes(self.store, *args)
        self.assertEqual((report.added, report.duplicates, report.discarded), (5, 1, 1))
        self.assertEqual(report.missing['franja'], 1)
        self.assertEqual(report.missing['barrio'], 1)
        self.assertEqual(self.store.crime_summary('Villa General Mitre', '2024-02')[0]['count'], 1)
        file, periods = self.store.crime_periods()
        self.assertEqual(file['filename'], fixture.name)
        self.assertEqual(periods, ['2024-02', '2024-01'])
        self.assertEqual(self.store.crime_summary('Caballito', '2024-01'),
                         [{'kind': 'Robo', 'hour': 0, 'count': 5}])
        self.assertEqual(self.store.crime_summary('Almagro', '2024-01')[0]['count'], 0)
        self.assertEqual(self.store.crime_summary('Almagro', '2024-02'), [])
        self.assertIsNone(self.store.crime_summary('Caballito', '2024-02')[0]['hour'])
        repeat = import_crimes(self.store, *args)
        self.assertEqual((repeat.added, repeat.duplicates), (0, 6))
        self.assertEqual(self.store.crime_summary('Caballito', '2024-01')[0]['count'], 5)
        self.assertEqual(import_crimes(self.store, args[0].replace(b'Robo', b'Lesiones'), 'otra.csv').added, 5)
        self.assertEqual(self.store.crime_summary('Caballito', '2024-01')[0]['kind'], 'Lesiones')

