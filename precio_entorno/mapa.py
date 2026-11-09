"""Mapa del entorno de un barrio con capas activables, armado con pydeck."""

import math

from .entorno import LEVELS, SUBTE_COLORS, bbox_of, features_in, in_bbox

LAYERS = ('Subte', 'Plazas y parques', 'Escuelas', 'Salud', 'Ruido', 'Riesgo hídrico', 'Delitos registrados')
PREFERENCES = LAYERS[:-1]
COLORS = {
    'cesac': [0, 150, 136], 'hospitales': [121, 85, 72], 'escuelas': [245, 124, 0],
    'verdes': [67, 160, 71], 'riesgo': [30, 136, 229], 'barrio': [33, 33, 33],
}
# Escala secuencial propia para que las calles sigan legibles; el visor oficial usa la paleta ISO.
NOISE_RAMP = {50: [255, 255, 204], 55: [255, 237, 160], 60: [254, 217, 118], 65: [254, 178, 76],
              70: [253, 141, 60], 75: [240, 59, 32], 80: [189, 0, 38]}
CRIME_RAMP = [[243, 229, 245], [206, 147, 216], [171, 71, 188], [123, 31, 162], [74, 20, 140]]
NOTES = {
    'Subte': 'Subte: estaciones y líneas. Indican conectividad, no tiempos de viaje puerta a puerta.',
    'Plazas y parques': 'Plazas y parques: sin canteros centrales, plazoletas ni patios.',
    'Escuelas': 'Escuelas: la cercanía no indica vacantes ni elegibilidad. Consultá cada establecimiento.',
    'Salud': 'Salud: CeSAC y hospitales. La cercanía no indica disponibilidad de turnos.',
    'Ruido': ('Ruido: nivel exterior típico en celdas de 100 m, sobre todo en calles y veredas. '
              'No describe el interior de un departamento.'),
    'Riesgo hídrico': ('Riesgo hídrico: áreas de prevención publicadas en 2020. '
                       'Que una dirección caiga dentro es un dato para investigar en la visita.'),
    'Delitos registrados': ('Delitos: hechos registrados por celda de 200 m en el mes elegido. Los conteos reflejan '
                            'también diferencias de exposición, registro y denuncia. No son un puntaje de seguridad.'),
}


def hex_color(rgb):
    return '#{:02X}{:02X}{:02X}'.format(*rgb[:3])


def rgb(value):
    value = value.lstrip('#')
    return [int(value[i:i + 2], 16) for i in (0, 2, 4)]


def view(bbox, width_px=700, height_px=520):
    """Vista que encuadra el barrio. deck.gl usa teselas de 512 px y Mercator estira la latitud."""
    west, south, east, north = bbox
    stretch = 1 / math.cos(math.radians((south + north) / 2))
    by_width = math.log2(width_px / 512 * 360 / max(east - west, 1e-4))
    by_height = math.log2(height_px / 512 * 360 / max((north - south) * stretch, 1e-4))
    zoom = min(by_width, by_height) - 0.15
    return {'longitude': (west + east) / 2, 'latitude': (south + north) / 2, 'zoom': max(11, min(16, zoom))}


def noise_label(value):
    return 'Menos de 55 dBA' if value < 55 else '80 dBA o más' if value >= 80 else band(value)


def noise_color(value):
    return NOISE_RAMP[max(50, min(80, value))] + ([70] if value < 55 else [125])


def band(value):
    return f'{value}–{value + 5} dBA'


CRIME_ALPHA = [70, 110, 150, 185, 215]


def crime_step(count, top):
    return min(len(CRIME_RAMP) - 1, int((count / top) * len(CRIME_RAMP))) if top else 0


def crime_color(count, top):
    step = crime_step(count, top)
    return CRIME_RAMP[step] + [CRIME_ALPHA[step]]


def crime_legend(top):
    """Rangos de hechos por celda que corresponden a cada tono de la escala."""
    groups = {}
    for count in range(1, top + 1):
        groups.setdefault(crime_step(count, top), []).append(count)
    return [(hex_color(CRIME_RAMP[step]), f'{c[0]} hecho' + ('' if c[0] == 1 == c[-1] else 's')
             if c[0] == c[-1] else f'{c[0]}–{c[-1]} hechos') for step, c in sorted(groups.items())]


def build(capas, barrio, active, level='primario', noise_period='diurno', crime=None, crime_label=''):
    """Devuelve las capas de pydeck, la vista y la leyenda de las capas activas."""
    import pydeck as pdk

    bbox = bbox_of(capas['barrios'], barrio)
    tight = bbox_of(capas['barrios'], barrio, margin_m=0)
    layers, legend = [], []

    if 'Ruido' in active:
        noise = capas['ruido']
        label = 'diurno' if noise_period == 'diurno' else 'nocturno'
        rows = [{'lon': lon, 'lat': lat, 'typical': typical, 'color': noise_color(typical),
                 'tooltip': f'Nivel exterior típico {band(typical)} · máximo en la celda {band(top)} · '
                            f'Mapa de Ruido 2025 ({label})'}
                for lon, lat, typical, top, _ in noise[noise_period] if in_bbox(lon, lat, bbox)]
        layers.append(pdk.Layer('ColumnLayer', rows, get_position=['lon', 'lat'], get_fill_color='color',
                                radius=noise['celda_m'] / math.sqrt(2), disk_resolution=4, angle=45,
                                extruded=False, pickable=True))
        seen = sorted({r['typical'] for r in rows})
        legend += [(hex_color(noise_color(v)), noise_label(v)) for v in sorted({max(50, min(80, v)) for v in seen})]

    if 'Riesgo hídrico' in active:
        layers.append(pdk.Layer('GeoJsonLayer', features_in(capas['riesgo_hidrico'], bbox),
                                get_fill_color=COLORS['riesgo'] + [90], get_line_color=COLORS['riesgo'] + [220],
                                line_width_min_pixels=1, pickable=True))
        legend.append((hex_color(COLORS['riesgo']), 'Área de prevención por riesgo hídrico'))

    if 'Delitos registrados' in active and crime:
        top = max(cell['hechos'] for cell in crime)
        rows = [dict(cell, color=crime_color(cell['hechos'], top),
                     tooltip=f"{cell['hechos']} hechos registrados · {crime_label}") for cell in crime]
        layers.append(pdk.Layer('ColumnLayer', rows, get_position=['lon', 'lat'], get_fill_color='color',
                                radius=200 / math.sqrt(2), disk_resolution=4, angle=45,
                                extruded=False, pickable=True))
        legend += [(color, ('Delitos registrados por celda: ' if i == 0 else '') + label)
                   for i, (color, label) in enumerate(crime_legend(top))]

    if 'Plazas y parques' in active:
        layers.append(pdk.Layer('GeoJsonLayer', features_in(capas['verdes'], bbox),
                                get_fill_color=COLORS['verdes'] + [140], get_line_color=COLORS['verdes'] + [255],
                                line_width_min_pixels=1, pickable=True))
        legend.append((hex_color(COLORS['verdes']), 'Plazas y parques'))

    outline = [dict(f, properties=dict(f['properties'], selected=f['properties']['barrio'] == barrio))
               for f in features_in(capas['barrios'], bbox)['features']]
    layers.append(pdk.Layer('GeoJsonLayer', {'type': 'FeatureCollection', 'features': outline}, stroked=True,
                            filled=False, get_line_color=COLORS['barrio'] + [200],
                            get_line_width='properties.selected ? 4 : 1', line_width_units='pixels'))

    points = capas['puntos']

    def scatter(items, color, radius=6):
        layers.append(pdk.Layer('ScatterplotLayer', [i for i in items if in_bbox(i['lon'], i['lat'], bbox)],
                                get_position=['lon', 'lat'], get_fill_color=color, get_line_color=[255, 255, 255],
                                stroked=True, line_width_min_pixels=1, radius_min_pixels=radius,
                                radius_max_pixels=radius + 4, get_radius=30, pickable=True))

    if 'Escuelas' in active:
        scatter([s for s in points['escuelas'] if level in s['levels']], COLORS['escuelas'] + [230], 5)
        legend.append((hex_color(COLORS['escuelas']), f'Escuelas de nivel {level}'))
    if 'Salud' in active:
        scatter(points['cesac'], COLORS['cesac'] + [240])
        scatter(points['hospitales'], COLORS['hospitales'] + [240], 8)
        legend += [(hex_color(COLORS['cesac']), 'CeSAC'), (hex_color(COLORS['hospitales']), 'Hospitales')]
    if 'Subte' in active:
        stations = [dict(s, color=rgb(SUBTE_COLORS.get(s['line'], '#555555')) + [255]) for s in points['subte']]
        scatter(stations, 'color', 7)
        lines = sorted({s['line'] for s in stations if in_bbox(s['lon'], s['lat'], tight)})
        legend += [(SUBTE_COLORS.get(line, '#555555'), f'Línea {line}') for line in lines]

    deck = pdk.Deck(layers=layers, initial_view_state=pdk.ViewState(**view(tight)), map_style=None,
                    tooltip={'html': '{tooltip}', 'style': {'fontSize': '12px', 'maxWidth': '320px'}})
    return deck, legend


def legend_html(items):
    chips = ''.join(
        f'<span style="display:inline-flex;align-items:center;gap:6px;margin:2px 12px 2px 0;font-size:0.8rem">'
        f'<span style="width:11px;height:11px;border-radius:3px;background:{color};display:inline-block"></span>'
        f'{label}</span>' for color, label in items)
    return f'<div style="line-height:1.6">{chips}</div>'


LEVEL_NAMES = list(LEVELS)
