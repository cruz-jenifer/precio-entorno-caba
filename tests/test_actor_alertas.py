"""Pruebas del núcleo del Actor de alertas, con sitios ficticios y sin red."""

import unittest
from collections import Counter
from unittest.mock import patch

from precio_entorno import inmobiliarias
from precio_entorno.actor_alertas import parse_input, run
from precio_entorno.inmobiliarias import Blocked, PoliteClient, record

SEARCHES = [
    {'id': 1, 'operacion': 'venta', 'barrio': 'caballito', 'presupuesto': 110000, 'superficie': 40, 'ambientes': 2},
    {'id': 'b', 'operacion': 'venta', 'barrio': 'Almagro', 'presupuesto': 200000, 'superficie': 30, 'ambientes': 1,
     'ambientesOMas': True},
]


def site(listings):
    """Sitio ficticio: cada aviso es (id, barrio, precio, ambientes)."""
    def scrape(client, captured_at, max_listings, known=frozenset()):
        return [record('ficticia', i, f'https://example.invalid/{i}', captured_at, price=price, currency='USD',
                       covered_area_m2=45, rooms=rooms, neighborhood=hood)
                for i, hood, price, rooms in listings][:max_listings], Counter()
    return scrape


def blocked(client, captured_at, max_listings, known=frozenset()):
    raise Blocked('HTTP 403')


class ParseInputTests(unittest.TestCase):
    def test_defaults_and_normalized_searches(self):
        config = parse_input({'busquedas': SEARCHES, 'autorizacionConfirmada': True})
        self.assertEqual((config['max_listings'], config['alert_first']), (50, False))
        self.assertEqual(config['sites'], list(inmobiliarias.DEFAULT_SITES))
        first, second = config['searches']
        self.assertEqual((first['neighborhood'], first['currency'], first['or_more']), ('Caballito', 'USD', False))
        self.assertTrue(second['or_more'])

    def test_rejects_unsafe_or_invalid_input(self):
        ok = {'busquedas': SEARCHES, 'autorizacionConfirmada': True}
        cases = {
            'autorizacionConfirmada': {**ok, 'autorizacionConfirmada': False},
            'no habilitados': {**ok, 'sitios': ['zonaprop']},
            'barrio oficial': {**ok, 'busquedas': [{**SEARCHES[0], 'barrio': 'Gotham'}]},
            'moneda': {**ok, 'busquedas': [{**SEARCHES[0], 'moneda': 'ARS'}]},  # Venta solo en USD.
            'único': {**ok, 'busquedas': [SEARCHES[0], SEARCHES[0]]},
            'entre 1 y 200': {**ok, 'maxAvisosPorSitio': 500},
            'al menos una': {**ok, 'busquedas': []},
        }
        for message, raw in cases.items():
            with self.subTest(message), self.assertRaisesRegex(ValueError, message):
                parse_input(raw)


class RunTests(unittest.TestCase):
    def setUp(self):
        self.client = PoliteClient(fetch=lambda url, params=None: (200, ''), pause_s=0, sleep=lambda s: None)

    def run_with(self, sites, seen, alert_first=False, max_listings=50):
        with patch.dict(inmobiliarias.SITES, sites, clear=True), \
                patch('precio_entorno.actor_alertas.DEFAULT_SITES', tuple(sites)):
            config = parse_input({'busquedas': SEARCHES, 'autorizacionConfirmada': True, 'sitios': list(sites),
                                  'maxAvisosPorSitio': max_listings, 'alertarPrimeraCorrida': alert_first})
            return run(config, seen, client=self.client, echo=lambda line: None, now='2026-11-09T12:00:00+00:00')

    def test_first_run_is_a_baseline_and_then_only_new_matches_alert(self):
        listings = [('1', 'Caballito', 100000, 2), ('2', 'Almagro', 150000, 3)]
        items, seen, summary = self.run_with({'ficticia': site(listings)}, {})
        self.assertEqual((items, summary['alertas'], summary['operaciones']['venta']['linea_base']), ([], 0, True))
        self.assertEqual(seen, {'venta': ['ficticia:1', 'ficticia:2']})

        listings += [('3', 'Caballito', 105000, 2),   # encaja en la búsqueda 1
                     ('4', 'Caballito', 150000, 2),   # supera el presupuesto
                     ('5', 'Almagro', 120000, 4),     # encaja en la búsqueda b (ambientes o más)
                     ('6', 'Palermo', 90000, 2)]      # otro barrio
        items, seen, summary = self.run_with({'ficticia': site(listings)}, seen)
        self.assertEqual([(i['busqueda'], i['avisos']) for i in items], [(1, ['ficticia:3']), ('b', ['ficticia:5'])])
        self.assertEqual((summary['estado'], summary['alertas'], summary['busquedas_con_avisos']), ('ok', 2, 2))
        self.assertEqual(summary['operaciones']['venta']['nuevos'], 4)
        self.assertEqual(items[1]['descripcion'], 'Almagro · hasta USD 200.000 · 30 m² o más · 1 ambientes o más')
        self.assertEqual(items[0]['alertas'][0]['url'], 'https://example.invalid/3')
        self.assertEqual(len(seen['venta']), 6)

        again, _, summary = self.run_with({'ficticia': site(listings)}, seen)
        self.assertEqual((again, summary['alertas']), ([], 0))  # Nada se alerta dos veces.

    def test_alert_first_run_when_asked(self):
        items, _, _ = self.run_with({'ficticia': site([('1', 'Caballito', 100000, 2)])}, {}, alert_first=True)
        self.assertEqual([i['avisos'] for i in items], [['ficticia:1']])

    def test_blocked_site_marks_partial_and_keeps_other_sites(self):
        sites = {'bloqueada': blocked, 'ficticia': site([('1', 'Caballito', 100000, 2)])}
        items, seen, summary = self.run_with(sites, {'venta': []})
        self.assertEqual(summary['estado'], 'parcial')
        self.assertEqual(summary['operaciones']['venta']['sitios']['bloqueada'], 'detenido: HTTP 403')
        self.assertEqual([i['avisos'] for i in items], [['ficticia:1']])

    def test_unexpected_failure_is_reported_and_seen_state_untouched(self):
        with patch('precio_entorno.actor_alertas.parse_listings', side_effect=OSError('disco lleno')):
            items, seen, summary = self.run_with({'ficticia': site([('1', 'Caballito', 100000, 2)])}, {'venta': ['x']})
        self.assertEqual((items, seen), ([], {}))
        self.assertEqual((summary['estado'], summary['error']), ('error', 'OSError: disco lleno'))


if __name__ == '__main__':
    unittest.main()
