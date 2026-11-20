"""Pruebas del ETL y el EDA del flujo Analytics con datos ficticios."""

import json
import tempfile
import unittest
from pathlib import Path

from precio_entorno.analytics.EDA import eda
from precio_entorno.analytics.ETL import CLEAN_COLUMNS, etl
from precio_entorno.analytics.preprocessing import read_clean, to_csv
from precio_entorno.analytics.tooling_business import SHEETS, clear_body, sheets_body

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

    def test_clean_csv_has_no_nulls_and_flags_every_imputation(self):
        crimes = self.crimes.read_text(encoding='utf-8') + '\n' + crime(6, 'Robo', 'BOEDO', 5)
        self.crimes.write_text(crimes, encoding='utf-8')
        raw = json.dumps([
            aviso(1, 'remax', 'Almagro', 150000, area=60, total_area_m2=70, expenses=90000,
                  latitude=-34.60, longitude=-58.42),
            aviso(2, 'remax', 'Almagro', 120000, latitude=-34.62, longitude=-58.44),
            aviso(3, 'migliorisi', 'Almagro', 110000, latitude=None, longitude=None),   # Sin pin.
            aviso(4, 'zonaprop', 'Almagro', 100000, latitude=None),                     # Medio par.
            aviso(5, 'migliorisi', 'Boedo', 100000, latitude=None, longitude=None),     # Barrio sin pines.
        ]).encode()
        clean, report = etl(raw, 'avisos.json', self.crimes)
        self.assertEqual(int(clean.isna().sum().sum()), 0)
        self.assertEqual(int(read_clean(to_csv(clean)).isna().sum().sum()), 0)
        rows = clean.set_index('id')

        # Superficie total: la publicada se respeta; la faltante toma la cubierta y queda marcada.
        self.assertEqual(rows.at['remax:1', 'superficie_total_m2'], 70)
        self.assertFalse(rows.at['remax:1', 'superficie_total_imputada'])
        self.assertEqual(rows.at['remax:2', 'superficie_total_m2'], 50)
        self.assertTrue(rows.at['remax:2', 'superficie_total_imputada'])

        # Expensas: no hay columna de montos, solo si se informaron.
        self.assertNotIn('expensas_ars', clean.columns)
        self.assertTrue(rows.at['remax:1', 'expensas_informadas'])
        self.assertFalse(rows.at['remax:2', 'expensas_informadas'])

        # Coordenadas: mediana de los pines publicados del barrio; si no hay, de la comuna.
        self.assertEqual(rows.at['remax:1', 'ubicacion_origen'], 'publicada')
        for i in ('migliorisi:3', 'zonaprop:4'):
            self.assertEqual(rows.at[i, 'ubicacion_origen'], 'mediana_barrio')
            self.assertFalse(rows.at[i, 'tiene_pin'])
            self.assertAlmostEqual(rows.at[i, 'latitud'], -34.61)
            self.assertAlmostEqual(rows.at[i, 'longitud'], -58.43)
        self.assertEqual(rows.at['migliorisi:5', 'ubicacion_origen'], 'mediana_comuna')
        self.assertAlmostEqual(rows.at['migliorisi:5', 'latitud'], -34.61)

        nulls = report['tratamiento_nulls']
        self.assertEqual(nulls['superficie_total_m2']['filas_imputadas'], 4)
        self.assertEqual(nulls['expensas_ars']['faltantes'], 4)
        self.assertEqual(nulls['latitud_longitud']['por_origen'],
                         {'publicada': 2, 'mediana_barrio': 2, 'mediana_comuna': 1})
        self.assertEqual(nulls['nulls_finales'], 0)

        # El EDA mide la cobertura de lo publicado, no de lo imputado, y correlaciona solo pines publicados.
        tables = eda(read_clean(to_csv(clean)), report)
        fuentes = tables['fuentes'].set_index('fuente')
        self.assertEqual(fuentes.at['remax', 'pct_con_expensas'], 50.0)
        self.assertEqual(fuentes.at['remax', 'pct_con_superficie_total'], 50.0)
        self.assertEqual(fuentes.at['migliorisi', 'pct_con_pin'], 0.0)
        corr = tables['correlaciones'].set_index('columna')
        self.assertEqual(corr.at['latitud', 'n'], 2)
        self.assertEqual(corr.at['ambientes', 'n'], 5)

    def test_etl_fails_instead_of_writing_nulls(self):
        # Palermo no está en el archivo de delitos: no hay comuna ni contexto delictivo para ese barrio.
        raw = json.dumps([aviso(1, 'remax', 'Palermo', 150000), aviso(2, 'remax', 'Almagro', 150000)]).encode()
        with self.assertRaisesRegex(ValueError, 'nulls en: comuna'):
            etl(raw, 'avisos.json', self.crimes)

    def test_etl_rejects_file_without_valid_listings(self):
        with self.assertRaises(ValueError):
            etl(json.dumps([aviso(9, 'remax', 'Atlantis', 1)]).encode(), 'avisos.json', self.crimes)


if __name__ == '__main__':
    unittest.main()
