"""Prepara las capas del mapa de entorno y un resumen por barrio oficial de CABA.

Fuentes (licencia CC-BY 2.5 AR, data.buenosaires.gob.ar), en `data/raw/badata-entorno/`
y `data/raw/badata-poi/`:
- Barrios oficiales: polígonos que definen la unidad geográfica de todo el resumen.
- Estaciones de subte y estaciones accesibles (ascensores y escaleras mecánicas).
- CeSAC, hospitales y establecimientos educativos: puntos.
- Espacios verdes públicos: plazas, parques, jardines y paseos. Se excluyen canteros
  centrales, plazoletas y patios.
- Mapa de Ruido: bandas de nivel exterior diurno y nocturno. Se resumen en una grilla
  de celdas de 100 m con 9 muestras por celda. El nivel típico de la celda es la banda
  mediana de las muestras relevadas; el mapa cubre sobre todo calles y veredas.
- Riesgo hídrico: áreas de prevención, en la proyección Gauss-Krüger Buenos Aires.

Cada punto se asigna al barrio cuyo polígono lo contiene. El porcentaje de ruido se calcula
sobre las celdas relevadas del barrio y el de riesgo hídrico, sobre las muestras de la grilla
que caen dentro del barrio.

Gastronomía (opcional): restaurantes, cafés y bares de OpenStreetMap (licencia ODbL, «© colaboradores
de OpenStreetMap»), de la captura más reciente en `data/raw/osm-AAAAMMDD/`. Solo se cuentan por barrio.
Si alguna categoría llegó al tope de puntos de su corrida, la captura está incompleta y no se usa.
"""

import argparse
import csv
import json
import math
import warnings
from collections import Counter, defaultdict
from datetime import date
from hashlib import sha256
from pathlib import Path

import numpy as np
from matplotlib.path import Path as Shape

from .badata_poi import PARK_CLASSES
from .importing import BARRIOS, key

ROOT = Path(__file__).resolve().parents[1]
CELL_M = 100
SUB = 3
# Cortes descriptivos sobre el nivel típico de cada celda; no son límites normativos.
LOUD_DBA = {'diurno': 70, 'nocturno': 65}
# Con menos celdas relevadas el porcentaje no representa al barrio y se informa sin dato.
MIN_NOISE_CELLS = 30
DECIMALS = 5
# Gauss-Krüger Buenos Aires (Campo Inchauspe), usado por la capa de riesgo hídrico.
GKBA = ('+proj=tmerc +lat_0=-34.629269 +lon_0=-58.4633 +k=0.9999980 +x_0=100000 +y_0=100000 '
        '+ellps=intl +towgs84=-148,136,90,0,0,0,0 +units=m +no_defs')
LEVELS = {
    'inicial': 'Nivel inicial común',
    'primario': 'Nivel primario común',
    'secundario': 'Nivel secundario común',
}
CDN = 'https://cdn.buenosaires.gob.ar/datosabiertos/datasets/'
SOURCES = {
    'barrios': ('entorno', 'barrios.geojson', 'innovacion-transformacion-digital/barrios/barrios.geojson',
                'Barrios oficiales', 'Límites vigentes según el portal'),
    'subte': ('entorno', 'estaciones_de_subte.geojson', 'sbase/subte-estaciones/estaciones_de_subte.geojson',
              'Estaciones de subte', 'Red publicada por SBASE'),
    'subte_accesible': ('entorno', 'estaciones-accesibles.csv', 'sbase/subte-estaciones/estaciones-accesibles.csv',
                        'Estaciones accesibles', 'Ascensores y escaleras mecánicas informados'),
    'cesac': ('entorno', 'centros_salud_nivel_1_cesac.geojson',
              'ministerio-de-salud/centros-salud-accion-comunitaria-cesac/centros_salud_nivel_1_cesac.geojson',
              'Centros de Salud y Acción Comunitaria', 'Listado del Ministerio de Salud'),
    'ruido_diurno': ('entorno', 'medicion_de_ruido_diurno.geojson',
                     'agencia-de-proteccion-ambiental/mapa-ruido/medicion_de_ruido_diurno.geojson',
                     'Mapa de Ruido diurno', 'Edición 2025'),
    'ruido_nocturno': ('entorno', 'medicion_de_ruido_nocturno.geojson',
                       'agencia-de-proteccion-ambiental/mapa-ruido/medicion_de_ruido_nocturno.geojson',
                       'Mapa de Ruido nocturno', 'Edición 2025'),
    'riesgo_hidrico': ('entorno', 'riesgo-hidrico.geojson',
                       'secretaria-de-desarrollo-urbano/riesgo-hidrico/riesgo-hidrico.geojson',
                       'Riesgo hídrico', 'Capa publicada en diciembre de 2020'),
    'verdes': ('poi', 'espacio_verde_publico.geojson', None, 'Espacios verdes públicos', 'Inventario oficial'),
    'escuelas': ('poi', 'establecimientos_educativos.geojson', None, 'Establecimientos educativos',
                 'Mapa Escolar del Ministerio de Educación'),
    'hospitales': ('poi', 'hospitales.geojson', None, 'Hospitales', 'Ministerio de Salud'),
}
SUBTE_COLORS = {'A': '#18CCCC', 'B': '#EB0909', 'C': '#233AA8', 'D': '#02A17A', 'E': '#AE3D97', 'H': '#FFD600'}
GASTRONOMIA = ('restaurantes', 'cafes', 'bares')
GARAJES_ARCHIVO = 'garajes-comerciales.geojson'
GARAJES_FUENTE = 'https://data.buenosaires.gob.ar/dataset/garajes-comerciales'


def polygons(geometry):
    """Lista de polígonos; cada uno es una lista de anillos y el primero es el exterior."""
    if not geometry:
        return []
    if geometry['type'] == 'Polygon':
        return [geometry['coordinates']]
    if geometry['type'] == 'MultiPolygon':
        return geometry['coordinates']
    return []


def inside(points, polygon):
    if not len(points):
        return np.zeros(0, bool)
    ok = Shape(np.asarray(polygon[0])[:, :2]).contains_points(points)
    for hole in polygon[1:]:
        ok &= ~Shape(np.asarray(hole)[:, :2]).contains_points(points)
    return ok


class Grid:
    """Muestras regulares sobre CABA: SUB × SUB muestras por celda de CELL_M metros."""

    def __init__(self, west, south, east, north, cell_m=CELL_M, sub=SUB):
        self.sub = sub
        self.dlat = cell_m / 111_320 / sub
        self.dlon = cell_m / (111_320 * math.cos(math.radians((south + north) / 2))) / sub
        self.west, self.south = west, south
        self.nx = math.ceil((east - west) / self.dlon / sub) * sub
        self.ny = math.ceil((north - south) / self.dlat / sub) * sub

    def lon(self, ix):
        return self.west + (np.asarray(ix) + 0.5) * self.dlon

    def lat(self, iy):
        return self.south + (np.asarray(iy) + 0.5) * self.dlat

    def cover(self, polygon):
        ring = np.asarray(polygon[0])[:, :2]
        x0 = max(0, math.floor((ring[:, 0].min() - self.west) / self.dlon))
        x1 = min(self.nx, math.ceil((ring[:, 0].max() - self.west) / self.dlon) + 1)
        y0 = max(0, math.floor((ring[:, 1].min() - self.south) / self.dlat))
        y1 = min(self.ny, math.ceil((ring[:, 1].max() - self.south) / self.dlat) + 1)
        if x0 >= x1 or y0 >= y1:
            return np.zeros(0, int), np.zeros(0, int)
        iy, ix = (a.ravel() for a in np.mgrid[y0:y1, x0:x1])
        ok = inside(np.column_stack([self.lon(ix), self.lat(iy)]), polygon)
        return iy[ok], ix[ok]

    def blocks(self, values):
        ny, nx, s = self.ny // self.sub, self.nx // self.sub, self.sub
        return values.reshape(ny, s, nx, s).transpose(0, 2, 1, 3).reshape(ny, nx, s * s)

    def cell_center(self, cy, cx):
        return (round(float(self.lon(cx * self.sub + (self.sub - 1) / 2)), DECIMALS),
                round(float(self.lat(cy * self.sub + (self.sub - 1) / 2)), DECIMALS))


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def rounded(geometry, transform=None):
    """Redondea a 5 decimales (≈1 m) y descarta vértices repetidos tras redondear."""
    out = []
    for polygon in polygons(geometry):
        new = []
        for ring in polygon:
            points = []
            for x, y, *_ in ring:
                if transform:
                    x, y = transform(x, y)
                point = [round(x, DECIMALS), round(y, DECIMALS)]
                if not points or point != points[-1]:
                    points.append(point)
            if len(points) >= 4:
                new.append(points)
        if new:
            out.append(new)
    return {'type': 'MultiPolygon', 'coordinates': out}


def barrio_name(value):
    return BARRIOS[key(value)]


class Barrios:
    def __init__(self, collection):
        self.names, self.shapes, self.comunas, self.area_ha = [], [], {}, {}
        for feature in collection['features']:
            props = feature['properties']
            name = barrio_name(props['nombre'])
            self.names.append(name)
            self.shapes.append(polygons(feature['geometry']))
            self.comunas[name] = props.get('comuna')
            self.area_ha[name] = round((props.get('area_metro') or 0) / 10_000, 1)
        rings = np.concatenate([np.asarray(p[0])[:, :2] for shape in self.shapes for p in shape])
        self.bbox = (*rings.min(axis=0), *rings.max(axis=0))

    def of(self, points):
        points = np.asarray(points, float).reshape(-1, 2)
        out = [None] * len(points)
        for name, shape in zip(self.names, self.shapes):
            hit = np.zeros(len(points), bool)
            for polygon in shape:
                hit |= inside(points, polygon)
            for i in np.flatnonzero(hit):
                out[i] = out[i] or name
        return out

    def raster(self, grid):
        values = np.full((grid.ny, grid.nx), -1, int)
        for index, shape in enumerate(self.shapes):
            for polygon in shape:
                iy, ix = grid.cover(polygon)
                values[iy, ix] = index
        return values


def projected(transformer):
    def point(geometry):
        x, y = geometry['coordinates'][:2]
        lon, lat = transformer.transform(x, y)
        return round(lon, DECIMALS), round(lat, DECIMALS)
    return point


def subte(collection, accessible_csv):
    elevators = {}
    with accessible_csv.open(encoding='utf-8-sig', newline='') as file:
        for row in csv.DictReader(file, delimiter=';'):
            try:
                elevators[(row['linea'].strip().upper(), key(row['estacion']))] = int(row['ascensores'])
            except (KeyError, ValueError):
                continue
    out = []
    for feature in collection['features']:
        props, geometry = feature['properties'], feature.get('geometry')
        if not geometry or geometry['type'] != 'Point':
            continue
        line = (props.get('linea') or '').strip().upper()
        name = (props.get('estacion') or '').strip()
        lift = elevators.get((line, key(name)))
        detail = f'Estación {name} · Línea {line}'
        if lift is not None:
            detail += f' · Ascensores informados: {lift}'
        out.append({'name': name, 'line': line, 'elevators': lift, 'lon': round(geometry['coordinates'][0], DECIMALS),
                    'lat': round(geometry['coordinates'][1], DECIMALS), 'tooltip': detail})
    return out


def school_levels(text):
    return [level for level, label in LEVELS.items() if label in (text or '')]


def schools(collection, point):
    out = []
    for feature in collection['features']:
        geometry = feature.get('geometry')
        if not geometry or geometry['type'] != 'Point':
            continue
        props = feature['properties']
        levels = school_levels(props.get('nen_mde'))
        if not levels:
            continue
        lon, lat = point(geometry)
        management = props.get('ges') or 'Sin dato'
        out.append({'name': props.get('nam'), 'levels': levels, 'management': management, 'lon': lon, 'lat': lat,
                    'tooltip': f"{props.get('nam')} · {', '.join(levels).capitalize()} · Gestión {management.lower()}"})
    return out


def hospitals(collection, point):
    out = []
    for feature in collection['features']:
        geometry = feature.get('geometry')
        if not geometry or geometry['type'] != 'Point':
            continue
        props = feature['properties']
        lon, lat = point(geometry)
        detail = f"{props.get('fna') or props.get('nam')} · {props.get('esp') or 'Sin especialidad informada'}"
        out.append({'name': props.get('fna') or props.get('nam'), 'lon': lon, 'lat': lat,
                    'web': props.get('web'), 'tooltip': detail})
    return out


def cesac(collection):
    out = []
    for feature in collection['features']:
        geometry = feature.get('geometry')
        if not geometry or geometry['type'] != 'Point':
            continue
        props = feature['properties']
        lon, lat = geometry['coordinates'][:2]
        out.append({'name': props.get('nombre'), 'lon': round(lon, DECIMALS), 'lat': round(lat, DECIMALS),
                    'web': props.get('web'), 'tooltip': f"{props.get('nombre')} · {props.get('direccion') or ''}".strip(' ·')})
    return out


def commercial_garages(collection):
    if collection.get('type') != 'FeatureCollection' or not isinstance(collection.get('features'), list):
        raise ValueError('El archivo de garajes debe ser una colección GeoJSON de puntos.')
    garages = {}
    for feature in collection['features']:
        geometry = feature.get('geometry') or {}
        coordinates = geometry.get('coordinates')
        if geometry.get('type') != 'Point' or not isinstance(coordinates, list) or len(coordinates) < 2:
            continue
        lon, lat = coordinates[:2]
        if not (isinstance(lon, (int, float)) and isinstance(lat, (int, float))
                and -180 <= lon <= 180 and -90 <= lat <= 90):
            continue
        props = {key(name): value for name, value in (feature.get('properties') or {}).items()}
        name = props.get('nombre') or props.get('fna') or props.get('nam') or 'Garaje comercial'
        address = props.get('direccion') or props.get('domicilio')
        if not address and props.get('calle'):
            address = f"{props['calle']} {props.get('num') or ''}".strip()
        if not address and props.get('calle_nombre'):
            address = f"{props['calle_nombre']} {props.get('calle_altura') or ''}".strip()
        tooltip = f'{name} · {address}' if address else str(name)
        lon, lat = round(lon, DECIMALS), round(lat, DECIMALS)
        garages[lon, lat, tooltip] = {'name': str(name), 'lon': lon, 'lat': lat, 'tooltip': tooltip}
    return list(garages.values())


def green_spaces(collection):
    features = []
    for feature in collection['features']:
        props = feature['properties']
        kind = (props.get('clasificac') or '').upper()
        if kind not in PARK_CLASSES or not feature.get('geometry'):
            continue
        geometry = rounded(feature['geometry'])
        if not geometry['coordinates']:
            continue
        area = props.get('area') or 0
        name = props.get('nombre') or kind.capitalize()
        features.append({'type': 'Feature', 'geometry': geometry, 'properties': {
            'name': name, 'kind': kind.capitalize(), 'area_m2': round(area),
            'tooltip': f'{name} · {kind.capitalize()} · {area / 10_000:.2f} ha'}})
    return features


def noise_grid(collection, grid):
    values = np.full((grid.ny, grid.nx), np.nan)
    colors = {}
    for feature in collection['features']:
        props = feature['properties']
        try:
            low = float(props['dba_low'])
        except (KeyError, TypeError, ValueError):
            continue
        if props.get('color'):
            colors[int(low)] = [int(c) for c in str(props['color']).split()[:3]]
        for polygon in polygons(feature['geometry']):
            iy, ix = grid.cover(polygon)
            values[iy, ix] = np.fmax(values[iy, ix], low)
    return values, colors


def noise_cells(values, grid, inside_city):
    blocks = grid.blocks(values)
    counts = (~np.isnan(blocks)).sum(axis=-1)
    with warnings.catch_warnings():
        warnings.simplefilter('ignore', RuntimeWarning)
        medians = np.floor(np.nanmedian(blocks, axis=-1) / 5) * 5
        highest = np.nanmax(blocks, axis=-1)
    cells = []
    for cy, cx in zip(*np.nonzero((counts > 0) & inside_city)):
        lon, lat = grid.cell_center(cy, cx)
        cells.append([lon, lat, int(medians[cy, cx]), int(highest[cy, cx])])
    return cells


def share(mask, within):
    total = int(within.sum())
    return round(float((mask & within).sum()) / total, 3) if total else None


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def latest_osm(raw_dir):
    """Carpeta `osm-AAAAMMDD` más reciente que tenga las tres categorías de gastronomía, o None."""
    found = sorted(p for p in Path(raw_dir).glob('osm-[0-9]*')
                   if p.is_dir() and all((p / f'{name}.json').exists() for name in GASTRONOMIA))
    return found[-1] if found else None


def osm_capture_date(folder):
    stamp = folder.name.removeprefix('osm-')
    return f'{stamp[:4]}-{stamp[4:6]}-{stamp[6:8]}' if len(stamp) == 8 and stamp.isdigit() else None


def gastronomy(osm_dir, barrios):
    """Conteos por barrio de restaurantes, cafés y bares de OSM; None si la captura está incompleta."""
    runs_path = osm_dir / 'corridas.json'
    runs = {r['nombre']: r for r in read(runs_path)} if runs_path.exists() else {}
    truncated = [name for name in GASTRONOMIA
                 if name in runs and runs[name].get('puntos', 0) >= runs[name].get('max_items', math.inf)]
    if truncated:
        warnings.warn(f"OSM incompleto en {', '.join(truncated)}: no se usa la gastronomía.")
        return None
    counts = defaultdict(Counter)
    for name in GASTRONOMIA:
        items = read(osm_dir / f'{name}.json')
        coords = [(i.get('lon', i.get('longitude')), i.get('lat', i.get('latitude'))) for i in items]
        coords = [c for c in coords if isinstance(c[0], (int, float)) and isinstance(c[1], (int, float))]
        for barrio in barrios.of(coords) if coords else []:
            if barrio:
                counts[barrio][name] += 1
    return counts


def convert(poi_dir, entorno_dir, target, downloaded=None, osm_dir=None):
    from pyproj import Transformer

    target.mkdir(parents=True, exist_ok=True)
    source_dirs = {'poi': poi_dir, 'entorno': entorno_dir}
    path = {name: source_dirs[folder] / file for name, (folder, file, *_) in SOURCES.items()}

    barrios = Barrios(read(path['barrios']))
    grid = Grid(*barrios.bbox)
    city = barrios.raster(grid)
    cell_barrio = np.full((grid.ny // grid.sub, grid.nx // grid.sub), -1, int)
    blocks = grid.blocks(city)
    for cy, cx in zip(*np.nonzero((blocks >= 0).any(axis=-1))):
        votes = Counter(int(v) for v in blocks[cy, cx] if v >= 0)
        cell_barrio[cy, cx] = votes.most_common(1)[0][0]
    names = barrios.names
    local = projected(Transformer.from_crs('EPSG:9498', 'EPSG:4326', always_xy=True))
    gkba = Transformer.from_crs(GKBA, 'EPSG:4326', always_xy=True)

    points = {
        'subte': subte(read(path['subte']), path['subte_accesible']),
        'cesac': cesac(read(path['cesac'])),
        'hospitales': hospitals(read(path['hospitales']), local),
        'escuelas': schools(read(path['escuelas']), local),
    }
    garage_path = entorno_dir / GARAJES_ARCHIVO
    if garage_path.is_file():
        points['estacionamiento'] = commercial_garages(read(garage_path))
    for items in points.values():
        for item, name in zip(items, barrios.of([(i['lon'], i['lat']) for i in items])):
            item['barrio'] = name
        items[:] = [item for item in items if item['barrio']]

    greens = green_spaces(read(path['verdes']))
    centers = [np.asarray(f['geometry']['coordinates'][0][0]).mean(axis=0) for f in greens]
    for feature, name in zip(greens, barrios.of(centers)):
        feature['properties']['barrio'] = name
    greens = [f for f in greens if f['properties']['barrio']]

    risk_features, risk = [], np.zeros((grid.ny, grid.nx), bool)
    for feature in read(path['riesgo_hidrico'])['features']:
        geometry = rounded(feature['geometry'], gkba.transform)
        for polygon in polygons(geometry):
            iy, ix = grid.cover(polygon)
            risk[iy, ix] = True
        if geometry['coordinates']:
            risk_features.append({'type': 'Feature', 'geometry': geometry, 'properties': {
                'tooltip': 'Área de prevención por riesgo hídrico · Capa 2020 · Dato para investigar en la visita'}})

    noise, noise_colors = {}, {}
    for period in ('diurno', 'nocturno'):
        values, colors = noise_grid(read(path[f'ruido_{period}']), grid)
        noise_colors.update(colors)
        noise[period] = noise_cells(values, grid, cell_barrio >= 0)
    for period, cells in noise.items():
        for cell in cells:
            cy = int((cell[1] - grid.south) / grid.dlat) // grid.sub
            cx = int((cell[0] - grid.west) / grid.dlon) // grid.sub
            cell.append(names[cell_barrio[cy, cx]])

    osm_dir = Path(osm_dir) if osm_dir else None
    food = gastronomy(osm_dir, barrios) if osm_dir else None
    capture = osm_capture_date(osm_dir) if osm_dir else None

    summary = {}
    for index, name in enumerate(names):
        within = city == index
        mine = {layer: [i for i in items if i['barrio'] == name] for layer, items in points.items()}
        school_counts = {level: Counter(s['management'] for s in mine['escuelas'] if level in s['levels'])
                         for level in LEVELS}
        own_greens = [f['properties'] for f in greens if f['properties']['barrio'] == name]
        noise_summary = {}
        for period, cells in noise.items():
            typical = [cell[2] for cell in cells if cell[4] == name]
            noise_summary[period] = {
                'celdas': len(typical),
                'alto': (round(sum(v >= LOUD_DBA[period] for v in typical) / len(typical), 3)
                         if len(typical) >= MIN_NOISE_CELLS else None),
            }
        summary[name] = {
            'comuna': barrios.comunas[name],
            'area_ha': barrios.area_ha[name],
            'subte_lineas': sorted({s['line'] for s in mine['subte']}),
            'subte_estaciones': len(mine['subte']),
            'verdes_cantidad': len(own_greens),
            'verdes_ha': round(sum(g['area_m2'] for g in own_greens) / 10_000, 1),
            'escuelas': {level: dict(counts) for level, counts in school_counts.items()},
            'cesac': len(mine['cesac']),
            'hospitales': len(mine['hospitales']),
            'ruido': noise_summary,
            'riesgo_hidrico': share(risk, within),
        }
        if food is not None:
            summary[name]['gastronomia'] = {**{k: food[name][k] for k in GASTRONOMIA}, 'captura': capture}

    barrio_features = []
    for feature in read(path['barrios'])['features']:
        name = barrio_name(feature['properties']['nombre'])
        barrio_features.append({'type': 'Feature', 'geometry': rounded(feature['geometry']), 'properties': {
            'barrio': name, 'comuna': barrios.comunas[name], 'tooltip': f"{name} · Comuna {barrios.comunas[name]}"}})

    sources = []
    for name, (folder, file, url, title, period) in SOURCES.items():
        sources.append({'capa': name, 'titulo': title, 'archivo': file, 'periodo': period,
                        'url': CDN + url if url else None, 'sha256': digest(path[name]),
                        'licencia': 'CC-BY 2.5 AR · Buenos Aires Data'})
    if 'estacionamiento' in points:
        sources.append({'capa': 'estacionamiento', 'titulo': 'Garajes comerciales habilitados',
                        'archivo': garage_path.name, 'periodo': 'Inventario histórico · archivo publicado en 2019; vigencia a confirmar',
                        'url': GARAJES_FUENTE, 'sha256': digest(garage_path),
                        'licencia': 'CC-BY 2.5 AR · Buenos Aires Data'})
    if food is not None:
        combined = sha256(b''.join((osm_dir / f'{n}.json').read_bytes() for n in GASTRONOMIA)).hexdigest()
        sources.append({'capa': 'gastronomia', 'titulo': 'Restaurantes, cafés y bares',
                        'archivo': ', '.join(f'{n}.json' for n in GASTRONOMIA),
                        'periodo': f'Captura del {capture}' if capture else 'Captura de OpenStreetMap',
                        'url': 'https://www.openstreetmap.org/copyright', 'sha256': combined,
                        'licencia': 'ODbL · © colaboradores de OpenStreetMap'})
    write = lambda name, data: (target / name).write_text(json.dumps(data, ensure_ascii=False) + '\n', encoding='utf-8')
    write('barrios.geojson', {'type': 'FeatureCollection', 'features': barrio_features})
    write('verdes.geojson', {'type': 'FeatureCollection', 'features': greens})
    write('riesgo_hidrico.geojson', {'type': 'FeatureCollection', 'features': risk_features})
    write('puntos.json', points)
    write('ruido.json', {'celda_m': CELL_M, 'umbral_dba': LOUD_DBA, 'colores': noise_colors, **noise})
    write('resumen.json', summary)
    write('fuentes.json', {'generado': (downloaded or date.today()).isoformat(), 'fuentes': sources})
    return summary


def load(folder):
    """Carga las capas procesadas; devuelve None si todavía no se generaron."""
    folder = Path(folder)
    files = ('barrios.geojson', 'verdes.geojson', 'riesgo_hidrico.geojson', 'puntos.json', 'ruido.json',
             'resumen.json', 'fuentes.json')
    if not all((folder / name).exists() for name in files):
        return None
    return {name.split('.')[0]: read(folder / name) for name in files}


def percent(value):
    return None if value is None else round(value * 100)


def comparison_columns(summary, preferences, level='primario'):
    """Columnas descriptivas para la tabla de barrios. No combina capas en un puntaje."""
    if summary is None:
        return {}
    row = {}
    if 'Subte' in preferences:
        row['Líneas de subte'] = ' · '.join(summary['subte_lineas']) or '—'
        row['Estaciones de subte'] = summary['subte_estaciones']
    if 'Plazas y parques' in preferences:
        row['Plazas y parques'] = summary['verdes_cantidad']
        row['Superficie verde (ha)'] = summary['verdes_ha']
    if 'Escuelas' in preferences:
        counts = summary['escuelas'].get(level, {})
        row[f'Escuelas de nivel {level}'] = sum(counts.values())
        row[f'De gestión estatal ({level})'] = counts.get('Estatal', 0)
    if 'Salud' in preferences:
        row['CeSAC'] = summary['cesac']
        row['Hospitales'] = summary['hospitales']
    if 'Ruido' in preferences:
        for period, label in (('diurno', 'de día'), ('nocturno', 'de noche')):
            row[f"Ruido ≥{LOUD_DBA[period]} dBA {label} (% de celdas relevadas)"] = percent(
                summary['ruido'][period]['alto'])
    if 'Riesgo hídrico' in preferences:
        row['Superficie en área de riesgo hídrico (%)'] = percent(summary['riesgo_hidrico'])
    return row


def bbox_of(feature_collection, name, margin_m=800):
    """Rectángulo del barrio con un margen, para centrar el mapa y recortar capas pesadas."""
    coords = [point for f in feature_collection['features'] if f['properties']['barrio'] == name
              for polygon in f['geometry']['coordinates'] for point in polygon[0]]
    if not coords:
        return None
    lons, lats = [c[0] for c in coords], [c[1] for c in coords]
    dlat = margin_m / 111_320
    dlon = margin_m / (111_320 * math.cos(math.radians(sum(lats) / len(lats))))
    return min(lons) - dlon, min(lats) - dlat, max(lons) + dlon, max(lats) + dlat


def in_bbox(lon, lat, bbox):
    return bbox[0] <= lon <= bbox[2] and bbox[1] <= lat <= bbox[3]


def features_in(collection, bbox):
    def touches(feature):
        return any(in_bbox(x, y, bbox) for polygon in feature['geometry']['coordinates']
                   for x, y in polygon[0])
    return {'type': 'FeatureCollection', 'features': [f for f in collection['features'] if touches(f)]}


def crime_cells(csv_path, period, kind=None, bbox=None, cell_m=200):
    """Hechos registrados del Mapa del Delito por celda, para un mes (AAAA-MM) y un tipo opcional."""
    totals, kinds = defaultdict(int), Counter()
    dlat = cell_m / 111_320
    dlon = cell_m / (111_320 * math.cos(math.radians(-34.62)))
    with Path(csv_path).open(encoding='utf-8-sig', newline='') as file:
        for row in csv.DictReader(file):
            row = {key(k): v for k, v in row.items() if k}
            if not (row.get('fecha') or '').startswith(period):
                continue
            try:
                lat, lon = float(row['latitud']), float(row['longitud'])
                count = int(float(row.get('cantidad') or row.get('cantidad_registrada') or 1))
            except (KeyError, TypeError, ValueError):
                continue
            if not (-34.75 < lat < -34.5 and -58.56 < lon < -58.32):
                continue
            if bbox and not in_bbox(lon, lat, bbox):
                continue
            row_kind = row.get('tipo') or row.get('tipo_delito') or 'Sin dato'
            kinds[row_kind] += count
            if kind and row_kind != kind:
                continue
            cell = (math.floor(lon / dlon), math.floor(lat / dlat))
            totals[cell] += count
    cells = [{'lon': round((cx + 0.5) * dlon, DECIMALS), 'lat': round((cy + 0.5) * dlat, DECIMALS), 'hechos': n}
             for (cx, cy), n in totals.items()]
    return cells, dict(kinds)


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--poi', type=Path, default=ROOT / 'data/raw/badata-poi')
    parser.add_argument('--entorno', type=Path, default=ROOT / 'data/raw/badata-entorno')
    parser.add_argument('--destino', type=Path, default=ROOT / 'data/processed/entorno')
    parser.add_argument('--osm', type=Path, default=None,
                        help='Captura de OpenStreetMap para gastronomía (por defecto, la osm-AAAAMMDD más reciente).')
    parser.add_argument('--sin-osm', action='store_true', help='No sumar la gastronomía de OpenStreetMap.')
    args = parser.parse_args()
    osm_dir = None if args.sin_osm else (args.osm or latest_osm(ROOT / 'data/raw'))
    summary = convert(args.poi, args.entorno, args.destino, osm_dir=osm_dir)
    with_food = any('gastronomia' in s for s in summary.values())
    print(json.dumps({'barrios': len(summary), 'destino': str(args.destino),
                      'gastronomia': str(osm_dir) if with_food else None}, ensure_ascii=False))


if __name__ == '__main__':
    main()
