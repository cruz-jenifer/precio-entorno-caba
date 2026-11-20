"""ETL: avisos crudos (JSON o CSV) + Mapa del Delito de CABA → un CSV limpio y un reporte de calidad.

- **Extracción:** los avisos llegan en la entrada del Actor; el Mapa del Delito se baja del portal
  oficial (`download`), porque pesa 17 MB, más de lo que Make Free puede mover.
- **Transformación:** valida los avisos con las reglas del importador, deja una fila por aviso (la
  captura más reciente), marca posibles duplicados entre fuentes, suma los delitos registrados por
  barrio como contexto y trata los nulls (ver `docs/tratamiento-nulls.md`): el CSV limpio sale sin
  ninguno y cada imputación queda marcada.
- **Carga:** devuelve el DataFrame limpio con columnas fijas (`CLEAN_COLUMNS`); `main.py` lo guarda.

Los precios son de publicación, no tasaciones. Los delitos son hechos registrados, con período y
unidad geográfica (barrio).
"""

from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

import numpy as np
import pandas as pd

from precio_entorno.eda_delitos import comuna_by_barrio, load as load_crimes
from precio_entorno.importing import parse_listings

SOURCE = 'inmobiliarias-autorizadas'
CRIMES_URL = ('https://cdn.buenosaires.gob.ar/datosabiertos/datasets/ministerio-de-justicia-y-seguridad/'
              'delitos/delitos_2025.csv')
CRIMES_SHA256 = '1ed67c3346eb4f42635cc44bc78e00ec2b023370f1ff6df0e7f309c72a6b45df'
CLEAN_COLUMNS = [
    'id', 'fuente', 'barrio', 'comuna', 'ambientes', 'superficie_cubierta_m2', 'superficie_total_m2',
    'superficie_total_imputada', 'precio', 'moneda', 'precio_m2_usd', 'expensas_informadas', 'latitud', 'longitud',
    'tiene_pin', 'ubicacion_origen', 'fecha_captura', 'grupo_duplicado', 'posible_duplicado', 'delitos_barrio',
    'robos_hurtos_barrio', 'pct_con_arma_barrio', 'periodo_delitos', 'unidad_delitos', 'url',
]
# Campos sin los cuales el importador descarta el aviso.
REQUIRED = ('listing_id', 'url', 'captured_at', 'price', 'currency', 'covered_area_m2', 'rooms', 'neighborhood')
# Origen de las coordenadas del CSV limpio (ver docs/tratamiento-nulls.md).
PIN_PUBLICADO, PIN_BARRIO, PIN_COMUNA = 'publicada', 'mediana_barrio', 'mediana_comuna'


def download(url, path=None, timeout=120):
    """Baja un archivo público. Si se da `path`, además lo escribe ahí."""
    request = Request(url, headers={'User-Agent': 'precio-entorno-caba (capstone)'})
    with urlopen(request, timeout=timeout) as response:
        data = response.read()
    if path:
        Path(path).write_bytes(data)
    return data


def crimes_by_barrio(crimes_path):
    """Hechos delictivos registrados por barrio en todo el archivo (sin siniestros viales)."""
    rows, quality = load_crimes(crimes_path)
    crimes = rows[rows['delito']]
    by_barrio = pd.DataFrame({
        'delitos_barrio': crimes.groupby('barrio')['cantidad'].sum(),
        'robos_hurtos_barrio': crimes[crimes['tipo'].isin(['Robo', 'Hurto'])].groupby('barrio')['cantidad'].sum(),
        'con_arma': crimes[crimes['uso_arma']].groupby('barrio')['cantidad'].sum(),
    }).fillna(0)
    # Un barrio sin delitos registrados tiene 0 % con arma, no un cociente indefinido.
    by_barrio['pct_con_arma_barrio'] = (by_barrio.pop('con_arma') / by_barrio['delitos_barrio'].where(
        by_barrio['delitos_barrio'] > 0) * 100).round(1).fillna(0.0)
    by_barrio['comuna'] = comuna_by_barrio(rows)
    period = f'{quality["periodo"][0]} a {quality["periodo"][1]}'
    return by_barrio, period, quality


def fill_total_area(total, covered):
    """Superficie total faltante → la cubierta. Es la cota inferior segura: la validación ya anula
    las totales menores que la cubierta, así que no se inventan m² descubiertos."""
    imputed = total.isna()
    return total.where(~imputed, covered), imputed


def fill_coordinates(lat, lon, barrio, comuna):
    """Sin pin publicado → mediana de los pines publicados del barrio (si no hay, de la comuna).

    Un par incompleto (latitud sin longitud o al revés) cuenta como sin pin: medio punto no ubica.
    Devuelve latitud, longitud y el origen de cada fila (`publicada`, `mediana_barrio`, `mediana_comuna`).
    """
    published = lat.notna() & lon.notna()
    lat, lon = lat.where(published), lon.where(published)
    origin = pd.Series(np.where(published, PIN_PUBLICADO, None), index=lat.index, dtype=object)
    for key, label in ((barrio, PIN_BARRIO), (comuna, PIN_COMUNA)):
        missing = lat.isna()
        if not missing.any():
            break
        med_lat = lat[published].groupby(key[published]).median()
        med_lon = lon[published].groupby(key[published]).median()
        fill_lat, fill_lon = key.map(med_lat), key.map(med_lon)
        use = missing & fill_lat.notna()
        lat, lon = lat.where(~use, fill_lat), lon.where(~use, fill_lon)
        origin[use] = label
    return lat.round(6), lon.round(6), origin


def etl(content, filename, crimes_path):
    """Avisos crudos (JSON o CSV) + Mapa del Delito → (DataFrame limpio, reporte)."""
    listings, report = parse_listings(content, filename, SOURCE)
    if not listings:
        raise ValueError('No hay avisos válidos en el archivo.')
    df = pd.DataFrame(listings)
    valid_observations = len(df)
    df['captured_at'] = pd.to_datetime(df['captured_at'], format='ISO8601', utc=True)
    df = df.sort_values('captured_at').drop_duplicates('id', keep='last').reset_index(drop=True)
    df['fuente'] = df['id'].map(lambda i: i.split(':', 1)[0] if ':' in i else SOURCE)
    # Misma regla que el modelo: fuentes distintas con barrio, ambientes, m² y precio redondeados iguales.
    key = (df['neighborhood'] + '|' + df['rooms'].astype(int).astype(str) + '|'
           + df['covered_area'].round().astype(int).astype(str) + '|' + df['price'].round(-3).astype(int).astype(str))
    many_sources = df.groupby(key)['fuente'].transform('nunique') > 1
    df['grupo_duplicado'] = np.where(many_sources, 'dup:' + key, df['id'])

    by_barrio, period, crime_quality = crimes_by_barrio(crimes_path)
    comuna = df['neighborhood'].map(by_barrio['comuna']).astype('Int64')
    nulls_before = {
        'superficie_total_m2': int(df['total_area_m2'].isna().sum()),
        'expensas_ars': int(df['expenses'].isna().sum()),
        'latitud': int(df['latitude'].isna().sum()),
        'longitud': int(df['longitude'].isna().sum()),
    }
    total_area, total_imputed = fill_total_area(df['total_area_m2'], df['covered_area'])
    lat, lon, pin_origin = fill_coordinates(df['latitude'], df['longitude'], df['neighborhood'], comuna)
    clean = pd.DataFrame({
        'id': df['id'],
        'fuente': df['fuente'],
        'barrio': df['neighborhood'],
        'comuna': comuna,
        'ambientes': df['rooms'].astype(int),
        'superficie_cubierta_m2': df['covered_area'],
        'superficie_total_m2': total_area,
        'superficie_total_imputada': total_imputed,
        'precio': df['price'],
        'moneda': df['currency'],
        'precio_m2_usd': np.where(df['currency'] == 'USD', (df['price'] / df['covered_area']).round(1), np.nan),
        'expensas_informadas': df['expenses'].notna(),
        'latitud': lat,
        'longitud': lon,
        'tiene_pin': pin_origin == PIN_PUBLICADO,
        'ubicacion_origen': pin_origin,
        'fecha_captura': df['captured_at'].dt.strftime('%Y-%m-%d'),
        'grupo_duplicado': df['grupo_duplicado'],
        'posible_duplicado': many_sources,
        'delitos_barrio': df['neighborhood'].map(by_barrio['delitos_barrio']).astype('Int64'),
        'robos_hurtos_barrio': df['neighborhood'].map(by_barrio['robos_hurtos_barrio']).astype('Int64'),
        'pct_con_arma_barrio': df['neighborhood'].map(by_barrio['pct_con_arma_barrio']),
        'periodo_delitos': period,
        'unidad_delitos': 'barrio',
        'url': df['url'],
    })[CLEAN_COLUMNS]
    clean = clean.sort_values(['barrio', 'precio_m2_usd']).reset_index(drop=True)
    remaining = clean.isna().sum()
    remaining = remaining[remaining > 0]
    if len(remaining):
        # El CSV limpio no sale con nulls: si una regla no alcanza, la corrida falla y Make corta el flujo.
        raise ValueError('El CSV limpio quedó con nulls en: '
                         + ', '.join(f'{col} ({n})' for col, n in remaining.items()))
    origins = clean['ubicacion_origen'].value_counts()
    return clean, {
        'archivo': filename,
        'filas_leidas': report.read,
        'observaciones_validas': valid_observations,
        'filas_descartadas': report.discarded,
        'motivos_descarte': dict(report.invalid),
        'campos_faltantes': dict(report.missing),
        'capturas_repetidas_unificadas': valid_observations - len(clean),
        'avisos': len(clean),
        'posibles_duplicados': int(clean['posible_duplicado'].sum()),
        'tratamiento_nulls': {
            # Sin un campo obligatorio el aviso no entra (eliminación por fila). Una fila puede faltar en varios.
            'obligatorios_faltantes_descartados': {k: int(report.missing[k]) for k in REQUIRED if report.missing[k]},
            'superficie_total_m2': {
                'faltantes': nulls_before['superficie_total_m2'],
                'tratamiento': 'imputada con la superficie cubierta; marca superficie_total_imputada',
                'filas_imputadas': int(clean['superficie_total_imputada'].sum()),
            },
            'expensas_ars': {
                'faltantes': nulls_before['expensas_ars'],
                'pct_faltante': round(nulls_before['expensas_ars'] / valid_observations * 100, 1),
                'tratamiento': 'columna eliminada; queda expensas_informadas (si/no)',
            },
            'latitud_longitud': {
                'faltantes_latitud': nulls_before['latitud'],
                'faltantes_longitud': nulls_before['longitud'],
                'tratamiento': 'par incompleto = sin pin; imputado con la mediana de los pines publicados del '
                               'barrio (o de la comuna); marca ubicacion_origen',
                'filas_imputadas': int(len(clean) - origins.get(PIN_PUBLICADO, 0)),
                'por_origen': {k: int(v) for k, v in origins.items()},
            },
            'nulls_finales': int(clean.isna().sum().sum()),
        },
        'delitos': {k: crime_quality[k] for k in ('archivo', 'sha256', 'filas_leidas', 'filas_validas',
                                                    'periodo', 'hechos_registrados')},
        'delitos_sha256_esperado': crime_quality['sha256'] == CRIMES_SHA256,
        'fecha_corrida': datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC'),
    }
