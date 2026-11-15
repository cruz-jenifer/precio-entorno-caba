"""Rasgos leídos de descripciones ficticias, y su paso por la importación y la base."""

import json
import tempfile
import unittest
from pathlib import Path

from precio_entorno.descripcion import DESCRIPTION_FIELDS, traits
from precio_entorno.importing import parse_listings
from precio_entorno.store import Store
from precio_entorno.zonaprop_apify import adapt, complete_base
from tests.test_zonaprop_apify import CAPTURED, zp_item


class TraitsTest(unittest.TestCase):
    def test_detecta_menciones_sin_tildes_ni_html(self):
        found = traits('Depto A ESTRENAR', '<p>Apto crédito. Balcón al frente, muy luminoso.</p><br>Amenities: S.U.M.')
        self.assertEqual(found['new_build'], 1)
        self.assertEqual(found['mortgage_eligible'], 1)
        self.assertEqual(found['balcony'], 1)
        self.assertEqual(found['bright'], 1)
        self.assertEqual(found['amenities'], 1)
        self.assertEqual(found['rear_facing'], 0)

    def test_negaciones_no_cuentan(self):
        found = traits('No apto crédito. No tiene balcón. Sin amenities. Poco luminoso.')
        for column in ('mortgage_eligible', 'balcony', 'amenities', 'bright'):
            self.assertEqual(found[column], 0, column)

    def test_con_o_sin_cuenta_como_mencion(self):
        self.assertEqual(traits('Puede adquirirse con o sin la terraza privada.')['terrace'], 1)

    def test_patio_de_luz_no_es_patio(self):
        self.assertEqual(traits('Cocina con ventana a patio de luz.')['patio'], 0)
        self.assertEqual(traits('PB con patio propio.')['patio'], 1)

    def test_reciclado_no_es_a_reciclar(self):
        self.assertEqual(traits('Reciclado a nuevo.')['needs_renovation'], 0)
        self.assertEqual(traits('Departamento a refaccionar.')['needs_renovation'], 1)

    def test_contrafrente_y_sum_sin_falsos_positivos(self):
        self.assertEqual(traits('Contrafrente, c/frente silencioso.')['rear_facing'], 1)
        self.assertEqual(traits('Salvo que se indique lo contrario. Sumando el entrepiso.')['rear_facing'], 0)
        self.assertEqual(traits('Sumando el entrepiso.')['amenities'], 0)

    def test_sin_texto_queda_sin_dato(self):
        self.assertEqual(traits(None, ''), {column: None for column in DESCRIPTION_FIELDS})


class ZonapropDescriptionTest(unittest.TestCase):
    def test_usa_la_descripcion_de_la_ficha_y_no_la_guarda(self):
        item = zp_item(11, description='Resumen corto.')
        item['_details']['description'] = 'Texto completo: apto crédito, terraza propia. Llamar a Anunciante Ficticio.'
        listing, why = adapt(item, CAPTURED, 'venta')
        self.assertIsNone(why)
        self.assertEqual((listing['mortgage_eligible'], listing['terrace'], listing['balcony']), (1, 1, 0))
        self.assertNotIn('Ficticio', json.dumps(listing))
        self.assertFalse(any('descrip' in k for k in listing))

    def test_sin_descripcion_los_rasgos_quedan_sin_dato(self):
        listing, _ = adapt(zp_item(12), CAPTURED, 'venta')
        self.assertTrue(all(listing[c] is None for c in DESCRIPTION_FIELDS))


class StoreTraitsTest(unittest.TestCase):
    def listing(self, pid, **extra):
        item = zp_item(pid)
        item['_details']['description'] = extra.pop('description', '')
        listing, _ = adapt(item, CAPTURED, 'venta')
        return listing

    def test_importa_valida_y_completa_sin_pisar(self):
        with tempfile.TemporaryDirectory() as temp:
            first = [self.listing(21, description='Luminoso.'), self.listing(22)]
            parsed, report = parse_listings(json.dumps(first).encode(), 'a.json', first[0]['source'])
            self.assertEqual(len(parsed), 2)
            store = Store(Path(temp) / 'base.sqlite3')
            store.ingest(parsed, source=first[0]['source'])
            rows = {r['id']: r for r in store.listings()}
            self.assertEqual(rows['zonaprop:21']['bright'], 1)
            self.assertIsNone(rows['zonaprop:22']['bright'])

            # La relectura completa el aviso sin dato y no pisa el que ya tenía.
            again = [self.listing(21, description='Contrafrente.'), self.listing(22, description='Balcón, a estrenar.')]
            path = Path(temp) / 'avisos.json'
            path.write_text(json.dumps(again), encoding='utf-8')
            valid, done = complete_base(path, 'venta', Path(temp) / 'base.sqlite3')
            self.assertEqual((valid, done), (2, 1))
            rows = {r['id']: r for r in store.listings()}
            self.assertEqual((rows['zonaprop:21']['bright'], rows['zonaprop:21']['rear_facing']), (1, 0))
            self.assertEqual((rows['zonaprop:22']['balcony'], rows['zonaprop:22']['new_build']), (1, 1))
            self.assertEqual(complete_base(path, 'venta', Path(temp) / 'base.sqlite3'), (2, 0))

    def test_acepta_nombres_en_castellano(self):
        row = {**self.listing(23)}
        for column in DESCRIPTION_FIELDS:
            row.pop(column)
        row.update(apto_credito='sí', balcon='no', luminoso=1)
        parsed, report = parse_listings(json.dumps([row]).encode(), 'a.json', row['source'])
        self.assertEqual((parsed[0]['mortgage_eligible'], parsed[0]['balcony'], parsed[0]['bright']), (1, 0, 1))


if __name__ == '__main__':
    unittest.main()
