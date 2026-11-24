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

    def test_ascensor(self):
        acceso = lambda texto: tuple(traits(texto)[c] for c in ('elevator', 'stairs_only', 'step_free'))
        self.assertEqual(acceso('Edificio con 2 ascensores y portero.'), (1, 0, 0))
        self.assertEqual(acceso('Tercer piso por escalera, muy luminoso.'), (0, 1, 0))
        self.assertEqual(acceso('Edificio sin ascensor.'), (0, 1, 0))
        # Dos palabras entre «no» y «ascensor»: la negación común no alcanza, decide «sin ascensor».
        self.assertEqual(acceso('El edificio no cuenta con ascensor.'), (0, 1, 0))
        self.assertEqual(acceso('Ingreso por escalera y ascensor.'), (1, 0, 0))
        self.assertEqual(acceso('Hall con rampa de acceso y ascensor.'), (1, 0, 1))
        self.assertEqual(acceso('PB apto para silla de ruedas.'), (0, 0, 1))
        self.assertEqual(acceso('No apto para silla de ruedas.'), (0, 0, 0))
        self.assertEqual(acceso('Departamento de 2 ambientes al frente.'), (0, 0, 0))

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


class ModelTraitsTest(unittest.TestCase):
    def test_comparacion_y_regresion_usan_los_rasgos(self):
        import warnings
        import numpy as np
        from precio_entorno.comparar_modelos import feature_sets, load_dataset
        from precio_entorno.efecto_rasgos import effects
        from tests.test_comparar_modelos import synthetic

        warnings.simplefilter('ignore')
        df = synthetic(n_per_barrio=80)
        rng = np.random.default_rng(3)
        amenities = rng.integers(0, 2, len(df))
        df['precio_m2'] *= np.where(amenities == 1, 1.2, 1.0)
        rows = [{'listing_id': i, **{c: 0 for c in DESCRIPTION_FIELDS}, 'amenities': int(a), 'age_years': 10}
                for i, a in zip(df['id'], amenities)]
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'model.csv'
            df.to_csv(path, index=False)
            extra = Path(temp) / 'avisos.json'
            extra.write_text(json.dumps(rows[:200]), encoding='utf-8')
            joined = load_dataset(path, [extra])
        self.assertEqual(int(joined['amenities'].notna().sum()), 200)
        self.assertIn('amenities', feature_sets(joined, False)[0])
        found = {r['columna']: r for r in effects(joined, with_age=False)['rasgos']}
        self.assertAlmostEqual(found['amenities']['diferencia_pct'], 20, delta=4)
        self.assertTrue(found['amenities']['distinto_de_cero'])


class AgencyBackfillTest(unittest.TestCase):
    def test_completa_solo_los_avisos_sin_rasgos_y_no_guarda_texto(self):
        from precio_entorno.inmobiliarias import PoliteClient, record
        from precio_entorno.rasgos_inmobiliarias import complete

        def aviso(agency, code, url):
            return record(agency, code, url, '2026-11-09T12:00:00+00:00', price=100000, currency='USD',
                          covered_area_m2=50, total_area_m2=50, rooms=2, neighborhood='Almagro')
        avisos = [aviso('remax', 'R1', 'https://www.remax.com.ar/listings/depto-ficticio'),
                  aviso('migliorisi', 'a1', 'https://www.migliorisi.com.ar/propiedad/ver/a1/depto'),
                  aviso('remax', 'R0', 'https://www.remax.com.ar/listings/dado-de-baja'),
                  dict(aviso('remax', 'R2', 'https://www.remax.com.ar/listings/ya-tiene'), balcony=1, bright=0,
                       **{c: 0 for c in DESCRIPTION_FIELDS if c not in ('balcony', 'bright')})]
        pages = {'findBySlug/dado-de-baja': json.dumps({'data': None}),
                 'findBySlug/depto-ficticio': json.dumps({'data': {'title': 'Depto', 'description': 'Con amenities. Agente Ficticio'}}),
                 '/propiedad/ver/a1': '<div id="div-descripcion"><p>A reciclar, con patio.</p></div>'}

        def fetch(url, params=None):
            for part, body in pages.items():
                if part in url:
                    return 200, body
            return (404, '') if 'robots' in url else (500, '')
        with tempfile.TemporaryDirectory() as temp:
            raw = Path(temp) / 'raw' / 'inmobiliarias-20261109'
            raw.mkdir(parents=True)
            (raw / 'avisos.json').write_text(json.dumps(avisos), encoding='utf-8')
            parsed, _ = parse_listings(json.dumps(avisos).encode(), 'a.json', avisos[0]['source'])
            store = Store(Path(temp) / 'base.sqlite3')
            store.ingest(parsed, source=avisos[0]['source'])
            client = PoliteClient(fetch=fetch, pause_s=0, sleep=lambda s: None)
            log = complete('venta', Path(temp) / 'salida', client, base=Path(temp) / 'base.sqlite3',
                           raw=Path(temp) / 'raw', echo=lambda line: None)
            self.assertEqual((log['pendientes'], log['con_rasgos'], log['errores'], log['completados_en_base']),
                             (3, 2, 1, 2))
            rows = {r['id']: r for r in store.listings()}
            self.assertEqual(rows['remax:R1']['amenities'], 1)
            self.assertEqual((rows['migliorisi:a1']['needs_renovation'], rows['migliorisi:a1']['patio']), (1, 1))
            self.assertNotIn('Ficticio', (Path(temp) / 'salida' / 'avisos.json').read_text(encoding='utf-8'))
            # Solo queda pendiente el aviso dado de baja.
            self.assertEqual(complete('venta', Path(temp) / 'otra', client, base=Path(temp) / 'base.sqlite3',
                                      raw=Path(temp) / 'raw', echo=lambda line: None)['pendientes'], 1)


class AccessBackfillTest(unittest.TestCase):
    def test_completa_accesibilidad_sin_pisar_los_rasgos_anteriores(self):
        from precio_entorno.descripcion import ACCESS_FIELDS, PRICE_FIELDS
        from precio_entorno.inmobiliarias import PoliteClient, record
        from precio_entorno.rasgos_inmobiliarias import complete

        # Avisos leídos antes de sumar los rasgos de accesibilidad: tienen los demás rasgos, no estos.
        def aviso(code, slug, balcony):
            return dict(record('remax', code, f'https://www.remax.com.ar/listings/{slug}', '2026-11-09T12:00:00+00:00',
                               price=100000, currency='USD', covered_area_m2=50, total_area_m2=50, rooms=2,
                               neighborhood='Almagro'), **{**{c: 0 for c in PRICE_FIELDS}, 'balcony': balcony})
        avisos = [aviso('R1', 'con-ascensor', 1), aviso('R2', 'por-escalera', 0)]
        pages = {'findBySlug/con-ascensor': json.dumps({'data': {'title': 'Depto', 'description': 'Edificio con ascensor.'}}),
                 'findBySlug/por-escalera': json.dumps({'data': {'title': 'Depto', 'description': 'Tercer piso por escalera, con balcón.'}})}

        def fetch(url, params=None):
            for part, body in pages.items():
                if part in url:
                    return 200, body
            return (404, '') if 'robots' in url else (500, '')
        with tempfile.TemporaryDirectory() as temp:
            raw = Path(temp) / 'raw' / 'inmobiliarias-20261109'
            raw.mkdir(parents=True)
            (raw / 'avisos.json').write_text(json.dumps(avisos), encoding='utf-8')
            parsed, _ = parse_listings(json.dumps(avisos).encode(), 'a.json', avisos[0]['source'])
            store = Store(Path(temp) / 'base.sqlite3')
            store.ingest(parsed, source=avisos[0]['source'])
            client = PoliteClient(fetch=fetch, pause_s=0, sleep=lambda s: None)
            run = lambda out, fields: complete('venta', Path(temp) / out, client, base=Path(temp) / 'base.sqlite3',
                                               raw=Path(temp) / 'raw', echo=lambda line: None, fields=fields)
            self.assertEqual(run('sin-modo', None)['pendientes'], 0)   # el modo de siempre no los ve
            log = run('accesibilidad', ACCESS_FIELDS)
            self.assertEqual((log['pendientes'], log['con_rasgos']), (2, 2))
            rows = {r['id']: r for r in store.listings()}
            self.assertEqual([rows['remax:R1'][c] for c in ACCESS_FIELDS], [1, 0, 0])
            self.assertEqual([rows['remax:R2'][c] for c in ACCESS_FIELDS], [0, 1, 0])
            self.assertEqual(rows['remax:R2']['balcony'], 0)   # COALESCE: no pisa lo que ya estaba
            self.assertEqual(run('otra', ACCESS_FIELDS)['pendientes'], 0)
