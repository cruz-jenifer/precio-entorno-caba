import unittest

from precio_entorno.ecomscrape_export import adapt_export
from precio_entorno.run_pilot import batch_stats


class EcomScrapeTests(unittest.TestCase):
    def test_nested_export_uses_sale_price_and_official_neighborhood(self):
        row = {
            'posting_id': '12345678',
            'url': '/propiedades/clasificado/aviso-ficticio-12345678.html',
            'real_estate_type': {'name': 'Departamentos'},
            'main_features': {'c_f_t1': {'value': '2'}, 'c_f_t100': {'value': '49'},
                              'c_f_t101': {'value': '42.5'}},
            'price_operation_types': [
                {'operation_type': {'name': 'Alquiler'}, 'prices': [{'amount': 900, 'currency': 'USD'}]},
                {'operation_type': {'name': 'Venta'}, 'prices': [{'amount': 105000, 'currency': 'USD'}]},
            ],
            'posting_location': {
                'location': {'name': 'Caballito Norte', 'label': 'ZONA',
                             'parent': {'name': 'Caballito', 'label': 'BARRIO'}},
                'posting_geolocation': {'geolocation': {'latitude': -34.62, 'longitude': -58.44}},
            },
            'publisher': {'name': 'Ficticio'},
        }
        rows = [row, row, dict(row, posting_id='12345679')]
        listings = adapt_export(rows, '2026-11-07')
        self.assertEqual((listings[0]['neighborhood'], listings[0]['price']), ('Caballito', 105000))
        self.assertNotIn('publisher', listings[0])
        stats = batch_stats(listings, len(rows))
        self.assertEqual((stats['comparables_con_barrio'], stats['duplicados'],
                          stats['fuera_de_alcance'], stats['pines_utilizables']), (1, 1, 1, 0))

