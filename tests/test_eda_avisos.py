"""Pruebas del EDA de avisos con una captura ficticia."""

import json
import tempfile
import unittest
from pathlib import Path

from precio_entorno.eda_avisos import by_neighborhood, inconsistencies, load, offer, quality


def aviso(i, agency, barrio, price, area, rooms=2, total=None, lat=-34.6):
    return {'listing_id': f'{agency}:{i}', 'source': 'ficticio', 'agency': agency,
            'url': f'https://example.invalid/{i}', 'captured_at': '2026-11-07', 'price': price,
            'currency': 'USD', 'covered_area_m2': area, 'total_area_m2': total, 'rooms': rooms,
            'neighborhood': barrio, 'latitude': lat, 'longitude': -58.44 if lat else None}


class EdaAvisosTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.dir = Path(temp.name)
        rows = [aviso(1, 'a', 'Caballito', 100000, 40, total=40), aviso(2, 'a', 'Caballito', 150000, 50, total=120),
                aviso(3, 'b', 'Almagro', 90000, 45, lat=None), aviso(4, 'b', 'Almagro', 1, 1),
                aviso(5, 'b', 'Almagro', 400000, 41, rooms=3)]
        (self.dir / 'avisos.json').write_text(json.dumps(rows), encoding='utf-8')
        (self.dir / 'registro.json').write_text(json.dumps({'sitios': {
            'a': {'omitidos': {'fuera_de_caba': 2}, 'pedidos': 3, 'segundos': 6},
            'b': {'omitidos': {}, 'pedidos': 4, 'segundos': 4}}}), encoding='utf-8')
        self.raw, self.df, self.report, self.log = load(self.dir, 'ficticio')

    def test_quality_uses_app_validation(self):
        table, missing = quality(self.raw, self.df, self.report, self.log)
        self.assertEqual(table.loc['a', ['capturados', 'validos', 'omitidos_por_alcance', 'con_coordenadas']].tolist(),
                         [2, 2, 2, 2])
        self.assertEqual(table.loc['b', ['capturados', 'validos', 'con_coordenadas']].tolist(), [3, 2, 1])
        self.assertEqual(table.loc['a', 'segundos_por_aviso_valido'], 3.0)
        self.assertEqual(missing.loc['price', 'invalidos'], 1)

    def test_neighborhood_and_offer_tables(self):
        barrios = by_neighborhood(self.df)
        self.assertEqual(barrios.loc['Caballito', 'avisos'], 2)
        self.assertEqual(barrios.loc['Caballito', 'usd_m2_mediano'], 2750)
        offer_table = offer(self.df).set_index(['presupuesto_usd', 'barrio'])
        self.assertEqual(offer_table.loc[(100000, 'Caballito'), 'coincidencias'], 1)
        self.assertEqual(offer_table.loc[(100000, 'Almagro'), 'coincidencias'], 1)
        self.assertEqual(offer_table.loc[(80000, 'Almagro'), 'coincidencias'], 0)

    def test_inconsistencies(self):
        result = inconsistencies(self.df)
        self.assertEqual((result['superficie_total_informada'], result['total_igual_a_cubierta'],
                          result['total_mas_del_doble_de_cubierta']), (2, 1, 1))
        self.assertEqual(result['mas_bajos'][0]['id'], 'b:3')
