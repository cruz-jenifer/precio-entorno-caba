"""Pruebas del lector de robots.txt con comodines."""

import unittest

from precio_entorno.inmobiliarias import USER_AGENT
from precio_entorno.robots import Robots, disallow_all

# Extracto de las reglas de Clarín Inmuebles, verificado el 2026-11-08.
CLARIN = """# V.7
User-agent: *
Disallow: /auth
Disallow: /*-o-*-o-*
Disallow: /*.webmanifest$
Allow: /*?orden-menorprecio
Disallow: /*?*orden-
Allow: /*?pagina-1$
Allow: /*?pagina-2$
Allow: /*?pagina-3$
Disallow: /*?pagina-
Disallow: /api/
Disallow: /*?*&*

User-agent: Bytespider
Disallow: /
"""
BASE = 'https://www.inmuebles.clarin.com'


class RobotsTests(unittest.TestCase):
    def setUp(self):
        self.robots = Robots(CLARIN, USER_AGENT)

    def test_only_first_three_pages_are_allowed(self):
        for page in ('', '?pagina-1', '?pagina-2', '?pagina-3'):
            self.assertTrue(self.robots.allowed(f'{BASE}/departamentos/venta/palermo{page}'), page)
        for page in ('?pagina-4', '?pagina-30', '?pagina-3&orden=1'):
            self.assertFalse(self.robots.allowed(f'{BASE}/departamentos/venta/palermo{page}'), page)

    def test_wildcards_and_end_anchor(self):
        self.assertFalse(self.robots.allowed(f'{BASE}/api/listado'))
        self.assertFalse(self.robots.allowed(f'{BASE}/inmuebles/venta?a=1&b=2'))
        self.assertFalse(self.robots.allowed(f'{BASE}/casa-o-depto-o-ph'))
        self.assertFalse(self.robots.allowed(f'{BASE}/site.webmanifest'))
        self.assertTrue(self.robots.allowed(f'{BASE}/site.webmanifest.bak'))
        self.assertTrue(self.robots.allowed(f'{BASE}/departamento-en-venta-en-palermo-3-ambientes--19622671'))

    def test_longest_rule_wins_and_allow_breaks_ties(self):
        self.assertTrue(self.robots.allowed(f'{BASE}/x?orden-menorprecio'))
        self.assertFalse(self.robots.allowed(f'{BASE}/x?orden-mayorprecio'))
        tie = Robots('User-agent: *\nDisallow: /a\nAllow: /a', USER_AGENT)
        self.assertTrue(tie.allowed('https://a.test/a'))

    def test_specific_group_replaces_the_generic_one(self):
        self.assertTrue(Robots(CLARIN, 'Bytespider').allowed(f'{BASE}/inmuebles') is False)
        own = Robots('User-agent: *\nDisallow: /\n\nUser-agent: precio-entorno-caba\nAllow: /', USER_AGENT)
        self.assertTrue(own.allowed('https://a.test/cualquier'))

    def test_empty_and_blocked_files(self):
        self.assertTrue(Robots('', USER_AGENT).allowed('https://a.test/x'))
        self.assertTrue(Robots('User-agent: *\nDisallow:', USER_AGENT).allowed('https://a.test/x'))
        self.assertFalse(disallow_all().allowed('https://a.test/'))


if __name__ == '__main__':
    unittest.main()
