"""Pruebas de la conversión de datasets de Buenos Aires Data a puntos."""

import json
import tempfile
import unittest
from pathlib import Path

from precio_entorno.badata_poi import convert


def collection(features):
    return {'type': 'FeatureCollection', 'features': features}


class BadataPoiTests(unittest.TestCase):
    def test_parks_filter_classes_and_points_are_reprojected(self):
        square = [[[-58.44, -34.60], [-58.43, -34.60], [-58.43, -34.61], [-58.44, -34.60]]]
        with tempfile.TemporaryDirectory() as temp:
            src, dst = Path(temp) / 'src', Path(temp) / 'dst'
            src.mkdir()
            (src / 'espacio_verde_publico.geojson').write_text(json.dumps(collection([
                {'properties': {'clasificac': 'PLAZA', 'nombre': 'Plaza'}, 'geometry': {'type': 'Polygon', 'coordinates': square}},
                {'properties': {'clasificac': 'CANTERO CENTRAL'}, 'geometry': {'type': 'Polygon', 'coordinates': square}},
            ])), encoding='utf-8')
            point = {'type': 'Point', 'coordinates': [26549.56742604346, 69922.54409977954]}
            for name in ('establecimientos_educativos.geojson', 'hospitales.geojson'):
                (src / name).write_text(json.dumps(collection([{'properties': {'nam': 'X'}, 'geometry': point}])),
                                        encoding='utf-8')
            log = {r['nombre']: r for r in convert(src, dst)}
            self.assertEqual((log['parques']['elementos'], log['parques']['puntos']), (1, 4))
            self.assertIsNone(log['escuelas']['max_items'])
            hospital, = json.loads((dst / 'hospitales.json').read_text(encoding='utf-8'))
            self.assertAlmostEqual(hospital['lat'], -34.630, places=2)
            self.assertAlmostEqual(hospital['lon'], -58.392, places=2)
