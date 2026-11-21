"""Validación temporal: exclusiones, formato de Zonaprop y resumen por segmento, con datos ficticios."""

import unittest

import numpy as np
import pandas as pd

from precio_entorno.validacion_temporal import evaluate, exclude_seen, summarize, zonaprop_rows


def listing(i, barrio='Caballito', rooms=2, area=40.0, price=100_000, captured='2026-11-20', segment='zonaprop_20261120'):
    return {'id': i, 'neighborhood': barrio, 'rooms': rooms, 'covered_area': area, 'price': price,
            'precio_m2': price / area, 'currency': 'USD', 'captured_at': pd.Timestamp(captured), 'segmento': segment}


class FakeModel:
    def predict(self, x):
        return np.full(len(x), 2500.0)


BUNDLE = {'model': FakeModel(), 'numeric': ['covered_area', 'rooms'], 'categorical': ['neighborhood'],
          'barrios': ['Caballito', 'Almagro'], 'version': 'ficticio'}


class TemporalValidationTests(unittest.TestCase):
    def test_zonaprop_rows_use_importer_names(self):
        row = zonaprop_rows([{'id': 'zonaprop:1', 'url': 'https://example.invalid/1', 'barrio_busqueda': 'Almagro',
                              'precio': 90000.0, 'moneda': 'USD', 'ambientes': 2.0, 'cubierta': 40.0, 'total': 45.0,
                              'lat': -34.6, 'lon': -58.42}], '2026-11-20T04:55:39+00:00')[0]
        self.assertEqual(row['listing_id'], 'zonaprop:1')
        self.assertEqual((row['covered_area_m2'], row['total_area_m2'], row['rooms']), (40.0, 45.0, 2.0))
        self.assertEqual((row['neighborhood'], row['latitude'], row['longitude']), ('Almagro', -34.6, -58.42))
        self.assertEqual(row['captured_at'], '2026-11-20T04:55:39+00:00')

    def test_excludes_same_id_and_probable_same_property_and_keeps_latest_capture(self):
        train = pd.DataFrame([listing('remax:1'), listing('century21:2', area=55.0, price=150_000)])
        new = pd.DataFrame([
            listing('remax:1'),                                         # Mismo ID.
            listing('zonaprop:9', area=55.4, price=150_400),            # Mismo inmueble, otra fuente.
            listing('zonaprop:7', area=60.0, price=130_000, captured='2026-11-13'),
            listing('zonaprop:7', area=60.0, price=125_000, captured='2026-11-17'),  # Captura más nueva.
        ])
        kept, counts = exclude_seen(new, train)
        self.assertEqual(kept['id'].tolist(), ['zonaprop:7'])
        self.assertEqual(kept['price'].iloc[0], 125_000)
        self.assertEqual(counts, {'avisos_validos': 3, 'mismo_id': 1, 'mismo_inmueble_probable': 1, 'evaluados': 1})

    def test_summary_reports_gain_interval_and_bias(self):
        y = np.array([2000.0, 2600.0, 3000.0, 2400.0])
        result = summarize(y, model=np.array([2100.0, 2500.0, 2800.0, 2400.0]), baseline=np.full(4, 2500.0))
        self.assertEqual(result['modelo']['mae'], 100.0)
        self.assertEqual(result['linea_de_base']['mae'], 300.0)
        self.assertEqual(result['mejora_mae_pct'], 66.7)
        low, high = result['mejora_mae_ic95_usd_m2']
        self.assertLessEqual(low, high)
        self.assertEqual(result['pct_avisos_subestimados'], 50.0)

    def test_evaluate_splits_segments_and_uses_training_comparables(self):
        train = pd.DataFrame([listing(f't:{i}', price=100_000 + 1_000 * i) for i in range(6)])
        new = pd.DataFrame([listing('zonaprop:1', price=104_000),
                            listing('remax:9', barrio='Almagro', price=90_000, segment='inmobiliarias_13a17'),
                            listing('remax:10', price=80_000, segment='inmobiliarias_13a17').copy() | {'currency': 'ARS'}])
        table, report = evaluate(new, train, BUNDLE)
        self.assertEqual(sorted(report['segmentos']), ['inmobiliarias_13a17', 'zonaprop_20261120'])
        self.assertEqual(report['todos']['avisos'], 2)                  # El aviso en pesos no entra.
        self.assertEqual(report['niveles_linea_de_base'], {'barrio_y_ambientes': 1, 'toda_la_muestra': 1})
        self.assertTrue((table['prediccion_usd_m2'] == 2500.0).all())


if __name__ == '__main__':
    unittest.main()
