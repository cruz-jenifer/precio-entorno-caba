"""Pruebas del radar de tendencias barriales con feeds y notas sintéticas, sin red.

Los textos de las notas están escritos para estas pruebas; no copian notas reales.
"""

import json
import tempfile
import unittest
from datetime import date
from pathlib import Path

from precio_entorno import radar
from precio_entorno import radar_clasificar as c

ROBOTS = 'User-agent: *\nDisallow: /api/\n'
HOY = date(2026, 11, 9)
DESDE, HASTA = radar.periodo(HOY)


def rss(*items):
    cuerpo = ''.join(f'<item><title><![CDATA[{t}]]></title><link>{u}?utm_source=rss</link>'
                     f'<pubDate>{f}</pubDate><content:encoded><![CDATA[TEXTO COMPLETO DEL FEED]]></content:encoded>'
                     f'</item>' for t, u, f in items)
    return ('<?xml version="1.0"?><rss xmlns:content="http://purl.org/rss/1.0/modules/content/" version="2.0">'
            f'<channel><title>x</title>{cuerpo}</channel></rss>')


def articulo(url, titular, bajada, cuerpo, publicado, libre=True):
    datos = {'@context': 'https://schema.org', '@type': 'NewsArticle', 'headline': titular, 'description': bajada,
             'datePublished': publicado, 'dateModified': publicado, 'articleBody': cuerpo, 'url': url}
    if not libre:
        datos['isAccessibleForFree'] = False
    return (f'<html><head><link rel="canonical" href="{url}"/>'
            f'<script type="application/ld+json">{json.dumps(datos)}</script></head><body></body></html>')


CL = 'https://www.clarin.com/propiedades/'
NOTA_CHACA = CL + 'chacarita-colegiales-polo_0_A.html'
NOTA_APERTURA = CL + 'abrio-bar-almagro_0_B.html'
NOTA_VIEJA = CL + 'nota-vieja-republicada_0_C.html'
NOTA_CERRADA = CL + 'nota-para-suscriptores_0_D.html'
FRASE_PRIVADA = 'Frase privada que no puede guardarse'


def paginas_clarin():
    feed = rss(
        ('Chacarita y Colegiales, el nuevo polo de la Ciudad', NOTA_CHACA, 'Wed, 04 Nov 2026 12:00:00 +0000'),
        ('Abrió un bar de vermut en Almagro', NOTA_APERTURA, 'Fri, 06 Nov 2026 12:00:00 +0000'),
        ('Una nota de agosto que volvió a la portada', NOTA_VIEJA, 'Sat, 07 Nov 2026 12:00:00 +0000'),
        ('Cuánto cuesta el metro cuadrado en Belgrano', NOTA_CERRADA, 'Sun, 08 Nov 2026 12:00:00 +0000'),
        ('Nota anterior al período', CL + 'anterior_0_E.html', 'Fri, 30 Oct 2026 12:00:00 +0000'),
    )
    indice = ('<sitemapindex><sitemap><loc>https://www.clarin.com/sitemaps/news-2026-11-0.xml</loc>'
              '<lastmod>2026-11-09T12:00:00Z</lastmod></sitemap><sitemap>'
              '<loc>https://www.clarin.com/sitemaps/news-2026-10-0.xml</loc><lastmod>2026-10-31T23:59:59Z</lastmod>'
              '</sitemap></sitemapindex>')
    mapa = (f'<urlset><url><loc>{NOTA_CHACA}</loc><lastmod>2026-11-04T12:00:00Z</lastmod></url>'
            '<url><loc>https://www.clarin.com/politica/otra-seccion_0_F.html</loc><lastmod>2026-10-28T12:00:00Z</lastmod></url>'
            '</urlset>')
    return {
        'https://www.clarin.com/robots.txt': (200, ROBOTS),
        'https://www.clarin.com/rss/propiedades/': (200, feed),
        'https://www.clarin.com/sitemaps/index_news.xml': (200, indice),
        'https://www.clarin.com/sitemaps/news-2026-11-0.xml': (200, mapa),
        NOTA_CHACA: (200, articulo(
            NOTA_CHACA, 'Chacarita y Colegiales, el nuevo polo de la Ciudad',
            'Dos barrios vecinos suman edificios, bares y espacios verdes.',
            'En Chacarita crecen los proyectos. En Colegiales se renovó el parque. Chacarita suma oferta. '
            'Colegiales atrae familias. La zona queda cerca de Palermo y Belgrano.', '2026-11-04T09:00:00-03:00')),
        NOTA_APERTURA: (200, articulo(
            NOTA_APERTURA, 'Abrió un bar de vermut en Almagro', 'El local apuesta por la esquina.',
            'El bar «La Vermutera» abrió el 5 de noviembre en Bulnes 900, en Almagro. '
            'El mismo grupo abrirá otro local el próximo mes.', '2026-11-06T09:00:00-03:00')),
        NOTA_VIEJA: (200, articulo(
            NOTA_VIEJA, 'Una nota de agosto que volvió a la portada', 'Sin fecha nueva.',
            'Saavedra y Núñez siguen creciendo. Saavedra suma obras. Núñez suma oficinas.',
            '2026-08-03T09:00:00-03:00')),
        NOTA_CERRADA: (200, articulo(
            NOTA_CERRADA, 'Cuánto cuesta el metro cuadrado en Belgrano', 'Valores publicados por barrio.',
            FRASE_PRIVADA + ' en Villa Urquiza y Villa Urquiza.', '2026-11-08T09:00:00-03:00', libre=False)),
    }


class Red:
    """Simula la red: devuelve páginas y cuenta pedidos. `fallas` responde error a esas direcciones."""

    def __init__(self, paginas, fallas=(), estado_falla=None):
        self.paginas, self.fallas, self.estado_falla, self.pedidos = paginas, set(fallas), estado_falla, []

    def __call__(self, url):
        self.pedidos.append(url)
        if url in self.fallas:
            if self.estado_falla:
                return self.estado_falla, ''
            raise ConnectionError('sin red')
        return self.paginas.get(url, (404, ''))

    def cliente(self):
        return radar.Cliente(fetch=self, pausa_s=0, sleep=lambda s: None)


class BarriosTests(unittest.TestCase):
    def nombres(self, texto):
        return [(e, b, m) for _, e, b, m in c.menciones(texto)]

    def test_official_names_aliases_and_ambiguous_zones(self):
        found = self.nombres('Departamentos en Núñez, Barrio Norte y Chacagiales, cerca de Parque Centenario.')
        self.assertEqual(found[0], ('Nunez', ('Núñez',), None))
        self.assertEqual(found[1][1], ('Recoleta',))
        self.assertEqual(found[2][1], ('Chacarita', 'Colegiales'))
        self.assertEqual(found[3][1], ())
        self.assertIn('cruza', found[3][2])
        self.assertEqual(len(c.OFICIALES), 48)

    def test_streets_people_and_homonyms_are_not_neighborhoods(self):
        texto = ('Sobre la Av. Belgrano opinó Luis Almagro. La Constitución Nacional no cambia. '
                 'Boca Juniors ganó. Once departamentos se vendieron. Juan Núñez habló del Belgrano Cargas.')
        self.assertEqual(self.nombres(texto), [])
        self.assertEqual(self.nombres('En Córdoba, Villa Belgrano supera los US$2.400 por m2.'), [])
        self.assertEqual([b for _, _, b, _ in c.menciones('Vive en Once y trabaja en La Boca.')],
                         [('Balvanera',), ('La Boca',)])

    def test_main_incidental_comparison_and_sections(self):
        texto = ('Durante años Palermo concentró la demanda. Hoy crecen Saavedra y Almagro. '
                 'Saavedra: verde y precios competitivos. Saavedra suma obras cerca de Palermo. '
                 'En Saavedra hay más oferta que en Belgrano. Como ocurrió en Palermo, sube la demanda. '
                 'Almagro: edificios nuevos. Almagro se renueva y en Palermo antes se construía más.')
        result = c.barrios_de('Barrios revelación de la Ciudad', 'Dos zonas que cambiaron.', texto)
        self.assertEqual(result['barrios'], ['Almagro', 'Saavedra'])
        self.assertEqual(result['incidentales'], ['Belgrano', 'Palermo'])

    def test_a_benchmark_neighborhood_does_not_join_the_headline_focus(self):
        texto = ('En Villa Urquiza hay 2.600 avisos. En Belgrano con el mismo tope la proporción baja. '
                 'En Belgrano ese tope alcanza a pocos nuevos. La comparación con Belgrano usa la misma fecha.')
        result = c.barrios_de('Departamentos en venta en Villa Urquiza', 'Cuántos hay y a qué precio.', texto)
        self.assertEqual((result['barrios'], result['incidentales']), (['Villa Urquiza'], ['Belgrano']))

    def test_note_about_another_city_assigns_no_neighborhood(self):
        result = c.barrios_de('Montevideo gana terreno entre los inversores', 'Qué barrios eligen en Uruguay.',
                              'En Pocitos y en Palermo, el barrio montevideano, suben los precios. Palermo crece.')
        self.assertEqual((result['alcance'], result['barrios'], result['incidentales']), ('otro', [], []))
        self.assertTrue(result['ambiguas'])

    def test_historical_case_shape_finds_the_six_neighborhoods(self):
        # Estructura del caso histórico de Clarín (agosto de 2026), con texto propio de la prueba.
        texto = ('Durante años Palermo Belgrano y Recoleta concentraron la demanda. '
                 'Los barrios revelación son Núñez Saavedra Chacarita y Almagro. '
                 'Otro especialista suma Villa Crespo y La Paternal impulsados por el derrame de Palermo. '
                 'Núñez: el ganador del corredor norte. Núñez recibe empresas. Es caro, solo detrás de Puerto Madero. '
                 'Saavedra: verde y competitivo. Así como ocurrió alrededor de Palermo Saavedra recibe demanda. '
                 'Chacarita: de barrio de paso a polo. Muchos miran Chacarita por el encarecimiento de Palermo. '
                 'Almagro: edificios modernos. Antes los proyectos iban a Palermo y ahora a este barrio. '
                 'Villa Crespo y La Paternal: el efecto Palermo. El crecimiento de Palermo derramó demanda.')
        result = c.clasificar('Clarín', 'Barrios revelación de CABA: seis lugares que se reconvirtieron',
                              'De Saavedra a Chacarita, varias zonas cambiaron.', texto, date(2026, 8, 3))
        self.assertEqual(result['barrios'], ['Almagro', 'Chacarita', 'La Paternal', 'Núñez', 'Saavedra', 'Villa Crespo'])
        self.assertIn('Palermo', result['incidentales'])
        self.assertEqual(result['tema'], 'transformacion')
        self.assertNotIn('derramó', result['resumen'])


class AperturasTests(unittest.TestCase):
    def test_reported_opening_with_date_address_and_neighborhood(self):
        hechos = c.aperturas('Abrió un bar en Almagro', '', 'El bar «La Vermutera» abrió el 5 de noviembre en '
                             'Bulnes 900, en Almagro.', date(2026, 11, 6))
        self.assertEqual(hechos[0], {'tipo': 'reportada', 'local': 'La Vermutera', 'direccion': 'Bulnes 900',
                                     'barrio': 'Almagro', 'fecha_hecho': '2026-11-05'})

    def test_announcement_relative_dates_and_missing_date(self):
        pub = date(2026, 11, 9)  # lunes
        futuro, = c.aperturas('', '', 'La cafetería Nube abrirá el 20 de diciembre en Gorriti 4800, Palermo.', pub)
        self.assertEqual((futuro['tipo'], futuro['fecha_hecho']), ('anuncio', '2026-12-20'))
        sabado, = c.aperturas('', '', 'La panadería Miga abrió el sábado en Av. Corrientes 5000, Villa Crespo.', pub)
        self.assertEqual((sabado['tipo'], sabado['fecha_hecho'], sabado['direccion']),
                         ('reportada', '2026-11-07', 'Av. Corrientes 5000'))
        sin_fecha, = c.aperturas('', '', 'Abrió un local de la cadena Tostado en Caballito.', pub)
        self.assertEqual((sin_fecha['tipo'], sin_fecha['fecha_hecho'], sin_fecha['direccion']),
                         ('reportada', None, None))
        self.assertEqual(c.aperturas('', '', 'El crédito abre la puerta al mercado.', pub), [])

    def test_summary_is_own_words_and_event_date_is_separate(self):
        result = c.clasificar('TN', 'Inauguró una heladería en Boedo', '',
                              'La heladería Polo inauguró ayer en Av. Boedo 800, en Boedo.', date(2026, 11, 6))
        self.assertEqual(result['fecha_hecho'], '2026-11-05')
        self.assertEqual(result['tema'], 'aperturas')
        self.assertTrue(result['resumen'].startswith('Nota de TN sobre aperturas'))
        self.assertIn('«Polo» en Av. Boedo 800, con fecha 05/11/2026', result['resumen'])


class RecolectorTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.dir = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def correr(self, red, fuente='clarin'):
        return radar.recolectar_fuente(radar.FUENTES[fuente], DESDE, HASTA, red.cliente(), self.dir,
                                       momento='2026-11-09T09:00:00-03:00')

    def test_collects_dedupes_and_never_stores_bodies(self):
        red = Red(paginas_clarin())
        registro = self.correr(red)
        self.assertEqual(registro['estado'], 'ok')
        self.assertEqual(registro['notas'], sorted([NOTA_CHACA, NOTA_APERTURA, NOTA_CERRADA]))
        datos = radar.cargar(self.dir, 'clarin')
        self.assertEqual(len(datos['notas']), 4)  # La republicada se guarda con su fecha original.
        self.assertEqual(datos['notas'][NOTA_VIEJA]['fecha_publicacion'][:10], '2026-08-03')
        guardado = radar.archivo(self.dir, 'clarin').read_text(encoding='utf-8')
        for prohibido in (FRASE_PRIVADA, 'TEXTO COMPLETO DEL FEED', 'En Colegiales se renovó el parque',
                          'Dos barrios vecinos suman', 'utm_source'):
            self.assertNotIn(prohibido, guardado)
        cerrada = datos['notas'][NOTA_CERRADA]
        self.assertEqual((cerrada['acceso'], cerrada['barrios']), ('restringido', ['Belgrano']))
        self.assertNotIn('Villa Urquiza', cerrada['barrios'] + cerrada['incidentales'])
        chaca = datos['notas'][NOTA_CHACA]
        self.assertEqual((chaca['barrios'], chaca['incidentales']), (['Chacarita', 'Colegiales'], ['Belgrano', 'Palermo']))
        self.assertEqual(set(chaca) & {'texto', 'bajada', 'articleBody'}, set())

    def test_second_run_of_the_same_period_adds_nothing(self):
        self.correr(Red(paginas_clarin()))
        antes = radar.cargar(self.dir, 'clarin')
        red = Red(paginas_clarin())
        registro = self.correr(red)
        despues = radar.cargar(self.dir, 'clarin')
        self.assertEqual(despues['notas'], antes['notas'])
        self.assertEqual(registro['ultimo_intento']['nuevas'], 0)
        self.assertFalse(any(u.startswith(CL) and u.endswith('.html') for u in red.pedidos))
        tablero = radar.boletin(self.dir)
        self.assertEqual(tablero['totales']['notas'], 3)

    def test_failed_run_keeps_previous_data_and_is_not_an_empty_week(self):
        self.correr(Red(paginas_clarin()))
        paginas = paginas_clarin()
        red = Red(paginas, fallas=set(paginas) - {'https://www.clarin.com/robots.txt'})
        registro = self.correr(red)
        self.assertEqual(registro['estado'], 'ok')  # Se conserva la recolección anterior.
        self.assertEqual(len(registro['notas']), 3)
        self.assertEqual(registro['ultimo_intento']['estado'], 'error')
        self.assertIn('intentos', registro['ultimo_intento']['motivo'])
        self.assertGreater(registro['ultimo_intento']['reintentos'], 0)
        # Sin datos previos, la falla queda como falla y no como cero notas.
        otro = Path(self.temp.name) / 'otro'
        registro = radar.recolectar_fuente(radar.FUENTES['clarin'], DESDE, HASTA, red.cliente(), otro)
        self.assertEqual((registro['estado'], registro['notas']), ('error', []))
        fuente = next(f for f in radar.boletin(otro)['fuentes'] if f['fuente'] == 'clarin')
        self.assertEqual(fuente['estado'], 'error')

    def test_restricted_source_is_recorded_and_others_continue(self):
        paginas = paginas_clarin()
        paginas.update({'https://tn.com.ar/robots.txt': (200, 'User-agent: *\nDisallow: /economia/\n'),
                        'https://tn.com.ar/arc/outboundfeeds/rss/category/economia/?outputType=xml': (200, rss()),
                        'https://www.lanacion.com.ar/robots.txt': (200, ROBOTS)})
        red = Red(paginas, fallas={'https://www.lanacion.com.ar/arc/outboundfeeds/rss/category/propiedades/?outputType=xml'},
                  estado_falla=403)
        resultados = radar.recolectar(DESDE, HASTA, self.dir, cliente_factory=red.cliente)
        self.assertEqual(resultados['clarin']['estado'], 'ok')
        self.assertEqual(resultados['lanacion']['estado'], 'restringido')
        self.assertIn('HTTP 403', resultados['lanacion']['motivo'])
        self.assertEqual(resultados['tn']['estado'], 'parcial')
        self.assertIn('robots.txt no permite', resultados['tn']['motivo'])

    def test_partial_coverage_is_flagged(self):
        paginas = paginas_clarin()
        paginas['https://www.clarin.com/rss/propiedades/'] = (200, rss(
            ('Chacarita y Colegiales, el nuevo polo de la Ciudad', NOTA_CHACA, 'Wed, 04 Nov 2026 12:00:00 +0000')))
        paginas['https://www.clarin.com/sitemaps/index_news.xml'] = (200, '<sitemapindex/>')
        registro = self.correr(Red(paginas))
        self.assertEqual(registro['estado'], 'parcial')
        self.assertIn('solo llegaban hasta 2026-11-04', registro['motivo'])


def nota(url, medio, titular, publicado, barrios=(), aperturas=(), incidentales=()):
    return {'id': url[-6:], 'fuente': 'clarin' if 'clarin' in url else 'tn', 'medio': medio, 'titular': titular,
            'url': url, 'urls_vistas': [url], 'fecha_publicacion': publicado, 'recolectado_en': publicado,
            'tema': 'aperturas' if aperturas else 'precios', 'tema_nombre': 'x', 'resumen': 'Resumen propio.',
            'fecha_hecho': None, 'acceso': 'libre', 'barrios': list(barrios), 'incidentales': list(incidentales),
            'ambiguas': [], 'alcance': 'caba', 'aperturas': list(aperturas)}


class BoletinTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.dir = Path(self.temp.name)
        bar = {'tipo': 'reportada', 'local': 'La Vermutera', 'direccion': 'Bulnes 900', 'barrio': 'Almagro',
               'fecha_hecho': '2026-11-05'}
        notas_clarin = [
            nota('https://www.clarin.com/propiedades/a', 'Clarín', 'Abrió La Vermutera, un bar de vermut en Almagro',
                 '2026-11-05T10:00:00-03:00', ['Almagro'], [bar]),
            nota('https://www.clarin.com/propiedades/b', 'Clarín', 'Cuánto cuesta vivir en Chacarita',
                 '2026-11-04T10:00:00-03:00', ['Chacarita'], incidentales=['Palermo']),
            nota('https://www.clarin.com/propiedades/c', 'Clarín', 'Una cafetería abrirá en Boedo',
                 '2026-11-06T10:00:00-03:00', ['Boedo'], [{**bar, 'tipo': 'anuncio', 'local': 'Nube',
                                                           'barrio': 'Boedo', 'fecha_hecho': '2026-12-01'}]),
            nota('https://www.clarin.com/propiedades/d', 'Clarín', 'Abrió un local sin fecha en Caballito',
                 '2026-11-07T10:00:00-03:00', ['Caballito'], [{**bar, 'local': 'Tostado', 'barrio': 'Caballito',
                                                               'direccion': None, 'fecha_hecho': None}]),
            nota('https://www.clarin.com/propiedades/e', 'Clarín', 'Nota vieja de agosto sobre Saavedra',
                 '2026-08-03T10:00:00-03:00', ['Saavedra']),
        ]
        notas_tn = [
            nota('https://tn.com.ar/economia/propiedades/x', 'TN', 'Cuánto cuesta vivir en Chacarita hoy',
                 '2026-11-06T10:00:00-03:00', ['Chacarita']),
            nota('https://tn.com.ar/economia/propiedades/y', 'TN', 'La Vermutera llega con barra y tapeo a una esquina porteña',
                 '2026-11-06T11:00:00-03:00', ['Almagro'], [{**bar, 'local': 'la vermutera', 'direccion': 'Bulnes  900'}]),
        ]
        for clave, notas in (('clarin', notas_clarin), ('tn', notas_tn)):
            radar.guardar(self.dir, clave, {
                'fuente': clave, 'notas': {n['url']: n for n in notas}, 'ultimo_intento': None,
                'periodos': {DESDE.isoformat(): {'desde': DESDE.isoformat(), 'hasta': HASTA.isoformat(),
                                                 'estado': 'ok', 'motivo': None, 'recolectado_en': '2026-11-09T09:00:00-03:00',
                                                 'notas': [], 'cobertura_desde': '2026-10-30',
                                                 'ultimo_intento': {'fecha': '2026-11-09T09:00:00-03:00', 'estado': 'ok'}}}})
        self.datos = radar.boletin(self.dir)

    def tearDown(self):
        self.temp.cleanup()

    def test_counts_notes_and_openings_separately_without_ranking(self):
        filas = {f['barrio']: f for f in self.datos['barrios']}
        self.assertEqual([f['barrio'] for f in self.datos['barrios']], ['Almagro', 'Boedo', 'Caballito', 'Chacarita', 'Palermo'])
        self.assertEqual((filas['Almagro']['notas'], filas['Almagro']['aperturas']), (2, 1))
        self.assertEqual((filas['Boedo']['notas'], filas['Boedo']['aperturas']), (1, 0))
        self.assertEqual((filas['Caballito']['notas'], filas['Caballito']['aperturas']), (1, 0))
        self.assertEqual((filas['Palermo']['notas'], filas['Palermo']['incidentales']), (0, 1))
        self.assertNotIn('Saavedra', filas)
        self.assertEqual(self.datos['periodo'], {'desde': '2026-11-02', 'hasta': '2026-11-08'})
        self.assertIn('No mide demanda', self.datos['aviso'])

    def test_same_opening_groups_every_supporting_link(self):
        apertura, = self.datos['aperturas']
        self.assertEqual((apertura['local'], apertura['fecha_apertura']), ('La Vermutera', '2026-11-05'))
        self.assertEqual(len(apertura['notas']), 2)
        motivos = sorted(a['motivo'] for a in self.datos['aperturas_sin_conteo'])
        self.assertEqual(motivos, ['anuncio de una apertura futura', 'sin fecha de apertura verificable'])

    def test_republications_collapse_into_the_original(self):
        chacarita = self.datos['detalle']['Chacarita']['notas']
        self.assertEqual(len(chacarita), 1)
        self.assertEqual(chacarita[0]['medio'], 'Clarín')
        self.assertEqual(chacarita[0]['republicaciones'][0]['url'], 'https://tn.com.ar/economia/propiedades/x')
        self.assertEqual(self.datos['totales']['republicaciones'], 1)


class ApiRadarTests(unittest.TestCase):
    def test_endpoint_reports_missing_run_and_saved_bulletin(self):
        from fastapi.testclient import TestClient
        from precio_entorno.api import create_app

        with tempfile.TemporaryDirectory() as temp:
            cliente = TestClient(create_app(demo_path=Path(temp) / 'demo.sqlite3', radar_dir=Path(temp) / 'radar',
                                            web_dir=Path(temp) / 'web'))
            vacio = cliente.get('/api/radar').json()
            self.assertFalse(vacio['disponible'])
            self.correr_en(Path(temp) / 'radar')
            datos = cliente.get('/api/radar').json()
            self.assertTrue(datos['disponible'])
            self.assertEqual(datos['totales']['notas'], 3)
            self.assertEqual(cliente.get('/api/radar', params={'periodo': '2020-01-01'}).json()['periodo']['desde'],
                             DESDE.isoformat())

    @staticmethod
    def correr_en(directorio):
        radar.recolectar_fuente(radar.FUENTES['clarin'], DESDE, HASTA, Red(paginas_clarin()).cliente(), directorio)


if __name__ == '__main__':
    unittest.main()
