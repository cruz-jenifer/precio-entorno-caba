"""Lugares para comer más valorados en Google, para la sección «Dónde comer» de la ficha de barrio.

Usa la API oficial de Places (New), nunca una extracción de Google Maps. Las reglas de Google dan forma
al módulo (ver docs/ui.md, «Dónde comer»):

- La consulta se hace en vivo, solo cuando la persona la pide, y la respuesta no se guarda ni se cachea.
  No se guardan calificaciones, listas ni conteos derivados.
- Los resultados se muestran como lista con atribución a Google Maps, nunca sobre el mapa de la app.
- La clave GOOGLE_MAPS_API_KEY se lee del entorno o de `.env` y no sale del servidor.

Cada llamada a Google se registra en `data/local/lugares-consumo.sqlite3`, por mes. Al llegar al tope
(PRECIO_ENTORNO_LUGARES_TOPE_MES, 900 llamadas por defecto, debajo de las 1.000 gratis de Text Search
Enterprise) la sección deja de consultar hasta el mes siguiente.
"""

import os
import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

import httpx
import numpy as np

from .entorno import inside, polygons

ROOT = Path(__file__).resolve().parents[1]
URL = 'https://places.googleapis.com/v1/places:searchText'
# Pedir rating y userRatingCount lleva la búsqueda al nivel Text Search Enterprise.
CAMPOS = ','.join(['places.id', 'places.displayName', 'places.rating', 'places.userRatingCount',
                   'places.priceLevel', 'places.googleMapsUri', 'places.location', 'nextPageToken'])
TIPOS = {'restaurantes': ('restaurant', 'Restaurantes'), 'cafes': ('cafe', 'Cafés'), 'bares': ('bar', 'Bares')}
PRECIOS = {'PRICE_LEVEL_FREE': 'Gratis', 'PRICE_LEVEL_INEXPENSIVE': '$', 'PRICE_LEVEL_MODERATE': '$$',
           'PRICE_LEVEL_EXPENSIVE': '$$$', 'PRICE_LEVEL_VERY_EXPENSIVE': '$$$$'}
POR_PAGINA = 20
PAGINAS = 2           # Hasta 40 candidatos por consulta: 2 llamadas facturables.
MAXIMO = 30           # Lugares que se devuelven a la ficha.
TOPE_MES = 900
TIMEOUT_S = 10


class ErrorLugares(Exception):
    """`motivo`: 'cupo' (se alcanzó el tope del mes) o 'google' (Google no respondió bien)."""

    def __init__(self, motivo, mensaje):
        super().__init__(mensaje)
        self.motivo = motivo


def leer_variable(nombre, env=ROOT / '.env'):
    """Valor de una variable del entorno o, si falta, del archivo `.env` (fuera de Git)."""
    valor = os.environ.get(nombre, '').strip()
    if not valor and env.is_file():
        for linea in env.read_text(encoding='utf-8-sig').splitlines():
            clave, sep, resto = linea.strip().partition('=')
            if sep and clave.strip().removeprefix('export ').strip() == nombre:
                valor = resto.strip().strip('"\'')
    return valor


def enlace_seguro(url):
    """Solo enlaces https a Google Maps; cualquier otra cosa se descarta."""
    if not isinstance(url, str):
        return None
    partes = urlsplit(url)
    host = partes.hostname or ''
    ok = partes.scheme == 'https' and (host in ('maps.google.com', 'google.com') or host.endswith('.google.com'))
    return url if ok else None


def mes_actual():
    return datetime.now(timezone.utc).strftime('%Y-%m')


class Lugares:
    def __init__(self, clave='', tope=0, registro=None, post=None, mes=mes_actual):
        self.clave = clave
        self.tope = tope
        self.registro = Path(registro) if registro else None
        self.post = post or httpx.post
        self.mes = mes
        self.enabled = bool(clave and tope > 0 and self.registro)

    @classmethod
    def from_env(cls, directorio, env=ROOT / '.env'):
        try:
            tope = int(leer_variable('PRECIO_ENTORNO_LUGARES_TOPE_MES', env) or TOPE_MES)
        except ValueError:
            tope = 0
        return cls(leer_variable('GOOGLE_MAPS_API_KEY', env), max(tope, 0),
                   Path(directorio) / 'lugares-consumo.sqlite3')

    def _reservar(self):
        """Cuenta una llamada antes de hacerla. La transacción serializa pedidos simultáneos."""
        self.registro.parent.mkdir(parents=True, exist_ok=True)
        with closing(sqlite3.connect(self.registro)) as db, db:
            db.execute('BEGIN IMMEDIATE')
            db.execute('CREATE TABLE IF NOT EXISTS consumo (mes TEXT PRIMARY KEY, llamadas INTEGER NOT NULL)')
            mes = self.mes()
            fila = db.execute('SELECT llamadas FROM consumo WHERE mes = ?', (mes,)).fetchone()
            usadas = fila[0] if fila else 0
            if usadas + 1 > self.tope:
                raise ErrorLugares('cupo', 'Se alcanzó el cupo mensual de consultas a Google.')
            db.execute('INSERT INTO consumo VALUES (?, 1) ON CONFLICT(mes) DO UPDATE SET llamadas = llamadas + 1',
                       (mes,))

    def consumo(self):
        if not self.registro or not self.registro.exists():
            return {'mes': self.mes(), 'llamadas': 0, 'tope': self.tope}
        with closing(sqlite3.connect(self.registro)) as db:
            try:
                fila = db.execute('SELECT llamadas FROM consumo WHERE mes = ?', (self.mes(),)).fetchone()
            except sqlite3.OperationalError:
                fila = None
        return {'mes': self.mes(), 'llamadas': fila[0] if fila else 0, 'tope': self.tope}

    def _pagina(self, cuerpo):
        respuesta = self.post(URL, json=cuerpo, timeout=TIMEOUT_S, headers={
            'X-Goog-Api-Key': self.clave, 'X-Goog-FieldMask': CAMPOS, 'Content-Type': 'application/json'})
        respuesta.raise_for_status()
        datos = respuesta.json()
        if not isinstance(datos, dict):
            raise ValueError('respuesta')
        return datos

    def buscar(self, barrio, geometria, bbox, tipo='restaurantes'):
        """Candidatos dentro del barrio, ordenados por calificación y cantidad de reseñas.

        `bbox` es (oeste, sur, este, norte). Devuelve todos los candidatos con calificación (hasta MAXIMO)
        para que la interfaz aplique el mínimo de reseñas sin otra llamada.
        """
        if not self.enabled:
            raise ErrorLugares('config', 'La consulta a Google no está configurada.')
        incluido, nombre = TIPOS[tipo]
        oeste, sur, este, norte = bbox
        cuerpo = {'textQuery': f'{nombre} en {barrio}, Buenos Aires', 'includedType': incluido,
                  'strictTypeFiltering': True, 'languageCode': 'es', 'regionCode': 'AR', 'pageSize': POR_PAGINA,
                  'locationRestriction': {'rectangle': {'low': {'latitude': sur, 'longitude': oeste},
                                                        'high': {'latitude': norte, 'longitude': este}}}}
        crudos, llamadas, completa = [], 0, True
        for pagina in range(PAGINAS):
            try:
                self._reservar()
            except ErrorLugares:
                if pagina == 0:
                    raise
                completa = False
                break
            except (OSError, sqlite3.Error):
                raise ErrorLugares('cupo', 'No se pudo verificar el cupo de consultas.') from None
            llamadas += 1
            try:
                datos = self._pagina(cuerpo)
            except (httpx.HTTPError, ValueError) as error:
                if pagina == 0:
                    raise ErrorLugares('google', 'Google no respondió la consulta.') from error
                completa = False
                break
            crudos.extend(datos.get('places') or [])
            token = datos.get('nextPageToken')
            if not token:
                break
            cuerpo = {**cuerpo, 'pageToken': token}
        formas = polygons(geometria)
        vistos, lugares = set(), []
        for p in crudos:
            if not isinstance(p, dict) or p.get('id') in vistos:
                continue
            vistos.add(p.get('id'))
            ubicacion = p.get('location') or {}
            lat, lon = ubicacion.get('latitude'), ubicacion.get('longitude')
            nota, resenas = p.get('rating'), p.get('userRatingCount')
            if not (isinstance(lat, (int, float)) and isinstance(lon, (int, float))):
                continue
            if not any(inside(np.array([[lon, lat]], float), forma)[0] for forma in formas):
                continue
            if not isinstance(nota, (int, float)) or not isinstance(resenas, int):
                continue
            lugares.append({'id': str(p.get('id')), 'nombre': str((p.get('displayName') or {}).get('text') or ''),
                            'nota': round(float(nota), 1), 'resenas': resenas,
                            'precio': PRECIOS.get(p.get('priceLevel')),
                            'enlace': enlace_seguro(p.get('googleMapsUri'))})
        lugares.sort(key=lambda x: (-x['nota'], -x['resenas'], x['nombre']))
        return {'lugares': lugares[:MAXIMO], 'devueltos': len(vistos), 'en_barrio': len(lugares),
                'llamadas': llamadas, 'completa': completa}
