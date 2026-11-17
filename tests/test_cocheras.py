import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from precio_entorno import cocheras
from precio_entorno.api import create_app


class CocherasTests(unittest.TestCase):
    def setUp(self):
        self.row = {'id': 'prueba', 'fuente': 'sintetica', 'barrio': 'Almagro',
                    'precio': 100, 'moneda': 'USD', 'periodicidad': 'mensual',
                    'url': 'https://example.invalid/cochera', 'capturado': '2026-11-17',
                    'lat': -34.615, 'lon': -58.44}

    def test_duplicate_and_conflict(self):
        self.assertEqual(len(cocheras.validate([self.row, self.row])), 1)
        with self.assertRaises(ValueError):
            cocheras.validate([self.row, dict(self.row, precio=200)])

    def test_expenses_require_currency_and_preserve_unknown(self):
        self.assertIsNone(cocheras.validate([self.row])[0]['expensas'])
        with self.assertRaises(ValueError):
            cocheras.validate([dict(self.row, expensas=20000)])
        item = cocheras.validate([dict(self.row, expensas=0, moneda_expensas='ARS')])[0]
        self.assertEqual(item['expensas'], 0)

    def test_radius_includes_neighboring_barrio_and_requires_both_coordinates(self):
        with TestClient(create_app()) as client, patch.object(cocheras, 'load', return_value=cocheras.validate([self.row])):
            params = {'barrio': 'Caballito', 'moneda': 'USD', 'presupuesto': 150}
            self.assertEqual(client.get('/api/cocheras', params=params).json()['avisos'], [])
            params.update(lat=-34.615, lon=-58.441)
            response = client.get('/api/cocheras', params=params)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(len(response.json()['avisos']), 1)
            del params['lon']
            self.assertEqual(client.get('/api/cocheras', params=params).status_code, 422)

    def test_missing_and_invalid_catalog(self):
        with TestClient(create_app()) as client:
            with patch.object(cocheras, 'load', return_value=None):
                self.assertFalse(client.get('/api/cocheras?barrio=Caballito').json()['disponible'])
            with patch.object(cocheras, 'load', side_effect=ValueError('invalid')):
                self.assertEqual(client.get('/api/cocheras?barrio=Caballito').status_code, 503)
