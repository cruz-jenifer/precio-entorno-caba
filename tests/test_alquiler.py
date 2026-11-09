"""Pruebas del flujo de alquiler: validación, moneda de las búsquedas y adaptadores."""

import json
import sqlite3
from contextlib import closing
import tempfile
import unittest
from pathlib import Path

from precio_entorno.importing import import_listings, parse_listings
from precio_entorno.inmobiliarias import (
    CATALOGS, parse_century21, parse_migliorisi_detail, parse_remax)
from precio_entorno.matching import compare_neighborhoods
from precio_entorno.store import Store

CAPTURED = '2026-11-07T12:00:00+00:00'


def rental(i, price, currency, area=45, rooms=2, barrio='Caballito', **extra):
    return dict({'listing_id': f'alq-{i}', 'url': f'https://example.invalid/{i}', 'captured_at': '2026-11-07',
                 'price': price, 'currency': currency, 'covered_area_m2': area, 'rooms': rooms,
                 'neighborhood': barrio}, **extra)


class RentalValidationTests(unittest.TestCase):
    def test_rentals_accept_pesos_and_dollars_with_monthly_ranges(self):
        rows = [rental(1, 750000, '$', expensas=95000), rental(2, 900, 'USD', expensas='95.000'),
                rental(3, 120000, 'USD'), rental(4, 30000, 'ARS'), rental(5, 750000, 'EUR'), rental(6, '750.000', 'ARS')]
        listings, report = parse_listings(json.dumps(rows).encode(), 'a.json', 'ficticio', 'alquiler')
        self.assertEqual([(l['id'], l['currency'], l['price']) for l in listings],
                         [('alq-1', 'ARS', 750000.0), ('alq-2', 'USD', 900.0)])
        self.assertEqual((listings[0]['expenses'], listings[1]['expenses']), (95000.0, None))
        self.assertEqual((report.invalid['price'], report.invalid['currency'], report.invalid['expenses']), (3, 1, 1))

    def test_sale_still_rejects_pesos(self):
        listings, report = parse_listings(json.dumps([rental(1, 750000, 'ARS')]).encode(), 'a.json', 'ficticio')
        self.assertEqual((listings, report.invalid['currency']), ([], 1))


class RentalStoreTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.path = Path(temp.name) / 'real-alquiler.sqlite3'
        self.store = Store(self.path)

    def test_alerts_only_match_searches_in_the_same_currency(self):
        self.store.save_search('Caballito', 800000, 40, 2, 'ARS')
        self.store.save_search('Caballito', 1000, 40, 2, 'USD')
        rows = [rental(1, 780000, 'ARS', expensas=95000), rental(2, 900, 'USD'), rental(3, 950000, 'ARS')]
        report = import_listings(self.store, json.dumps(rows).encode(), 'a.json', CATALOGS['alquiler'], 'alquiler')
        self.assertEqual((report.added, report.alerts), (3, 2))
        alerts = {(a['search_id'], a['id']): a for a in self.store.alerts()}
        self.assertEqual(set(alerts), {(1, 'alq-1'), (2, 'alq-2')})
        self.assertEqual((alerts[(1, 'alq-1')]['currency'], alerts[(1, 'alq-1')]['expenses']), ('ARS', 95000.0))
        ars = compare_neighborhoods(self.store.listings(), 800000, 40, 2, 'ARS')
        self.assertEqual(ars, [{'Barrio': 'Caballito', 'Coincidencias': 1, 'Precio mediano de coincidencias (ARS)': 780000}])
        repeat = import_listings(self.store, json.dumps(rows).encode(), 'a.json', CATALOGS['alquiler'], 'alquiler')
        self.assertEqual((repeat.added, repeat.alerts), (0, 0))

    def test_old_databases_get_the_new_columns(self):
        old = Path(self.path.parent) / 'vieja.sqlite3'
        with closing(sqlite3.connect(old)) as db:
            db.executescript("""
                CREATE TABLE searches (id INTEGER PRIMARY KEY, neighborhood TEXT NOT NULL, budget INTEGER NOT NULL,
                    min_area INTEGER NOT NULL, rooms INTEGER NOT NULL, UNIQUE (neighborhood, budget, min_area, rooms));
                INSERT INTO searches VALUES (1, 'Caballito', 110000, 40, 2);
                CREATE TABLE listing_details (listing_id TEXT PRIMARY KEY, source TEXT NOT NULL, url TEXT NOT NULL,
                    captured_at TEXT NOT NULL, currency TEXT NOT NULL, total_area_m2 REAL, latitude REAL,
                    longitude REAL, location_accuracy_m REAL);
            """)
        store = Store(old)
        self.assertEqual(store.searches()[0]['currency'], 'USD')
        store.ingest([dict(id='v1', neighborhood='Caballito', price=100000, covered_area=45, rooms=2)])
        self.assertEqual([a['id'] for a in store.alerts()], ['v1'])


class RentalAdapterTests(unittest.TestCase):
    def test_remax_keeps_rent_and_expenses(self):
        base = {'id': 1, 'internalId': 'R-1', 'entrepreneurship': False, 'slug': 'alquiler-ficticio',
                'listingStatus': {'value': 'active'}, 'operation': {'value': 'rent'}, 'currency': {'value': 'ARS'},
                'price': 750000, 'priceExposure': True, 'expensesPrice': 95000, 'expensesCurrency': {'value': 'ARS'},
                'dimensionCovered': 45, 'dimensionTotalBuilt': 45, 'totalRooms': 2,
                'geoLabel': 'Caballito, Capital Federal', 'location': {'coordinates': [-58.44, -34.61]}}
        payload = {'data': {'totalPages': 1, 'data': [base, dict(base, id=2, operation={'value': 'sale'})]}}
        listings, skipped, _ = parse_remax(payload, CAPTURED, 'alquiler')
        self.assertEqual([(l['listing_id'], l['source'], l['expenses']) for l in listings],
                         [('remax:R-1', 'inmobiliarias-alquiler', 95000.0)])
        self.assertEqual(skipped['otra_operacion'], 1)

    def test_century21_and_migliorisi_rentals(self):
        item = {'property_id': '9', 'operation_type': 'rent', 'prop_type': 'departamento', 'status': 'active',
                'addr_region': 'Capital Federal', 'addr_neighborhood': 'Almagro', 'price': '690000.00',
                'currency_id': 'ARS', 'covered_square_meters': '42.00', 'rooms': 2}
        page = f'<script>self.__next_f.push([1,{json.dumps(json.dumps({"p": [item]}))}])</script>'
        c21, _, _ = parse_century21(page, CAPTURED, 'alquiler')
        self.assertEqual((c21[0]['currency'], c21[0]['source']), ('ARS', 'inmobiliarias-alquiler'))
        self.assertEqual(parse_century21(page, CAPTURED, 'venta')[0], [])
        detail = ('<title>Inmobiliaria Migliorisi | DEPARTAMENTO. 2 ambientes. ALQUILER. Almagro. POTOSI al 4300</title>'
                  '<p>Precio $ 750.000</p><td>Superficie Cubierta</td><td>37 m2</td><td>Expensas</td><td>$ 85.000</td>')
        listing, is_rent, is_flat = parse_migliorisi_detail(detail, '/propiedad/ver/a1/x', 'a1', '', CAPTURED, 'alquiler')
        self.assertTrue(is_rent and is_flat)
        self.assertEqual((listing['price'], listing['currency'], listing['expenses'], listing['neighborhood']),
                         (750000, 'ARS', 85000, 'Almagro'))
        _, is_sale, _ = parse_migliorisi_detail(detail, '/propiedad/ver/a1/x', 'a1', '', CAPTURED, 'venta')
        self.assertFalse(is_sale)
