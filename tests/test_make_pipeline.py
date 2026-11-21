"""Blueprint del escenario Analytics de Make, sin red ni tokens reales."""

import json
import unittest

from precio_entorno.analytics.tooling_business import PREDICTIONS_SHEET, SHEETS
from precio_entorno.make_pipeline import pipeline_blueprint


class PipelineBlueprintTests(unittest.TestCase):
    def setUp(self):
        self.flow = {m['id']: m for m in pipeline_blueprint('token-ficticio', 'usuario', 'ALMACENFICTICIO01')['flow']}

    def test_inference_runs_on_the_clean_csv_with_the_model_store(self):
        body = self.flow[8]['mapper']['jsonStringBodyContent']
        self.assertIn('"operacion":"inferencia"', body)
        self.assertIn('"almacenModelo":"ALMACENFICTICIO01"', body)
        self.assertIn('{{base64(toString(4.data))}}', body)    # El mismo CSV que lee el EDA.
        self.assertEqual(self.flow[9]['mapper']['body'], '{{toString(8.data)}}')

    def test_clear_includes_the_predictions_tab(self):
        ranges = json.loads(self.flow[6]['mapper']['body'])['ranges']
        self.assertEqual(ranges, list(SHEETS) + [PREDICTIONS_SHEET])

    def test_modules_are_in_order(self):
        self.assertEqual(sorted(self.flow), list(range(1, 10)))
        xs = [self.flow[i]['metadata']['designer']['x'] for i in range(1, 10)]
        self.assertEqual(xs, sorted(xs))


if __name__ == '__main__':
    unittest.main()
