"""Pruebas del adaptador de Clarín Inmuebles con tarjetas sintéticas."""

import unittest

from precio_entorno.inmobiliarias import DEFAULT_SITES, SITES, PoliteClient, parse_clarin, scrape_clarin

CAPTURED = '2026-11-08T00:00:00+00:00'
ROBOTS = 'User-agent: *\nAllow: /*?pagina-1$\nAllow: /*?pagina-2$\nAllow: /*?pagina-3$\nDisallow: /*?pagina-\nDisallow: /api/\n'


def card(local_id, price='USD</span> 120.000', address='Gascón 800, Almagro', features=('45 m² cubie.', '2 ambientes'),
         expenses='$80.000', tipo='1', sugerido='False'):
    spans = ''.join(f'<li><i></i><span> {f} </span></li>' for f in features)
    extra = f'<p class="card__expenses" title="{expenses} expensas"> + {expenses} expensas</p>' if expenses else ''
    return f'''<div class="listing__item " id="{local_id}">
      <a href="/departamento-en-venta-en-almagro--{local_id}" class="card" idaviso="{local_id}" idanunciante="999"
         idtipopropiedad="{tipo}" esavisosugerido="{sugerido}">
      <div class="card__details-box">
        <p class="card__address" data-card-direccion> {address} </p>
        <p class="card__price"> <span class="card__currency">{price} </p>
        {extra}
        <ul class="card__main-features">{spans}</ul>
        <p class="card__info">Contacto: Juan, 11-5555-5555</p>
      </div></a></div>'''


def page(*cards):
    return '<html><div class="listing__items">' + ''.join(cards) + '</div></html>'


class ParseClarinTests(unittest.TestCase):
    def test_reads_contract_fields_only(self):
        items, skipped = parse_clarin(page(card('1')), CAPTURED)
        self.assertEqual(skipped, {})
        item, = items
        self.assertEqual(item['listing_id'], 'clarin:1')
        self.assertEqual(item['url'], 'https://www.inmuebles.clarin.com/departamento-en-venta-en-almagro--1')
        self.assertEqual((item['price'], item['currency'], item['covered_area_m2'], item['rooms']), (120000, 'USD', 45, 2))
        self.assertEqual((item['neighborhood'], item['expenses'], item['source']), ('Almagro', 80000, 'inmobiliarias-autorizadas'))
        self.assertNotIn('999', str(item))
        self.assertNotIn('5555', str(item))

    def test_one_room_pesos_subzones_and_missing_fields(self):
        items, _ = parse_clarin(page(
            card('2', price='$</span> 90.000.000', address='Cabello 3300, Piso 1°, Palermo Chico',
                 features=('32 m² cubie.', '50 m² tot.', 'Monoam.'), expenses=None),
            card('3', address='Franklin 2100, Caballito Norte', features=('40 m² cubie.', '1 dorm.')),
        ), CAPTURED)
        mono, no_rooms = items
        self.assertEqual((mono['currency'], mono['price'], mono['rooms']), ('ARS', 90_000_000, 1))
        self.assertEqual((mono['neighborhood'], mono['total_area_m2'], mono['expenses']), ('Palermo', 50, None))
        self.assertEqual((no_rooms['neighborhood'], no_rooms['rooms']), ('Caballito', None))

    def test_skips_suggestions_other_types_and_uses_listing_barrio_as_fallback(self):
        items, skipped = parse_clarin(page(
            card('4', sugerido='True'), card('5', tipo='2'), card('6', address='Av. Rivadavia 4000, Centro'),
            card('7', address='Sin zona'),
        ), CAPTURED, fallback=None)
        self.assertEqual(skipped, {'clarin:4': 'sugerido_de_otra_zona', 'clarin:5': 'fuera_de_alcance',
                                   'clarin:6': 'barrio_ambiguo', 'clarin:7': 'barrio_ambiguo'})
        self.assertEqual([i['neighborhood'] for i in items], [None, None])
        items, _ = parse_clarin(page(card('6', address='Av. Rivadavia 4000, Centro')), CAPTURED, fallback='Almagro')
        self.assertEqual(items[0]['neighborhood'], 'Almagro')


class ScrapeClarinTests(unittest.TestCase):
    def client(self, pages):
        calls = []

        def fetch(url, params=None):
            calls.append(url)
            if url.endswith('/robots.txt'):
                return 200, ROBOTS
            return pages.get(url, (404, 'no existe'))

        return PoliteClient(fetch=fetch, pause_s=0, sleep=lambda s: None), calls

    def test_walks_first_pages_of_each_barrio_and_respects_page_limit(self):
        base = 'https://www.inmuebles.clarin.com'
        sitemap = ('<urlset><url><loc>https://www.inmuebles.clarin.com/departamentos/venta/almagro</loc></url>'
                   '<url><loc>https://www.inmuebles.clarin.com/departamentos/venta/barrio-inexistente</loc></url>'
                   '<url><loc>https://www.inmuebles.clarin.com/departamentos/venta/capital-federal</loc></url>'
                   '<url><loc>https://www.inmuebles.clarin.com/casas/venta/almagro</loc></url></urlset>')
        full = lambda start: page(*(card(str(n)) for n in range(start, start + 20)))
        pages = {
            f'{base}/sitemaps/sitemap-listing-venta-caba.xml.gz': (200, sitemap),
            f'{base}/departamentos/venta/almagro': (200, full(100)),
            f'{base}/departamentos/venta/almagro?pagina-2': (200, full(200)),
            f'{base}/departamentos/venta/almagro?pagina-3': (200, full(300)),
        }
        client, calls = self.client(pages)
        items, skipped = scrape_clarin(client, CAPTURED, max_listings=500)
        self.assertEqual(len(items), 60)
        self.assertNotIn(f'{base}/departamentos/venta/almagro?pagina-4', calls)
        self.assertNotIn(f'{base}/departamentos/venta/capital-federal', calls)
        self.assertEqual(calls.count(f'{base}/departamentos/venta/barrio-inexistente'), 1)
        self.assertTrue(all(i['neighborhood'] == 'Almagro' for i in items))

    def test_stops_at_the_cap_and_is_not_in_the_scheduled_update(self):
        base = 'https://www.inmuebles.clarin.com'
        pages = {f'{base}/sitemaps/sitemap-listing-venta-caba.xml.gz':
                 (200, '<loc>https://www.inmuebles.clarin.com/departamentos/venta/almagro</loc>'),
                 f'{base}/departamentos/venta/almagro': (200, page(*(card(str(n)) for n in range(20))))}
        client, _ = self.client(pages)
        items, _ = scrape_clarin(client, CAPTURED, max_listings=5)
        self.assertEqual(len(items), 5)
        self.assertIn('clarin', SITES)
        self.assertNotIn('clarin', DEFAULT_SITES)


if __name__ == '__main__':
    unittest.main()
