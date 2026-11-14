"""Pruebas del ETL y el EDA del flujo Analytics con datos ficticios."""

import json
import tempfile
import unittest
from pathlib import Path

from precio_entorno.pipeline_analytics import CLEAN_COLUMNS, SHEETS, clear_body, eda, etl, read_clean, sheets_body, to_csv

CRIME_HEADER = '"id-mapa","anio","mes","dia","fecha","franja","tipo","subtipo","uso_arma","uso_moto","barrio","comuna","latitud","longitud","cantidad"'


def crime(i, tipo, barrio, comuna, arma='NO'):
    return f'{i},"2025","MARZO","LUNES","2025-03-0{i % 9 + 1}",10,"{tipo}","x","{arma}","NO","{barrio}",{comuna},"-34.61","-58.43",1'


def aviso(i, fuente, barrio, price, area=50, rooms=2, captured='2026-11-08T10:00:00+00:00', **extra):
    return {'listing_id': f'{fuente}:{i}', 'url': f'https://example.invalid/{i}', 'captured_at': captured,
            'price': price, 'currency': 'USD', 'covered_area_m2': area, 'rooms': rooms, 'neighborhood': barrio,
            'latitude': -34.61, 'longitude': -58.43, **extra}


class PipelineAnalyticsTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.crimes = Path(tmp.name) / 'delitos.csv'
        self.crimes.write_text('\n'.join([CRIME_HEADER,
                                          crime(1, 'Robo', 'CABALLITO', 6, 'SI'), crime(2, 'Hurto', 'CABALLITO', 6),
                                          crime(3, 'Amenazas', 'CABALLITO', 6), crime(4, 'Vialidad', 'CABALLITO', 6),
                                          crime(5, 'Robo', 'ALMAGRO', 5)]), encoding='utf-8')
        self.raw = json.dumps([
            aviso(1, 'remax', 'Caballito', 120000),
            aviso(1, 'remax', 'Caballito', 118000, captured='2026-11-09T10:00:00+00:00'),  # Captura más nueva.
            aviso(2, 'zonaprop', 'Caballito', 118000),                                     # Posible duplicado.
            aviso(3, 'century21', 'Almagro', 150000, area=60, rooms=3),
            aviso(4, 'century21', 'Almagro', 90000, area=40, rooms=1, latitude=None, longitude=None),
            aviso(5, 'remax', 'Atlantis', 100000),                                         # Barrio inválido.
            aviso(6, 'remax', 'Almagro', None),                                            # Sin precio.
        ]).encode()

    def test_etl_cleans_dedups_and_adds_crime_context_by_barrio(self):
        clean, report = etl(self.raw, 'avisos.json', self.crimes)
        self.assertEqual(list(clean.columns), CLEAN_COLUMNS)
        self.assertEqual(report['filas_leidas'], 7)
        self.assertEqual(report['filas_descartadas'], 2)
        self.assertEqual(report['capturas_repetidas_unificadas'], 1)
        self.assertEqual(len(clean), 4)
        row = clean.set_index('id').loc['remax:1']
        self.assertEqual(row['precio'], 118000)
        self.assertEqual(row['precio_m2_usd'], 2360.0)
        self.assertTrue(row['posible_duplicado'])
        self.assertEqual(row['grupo_duplicado'], clean.set_index('id').at['zonaprop:2', 'grupo_duplicado'])
        # Caballito: robo + hurto + amenazas; los siniestros viales no son delitos.
        self.assertEqual(row['delitos_barrio'], 3)
        self.assertEqual(row['robos_hurtos_barrio'], 2)
        self.assertEqual(row['pct_con_arma_barrio'], 33.3)
        self.assertEqual(row['comuna'], 6)
        self.assertEqual(row['periodo_delitos'], '2025-03-02 a 2025-03-06')
        self.assertEqual(row['unidad_delitos'], 'barrio')

    def test_eda_tables_from_clean_csv_and_sheets_body(self):
        clean, report = etl(self.raw, 'avisos.json', self.crimes)
        tables = eda(read_clean(to_csv(clean).encode()), report)
        self.assertEqual(set(tables), set(SHEETS))
        resumen = tables['resumen'].iloc[0]
        self.assertEqual(resumen['avisos'], 4)
        self.assertEqual(resumen['barrios'], 2)
        self.assertEqual(resumen['filas_descartadas'], 2)
        barrios = tables['barrios'].set_index('barrio')
        self.assertEqual(barrios.at['Almagro', 'avisos'], 2)
        self.assertEqual(barrios.at['Almagro', 'pct_con_pin'], 50.0)
        self.assertEqual(barrios.at['Almagro', 'muestra_chica'], 'si')
        self.assertEqual(set(tables['ambientes']['ambientes']), {'1', '2', '3'})
        self.assertEqual(tables['distribucion']['avisos'].sum(), 4)

        body = sheets_body(tables)
        self.assertEqual([d['range'] for d in body['data']], [f'{s}!A1' for s in SHEETS])
        json.dumps(body)  # Serializable: sin NaN ni tipos de numpy.
        self.assertNotIn('NaN', json.dumps(body))
        self.assertEqual(clear_body()['ranges'], list(SHEETS))

    def test_etl_rejects_file_without_valid_listings(self):
        with self.assertRaises(ValueError):
            etl(json.dumps([aviso(9, 'remax', 'Atlantis', 1)]).encode(), 'avisos.json', self.crimes)


if __name__ == '__main__':
    unittest.main()
