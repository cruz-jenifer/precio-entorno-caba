"""Pruebas de las distancias en línea recta del explorador de necesidades, con capas armadas a mano."""

import math
import unittest

from precio_entorno import cercania


def cuadrado(lon, lat, lado_m):
    dlon, dlat = lado_m / cercania.KX, lado_m / cercania.M_LAT
    ring = [[lon, lat], [lon + dlon, lat], [lon + dlon, lat + dlat], [lon, lat + dlat], [lon, lat]]
    return {'type': 'Feature', 'geometry': {'type': 'Polygon', 'coordinates': [ring]}, 'properties': {}}


ORIGEN = (-58.44, -34.62)
ESTE_500 = ORIGEN[0] + 500 / cercania.KX       # 500 m al este del origen
NORTE_123 = ORIGEN[1] + 123 / cercania.M_LAT   # 123 m al norte del origen

CAPAS = {
    'puntos': {
        'universidades': [{'name': 'Universidad', 'unit': 'Facultad', 'lon': ORIGEN[0], 'lat': NORTE_123}],
        'trenes': [{'name': 'Estación', 'line': 'Mitre', 'lon': ESTE_500, 'lat': ORIGEN[1]}],
        'subte': [{'name': 'Lejana', 'line': 'B', 'lon': ORIGEN[0] + 0.05, 'lat': ORIGEN[1], 'elevators': 2},
                  {'name': 'Cercana', 'line': 'A', 'lon': ESTE_500, 'lat': ORIGEN[1], 'elevators': 0},
                  {'name': 'Sin dato', 'line': 'C', 'lon': ESTE_500, 'lat': NORTE_123, 'elevators': None}],
        'escuelas': [{'name': 'Inicial', 'levels': ['inicial'], 'lon': ORIGEN[0], 'lat': NORTE_123},
                     {'name': 'Primaria', 'levels': ['primario'], 'lon': ESTE_500, 'lat': ORIGEN[1]}],
        'cesac': [],
        'hospitales': [{'name': 'H', 'lon': ORIGEN[0], 'lat': NORTE_123}],
    },
    # Plaza cuadrada de 200 m cuyo borde oeste queda 300 m al este del origen.
    'verdes': {'type': 'FeatureCollection', 'features': [cuadrado(ORIGEN[0] + 300 / cercania.KX, ORIGEN[1] - 0.0005, 200)]},
    'ruido': {'celda_m': 100, 'diurno': [[ORIGEN[0], ORIGEN[1], 70, 75, 'X'],
                                         [ESTE_500, ORIGEN[1], 55, 60, 'X']],
              # De noche, otra grilla: el origen tiene celda, el punto 500 m al este no.
              'nocturno': [[ORIGEN[0], ORIGEN[1], 62, 66, 'X']]},
}


class CercaniaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.indice = cercania.Cercania(CAPAS)

    def calcular(self, capas, nivel='primario', puntos=(ORIGEN,)):
        lons, lats = zip(*puntos)
        return self.indice.calcular(list(lons), list(lats), capas, nivel)

    def test_nearest_subway_station_with_its_line(self):
        self.assertEqual(self.calcular(['subte'])[0]['subte'], {'m': 500, 'estacion': 'Cercana', 'linea': 'A'})

    def test_nearest_station_with_a_reported_elevator(self):
        # «Cercana» tiene 0 ascensores y «Sin dato» no tiene información: ninguna cuenta.
        lejos = round(0.05 * cercania.KX / 10) * 10
        self.assertEqual(self.calcular(['subte'])[0]['subte_ascensor'], {'m': lejos, 'estacion': 'Lejana', 'linea': 'B'})

    def test_school_respects_the_chosen_level(self):
        self.assertEqual(self.calcular(['escuelas'], 'inicial')[0]['escuela'], {'m': 120, 'nivel': 'inicial'})
        self.assertEqual(self.calcular(['escuelas'], 'primario')[0]['escuela'], {'m': 500, 'nivel': 'primario'})
        self.assertEqual(self.calcular(['escuelas'], 'secundario')[0]['escuela'], {'m': None})

    def test_empty_health_layer_gives_no_distance(self):
        salud = self.calcular(['salud'])[0]
        self.assertEqual(salud['cesac'], {'m': None})
        self.assertEqual(salud['hospital'], {'m': 120})

    def test_park_distance_is_measured_to_its_edge(self):
        self.assertEqual(self.calcular(['verdes'])[0]['plaza'], {'m': 300})

    def test_noise_is_read_from_the_cell_that_contains_the_point(self):
        cerca = (ORIGEN[0] + 40 / cercania.KX, ORIGEN[1] - 40 / cercania.M_LAT)
        lejos = (ORIGEN[0] + 250 / cercania.KX, ORIGEN[1])
        valores = [r['ruido_diurno']['dba'] for r in self.calcular(['ruido'], puntos=(ORIGEN, cerca, lejos))]
        self.assertEqual(valores, [70, 70, None])

    def test_university_and_train_distances_with_their_names(self):
        fila = self.calcular(['universidades', 'trenes'])[0]
        self.assertEqual(fila['universidad'], {'m': 120, 'nombre': 'Universidad', 'unidad': 'Facultad'})
        self.assertEqual(fila['tren'], {'m': 500, 'estacion': 'Estación', 'linea': 'Mitre'})
        sin = cercania.Cercania({**CAPAS, 'puntos': {k: v for k, v in CAPAS['puntos'].items() if k not in ('universidades', 'trenes')}})
        vacia = sin.calcular([ORIGEN[0]], [ORIGEN[1]], ['universidades', 'trenes'])[0]
        self.assertEqual((vacia['universidad'], vacia['tren']), ({'m': None}, {'m': None}))

    def test_night_noise_uses_its_own_grid(self):
        este = (ESTE_500, ORIGEN[1])
        filas = self.calcular(['ruido'], puntos=(ORIGEN, este))
        self.assertEqual([(r['ruido_diurno']['dba'], r['ruido_nocturno']['dba']) for r in filas], [(70, 62), (55, None)])
        sin_noche = cercania.Cercania({**CAPAS, 'ruido': {'celda_m': 100, 'diurno': CAPAS['ruido']['diurno']}})
        self.assertEqual(sin_noche.calcular([ORIGEN[0]], [ORIGEN[1]], ['ruido'])[0]['ruido_nocturno'], {'dba': None})

    def test_only_requested_layers_are_returned_and_rounding_is_to_tens(self):
        self.assertEqual(set(self.calcular(['subte', 'verdes'])[0]), {'subte', 'subte_ascensor', 'plaza'})
        self.assertEqual(self.calcular([]), [{}])
        self.assertEqual(cercania.redondear(124.9), 120)
        self.assertEqual(cercania.redondear(125.1), 130)
        self.assertIsNone(cercania.redondear(math.inf))

    def test_many_origins_and_blocks_give_the_same_answer(self):
        puntos = [(ORIGEN[0] + i * 1e-4, ORIGEN[1]) for i in range(30)]
        uno_por_uno = [self.calcular(['subte', 'escuelas'], puntos=(p,))[0] for p in puntos]
        original, cercania.BLOQUE = cercania.BLOQUE, 1
        try:
            juntos = self.calcular(['subte', 'escuelas'], puntos=puntos)
        finally:
            cercania.BLOQUE = original
        self.assertEqual(juntos, uno_por_uno)

    def test_no_origins(self):
        self.assertEqual(self.indice.calcular([], [], ['subte']), [])


if __name__ == '__main__':
    unittest.main()
