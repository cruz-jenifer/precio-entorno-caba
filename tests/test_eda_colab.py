"""Pruebas del paquete de datos para el EDA en Colab, con datos ficticios."""

import json
import sqlite3
import tempfile
import unittest
import zipfile
from contextlib import closing
from pathlib import Path

import pandas as pd

from precio_entorno.eda_colab import DELITOS_FILES, ENTORNO_FILES, SALE_COLUMNS, build


def make_db(path, rows):
    with closing(sqlite3.connect(path)) as db, db:
        db.execute('CREATE TABLE listings (id TEXT PRIMARY KEY, neighborhood TEXT, price INTEGER, '
                   'covered_area INTEGER, rooms INTEGER)')
        db.execute('CREATE TABLE listing_details (listing_id TEXT PRIMARY KEY, source TEXT, url TEXT, captured_at TEXT, '
                   'currency TEXT, total_area_m2 REAL, latitude REAL, longitude REAL, location_accuracy_m REAL, '
                   'expenses REAL, contacto TEXT)')
        for i, barrio, price, currency in rows:
            db.execute('INSERT INTO listings VALUES (?, ?, ?, 40, 2)', (i, barrio, price))
            db.execute('INSERT INTO listing_details VALUES (?, ?, ?, ?, ?, 45, -34.6, -58.4, NULL, NULL, ?)',
                       (i, 'ficticio', f'https://example.invalid/{i}', '2026-11-08 10:00:00', currency, 'no-copiar'))


class EdaColabTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        d = Path(temp.name)
        model = pd.DataFrame([{c: None for c in SALE_COLUMNS + ['ventana', 'telefono']} for _ in range(2)])
        model['id'] = ['a:1', 'b:2']
        model['captured_at'] = '2026-11-08 10:00:00'
        model['telefono'] = 'no-copiar'
        model.to_csv(d / 'dataset_modelo.csv', index=False)
        make_db(d / 'venta.sqlite3', [('a:1', 'Caballito', 100000, 'USD')])
        make_db(d / 'alquiler.sqlite3', [('mob:1', 'Almagro', 700000, 'ARS'), ('mob:2', 'Almagro', 600, 'USD')])
        (d / 'entorno').mkdir()
        (d / 'delitos').mkdir()
        for name in ENTORNO_FILES:
            (d / 'entorno' / name).write_text('{}', encoding='utf-8')
        for name in DELITOS_FILES:
            (d / 'delitos' / name).write_text('barrio\nAlmagro\n', encoding='utf-8')
        self.out, self.meta = build(d / 'dataset_modelo.csv', d / 'venta.sqlite3', d / 'alquiler.sqlite3',
                                    d / 'entorno', d / 'delitos', d / 'salida' / 'bundle.zip')

    def test_bundle_has_expected_files_and_no_contacts(self):
        with zipfile.ZipFile(self.out) as z:
            names = set(z.namelist())
            self.assertIn('venta.csv', names)
            self.assertIn('entorno/barrios.geojson', names)
            self.assertIn('delitos/barrio_anio.csv', names)
            for name in names:
                self.assertNotIn('no-copiar', z.read(name).decode('utf-8'), name)
            venta = pd.read_csv(z.open('venta.csv'))
            alquiler = pd.read_csv(z.open('alquiler.csv'))
            meta = json.loads(z.read('meta.json'))
        self.assertEqual(list(venta.columns), SALE_COLUMNS + ['url'])
        self.assertEqual(venta.set_index('id').loc['a:1', 'url'], 'https://example.invalid/a:1')
        self.assertTrue(pd.isna(venta.set_index('id').loc['b:2', 'url']))
        self.assertEqual(alquiler['agency'].unique().tolist(), ['mob'])
        self.assertEqual(meta['alquiler']['por_moneda'], {'ARS': 1, 'USD': 1})
        self.assertIn('no tasaciones', meta['aviso'])


if __name__ == '__main__':
    unittest.main()
