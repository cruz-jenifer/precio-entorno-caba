"""Prueba del reporte del ETL con una captura y un CSV de delitos mínimos."""

import json
import tempfile
import unittest
from pathlib import Path

from precio_entorno.etl_reporte import run
from precio_entorno.inmobiliarias import CATALOG

CRIMES = ('"id-mapa","fecha","franja","tipo","barrio","cantidad"\n'
          '1,"2025-03-02",14,"Robo","CABALLITO",1\n'
          '2,"2025-03-05",,"Hurto","CABALLITO",1\n'
          '3,"2025-03-05",9,"Hurto",,1\n')


class EtlReportTests(unittest.TestCase):
    def test_counts_reimport_and_invalid_batch(self):
        with tempfile.TemporaryDirectory() as temp:
            capture = Path(temp) / 'captura'
            capture.mkdir()
            rows = [{'listing_id': f'x:{i}', 'source': CATALOG, 'url': f'https://example.invalid/{i}',
                     'captured_at': '2026-11-09T12:00:00', 'price': 120000, 'currency': 'USD',
                     'covered_area_m2': 50, 'rooms': 2, 'neighborhood': 'Caballito'} for i in range(3)]
            rows.append(dict(rows[0], listing_id='x:malo', neighborhood='Gotham'))
            (capture / 'avisos.json').write_text(json.dumps(rows), encoding='utf-8')
            (capture / 'registro.json').write_text(json.dumps({
                'avisos': 4, 'sitios': {'x': {'avisos': 4, 'omitidos': {'barrio_ambiguo': 2}}},
                'posibles_duplicados_entre_inmobiliarias': [['x:1', 'y:1']]}), encoding='utf-8')
            crimes = Path(temp) / 'delitos.csv'
            crimes.write_text(CRIMES, encoding='utf-8')
            result = run(capture, crimes)
        self.assertEqual((result['avisos']['leidas'], result['avisos']['aceptadas'], result['avisos']['descartadas']),
                         (4, 3, 1))
        self.assertEqual((result['reimportacion']['aceptadas'], result['reimportacion']['duplicadas'],
                          result['reimportacion']['alertas']), (0, 3, 0))
        self.assertEqual(result['captura']['posibles_duplicados_entre_inmobiliarias'], {'grupos': 1, 'avisos': 2})
        self.assertEqual((result['delitos']['aceptadas'], result['delitos']['descartadas']), (2, 1))
        self.assertEqual(result['delitos']['faltantes']['franja'], 1)  # Se conserva como franja desconocida.
        self.assertEqual(result['lote_invalido']['aceptadas'], ['ficticio:ok'])
        self.assertEqual(result['lote_invalido']['descartadas'], 6)


if __name__ == '__main__':
    unittest.main()
