"""Pruebas de la actualización periódica con sitios ficticios."""

import json
import tempfile
import unittest
from collections import Counter
from pathlib import Path
from unittest.mock import patch

from precio_entorno import inmobiliarias
from precio_entorno.actualizar import update
from precio_entorno.inmobiliarias import CATALOG, PoliteClient, record, scrape_migliorisi
from precio_entorno.store import Store


def fake_site(ids):
    def scrape(client, captured_at, max_listings, known=frozenset()):
        return [record('ficticia', i, f'https://example.invalid/{i}', captured_at, price=100000, currency='USD',
                       covered_area_m2=45, rooms=2, neighborhood='Caballito') for i in ids], Counter()
    return scrape


class UpdateTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.dir = Path(temp.name)
        self.store = Store(self.dir / 'real.sqlite3')
        self.store.save_search('Caballito', 110000, 40, 2)
        self.client = PoliteClient(fetch=lambda url, params=None: (200, ''), pause_s=0, sleep=lambda s: None)

    def run_update(self, name, ids):
        with patch.dict(inmobiliarias.SITES, {'ficticia': fake_site(ids)}, clear=True):
            return update(self.store, self.dir / name, ['ficticia'], 10, client=self.client,
                          history=self.dir / 'actualizaciones.jsonl', echo=lambda line: None)

    def test_new_ids_generate_one_alert_each_and_repeats_none(self):
        first = self.run_update('c1', ['1', '2'])
        self.assertEqual((first['nuevos'], first['alertas_nuevas']), (2, 2))
        second = self.run_update('c2', ['2', '3'])
        self.assertEqual((second['nuevos'], second['repetidos'], second['alertas_nuevas']), (1, 1, 1))
        self.assertEqual([a['aviso'] for a in second['alertas']], ['ficticia:3'])
        history = [json.loads(line) for line in (self.dir / 'actualizaciones.jsonl').read_text().splitlines()]
        self.assertEqual([h['alertas_nuevas'] for h in history], [2, 1])
        self.assertTrue(all(i['source'] == CATALOG for i in
                            json.loads((self.dir / 'c2' / 'avisos.json').read_text(encoding='utf-8'))))

    def test_migliorisi_skips_details_of_known_listings(self):
        listing_page = ('<a href="/propiedad/ver/a1/x"> <div> <img title="DEPARTAMENTO. 2 ambientes. VENTA. '
                        'Almagro. CALLE"> </div></a><a href="/propiedad/ver/a2/y"> <div> <img title="DEPARTAMENTO.'
                        ' 2 ambientes. VENTA. Almagro. CALLE"> </div></a>')
        detail = '<p>Precio U$S 100.000</p><td>Superficie Cubierta</td><td>45 m2</td>'
        calls = []

        def fetch(url, params=None):
            calls.append(url)
            return 200, listing_page if 'busqueda' in url else ('' if 'robots' in url else detail)
        client = PoliteClient(fetch=fetch, pause_s=0, sleep=lambda s: None)
        listings, skipped = scrape_migliorisi(client, '2026-11-09', 10, known=frozenset({'migliorisi:a1'}))
        self.assertEqual([l['listing_id'] for l in listings], ['migliorisi:a2'])
        self.assertEqual(skipped['ya_conocido'], 1)
        self.assertFalse(any('/propiedad/ver/a1/' in c for c in calls))
        # Las conocidas ocupan la ventana de recientes: con tope 1, no se baja a la ficha siguiente.
        window, skipped = scrape_migliorisi(client, '2026-11-09', 1, known=frozenset({'migliorisi:a1'}))
        self.assertEqual((window, skipped['ya_conocido']), ([], 1))
