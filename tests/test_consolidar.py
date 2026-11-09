"""Pruebas de la consolidación de capturas y de los grupos de posibles duplicados."""

import json
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from precio_entorno.consolidar import consolidate
from precio_entorno.modelo import duplicate_groups


def listing(lid, price=120000, area=50, barrio='Caballito'):
    return {'listing_id': lid, 'source': 'inmobiliarias-autorizadas', 'agency': lid.split(':')[0],
            'url': f'https://example.invalid/{lid}', 'captured_at': '2026-11-08T12:00:00+00:00', 'price': price,
            'currency': 'USD', 'covered_area_m2': area, 'total_area_m2': None, 'rooms': 2,
            'neighborhood': barrio, 'latitude': None, 'longitude': None}


def capture(root, name, items, log):
    folder = root / name
    folder.mkdir()
    (folder / 'avisos.json').write_text(json.dumps(items), encoding='utf-8')
    (folder / 'registro.json').write_text(json.dumps(log), encoding='utf-8')
    return folder


class ConsolidarTests(unittest.TestCase):
    def test_merges_captures_logs_and_cross_source_duplicates(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            a = capture(root, 'inmo', [listing('remax:1'), listing('remax:2', price=99000)],
                        {'catalogo': 'inmobiliarias-autorizadas',
                         'sitios': {'remax': {'avisos': 2, 'omitidos': {'x': 1}, 'pedidos': 3, 'segundos': 6}}})
            b = capture(root, 'zp', [listing('zonaprop:9'), listing('remax:1')],
                        {'catalogo': 'inmobiliarias-autorizadas',
                         'corridas': [{'avisos': 2, 'omitidos': {'fuera_de_caba': 4}}]})
            listings, log = consolidate([a, b], root / 'salida')
            saved = json.loads((root / 'salida' / 'registro.json').read_text(encoding='utf-8'))
        self.assertEqual([x['listing_id'] for x in listings], ['remax:1', 'remax:2', 'zonaprop:9'])
        self.assertEqual(saved['sitios']['zonaprop'], {'estado': 'completo', 'avisos': 2,
                                                        'omitidos': {'fuera_de_caba': 4}, 'pedidos': 1})
        self.assertEqual(saved['sitios']['remax']['segundos'], 6)
        self.assertEqual(log['posibles_duplicados_entre_inmobiliarias'], [['remax:1', 'zonaprop:9']])

    def test_rejects_mixed_catalogs(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            a = capture(root, 'v', [listing('remax:1')], {'catalogo': 'inmobiliarias-autorizadas'})
            b = capture(root, 'a', [listing('mob:1')], {'catalogo': 'inmobiliarias-alquiler'})
            with self.assertRaisesRegex(ValueError, 'catálogos distintos'):
                consolidate([a, b], root / 'salida')

    def test_duplicate_groups_only_join_different_sources(self):
        df = pd.DataFrame({'id': ['remax:1', 'zonaprop:9', 'remax:2', 'remax:3'],
                           'agency': ['remax', 'zonaprop', 'remax', 'remax'],
                           'neighborhood': ['Caballito'] * 4, 'rooms': [2] * 4,
                           'covered_area': [50.2, 49.8, 70, 70], 'price': [120400, 119800, 150000, 150000]})
        groups = list(duplicate_groups(df))
        self.assertEqual(groups[0], groups[1])
        self.assertTrue(groups[0].startswith('dup:'))
        self.assertEqual(groups[2:], ['remax:2', 'remax:3'])


if __name__ == '__main__':
    unittest.main()
