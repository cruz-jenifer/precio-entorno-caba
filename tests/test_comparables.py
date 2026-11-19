"""Pruebas de la comparación de cada aviso con avisos parecidos del barrio."""

import unittest

from precio_entorno import comparables


def aviso(id_, price, area=50, rooms=2, barrio='Caballito', currency='USD', age=None):
    return {'id': id_, 'price': price, 'covered_area': area, 'rooms': rooms, 'neighborhood': barrio,
            'currency': currency, 'age_years': age}


def pool(n, base=2_000, **kwargs):
    """n avisos de 50 m² de una misma fuente con USD/m² base, base+30, base+60…"""
    return [aviso(f'remax:{i}', (base + 30 * i) * 50, **kwargs) for i in range(n)]


class ComparablesTests(unittest.TestCase):
    def test_position_against_central_half(self):
        others = pool(11)  # 2.000 a 2.300 USD/m², mediana 2.150
        low = comparables.comparar(aviso('century21:1', 1_800 * 50), others)
        self.assertEqual((low['n'], low['posicion'], low['mediana_m2'], low['precio_m2']), (11, 'debajo', 2_150, 1_800))
        self.assertEqual(low['diferencia_pct'], -16)
        self.assertEqual(comparables.comparar(aviso('century21:2', 2_160 * 50), others)['posicion'], 'dentro')
        self.assertEqual(comparables.comparar(aviso('century21:3', 2_500 * 50), others)['posicion'], 'arriba')

    def test_too_few_similar_listings_gives_no_position(self):
        result = comparables.comparar(aviso('century21:1', 95_000), pool(comparables.MINIMO - 1))
        self.assertIsNone(result['posicion'])
        self.assertEqual(result['n'], comparables.MINIMO - 1)
        self.assertIn('al menos', result['motivo'])

    def test_size_and_rooms_filter_the_reference(self):
        others = pool(10) + [aviso('remax:grande', 9_000_000, area=200), aviso('remax:4amb', 9_000_000, rooms=4)]
        self.assertEqual(comparables.comparar(aviso('century21:1', 95_000), others)['n'], 10)

    def test_possible_copies_count_once_and_the_listing_itself_is_excluded(self):
        target = aviso('zonaprop:1', 90_000)
        copy = aviso('remax:copia', 90_200)  # otra fuente, mismo precio redondeado a miles: posible copia
        repeated = [aviso('century21:x', 200_000), aviso('migliorisi:x', 200_000)]
        result = comparables.comparar(target, pool(9) + [target, copy, *repeated])
        self.assertEqual(result['n'], 10)

    def test_declared_age_narrows_when_enough_and_falls_back_otherwise(self):
        old, new = pool(10, base=1_500, age=50), [aviso(f'remax:n{i}', (3_000 + 30 * i) * 50, age=2) for i in range(10)]
        result = comparables.comparar(aviso('century21:1', 3_100 * 50, age=5), old + new)
        self.assertEqual((result['n'], result['posicion'], result['sin_antiguedad']), (10, 'dentro', False))
        self.assertIn('antigüedad ±10 años', result['criterios'])
        few_new = comparables.comparar(aviso('century21:1', 3_100 * 50, age=5), old + new[:3])
        self.assertTrue(few_new['sin_antiguedad'])
        self.assertEqual(few_new['n'], 13)

    def test_zonaprop_zero_years_is_not_a_declared_age(self):
        self.assertIsNone(comparables.antiguedad(aviso('zonaprop:1', 1, age=0)))
        self.assertEqual(comparables.antiguedad(aviso('remax:1', 1, age=0)), 0)

    def test_compare_all_groups_by_neighborhood_and_currency(self):
        listings = pool(10) + pool(10, base=3_000, barrio='Almagro') + pool(10, base=20_000, currency='ARS')
        target = aviso('century21:1', 1_900 * 50)
        result = comparables.comparar_todos([target], listings + [target])
        self.assertEqual((result['century21:1']['n'], result['century21:1']['mediana_m2']), (10, 2_135))


if __name__ == '__main__':
    unittest.main()
