"""Vigencia de los avisos: bajas por barrido completo, cambios de precio y migración de bases viejas."""

import json
import sqlite3
import tempfile
import unittest
from collections import Counter
from pathlib import Path
from unittest.mock import patch

from precio_entorno import inmobiliarias
from precio_entorno.actualizar import update
from precio_entorno.inmobiliarias import PoliteClient, record, scrape_migliorisi, scrape_remax
from precio_entorno.store import Store


def item(i, price=100000, captured_at='2026-11-01T00:00:00+00:00'):
    return {'id': f'ficticia:{i}', 'neighborhood': 'Caballito', 'price': price, 'covered_area': 45, 'rooms': 2,
            'currency': 'USD', 'url': f'https://example.invalid/{i}', 'captured_at': captured_at,
            'total_area_m2': None, 'latitude': None, 'longitude': None, 'location_accuracy_m': None}


def fake_site(ids, complete=True, price=100000):
    def scrape(client, captured_at, max_listings, known=frozenset(), sweep=None):
        if sweep is not None:
            sweep['completo'] = complete
        return [record('ficticia', i, f'https://example.invalid/{i}', captured_at, price=price, currency='USD',
                       covered_area_m2=45, rooms=2, neighborhood='Caballito') for i in ids], Counter()
    return scrape


class StoreTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.path = Path(temp.name) / 'real.sqlite3'
        self.store = Store(self.path)

    def status(self, i):
        return {l['id']: l['status'] for l in self.store.listings(include_inactive=True)}[f'ficticia:{i}']

    def test_two_complete_sweeps_without_the_listing_mark_it_as_gone(self):
        self.store.ingest([item(i) for i in range(10)], source='prueba')
        seen = [f'ficticia:{i}' for i in range(1, 10)]
        first = self.store.apply_sweep('ficticia', seen, '2026-11-02')
        self.assertEqual((first['aplicado'], first['no_vistos'], first['bajas']), (True, 1, 0))
        self.assertEqual(self.status(0), 'no_visto')
        # Un aviso no visto una vez sigue contando como vigente.
        self.assertEqual(len(self.store.listings()), 10)
        second = self.store.apply_sweep('ficticia', seen, '2026-11-05')
        self.assertEqual((second['no_vistos'], second['bajas']), (0, 1))
        self.assertEqual(self.status(0), 'baja')
        self.assertEqual(len(self.store.listings()), 9)
        self.assertEqual(len(self.store.listings(include_inactive=True)), 10)

    def test_a_listing_seen_again_goes_back_to_active(self):
        self.store.ingest([item(i) for i in range(10)], source='prueba')
        seen = [f'ficticia:{i}' for i in range(1, 10)]
        self.store.apply_sweep('ficticia', seen, '2026-11-02')
        self.store.apply_sweep('ficticia', seen, '2026-11-05')
        back = self.store.apply_sweep('ficticia', seen + ['ficticia:0'], '2026-11-08')
        self.assertEqual(back['reactivados'], 1)
        self.assertEqual(self.status(0), 'activo')

    def test_a_sweep_missing_too_many_listings_changes_nothing(self):
        self.store.ingest([item(i) for i in range(10)], source='prueba')
        result = self.store.apply_sweep('ficticia', ['ficticia:0'], '2026-11-02')
        self.assertFalse(result['aplicado'])
        self.assertIn('falla de la fuente', result['motivo'])
        self.assertEqual({l['status'] for l in self.store.listings(include_inactive=True)}, {'activo'})

    def test_a_sweep_only_touches_its_own_source(self):
        self.store.ingest([item(i) for i in range(10)] + [{**item(0), 'id': 'otra:0'}], source='prueba')
        self.store.apply_sweep('ficticia', [f'ficticia:{i}' for i in range(1, 10)], '2026-11-02')
        statuses = {l['id']: l['status'] for l in self.store.listings(include_inactive=True)}
        self.assertEqual(statuses['otra:0'], 'activo')

    def test_price_drop_is_kept_in_history_and_can_trigger_an_alert(self):
        self.store.save_search('Caballito', 95000, 40, 2)
        self.store.ingest([item(1)], source='prueba')
        self.assertEqual(self.store.alerts(), [])
        stats = {}
        added, alerts = self.store.ingest([item(1, 90000, '2026-11-04T00:00:00+00:00')], source='prueba', stats=stats)
        self.assertEqual((added, alerts, stats['cambios_de_precio']), (0, 1, 1))
        self.assertEqual(self.store.listings()[0]['price'], 90000)
        self.assertEqual([h['price'] for h in self.store.price_history('ficticia:1')], [100000, 90000])
        # Volver a ver el mismo precio no agrega historial ni alertas.
        self.assertEqual(self.store.ingest([item(1, 90000, '2026-11-06T00:00:00+00:00')], source='prueba'), (0, 0))
        self.assertEqual(len(self.store.price_history('ficticia:1')), 2)

    def test_an_older_capture_does_not_overwrite_a_newer_price(self):
        self.store.ingest([item(1, 90000, '2026-11-04T00:00:00+00:00')], source='prueba')
        stats = {}
        self.store.ingest([item(1, 100000, '2026-11-01T00:00:00+00:00')], source='prueba', stats=stats)
        self.assertEqual(stats['cambios_de_precio'], 0)
        self.assertEqual(self.store.listings()[0]['price'], 90000)

    def test_a_gone_listing_republished_is_active_again(self):
        self.store.ingest([item(i) for i in range(10)], source='prueba')
        for day in ('2026-11-02', '2026-11-05'):
            self.store.apply_sweep('ficticia', [f'ficticia:{i}' for i in range(1, 10)], day)
        stats = {}
        self.store.ingest([item(0, captured_at='2026-11-08T00:00:00+00:00')], source='prueba', stats=stats)
        self.assertEqual(stats['reactivados'], 1)
        self.assertEqual(self.status(0), 'activo')

    def test_old_databases_get_status_and_price_history(self):
        old = Path(self.path.parent / 'vieja.sqlite3')
        with sqlite3.connect(old) as db:
            db.executescript("""
                CREATE TABLE listings (id TEXT PRIMARY KEY, neighborhood TEXT NOT NULL, price INTEGER NOT NULL,
                    covered_area INTEGER NOT NULL, rooms INTEGER NOT NULL);
                CREATE TABLE listing_details (listing_id TEXT PRIMARY KEY, source TEXT NOT NULL, url TEXT NOT NULL,
                    captured_at TEXT NOT NULL, currency TEXT NOT NULL, total_area_m2 REAL, latitude REAL,
                    longitude REAL, location_accuracy_m REAL);
                INSERT INTO listings VALUES ('ficticia:1', 'Caballito', 100000, 45, 2);
                INSERT INTO listing_details VALUES ('ficticia:1', 'prueba', 'https://example.invalid/1',
                    '2026-11-01T00:00:00+00:00', 'USD', NULL, NULL, NULL, NULL);
            """)
        db.close()
        store = Store(old)
        Store(old)  # Abrirla dos veces no duplica el historial.
        listing = store.listings()[0]
        self.assertEqual((listing['status'], listing['last_seen']), ('activo', '2026-11-01T00:00:00+00:00'))
        self.assertEqual(store.price_history('ficticia:1'),
                         [{'price': 100000, 'currency': 'USD', 'seen_at': '2026-11-01T00:00:00+00:00'}])


class UpdateTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.dir = Path(temp.name)
        self.store = Store(self.dir / 'real.sqlite3')
        self.client = PoliteClient(fetch=lambda url, params=None: (200, ''), pause_s=0, sleep=lambda s: None)

    def run_update(self, name, site):
        with patch.dict(inmobiliarias.SITES, {'ficticia': site}, clear=True):
            return update(self.store, self.dir / name, ['ficticia'], 50, client=self.client, echo=lambda line: None)

    def test_complete_sweeps_mark_gone_listings_and_partial_ones_do_not(self):
        everything = [str(i) for i in range(10)]
        self.run_update('c1', fake_site(everything))
        partial = self.run_update('c2', fake_site(everything[1:], complete=False))
        self.assertEqual((partial['no_vistos'], partial['bajas'], partial['vigencia']), (0, 0, {}))
        first = self.run_update('c3', fake_site(everything[1:]))
        self.assertEqual((first['no_vistos'], first['bajas']), (1, 0))
        second = self.run_update('c4', fake_site(everything[1:]))
        self.assertEqual((second['no_vistos'], second['bajas']), (0, 1))
        self.assertNotIn('ficticia:0', {l['id'] for l in self.store.listings()})
        seen = json.loads((self.dir / 'c4' / 'vistos.json').read_text(encoding='utf-8'))
        self.assertEqual(seen['ficticia']['barrido_completo'], True)
        self.assertEqual(len(seen['ficticia']['ids']), 9)

    def test_price_changes_are_reported(self):
        self.run_update('c1', fake_site(['1', '2']))
        entry = self.run_update('c2', fake_site(['1', '2'], price=95000))
        self.assertEqual((entry['nuevos'], entry['cambios_de_precio']), (0, 2))


class ScraperSweepTests(unittest.TestCase):
    def remax_client(self, count):
        listing = {'listingStatus': {'value': 'active'}, 'operation': {'value': 'sale'},
                   'geoLabel': 'Caballito, Capital Federal', 'price': 100000, 'priceExposure': True,
                   'currency': {'value': 'USD'}, 'dimensionCovered': 45, 'totalRooms': 2,
                   'location': {'coordinates': [-58.44, -34.62]}}
        payload = {'data': {'data': [dict(listing, id=str(i), slug=f'x{i}') for i in range(count)], 'totalPages': 1}}
        return PoliteClient(fetch=lambda url, params=None: (200, '' if 'robots' in url else json.dumps(payload)),
                            pause_s=0, sleep=lambda s: None)

    def test_remax_sweep_is_complete_only_when_every_page_fits_under_the_limit(self):
        sweep = {'completo': False, 'vistos': set()}
        scrape_remax(self.remax_client(3), '2026-11-09', 10, sweep=sweep)
        self.assertTrue(sweep['completo'])
        sweep = {'completo': False, 'vistos': set()}
        scrape_remax(self.remax_client(3), '2026-11-09', 2, sweep=sweep)
        self.assertFalse(sweep['completo'])

    def test_migliorisi_counts_known_listings_as_seen(self):
        page = ('<a href="/propiedad/ver/a1/x"> <div> <img title="DEPARTAMENTO. 2 ambientes. VENTA. Almagro. C">'
                ' </div></a>')

        def fetch(url, params=None):
            return 200, page if 'busqueda' in url else ''
        client = PoliteClient(fetch=fetch, pause_s=0, sleep=lambda s: None)
        sweep = {'completo': False, 'vistos': set()}
        listings, _ = scrape_migliorisi(client, '2026-11-09', 10, known=frozenset({'migliorisi:a1'}), sweep=sweep)
        self.assertEqual((listings, sweep['vistos'], sweep['completo']), ([], {'migliorisi:a1'}, True))


if __name__ == '__main__':
    unittest.main()
