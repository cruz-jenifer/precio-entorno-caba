"""API local de la interfaz web: barrios, avisos que encajan, capas del entorno y alertas.

Se ejecuta con `python -m precio_entorno.api` y sirve la página de `web/` en http://127.0.0.1:8000.
"""

import argparse
import math
from hashlib import sha256
from pathlib import Path
from statistics import median
from typing import Literal

from fastapi import FastAPI, HTTPException, Query
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import entorno
from .bases import REAL_BASE, ROOT, demo_base, open_store
from .importing import BARRIOS
from .matching import matches

Mode = Literal['demo', 'real']
Operation = Literal['venta', 'alquiler']
LAYER_KEYS = ('subte', 'verdes', 'escuelas', 'salud', 'ruido', 'riesgo')
CURRENCIES = {'venta': ('USD',), 'alquiler': ('ARS', 'USD')}
OFFICIAL = sorted(set(BARRIOS.values()))


class SearchIn(BaseModel):
    barrio: str
    presupuesto: int = Field(ge=1)
    superficie: int = Field(ge=1)
    ambientes: int = Field(ge=1, le=20)
    moneda: str = 'USD'


def square(lon, lat, size_m):
    half_lat = size_m / 2 / 111_320
    half_lon = size_m / 2 / (111_320 * math.cos(math.radians(lat)))
    ring = [[lon - half_lon, lat - half_lat], [lon + half_lon, lat - half_lat], [lon + half_lon, lat + half_lat],
            [lon - half_lon, lat + half_lat], [lon - half_lon, lat - half_lat]]
    return {'type': 'Polygon', 'coordinates': [[[round(x, 6), round(y, 6)] for x, y in ring]]}


def collection(features):
    return {'type': 'FeatureCollection', 'features': features}


def point_features(items, kind, bbox):
    return [{'type': 'Feature', 'geometry': {'type': 'Point', 'coordinates': [i['lon'], i['lat']]},
             'properties': {'kind': kind, 'name': i['name'], 'tooltip': i['tooltip'],
                            'line': i.get('line'), 'web': i.get('web')}}
            for i in items if entorno.in_bbox(i['lon'], i['lat'], bbox)]


def create_app(demo_path=None, real_path=None, entorno_dir=None, raw_dir=None, web_dir=None):
    entorno_dir = Path(entorno_dir or ROOT / 'data/processed/entorno')
    raw_dir = Path(raw_dir or ROOT / 'data/raw')
    web_dir = Path(web_dir or ROOT / 'web')
    cache = {}
    app = FastAPI(title='Precio y Entorno CABA', docs_url='/api/docs', openapi_url='/api/openapi.json')

    def layers():
        marker = entorno_dir / 'resumen.json'
        stamp = marker.stat().st_mtime if marker.exists() else None
        if cache.get('stamp') != stamp:
            cache.update(stamp=stamp, layers=entorno.load(entorno_dir) if stamp else None)
        return cache['layers']

    def store_for(mode, operation):
        return open_store(mode == 'demo', operation, demo_path or demo_base(), real_path or REAL_BASE)

    def check_barrio(name):
        if name not in OFFICIAL:
            raise HTTPException(404, f'{name} no es un barrio oficial de CABA.')
        return name

    def check_currency(operation, currency):
        if currency not in CURRENCIES[operation]:
            raise HTTPException(422, f"En {operation} la moneda tiene que ser {' o '.join(CURRENCIES[operation])}.")
        return currency

    def crime_source(store):
        crime_file, periods = store.crime_periods()
        if not crime_file:
            return None, periods, 'Todavía no se cargó un archivo del Mapa del Delito.'
        path = raw_dir / crime_file['filename']
        if not path.exists():
            return None, periods, f"Falta {crime_file['filename']} en data/raw/ para ubicar los hechos."
        key = ('digest', str(path), path.stat().st_mtime)
        if key not in cache:
            cache[key] = sha256(path.read_bytes()).hexdigest()
        if cache[key] != crime_file['digest']:
            return None, periods, f"{crime_file['filename']} en data/raw/ no es el mismo archivo que se cargó."
        return path, periods, None

    @app.get('/api/estado')
    def state(modo: Mode = 'demo', operacion: Operation = 'venta'):
        store = store_for(modo, operacion)
        listings = store.listings()
        crime_file, periods = store.crime_periods()
        return {
            'modo': modo, 'operacion': operacion, 'monedas': CURRENCIES[operacion],
            'catalogo': listings[0].get('source') if listings and listings[0].get('source') else None,
            'avisos': len(listings),
            'avisos_por_moneda': {c: sum((i.get('currency') or 'USD') == c for i in listings)
                                  for c in CURRENCIES[operacion]},
            'capas': layers() is not None,
            'delitos': None if modo == 'demo' or not crime_file else {
                'archivo': crime_file['filename'], 'periodos': periods},
        }

    @app.get('/api/barrios')
    def neighborhoods(modo: Mode = 'demo', operacion: Operation = 'venta', presupuesto: int = Query(110_000, ge=1),
                      superficie: int = Query(40, ge=1), ambientes: int = Query(2, ge=1), moneda: str = 'USD',
                      ambientes_o_mas: bool = False):
        check_currency(operacion, moneda)
        listings = store_for(modo, operacion).listings()
        summary = (layers() or {}).get('resumen', {})
        rows = []
        for name in OFFICIAL:
            own = [i for i in listings if i['neighborhood'] == name and (i.get('currency') or 'USD') == moneda]
            found = [i['price'] for i in own if matches(i, presupuesto, superficie, ambientes, moneda, ambientes_o_mas)]
            rows.append({'barrio': name, 'comuna': (summary.get(name) or {}).get('comuna'),
                         'avisos': len(own), 'coincidencias': len(found),
                         'mediana': int(median(found)) if found else None, 'entorno': summary.get(name)})
        rows.sort(key=lambda r: (-r['coincidencias'], r['barrio']))
        return {'moneda': moneda, 'barrios': rows}

    @app.get('/api/barrios/{barrio}/avisos')
    def listings_for(barrio: str, modo: Mode = 'demo', operacion: Operation = 'venta',
                     presupuesto: int = Query(110_000, ge=1), superficie: int = Query(40, ge=1),
                     ambientes: int = Query(2, ge=1), moneda: str = 'USD', ambientes_o_mas: bool = False):
        check_barrio(barrio)
        check_currency(operacion, moneda)
        found = [i for i in store_for(modo, operacion).listings()
                 if i['neighborhood'] == barrio and matches(i, presupuesto, superficie, ambientes, moneda, ambientes_o_mas)]
        found.sort(key=lambda i: (i['price'], -i['covered_area']))
        return {'avisos': [{
            'id': i['id'], 'precio': i['price'], 'moneda': i.get('currency') or 'USD',
            'superficie': i['covered_area'], 'superficie_total': i.get('total_area_m2'), 'ambientes': i['rooms'],
            'expensas': i.get('expenses'), 'capturado': i.get('captured_at'),
            'enlace': i.get('url') if modo == 'real' else None} for i in found]}

    @app.get('/api/mapa/barrios')
    def neighborhood_shapes():
        data = layers()
        if data is None:
            raise HTTPException(503, 'Las capas no se generaron. Ejecutá python -m precio_entorno.entorno.')
        return data['barrios']

    @app.get('/api/mapa/capas')
    def map_layers(barrio: str, capas: list[str] = Query(default=[]), nivel: str = 'primario',
                   ruido: Literal['diurno', 'nocturno'] = 'diurno'):
        check_barrio(barrio)
        data = layers()
        if data is None:
            raise HTTPException(503, 'Las capas no se generaron. Ejecutá python -m precio_entorno.entorno.')
        bbox = entorno.bbox_of(data['barrios'], barrio)
        points, out = data['puntos'], {}
        for name in capas:
            if name not in LAYER_KEYS:
                raise HTTPException(422, f'Capa desconocida: {name}.')
        if 'subte' in capas:
            out['subte'] = collection(point_features(points['subte'], 'subte', bbox))
        if 'escuelas' in capas:
            out['escuelas'] = collection(point_features(
                [s for s in points['escuelas'] if nivel in s['levels']], 'escuela', bbox))
        if 'salud' in capas:
            out['salud'] = collection(point_features(points['cesac'], 'cesac', bbox)
                                      + point_features(points['hospitales'], 'hospital', bbox))
        if 'verdes' in capas:
            out['verdes'] = entorno.features_in(data['verdes'], bbox)
        if 'riesgo' in capas:
            out['riesgo'] = entorno.features_in(data['riesgo_hidrico'], bbox)
        if 'ruido' in capas:
            size = data['ruido']['celda_m']
            out['ruido'] = collection([
                {'type': 'Feature', 'geometry': square(lon, lat, size),
                 'properties': {'tipico': typical, 'maximo': top}}
                for lon, lat, typical, top, _ in data['ruido'][ruido] if entorno.in_bbox(lon, lat, bbox)])
        return out

    @app.get('/api/delitos')
    def crimes(barrio: str, periodo: str | None = None, tipo: str | None = None,
               modo: Mode = 'real', operacion: Operation = 'venta'):
        check_barrio(barrio)
        if modo == 'demo':
            return {'disponible': False, 'motivo': 'En la demo los delitos son ficticios y no se ubican en el mapa.'}
        data = layers()
        path, periods, reason = crime_source(store_for(modo, operacion))
        if reason or data is None:
            return {'disponible': False, 'motivo': reason or 'Las capas no se generaron.', 'periodos': periods}
        period = periodo if periodo in periods else periods[0]
        bbox = entorno.bbox_of(data['barrios'], barrio)
        key = ('delitos', str(path), period, tipo, bbox)
        if key not in cache:
            cache[key] = entorno.crime_cells(path, period, tipo, bbox)
        cells, kinds = cache[key]
        if tipo and tipo not in kinds:
            cells = []
        return {'disponible': True, 'archivo': path.name, 'periodo': period, 'periodos': periods,
                'tipo': tipo, 'tipos': kinds, 'maximo': max((c['hechos'] for c in cells), default=0),
                'celdas': collection([{'type': 'Feature', 'geometry': square(c['lon'], c['lat'], 200),
                                       'properties': {'hechos': c['hechos']}} for c in cells])}

    @app.get('/api/fuentes')
    def sources():
        data = layers()
        return data['fuentes'] if data else {'generado': None, 'fuentes': []}

    @app.get('/api/busquedas')
    def searches(modo: Mode = 'demo', operacion: Operation = 'venta'):
        store = store_for(modo, operacion)
        return {
            'busquedas': [{'id': s['id'], 'barrio': s['neighborhood'], 'presupuesto': s['budget'],
                           'superficie': s['min_area'], 'ambientes': s['rooms'],
                           'moneda': s.get('currency') or 'USD'} for s in store.searches()],
            'alertas': [{'busqueda': a['search_id'], 'id': a['id'], 'barrio': a['neighborhood'],
                         'precio': a['price'], 'moneda': a['currency'], 'superficie': a['covered_area'],
                         'ambientes': a['rooms'], 'expensas': a.get('expenses'),
                         'enlace': a.get('url') if modo == 'real' else None} for a in store.alerts()],
        }

    @app.post('/api/busquedas')
    def save_search(search: SearchIn, modo: Mode = 'demo', operacion: Operation = 'venta'):
        check_barrio(search.barrio)
        check_currency(operacion, search.moneda)
        created = store_for(modo, operacion).save_search(
            search.barrio, search.presupuesto, search.superficie, search.ambientes, search.moneda)
        return {'creada': created}

    if web_dir.exists():
        app.mount('/', StaticFiles(directory=web_dir, html=True), name='web')
    return app


app = create_app()


def main():
    import uvicorn

    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--puerto', type=int, default=8000)
    args = parser.parse_args()
    uvicorn.run(app, host='127.0.0.1', port=args.puerto)


if __name__ == '__main__':
    main()
