"""Pruebas de los adaptadores de inmobiliarias con respuestas sintéticas y ficticias."""

import json
import unittest

from precio_entorno.importing import parse_listings
from precio_entorno.inmobiliarias import (
    CATALOG, Blocked, PoliteClient, parse_century21, parse_migliorisi_detail, parse_migliorisi_list,
    parse_remax, possible_duplicates, scrape_remax)

CAPTURED = '2026-11-07T12:00:00+00:00'
CONTACT_KEYS = ('email', 'phone', 'associate', 'user_name', 'customer', 'commission')


def remax_item(i, **extra):
    item = {'id': i, 'internalId': f'X-{i}', 'entrepreneurship': False, 'slug': f'aviso-ficticio-{i}',
            'operation': {'value': 'sale'}, 'listingStatus': {'value': 'active'},
            'currency': {'value': 'USD'}, 'price': 120000, 'priceExposure': True,
            'dimensionCovered': 50, 'dimensionTotalBuilt': 55, 'totalRooms': 2,
            'geoLabel': 'Palermo Hollywood, Capital Federal', 'location': {'coordinates': [-58.43, -34.58]},
            'associate': {'name': 'Agente Ficticio', 'emails': [{'value': 'agente@example.invalid'}],
                          'phones': [{'value': '+54 11 0000-0000'}]}}
    item.update(extra)
    return item


def c21_page(items, count):
    payload = json.dumps({'properties': items, 'count': count})
    return f'<html><script>self.__next_f.push([1,{json.dumps(payload)}])</script></html>'


def c21_item(pid, **extra):
    item = {'property_id': pid, 'operation_type': 'sell', 'prop_type': 'departamento', 'status': 'active',
            'addr_region': 'Ciudad Autónoma de Buenos Aires', 'addr_neighborhood': 'Caballito',
            'price': '99000.00', 'price_hidden': False, 'currency_id': 'USD', 'covered_square_meters': '45.00',
            'land_square_meters': '48.00', 'rooms': 2, 'geo_lat': '-34.618', 'geo_lon': '-58.443',
            'property_url': f'https://century21.com.ar/propiedades/{pid}', 'user_name': 'Agente Ficticio',
            'email': 'agente@example.invalid', 'phone_mobile': '+5491100000000', 'commission': '6.00'}
    item.update(extra)
    return item


class AdapterTests(unittest.TestCase):
    def assert_no_contacts(self, listings):
        text = json.dumps(listings)
        for word in ('example.invalid"', 'Agente Ficticio', '+54'):
            self.assertNotIn(word, text.replace('https://example.invalid', ''))
        for listing in listings:
            self.assertFalse([k for k in listing if any(c in k for c in CONTACT_KEYS)])

    def test_remax_keeps_contract_fields_and_scope(self):
        payload = {'data': {'totalPages': 1, 'data': [
            remax_item(1), remax_item(2, geoLabel='Ramos Mejia, La Matanza, Buenos Aires'),
            remax_item(3, entrepreneurship=True), remax_item(4, priceExposure=False),
            remax_item(5, geoLabel='Congreso, Capital Federal')]}}
        listings, skipped, pages = parse_remax(payload, CAPTURED)
        self.assertEqual([l['listing_id'] for l in listings], ['remax:X-1', 'remax:X-4', 'remax:X-5'])
        first = listings[0]
        self.assertEqual((first['neighborhood'], first['latitude'], first['longitude'], first['source']),
                         ('Palermo', -34.58, -58.43, CATALOG))
        self.assertIsNone(listings[1]['price'])        # Precio no publicado: lo descarta la validación.
        self.assertIsNone(listings[2]['neighborhood'])  # Zona ambigua: no se inventa un barrio.
        self.assertEqual(dict(skipped), {'fuera_de_caba': 1, 'no_activo_o_emprendimiento': 1, 'barrio_ambiguo': 1})
        self.assert_no_contacts(listings)
        valid, report = parse_listings(json.dumps(listings).encode(), 'avisos.json', CATALOG)
        self.assertEqual((len(valid), report.discarded), (1, 2))

    def test_century21_reads_embedded_payload(self):
        page = c21_page([c21_item('1'), c21_item('1'), c21_item('2', addr_region='Provincia de Buenos Aires'),
                         c21_item('3', operation_type='rent'), {'property_id': '9', 'title': 'Tarjeta resumida'}], 3510)
        listings, skipped, count = parse_century21(page, CAPTURED)
        self.assertEqual((count, [l['listing_id'] for l in listings]), (3510, ['century21:1']))
        self.assertEqual((listings[0]['latitude'], listings[0]['total_area_m2']), (-34.618, 48.0))
        self.assertEqual(dict(skipped), {'fuera_de_caba': 1, 'fuera_de_alcance': 1})
        self.assert_no_contacts(listings)
        # Sin datos del edificio, los campos opcionales quedan vacíos.
        self.assertEqual([listings[0][k] for k in ('age_years', 'condition', 'garages', 'floor')], [None] * 4)

    def test_century21_building_fields(self):
        page = c21_page([c21_item('1', construction_year=1960, property_condition='Muy Bueno', garage=1, addr_floor='9°F'),
                         c21_item('2', construction_year=2028, property_condition='En construcción', addr_floor='PB'),
                         c21_item('3', construction_year=0, property_condition='Raro', garage=None, addr_floor='')], 3)
        listings, _, _ = parse_century21(page, CAPTURED)
        fields = [[l[k] for k in ('age_years', 'condition', 'garages', 'floor')] for l in listings]
        self.assertEqual(fields, [[66, 'Muy Bueno', 1, 9], [0, 'En construcción', None, 0], [None, 'Raro', None, None]])
        valid, report = parse_listings(json.dumps(listings).encode(), 'avisos.json', CATALOG)
        self.assertEqual([v['condition'] for v in valid], ['muy bueno', 'en construcción', None])
        self.assertEqual(report.invalid['condition'], 1)   # Un estado desconocido no se inventa.
        self.assertEqual([v['age_years'] for v in valid], [66, 0, None])

    def test_migliorisi_list_and_detail(self):
        page = ('<a href="/propiedad/ver/a1/depto"> <div class="x"> <img title="DEPARTAMENTO. 2 ambientes.  '
                'VENTA. Almagro. CALLE al 100"> </div></a><a href="/busqueda-propiedades/a/0/0/1/2/3">3</a>'
                '<a href="/propiedad/ver/a1/depto">repetido</a>')
        cards, last = parse_migliorisi_list(page)
        self.assertEqual((last, cards), (3, [('/propiedad/ver/a1/depto', 'a1',
                                              'DEPARTAMENTO. 2 ambientes.  VENTA. Almagro. CALLE al 100')]))
        detail = ('<title>Inmobiliaria Migliorisi | DEPARTAMENTO. 2 ambientes. VENTA. Almagro. CALLE al 100</title>'
                  '<p>Precio U$S 1.100.540</p><td>Superficie Cubierta</td><td>52,5 m2</td>'
                  '<td>Superficie Descubierta</td><td>4 m2</td><a>vendedor@example.invalid</a>')
        listing, is_sale, is_flat = parse_migliorisi_detail(detail, '/propiedad/ver/a1/depto', 'a1', '', CAPTURED)
        self.assertTrue(is_sale and is_flat)
        self.assertEqual((listing['price'], listing['currency'], listing['covered_area_m2'],
                          listing['total_area_m2'], listing['rooms'], listing['neighborhood']),
                         (1100540, 'USD', 52.5, 56.5, 2, 'Almagro'))
        self.assert_no_contacts([listing])
        self.assertIsNone(listing['age_years'])
        aged = detail + '<td>Antiguedad</td><td>40 años</td>'
        self.assertEqual(parse_migliorisi_detail(aged, '/propiedad/ver/a1/depto', 'a1', '', CAPTURED)[0]['age_years'], 40)
        new = detail + '<td>Antigüedad:</td><td>A estrenar</td>'
        self.assertEqual(parse_migliorisi_detail(new, '/propiedad/ver/a1/depto', 'a1', '', CAPTURED)[0]['age_years'], 0)
        decimal = detail.replace('52,5 m2', '37.49 m2').replace('1.100.540', '888.888')
        listing, _, _ = parse_migliorisi_detail(decimal, '/propiedad/ver/a1/depto', 'a1', '', CAPTURED)
        self.assertEqual((listing['covered_area_m2'], listing['price']), (37.49, None))

    def test_possible_duplicates_only_across_agencies(self):
        base = dict(neighborhood='Caballito', rooms=2, covered_area_m2=45.2, price=99400)
        listings = [dict(base, listing_id='remax:1', agency='remax'),
                    dict(base, listing_id='century21:1', agency='century21'),
                    dict(base, listing_id='remax:2', agency='remax', price=150000),
                    dict(base, listing_id='remax:3', agency='remax', price=150000)]
        self.assertEqual(possible_duplicates(listings), [['remax:1', 'century21:1']])


class PoliteClientTests(unittest.TestCase):
    def client(self, responses):
        calls, waits = [], []

        def fetch(url, params=None):
            calls.append(url)
            return responses.get(url, (200, '{}'))
        return PoliteClient(fetch=fetch, pause_s=3, sleep=waits.append), calls, waits

    def test_respects_robots_and_pauses(self):
        client, calls, waits = self.client({'https://a.test/robots.txt': (200, 'User-agent: *\nDisallow: /privado')})
        client.get('https://a.test/publico')
        client.get('https://a.test/publico')
        with self.assertRaisesRegex(Blocked, 'robots.txt'):
            client.get('https://a.test/privado/1')
        self.assertEqual(calls.count('https://a.test/robots.txt'), 1)
        self.assertTrue(waits and all(w > 0 for w in waits))

    def test_unreachable_robots_counts_as_missing_and_network_errors_are_reported(self):
        def fetch(url, params=None):
            if url.endswith('/robots.txt'):
                raise ConnectionError('demasiadas redirecciones')
            if url.endswith('/caido'):
                raise TimeoutError
            return 200, '{}'
        client = PoliteClient(fetch=fetch, pause_s=0, sleep=lambda s: None)
        self.assertEqual(client.get('https://c.test/ok'), '{}')
        self.assertEqual(client.log['robots_no_disponible:c.test'], 1)
        with self.assertRaisesRegex(RuntimeError, 'TimeoutError'):
            client.get('https://c.test/caido')

    def test_stops_on_block_or_challenge(self):
        for response in [(403, 'Forbidden'), (429, ''), (200, '<title>Just a moment...</title>')]:
            client, _, _ = self.client({'https://b.test/x': response})
            with self.assertRaises(Blocked):
                client.get('https://b.test/x')

    def test_remax_pagination_stops_at_limit(self):
        page = {'data': {'totalPages': 5, 'data': [remax_item(i) for i in range(3)]}}
        client, calls, _ = self.client({})
        client._fetch = lambda url, params=None: (200, json.dumps(page))
        known = {'remax:X-0', 'remax:X-1'}
        listings, _ = scrape_remax(client, CAPTURED, max_listings=4, page_size=3, known=known)
        self.assertEqual(len(listings), 4)
        # robots.txt, dos páginas y la ficha del único aviso que no estaba en `known`.
        self.assertEqual(client.log['pedidos'], 4)


class DescriptionTraitsTests(unittest.TestCase):
    def test_remax_reads_traits_from_the_detail_of_new_listings_only(self):
        page = {'data': {'totalPages': 1, 'data': [remax_item(1), remax_item(2)]}}
        detail = {'data': {'title': 'Depto con balcón', 'description': '<p>Apto crédito. Llamar a Agente Ficticio.</p>'}}
        calls = []

        def fetch(url, params=None):
            calls.append(url)
            return 200, json.dumps(detail if 'findBySlug' in url else page)
        client = PoliteClient(fetch=fetch, pause_s=0, sleep=lambda s: None)
        listings, _ = scrape_remax(client, CAPTURED, max_listings=10, known={'remax:X-2'})
        by_id = {l['listing_id']: l for l in listings}
        self.assertEqual((by_id['remax:X-1']['balcony'], by_id['remax:X-1']['mortgage_eligible'],
                          by_id['remax:X-1']['terrace']), (1, 1, 0))
        self.assertIsNone(by_id['remax:X-2']['balcony'])
        self.assertEqual([c for c in calls if 'findBySlug' in c], [
            'https://api-ar.redremax.com/remaxweb-ar/api/listings/findBySlug/aviso-ficticio-1'])
        self.assertNotIn('Ficticio', json.dumps(listings))

    def test_remax_detail_error_leaves_traits_empty_but_block_stops(self):
        page = {'data': {'totalPages': 1, 'data': [remax_item(1)]}}
        for status, expected in [(500, None), (403, Blocked)]:
            def fetch(url, params=None, status=status):
                return (status, '') if 'findBySlug' in url else (200, json.dumps(page))
            client = PoliteClient(fetch=fetch, pause_s=0, sleep=lambda s: None)
            if expected:
                with self.assertRaises(Blocked):
                    scrape_remax(client, CAPTURED, max_listings=10)
            else:
                listings, skipped = scrape_remax(client, CAPTURED, max_listings=10)
                self.assertIsNone(listings[0]['balcony'])
                self.assertEqual(skipped['sin_descripcion'], 1)

    def test_migliorisi_traits_from_description_block(self):
        detail = ('<title>Inmobiliaria Migliorisi | DEPARTAMENTO. 2 ambientes. VENTA. Almagro. CALLE al 100</title>'
                  '<p>Precio U$S 100.000</p><td>Superficie Cubierta</td><td>40 m2</td>'
                  '<div id="div-descripcion"><p>Luminoso, con terraza. No apto cr&#233;dito.</p></div>'
                  '<footer>Amenities del barrio</footer>')
        listing, _, _ = parse_migliorisi_detail(detail, '/propiedad/ver/a1/depto', 'a1', '', CAPTURED)
        self.assertEqual((listing['bright'], listing['terrace'], listing['mortgage_eligible'], listing['amenities']),
                         (1, 1, 0, 0))
        plain = detail.replace('div-descripcion', 'otro')
        self.assertIsNone(parse_migliorisi_detail(plain, '/propiedad/ver/a1/depto', 'a1', '', CAPTURED)[0]['bright'])

    def test_migliorisi_ascensores_de_la_tabla(self):
        from precio_entorno.inmobiliarias import migliorisi_traits

        def page(tabla, texto='Muy luminoso.'):
            return f'<td>Ascensores</td><td>{tabla}</td><div id="div-descripcion"><p>{texto}</p></div>'
        acceso = lambda p: (migliorisi_traits(p)['elevator'], migliorisi_traits(p)['stairs_only'])
        self.assertEqual(acceso(page(2)), (1, 0))
        self.assertEqual(acceso(page(1, 'Primer piso por escalera.')), (1, 0))   # la tabla gana
        self.assertEqual(acceso(page(0)), (0, 0))                                 # 0: puede ser un campo vacío
        self.assertEqual(acceso(page(0, 'Edificio sin ascensor.')), (0, 1))
        self.assertEqual(acceso('<div id="div-descripcion"><p>Sin ascensores 3 cuadras del subte.</p></div>'), (0, 1))
        self.assertEqual(migliorisi_traits('<td>Ascensores</td><td>2</td>'), {})  # sin descripción, sin dato


if __name__ == '__main__':
    unittest.main()
