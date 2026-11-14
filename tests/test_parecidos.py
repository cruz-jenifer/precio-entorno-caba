"""Pruebas de barrios parecidos: comparación por entorno, sin puntaje, con motivos legibles."""

import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from precio_entorno import entorno
from precio_entorno.api import create_app
from precio_entorno.lugares import Lugares
from precio_entorno.parecidos import escalas, parecidos

try:
    from test_entorno import build_sources
except ImportError:  # Ejecutado como tests.test_parecidos
    from tests.test_entorno import build_sources


def env(area=400, subte=0, verdes=1.0, escuelas=10, cesac=1, hospitales=0, ruido=0.5, riesgo=0.1, gastro=None):
    datos = {'area_ha': area, 'subte_estaciones': subte, 'verdes_ha': verdes,
             'escuelas': {'primario': {'Estatal': escuelas}}, 'cesac': cesac, 'hospitales': hospitales,
             'ruido': {'diurno': {'alto': ruido}}, 'riesgo_hidrico': riesgo}
    if gastro is not None:
        datos['gastronomia'] = {'restaurantes': gastro, 'cafes': 0, 'bares': 0}
    return datos


def fila(nombre, entorno_, coincidencias=3, mediana=100_000):
    return {'barrio': nombre, 'entorno': entorno_, 'coincidencias': coincidencias, 'avisos': 10,
            'mediana': mediana if coincidencias else None}


class ParecidosTests(unittest.TestCase):
    def setUp(self):
        self.filas = [
            fila('Origen', env(subte=4, verdes=1, ruido=0.8, riesgo=0.1, gastro=120)),
            fila('Gemelo', env(subte=4, verdes=1.1, ruido=0.82, riesgo=0.1, gastro=118), mediana=90_000),
            fila('Gemelo sin avisos', env(subte=4, verdes=1, ruido=0.8, riesgo=0.1, gastro=120), coincidencias=0),
            fila('Verde', env(subte=4, verdes=40, ruido=0.8, riesgo=0.1, gastro=120), mediana=120_000),
            fila('Lejano', env(subte=0, verdes=30, escuelas=2, ruido=0.1, riesgo=0.6, gastro=5)),
            fila('Sin entorno', None),
        ]

    def test_similar_with_listings_come_first_and_explain_without_score(self):
        resultado = parecidos('Origen', self.filas)
        self.assertEqual([p['barrio'] for p in resultado], ['Gemelo', 'Verde', 'Lejano'])
        gemelo = resultado[0]
        self.assertEqual((gemelo['mediana'], gemelo['diferencia_mediana']), (90_000, -10_000))
        self.assertEqual((len(gemelo['parecido_en']), gemelo['diferencias']), (3, []))
        self.assertNotIn('distancia', gemelo)
        con_ruido = parecidos('Origen', self.filas, prefs=['ruido'])[0]
        self.assertEqual(con_ruido['parecido_en'][0]['texto'],
                         'Ruido de día: 82 % y 80 % en Origen (de las celdas con 70 dBA o más)')
        verde = resultado[1]
        self.assertEqual([m['texto'] for m in verde['diferencias']],
                         ['Más espacio verde: 10 contra 0,2 en Origen (ha cada 100 ha)'])

    def test_listing_less_neighbors_fill_the_list_when_needed(self):
        resultado = parecidos('Origen', self.filas, cantidad=5)
        self.assertEqual(resultado[-1]['barrio'], 'Gemelo sin avisos')
        self.assertEqual(resultado[-1]['diferencia_mediana'], None)

    def test_marked_preferences_weigh_double(self):
        filas = [
            fila('Origen', env(verdes=1, ruido=0.8)),
            fila('Mismo ruido', env(verdes=20, ruido=0.8)),
            fila('Mismo verde', env(verdes=1, ruido=0.2)),
        ]
        self.assertEqual(parecidos('Origen', filas, prefs=['ruido'])[0]['barrio'], 'Mismo ruido')
        self.assertEqual(parecidos('Origen', filas, prefs=['verdes'])[0]['barrio'], 'Mismo verde')

    def test_missing_noise_is_skipped_and_unknown_barrio_returns_nothing(self):
        filas = [fila('Origen', env(ruido=None)), fila('Otro', env(ruido=0.9))]
        resultado = parecidos('Origen', filas)
        self.assertEqual(resultado[0]['barrio'], 'Otro')
        self.assertNotIn('ruido', [m['capa'] for m in resultado[0]['parecido_en'] + resultado[0]['diferencias']])
        self.assertEqual(parecidos('Narnia', filas), [])
        self.assertEqual(parecidos('Sin entorno', self.filas), [])

    def test_scales_are_log_for_densities_and_linear_for_shares(self):
        rango = escalas({'a': {'subte': 0, 'ruido': 0.2}, 'b': {'subte': 3, 'ruido': 0.6}, 'c': {'subte': 15, 'ruido': 1.0}})
        self.assertEqual((rango['a']['subte'], rango['c']['subte']), (0.0, 1.0))
        self.assertAlmostEqual(rango['b']['subte'], 0.5)
        self.assertAlmostEqual(rango['b']['ruido'], 0.5)


class ParecidosApiTests(unittest.TestCase):
    def test_endpoint_uses_current_filters_and_known_preferences(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            poi, raw = build_sources(root)
            entorno.convert(poi, raw, root / 'entorno')
            client = TestClient(create_app(demo_path=root / 'demo.sqlite3', real_path=root / 'real.sqlite3',
                                           entorno_dir=root / 'entorno', raw_dir=root, lugares=Lugares()))
            datos = client.get('/api/barrios/Almagro/parecidos', params={'prefs': ['subte', 'inventada']}).json()
            self.assertEqual(datos['barrio'], 'Almagro')
            self.assertEqual([p['barrio'] for p in datos['parecidos']], ['Caballito'])
            self.assertEqual(datos['parecidos'][0]['coincidencias'], 1)
            self.assertEqual(client.get('/api/barrios/Narnia/parecidos').status_code, 404)


if __name__ == '__main__':
    unittest.main()
