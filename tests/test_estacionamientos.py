import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient
from precio_entorno import entorno
from precio_entorno.api import create_app


class ParkingLocationsTests(unittest.TestCase):
    def test_barrio_radius_order_and_missing_coordinates(self):
        rows = [dict(name='Lejos', tooltip='Lejos', barrio='Caballito', lat=-34.62, lon=-58.45),
                dict(name='Vecino', tooltip='Vecino', barrio='Almagro', lat=-34.615, lon=-58.4401),
                dict(name='Cerca', tooltip='Cerca', barrio='Caballito', lat=-34.615, lon=-58.441)]
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp, 'resumen.json').write_text('{}')
            with patch('precio_entorno.api.entorno.load', return_value={'puntos': {'estacionamiento': rows}}), TestClient(create_app(entorno_dir=tmp)) as client:
                route = '/api/estacionamientos?barrio=Caballito'
                self.assertEqual(len(client.get(route).json()['estacionamientos']), 2)
                data = client.get(route + '&lat=-34.615&lon=-58.44&radio=300').json()
                self.assertEqual([r['nombre'] for r in data['estacionamientos']], ['Vecino', 'Cerca'])
                self.assertEqual(data['periodo'], entorno.GARAJES_PERIODO)
                for query in ('&lat=-34.615', '&lat=nan&lon=-58.44', '&radio=0', '&lat=0&lon=0'):
                    self.assertEqual(client.get(route + query).status_code, 422)

    def test_missing_layer_is_distinct_from_zero_results(self):
        with tempfile.TemporaryDirectory() as tmp, TestClient(create_app(entorno_dir=tmp)) as client:
            response = client.get('/api/estacionamientos?barrio=Caballito').json()
            self.assertFalse(response['disponible'])
            self.assertEqual(response['estacionamientos'], [])


if __name__ == '__main__':
    unittest.main()
