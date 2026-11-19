"""ETL y EDA del flujo Analytics: crudo en Drive → Apify (ETL) → CSV limpio → Apify (EDA) → tablas.

Lo usa el Actor `precio-entorno-analytics` (`actor_analytics.py`) y también se corre local:

    python -m precio_entorno.pipeline_analytics etl data/raw/venta-consolidada-20261108/avisos.json
    python -m precio_entorno.pipeline_analytics eda data/processed/pipeline/dataset_limpio.csv

- **ETL:** valida los avisos con las reglas del importador, deja una fila por aviso (la captura
  más reciente), marca posibles duplicados entre fuentes y suma el contexto del Mapa del Delito
  por barrio. Devuelve un único CSV limpio y un reporte de calidad.
- **EDA:** arma las tablas del dashboard (resumen, barrios, ambientes, fuentes, distribución y
  correlaciones) y el cuerpo para escribirlas en Google Sheets con `values:batchUpdate`.

Los precios son de publicación, no tasaciones. Los delitos son hechos registrados, con período y
unidad geográfica (barrio), y se muestran como contexto.
"""

import argparse
import io
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from precio_entorno.eda_delitos import comuna_by_barrio, load as load_crimes
from precio_entorno.importing import parse_listings

ROOT = Path(__file__).resolve().parents[1]
SOURCE = 'inmobiliarias-autorizadas'
CRIMES_URL = ('https://cdn.buenosaires.gob.ar/datosabiertos/datasets/ministerio-de-justicia-y-seguridad/'
              'delitos/delitos_2025.csv')
CRIMES_SHA256 = '1ed67c3346eb4f42635cc44bc78e00ec2b023370f1ff6df0e7f309c72a6b45df'
SMALL_SAMPLE = 10
CLEAN_COLUMNS = [
    'id', 'fuente', 'barrio', 'comuna', 'ambientes', 'superficie_cubierta_m2', 'superficie_total_m2',
    'precio', 'moneda', 'precio_m2_usd', 'expensas_ars', 'latitud', 'longitud', 'tiene_pin', 'fecha_captura',
    'grupo_duplicado', 'posible_duplicado', 'delitos_barrio', 'robos_hurtos_barrio', 'pct_con_arma_barrio',
    'periodo_delitos', 'unidad_delitos', 'url',
]
# Pestañas de la planilla del dashboard, sin tildes (Make y Looker las leen mejor así).
SHEETS = ('resumen', 'barrios', 'ambientes', 'fuentes', 'distribucion', 'correlaciones')


# ---------------------------------------------------------------- ETL

def crimes_by_barrio(crimes_path):
    """Hechos delictivos registrados por barrio en todo el archivo (sin siniestros viales)."""
    rows, quality = load_crimes(crimes_path)
    crimes = rows[rows['delito']]
    by_barrio = pd.DataFrame({
        'delitos_barrio': crimes.groupby('barrio')['cantidad'].sum(),
        'robos_hurtos_barrio': crimes[crimes['tipo'].isin(['Robo', 'Hurto'])].groupby('barrio')['cantidad'].sum(),
        'con_arma': crimes[crimes['uso_arma']].groupby('barrio')['cantidad'].sum(),
    }).fillna(0)
    by_barrio['pct_con_arma_barrio'] = (by_barrio.pop('con_arma') / by_barrio['delitos_barrio'] * 100).round(1)
    by_barrio['comuna'] = comuna_by_barrio(rows)
    period = f'{quality["periodo"][0]} a {quality["periodo"][1]}'
    return by_barrio, period, quality


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
    clean = pd.DataFrame({
        'id': df['id'],
        'fuente': df['fuente'],
        'barrio': df['neighborhood'],
        'comuna': df['neighborhood'].map(by_barrio['comuna']).astype('Int64'),
        'ambientes': df['rooms'].astype(int),
        'superficie_cubierta_m2': df['covered_area'],
        'superficie_total_m2': df['total_area_m2'],
        'precio': df['price'],
        'moneda': df['currency'],
        'precio_m2_usd': np.where(df['currency'] == 'USD', (df['price'] / df['covered_area']).round(1), np.nan),
        'expensas_ars': df['expenses'],
        'latitud': df['latitude'],
        'longitud': df['longitude'],
        'tiene_pin': df['latitude'].notna() & df['longitude'].notna(),
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
        'delitos': {k: crime_quality[k] for k in ('archivo', 'sha256', 'filas_leidas', 'filas_validas',
                                                    'periodo', 'hechos_registrados')},
        'delitos_sha256_esperado': crime_quality['sha256'] == CRIMES_SHA256,
        'fecha_corrida': datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC'),
    }


def to_csv(df):
    return df.to_csv(index=False, lineterminator='\n')


# ---------------------------------------------------------------- EDA

def read_clean(content):
    return pd.read_csv(io.BytesIO(content) if isinstance(content, bytes) else io.StringIO(content))


def rooms_label(n):
    return '5 o más' if n >= 5 else str(int(n))


def eda(clean, etl_report=None):
    """Tablas del dashboard a partir del CSV limpio. Solo los avisos en USD entran en USD/m²."""
    usd = clean[clean['precio_m2_usd'].notna()].copy()
    usd['tiene_pin'] = usd['tiene_pin'].astype(str).str.lower().eq('true')
    period = usd['periodo_delitos'].dropna().iloc[0] if usd['periodo_delitos'].notna().any() else ''
    median = lambda s: round(float(s.median()), 1) if s.notna().any() else None

    resumen = pd.DataFrame([{
        'fecha_corrida': (etl_report or {}).get('fecha_corrida') or datetime.now(timezone.utc).strftime(
            '%Y-%m-%d %H:%M UTC'),
        'filas_leidas': (etl_report or {}).get('filas_leidas'),
        'filas_descartadas': (etl_report or {}).get('filas_descartadas'),
        'avisos': len(usd),
        'barrios': int(usd['barrio'].nunique()),
        'fuentes': int(usd['fuente'].nunique()),
        'mediana_usd_m2': median(usd['precio_m2_usd']),
        'mediana_precio_usd': median(usd['precio']),
        'mediana_superficie_m2': median(usd['superficie_cubierta_m2']),
        'posibles_duplicados': int(usd['posible_duplicado'].astype(str).str.lower().eq('true').sum()),
        'periodo_delitos': period,
        'nota': 'Precios de publicación, no tasaciones. Delitos registrados por barrio, como contexto.',
    }])

    g = usd.groupby('barrio')
    barrios = pd.DataFrame({
        'comuna': g['comuna'].first(),
        'avisos': g.size(),
        'mediana_usd_m2': g['precio_m2_usd'].median().round(0),
        'p25_usd_m2': g['precio_m2_usd'].quantile(0.25).round(0),
        'p75_usd_m2': g['precio_m2_usd'].quantile(0.75).round(0),
        'mediana_precio_usd': g['precio'].median().round(0),
        'mediana_superficie_m2': g['superficie_cubierta_m2'].median().round(0),
        'pct_con_pin': (g['tiene_pin'].mean() * 100).round(1),
        'latitud': g['latitud'].median().round(5),
        'longitud': g['longitud'].median().round(5),
        'delitos_registrados': g['delitos_barrio'].first(),
        'robos_hurtos': g['robos_hurtos_barrio'].first(),
        'pct_con_arma': g['pct_con_arma_barrio'].first(),
    }).reset_index()
    # Looker Studio reconoce "lat,lon" como campo geográfico para el mapa de burbujas.
    barrios['ubicacion'] = np.where(barrios['latitud'].notna(),
                                    barrios['latitud'].astype(str) + ',' + barrios['longitud'].astype(str), '')
    barrios['muestra_chica'] = np.where(barrios['avisos'] < SMALL_SAMPLE, 'si', 'no')
    barrios['periodo_delitos'] = period
    barrios['unidad_delitos'] = 'barrio'
    barrios = barrios.sort_values('mediana_usd_m2', ascending=False)

    usd['ambientes_grupo'] = usd['ambientes'].map(rooms_label)
    g = usd.groupby('ambientes_grupo')
    ambientes = pd.DataFrame({
        'avisos': g.size(),
        'mediana_usd_m2': g['precio_m2_usd'].median().round(0),
        'mediana_precio_usd': g['precio'].median().round(0),
        'mediana_superficie_m2': g['superficie_cubierta_m2'].median().round(0),
    }).reset_index().rename(columns={'ambientes_grupo': 'ambientes'})

    g = usd.groupby('fuente')
    fuentes = pd.DataFrame({
        'avisos': g.size(),
        'pct_avisos': (g.size() / len(usd) * 100).round(1),
        'mediana_usd_m2': g['precio_m2_usd'].median().round(0),
        'pct_con_pin': (g['tiene_pin'].mean() * 100).round(1),
        'pct_con_expensas': (g['expensas_ars'].apply(lambda s: s.notna().mean()) * 100).round(1),
        'pct_con_superficie_total': (g['superficie_total_m2'].apply(lambda s: s.notna().mean()) * 100).round(1),
    }).reset_index().sort_values('avisos', ascending=False)

    edges = list(range(0, 6000, 500)) + [np.inf]
    bins = pd.cut(usd['precio_m2_usd'], edges, right=False)
    counts = bins.value_counts().sort_index()
    distribucion = pd.DataFrame({
        'rango_usd_m2': [f'{int(i.left):,}+'.replace(',', '.') if np.isinf(i.right)
                         else f'{int(i.left):,}–{int(i.right) - 1:,}'.replace(',', '.') for i in counts.index],
        'desde_usd_m2': [int(i.left) for i in counts.index],
        'avisos': counts.to_numpy(),
    })
    distribucion['pct'] = (distribucion['avisos'] / len(usd) * 100).round(1)
    distribucion = distribucion[distribucion['avisos'] > 0]

    variables = {'superficie_cubierta_m2': 'Superficie cubierta (m²)', 'ambientes': 'Ambientes',
                 'delitos_barrio': 'Delitos registrados en el barrio', 'robos_hurtos_barrio': 'Robos y hurtos en el barrio',
                 'latitud': 'Latitud (norte-sur)', 'longitud': 'Longitud (este-oeste)'}
    corr = []
    for col, label in variables.items():
        pair = usd[[col, 'precio_m2_usd']].dropna().astype(float)
        defined = len(pair) > 2 and (pair.std() > 0).all()
        # Spearman = Pearson sobre rangos; así el Actor no necesita scipy.
        corr.append({'variable': label, 'columna': col, 'n': len(pair),
                     'pearson': round(float(pair[col].corr(pair['precio_m2_usd'])), 3) if defined else None,
                     'spearman': round(float(pair.rank()[col].corr(pair.rank()['precio_m2_usd'])), 3) if defined else None,
                     'unidad': 'aviso', 'nota': 'Asociación, no causalidad'})
    correlaciones = pd.DataFrame(corr)
    return {'resumen': resumen, 'barrios': barrios, 'ambientes': ambientes, 'fuentes': fuentes,
            'distribucion': distribucion, 'correlaciones': correlaciones}


def cell(v):
    if v is None or (isinstance(v, float) and np.isnan(v)) or v is pd.NA:
        return ''
    if isinstance(v, (np.integer,)):
        return int(v)
    if isinstance(v, (np.floating,)):
        return float(v)
    if isinstance(v, (np.bool_, bool)):
        return 'si' if v else 'no'
    return v


def sheets_body(tables):
    """Cuerpo de `spreadsheets.values:batchUpdate`: una pestaña por tabla, desde A1."""
    data = []
    for name in SHEETS:
        df = tables[name].astype(object).where(tables[name].notna(), None)
        values = [list(df.columns)] + [[cell(v) for v in row] for row in df.itertuples(index=False)]
        data.append({'range': f'{name}!A1', 'majorDimension': 'ROWS', 'values': values})
    return {'valueInputOption': 'RAW', 'data': data}


def clear_body():
    return {'ranges': list(SHEETS)}


def inference(clean, model_folder):
    """CSV limpio → referencias versionadas; no entrena ni usa delitos como variables."""
    from precio_entorno.inferencia import load, predict
    frame = clean.rename(columns={
        'barrio': 'neighborhood', 'ambientes': 'rooms', 'moneda': 'currency',
        'superficie_cubierta_m2': 'covered_area', 'superficie_total_m2': 'total_area_m2',
        'latitud': 'latitude', 'longitud': 'longitude', 'fuente': 'agency',
    })
    return predict(load(model_folder), frame)


# ---------------------------------------------------------------- CLI

def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('operacion', choices=('etl', 'eda', 'inferencia'))
    parser.add_argument('archivo', type=Path, help='etl: avisos crudos (JSON o CSV); eda: CSV limpio')
    parser.add_argument('--delitos', type=Path, default=ROOT / 'data/raw/delitos_2025.csv')
    parser.add_argument('--salida', type=Path, default=ROOT / 'data/processed/pipeline')
    parser.add_argument('--modelo', type=Path, default=ROOT / 'data/processed/inferencia')
    args = parser.parse_args()
    args.salida.mkdir(parents=True, exist_ok=True)
    try:
        if args.operacion == 'etl':
            clean, report = etl(args.archivo.read_bytes(), args.archivo.name, args.delitos)
            (args.salida / 'dataset_limpio.csv').write_bytes(to_csv(clean).encode('utf-8'))
            (args.salida / 'reporte_etl.json').write_text(json.dumps(report, ensure_ascii=False, indent=2),
                                                          encoding='utf-8')
            print(json.dumps(report, ensure_ascii=False, indent=2))
        elif args.operacion == 'inferencia':
            predictions = inference(read_clean(args.archivo.read_bytes()), args.modelo)
            predictions.to_csv(args.salida / 'predicciones.csv', index=False)
            values = [list(predictions.columns)] + predictions.values.tolist()
            body = {'valueInputOption': 'RAW', 'data': [{'range': 'predicciones!A1', 'values': values}]}
            (args.salida / 'sheets_predicciones_body.json').write_text(
                json.dumps(body, ensure_ascii=False), encoding='utf-8')
            print(f'{len(predictions)} referencias generadas con el modelo guardado.')
        else:
            report_path = args.salida / 'reporte_etl.json'
            report = json.loads(report_path.read_text(encoding='utf-8')) if report_path.exists() else None
            tables = eda(read_clean(args.archivo.read_bytes()), report)
            for name, df in tables.items():
                (args.salida / f'{name}.csv').write_bytes(to_csv(df).encode('utf-8'))
            (args.salida / 'sheets_body.json').write_text(json.dumps(sheets_body(tables), ensure_ascii=False),
                                                          encoding='utf-8')
            print(tables['resumen'].T.to_string(header=False))
    except (OSError, ValueError) as error:
        parser.exit(1, f'Error: {error}\n')


if __name__ == '__main__':
    main()
