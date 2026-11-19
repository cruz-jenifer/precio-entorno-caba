"""Contrastes entre barrios sobre datos ficticios separados del catálogo real."""
import unittest

import numpy as np
import pandas as pd
from scipy import stats

from precio_entorno.anova_barrios import analyze, holm


class AnovaTests(unittest.TestCase):
    def sample(self):
        rng = np.random.default_rng(123)
        return pd.DataFrame([{'grupo': f'ficticio:{b}:{i}', 'neighborhood': b, 'precio_m2': x,
                              'currency': 'USD'}
                             for b, base, sd in [('A', 1500, 50), ('B', 2000, 100), ('C', 3000, 300)]
                             for i, x in enumerate(rng.normal(base, sd, 20))])

    def test_reference_and_sum_of_squares(self):
        data = self.sample()
        report, _, table, pairs = analyze(data)
        arrays = [g['precio_m2'].to_numpy() for _, g in data.groupby('neighborhood')]
        self.assertAlmostEqual(report['welch']['F'], stats.f_oneway(*arrays, equal_var=False).statistic)
        self.assertTrue(report['welch']['rechaza_h0'])
        self.assertEqual(len(pairs), 3)
        self.assertAlmostEqual(table.iloc[2]['suma_cuadrados'],
                               np.sum((data['precio_m2'] - data['precio_m2'].mean()) ** 2))

    def test_duplicate_copies_do_not_increase_sample_or_change_test(self):
        data = self.sample()
        one = analyze(data)[0]
        two = analyze(pd.concat([data, data]))[0]
        self.assertEqual(two['unidades_analizadas'], len(data))
        self.assertEqual(one['welch'], two['welch'])

    def test_holm_known_example(self):
        np.testing.assert_allclose(holm([.04, .001, .03]), [.06, .003, .06])

    def test_invalid_input_and_conflicting_groups(self):
        data = self.sample()
        for bad in [data.assign(precio_m2=-1), data.assign(currency='ARS'),
                    data.assign(grupo='mismo'), data.drop(columns='neighborhood')]:
            with self.assertRaises(ValueError):
                analyze(bad)

    def test_low_coverage_is_reported(self):
        data = self.sample()
        data = data.drop(data[data['neighborhood'].eq('C')].index[3:])
        result, _, _, pairs = analyze(data)
        self.assertEqual(result['barrios_excluidos'], ['C'])
        self.assertEqual(result['barrios_incluidos'], 2)
        self.assertEqual(len(pairs), 1)
