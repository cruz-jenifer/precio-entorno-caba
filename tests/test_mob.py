"""Pruebas del adaptador de Mob con páginas sintéticas y avisos ficticios."""

import json
import unittest

from precio_entorno.importing import parse_listings
from precio_entorno.inmobiliarias import CATALOGS, PoliteClient, mob_barrio, parse_mob, scrape_mob

CAPTURED = '2026-11-08T12:00:00+00:00'


def mob_item(i, **extra):
    item = {'id': str(i), 'slug': f'departamento-alquiler-2-ambientes-ficticio-{i}', 'address': 'Calle Ficticia 100',
            'neighborhood': 'Caballito', 'description': 'Escribime al 11 0000-0000', 'price': 960000,
            'rentPrice': 750000, 'expensas': 210000, 'currency': 'ARS', 'type': 'dueno', 'rooms': 2,
            'surface': 44, 'propertyType': 'Departamento', 'publisherType': 'dueno-verificado',
            'geoLat': -34.6276, 'geoLong': -58.4434}
    item.update(extra)
    return item


def mob_page(items):
    payload = json.dumps({'initialProperties': items, 'initialTotal': 1240})
    return f'<html><script>self.__next_f.push([1,{json.dumps(payload)}])</script></html>'


def sitemap(paths):
    return '<urlset>' + ''.join(f'<url><loc>https://www.mob.ar{p}</loc></url>' for p in paths) + '</urlset>'


class MobTests(unittest.TestCase):
    def test_reads_rent_expenses_and_excludes_contacts(self):
        items = [mob_item(1), mob_item(2, currency='USD', rentPrice=1900, expensas=0, price=3536450),
                 mob_item(3, propertyType='Local'), mob_item(4, neighborhood='Las Cañitas, Palermo'),
                 mob_item(5, neighborhood='Distrito Quartier')]
        listings, skipped = parse_mob(mob_page(items), CAPTURED)
        by_id = {x['listing_id']: x for x in listings}
        self.assertEqual(set(by_id), {'mob:1', 'mob:2', 'mob:4', 'mob:5'})
        self.assertEqual((by_id['mob:1']['price'], by_id['mob:1']['currency'], by_id['mob:1']['expenses']),
                         (750000, 'ARS', 210000))
        self.assertEqual((by_id['mob:2']['price'], by_id['mob:2']['currency'], by_id['mob:2']['expenses']),
                         (1900, 'USD', None))
        self.assertEqual(by_id['mob:4']['neighborhood'], 'Palermo')
        self.assertIsNone(by_id['mob:5']['neighborhood'])
        self.assertEqual(skipped, {'mob:3': 'fuera_de_alcance', 'mob:5': 'barrio_ambiguo'})
        self.assertEqual(by_id['mob:1']['url'], 'https://www.mob.ar/propiedad/departamento-alquiler-2-ambientes-ficticio-1')
        self.assertEqual(by_id['mob:1']['source'], CATALOGS['alquiler'])
        text = json.dumps(listings, ensure_ascii=False)
        for word in ('Calle Ficticia', '0000-0000', 'dueno'):
            self.assertNotIn(word, text)

    def test_subzones(self):
        self.assertEqual(mob_barrio('Caballito Norte'), 'Caballito')
        self.assertEqual(mob_barrio('Palermo Hollywood'), 'Palermo')
        self.assertEqual(mob_barrio('Boca'), 'La Boca')
        self.assertIsNone(mob_barrio('Congreso'))

    def test_imports_into_rental_catalog(self):
        listings, _ = parse_mob(mob_page([mob_item(1), mob_item(2, currency='USD', rentPrice=1900)]), CAPTURED)
        valid, report = parse_listings(json.dumps(listings).encode(), 'avisos.json', CATALOGS['alquiler'],
                                       operation='alquiler')
        self.assertEqual(len(valid), 2)
        self.assertEqual((report.discarded, sum(report.invalid.values())), (0, 0))

    def test_walks_sitemap_listings_deduplicates_and_respects_limit(self):
        pages = {
            'https://www.mob.ar/sitemap/2.xml': sitemap(['/alquileres/capital-federal/caballito',
                                                         '/alquileres/cordoba', '/blog/x']),
            'https://www.mob.ar/sitemap/3.xml': sitemap(['/alquileres/departamentos/capital-federal/almagro']),
            'https://www.mob.ar/alquileres/capital-federal': mob_page([mob_item(1), mob_item(2)]),
            'https://www.mob.ar/alquileres/departamentos/capital-federal/almagro': mob_page([mob_item(2), mob_item(3)]),
            'https://www.mob.ar/alquileres/capital-federal/caballito': mob_page([mob_item(4), mob_item(5)]),
        }
        calls = []

        def fetch(url, params=None):
            calls.append(url)
            return (200, 'User-agent: *\nDisallow: /api/') if url.endswith('robots.txt') else (200, pages[url])
        client = PoliteClient(fetch=fetch, pause_s=0, sleep=lambda s: None)
        listings, _ = scrape_mob(client, CAPTURED, max_listings=3, operation='alquiler')
        self.assertEqual([x['listing_id'] for x in listings], ['mob:1', 'mob:2', 'mob:3'])
        self.assertNotIn('https://www.mob.ar/alquileres/capital-federal/caballito', calls)
        self.assertFalse([c for c in calls if 'cordoba' in c or '/api/' in c])

    def test_sale_operation_makes_no_requests(self):
        client = PoliteClient(fetch=lambda url, params=None: self.fail('no debería pedir nada'))
        listings, skipped = scrape_mob(client, CAPTURED, 10, operation='venta')
        self.assertEqual(listings, [])
        self.assertIn('mob_solo_publica_alquileres', skipped)


if __name__ == '__main__':
    unittest.main()
