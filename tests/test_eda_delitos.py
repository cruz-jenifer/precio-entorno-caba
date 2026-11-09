import tempfile
import unittest
from pathlib import Path

from precio_entorno.eda_delitos import load, load_many, tables

HEADER = '"id-mapa","anio","mes","dia","fecha","franja","tipo","subtipo","uso_arma","uso_moto","barrio","comuna","latitud","longitud","cantidad"\n'
ROWS = [
    '1,"2024","ENERO","LUNES","2024-01-01",21,"Robo","Robo total","SI","NO","CABALLITO",6,"-34.62","-58.44",1',
    '1,"2024","ENERO","LUNES","2024-01-01",21,"Robo","Robo total","SI","NO","CABALLITO",6,"-34.62","-58.44",1',
    '2,"2024","ENERO","MARTES","2024-01-02",12,"Hurto","Hurto automotor","NO","SI","CABALLITO",6,"-34.62","-58.44",1',
    '3,"2024","ENERO","MARTES","2024-01-02",NULL,"Vialidad","Lesiones por siniestros viales","NO","NO","CABALLITO",6,"-34.62","-58.44",1',
    '4,"2024","FEBRERO","JUEVES","2024-02-01",3,"Robo","Robo total","NO","NO","ALMAGRO",5,"-34.60","-58.42",1',
    '5,"2024","FEBRERO","JUEVES","2024-02-01",3,"Robo","Robo total","NO","NO",NULL,NULL,NULL,NULL,1',
    '6,"2024","FEBRERO","JUEVES","2024-02-01",3,"Robo","Robo total","NO","NO","VILLA GRAL. MITRE",11,"0","0",1',
]


class EdaDelitosTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.path = Path(temp.name) / 'delitos.csv'
        self.path.write_text(HEADER + '\n'.join(ROWS) + '\n', encoding='utf-8')

    def test_quality_report_matches_app_rules(self):
        rows, calidad = load(self.path)
        self.assertEqual((calidad['filas_leidas'], calidad['filas_validas'],
                          calidad['descartadas'], calidad['duplicadas']), (7, 5, 1, 1))
        self.assertEqual(calidad['faltantes_por_columna']['barrio'], 1)
        self.assertEqual(calidad['franja_sin_dato'], 1)
        self.assertEqual((calidad['con_coordenadas'], calidad['pin_en_caba']), (5, 4))
        self.assertIn('Villa General Mitre', set(rows['barrio']))

    def test_barrio_month_keeps_coverage_and_excludes_road_incidents(self):
        rows, _ = load(self.path)
        data = tables(rows)['barrio_mes'].set_index(['barrio', 'mes'])
        caballito = data.loc[('Caballito', '2024-01')]
        self.assertEqual((caballito['filas_validas'], caballito['total_delitos'],
                          caballito['siniestros_viales']), (3, 2, 1))
        self.assertEqual((caballito['delitos_con_arma'], caballito['delitos_con_moto'],
                          caballito['delitos_nocturnos'], caballito['automotor']), (1, 1, 1, 1))
        self.assertEqual(caballito['amenazas'], 0)
        # Sin filas válidas no hay fila: la falta de cobertura no se completa con ceros.
        self.assertNotIn(('Caballito', '2024-02'), data.index)
        self.assertNotIn(('Almagro', '2024-01'), data.index)

    def test_several_years_count_each_id_once_per_year(self):
        later = self.path.with_name('delitos_2025.csv')
        later.write_text(HEADER + '\n'.join([
            ROWS[0],  # Mismo ID y año que el archivo anterior: se cuenta una vez.
            '1,"2025","ENERO","MIERCOLES","2025-01-01",21,"Robo","Robo total","SI","NO","ALMAGRO",5,"-34.60","-58.42",1',
        ]) + '\n', encoding='utf-8')
        rows, calidades, repeated = load_many([self.path, later])
        self.assertEqual(([c['filas_validas'] for c in calidades], repeated, len(rows)), ([5, 2], 1, 6))
        data = tables(rows)
        self.assertEqual(list(data['anio_categoria'].index), [2024, 2025])
        self.assertEqual(data['barrio_anio'].loc[('Almagro', 2025), 'total_delitos'], 1)
        self.assertEqual(data['barrio_anio'].loc[('Caballito', 2024), 'pct_con_arma'], 50.0)

    def test_missing_official_columns_are_rejected(self):
        self.path.write_text('id-mapa,fecha,barrio\n1,2024-01-01,CABALLITO\n', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'Faltan columnas'):
            load(self.path)
