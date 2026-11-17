import unittest

from precio_entorno.verificar_cocheras import monthly_evidence


class MonthlyEvidenceTests(unittest.TestCase):
    def test_visible_price_and_currency_must_match(self):
        self.assertTrue(monthly_evidence('<p>Alquiler: $150.000 / mes (+ expensas)</p>', 150000, 'ARS'))
        self.assertFalse(monthly_evidence('$150.000 / mes', 170000, 'ARS'))
        self.assertFalse(monthly_evidence('US$150.000 / mes', 150000, 'ARS'))

    def test_ambiguous_and_embedded_prices_are_not_evidence(self):
        self.assertFalse(monthly_evidence('<script>"$150.000 / mes"</script>', 150000, 'ARS'))
        self.assertFalse(monthly_evidence('$150.000 / mes o $170.000 / mes', 150000, 'ARS'))
        self.assertFalse(monthly_evidence('Alquiler $150.000. Contrato mensual.', 150000, 'ARS'))


if __name__ == '__main__':
    unittest.main()
