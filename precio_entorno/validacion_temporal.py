"""Validación temporal del modelo guardado con avisos publicados después del entrenamiento.

El modelo vigente se entrenó con avisos de venta capturados del 7 al 9/11/2026. Esta validación lo
evalúa, sin reentrenar ni ajustar nada, con capturas posteriores:

- `zonaprop-exclusividad-20261120`: Zonaprop por Apify, Caballito y Almagro, 2 ambientes, hasta
  USD 165.000 (un segmento angosto, sin rasgos de edificio ni de descripción);
- `inmobiliarias-2026111{3,5,7}-0900`: inmobiliarias autorizadas, 40 barrios.

Se quitan los avisos que ya estaban en el entrenamiento (mismo ID) y los que probablemente son el
mismo inmueble publicado por otra fuente (misma regla de duplicados del modelo: barrio, ambientes,
m² cubiertos y precio redondeados). Las variables se calculan con el mismo pipeline del
entrenamiento (`modelo.load_listings` con pines aproximados y `modelo.amenities` con las mismas
capas). La línea de base es la mediana de comparables calculada solo con los datos de
entrenamiento. Cada segmento se informa por separado.

    python -m precio_entorno.validacion_temporal

Escribe `reports/validacion_temporal.json` (solo agregados, sin avisos) y las predicciones por
aviso en `data/processed/validacion-temporal/`, fuera de Git. Mide precios de publicación, no
precios de cierre.
"""

import argparse
import json
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd

from precio_entorno.analytics.inference import load, predict
from precio_entorno.comparar_modelos import DEFAULT_DATASET, load_dataset, metrics
from precio_entorno.inferencia import DEFAULT_OUT
from precio_entorno.modelo import amenities, comparables, load_listings, load_osm

ROOT = Path(__file__).resolve().parents[1]
CATALOG = 'inmobiliarias-autorizadas'
OSM = (ROOT / 'data/raw/osm-20261107', ROOT / 'data/processed/poi-badata')
ZONAPROP = ROOT / 'data/raw/zonaprop-exclusividad-20261120'
AGENCIES = [ROOT / f'data/raw/inmobiliarias-2026111{d}-0900' for d in (3, 5, 7)]
SEGMENTS = {'zonaprop_20261120': 'Zonaprop 20/11 · Caballito y Almagro, 2 amb., hasta USD 165.000',
            'inmobiliarias_13a17': 'Inmobiliarias autorizadas 13 a 17/11 · 40 barrios'}
THRESHOLD = 0.20


def zonaprop_rows(rows, captured_at):
    """Filas de la captura de Zonaprop (formato del Actor) → formato del importador."""
    return [{'listing_id': r.get('id'), 'url': r.get('url'), 'captured_at': captured_at,
             'price': r.get('precio'), 'currency': r.get('moneda'), 'covered_area_m2': r.get('cubierta'),
             'total_area_m2': r.get('total'), 'rooms': r.get('ambientes'),
             'neighborhood': r.get('barrio_busqueda'), 'latitude': r.get('lat'), 'longitude': r.get('lon')}
            for r in rows]


def property_key(df):
    """Misma regla de duplicados entre fuentes que `modelo.duplicate_groups`."""
    return (df['neighborhood'].astype(str) + '|' + df['rooms'].astype(int).astype(str) + '|'
            + df['covered_area'].round().astype(int).astype(str) + '|'
            + df['price'].round(-3).astype(int).astype(str))


def exclude_seen(new, train):
    """Deja una fila por aviso (la última captura) y quita lo ya visto en el entrenamiento."""
    new = new.sort_values('captured_at').drop_duplicates('id', keep='last')
    same_id = new['id'].isin(set(train['id']))
    same_property = ~same_id & property_key(new).isin(set(property_key(train)))
    kept = new[~same_id & ~same_property].reset_index(drop=True)
    return kept, {'avisos_validos': int(len(new)), 'mismo_id': int(same_id.sum()),
                  'mismo_inmueble_probable': int(same_property.sum()), 'evaluados': int(len(kept))}


def bootstrap_gain(y, model, baseline, seed=42, draws=2000):
    """Intervalo del 95 % de la mejora de MAE (línea de base − modelo), remuestreando avisos."""
    gain = np.abs(y - baseline) - np.abs(y - model)
    rng = np.random.default_rng(seed)
    means = gain[rng.integers(0, len(gain), (draws, len(gain)))].mean(axis=1)
    return [round(float(np.percentile(means, 2.5)), 1), round(float(np.percentile(means, 97.5)), 1)]


def summarize(y, model, baseline):
    m, b = metrics(y, model), metrics(y, baseline)
    within = lambda p: round(float((np.abs(y - p) / y <= THRESHOLD).mean()) * 100, 1)
    return {'avisos': int(len(y)), 'mediana_usd_m2_publicado': round(float(np.median(y)), 0),
            'modelo': {'mae': round(m['mae'], 1), 'rmse': round(m['rmse'], 1), 'r2': round(m['r2'], 3),
                       'dentro_20_pct': within(model)},
            'linea_de_base': {'mae': round(b['mae'], 1), 'rmse': round(b['rmse'], 1), 'r2': round(b['r2'], 3),
                              'dentro_20_pct': within(baseline)},
            'mejora_mae_pct': round(100 * (1 - m['mae'] / b['mae']), 1),
            'mejora_mae_ic95_usd_m2': bootstrap_gain(y, model, baseline),
            # Negativo = el modelo da una referencia más baja que el precio publicado.
            'sesgo_mediano_modelo_usd_m2': round(float(np.median(model - y)), 0),
            'pct_avisos_subestimados': round(float((model < y).mean()) * 100, 1)}


def evaluate(new, train, bundle):
    """Predicciones del modelo guardado y de la línea de base, con el resumen por segmento."""
    new = new[new['currency'].eq('USD')].reset_index(drop=True)
    pred = predict(bundle, new)
    baseline, levels = comparables(train, new)
    table = new[['id', 'segmento', 'neighborhood', 'rooms', 'covered_area', 'price', 'precio_m2']].copy()
    table['prediccion_usd_m2'] = pred['referencia_publicacion_usd_m2'].to_numpy()
    table['baseline_usd_m2'] = baseline
    table['variables_numericas_faltantes'] = pred['variables_numericas_faltantes'].to_numpy()
    report = {'todos': summarize(table['precio_m2'].to_numpy(), table['prediccion_usd_m2'].to_numpy(), baseline),
              'niveles_linea_de_base': levels, 'segmentos': {}}
    for name, part in table.groupby('segmento'):
        report['segmentos'][name] = {
            'descripcion': SEGMENTS.get(name, name),
            'mediana_variables_faltantes': float(part['variables_numericas_faltantes'].median()),
            **summarize(part['precio_m2'].to_numpy(), part['prediccion_usd_m2'].to_numpy(),
                        part['baseline_usd_m2'].to_numpy())}
    return table, report


def in_time_segment(train, errors_path):
    """Error del mismo segmento angosto en la prueba original (modelo ajustado sin esos avisos)."""
    errors = pd.read_csv(errors_path).merge(train[['id', 'rooms', 'price']].drop_duplicates('id'), on='id')
    part = errors[errors['neighborhood'].isin(['Caballito', 'Almagro']) & errors['rooms'].eq(2)
                  & errors['price'].le(165_000)]
    if part.empty:
        return None
    y = part['precio_m2'].to_numpy()
    segment = train['neighborhood'].isin(['Caballito', 'Almagro']) & train['rooms'].eq(2) & train['price'].le(165_000)
    return {'avisos': int(len(part)),
            'mae_modelo': round(float(np.mean(np.abs(y - part['prediccion_usd_m2']))), 1),
            'mae_linea_de_base': round(float(np.mean(np.abs(y - part['baseline_usd_m2']))), 1),
            'mediana_usd_m2_entrenamiento': round(float(train.loc[segment, 'precio_m2'].median()), 0),
            'avisos_entrenamiento': int(segment.sum())}


def load_new():
    """Une las capturas posteriores con el mismo pipeline de variables del entrenamiento."""
    log = json.loads((ZONAPROP / 'registro.json').read_text(encoding='utf-8'))
    rows = json.loads((ZONAPROP / 'avisos.json').read_text(encoding='utf-8'))
    with tempfile.TemporaryDirectory() as tmp:
        converted = Path(tmp) / 'zonaprop.json'
        converted.write_text(json.dumps(zonaprop_rows(rows, log['captura'])), encoding='utf-8')
        zonaprop, z_summary = load_listings([converted], CATALOG, approximate_pins=True)
    agencies, a_summary = load_listings([p / 'avisos.json' for p in AGENCIES], CATALOG, approximate_pins=True)
    zonaprop['segmento'], agencies['segmento'] = 'zonaprop_20261120', 'inmobiliarias_13a17'
    data = pd.concat([zonaprop, agencies], ignore_index=True)
    return amenities(data, load_osm(*OSM)), {'zonaprop': z_summary, 'inmobiliarias': a_summary}


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--modelo', type=Path, default=DEFAULT_OUT)
    parser.add_argument('--reporte', type=Path, default=ROOT / 'reports/validacion_temporal.json')
    parser.add_argument('--salida', type=Path, default=ROOT / 'data/processed/validacion-temporal')
    args = parser.parse_args()
    bundle = load(args.modelo)
    train = load_dataset(DEFAULT_DATASET)
    new, loaded = load_new()
    report = {'modelo_version': bundle.get('version'), 'entrenado_utc': bundle['report']['fecha_utc'],
              'capturas_entrenamiento': [str(train['captured_at'].min())[:10], str(train['captured_at'].max())[:10]],
              'capturas_evaluadas': [str(new['captured_at'].min())[:10], str(new['captured_at'].max())[:10]],
              'exclusiones': {}}
    kept = []
    for name, part in new.groupby('segmento'):
        part, counts = exclude_seen(part, train)
        report['exclusiones'][name] = counts
        kept.append(part)
    table, result = evaluate(pd.concat(kept, ignore_index=True), train, bundle)
    report.update(result)
    report['prueba_original'] = {
        'modelo_mae': round(bundle['report']['modelo_prueba']['mae'], 1),
        'linea_de_base_mae': round(bundle['report']['baseline_prueba']['mae'], 1),
        'solo_campos_importador_mae': round(bundle['report']['prueba_solo_campos_importador']['mae'], 1),
        'mismo_segmento_zonaprop': in_time_segment(train, args.modelo / 'errores_prueba.csv')}
    report['nota'] = ('Avisos publicados después del entrenamiento, sin reentrenar. Precios de publicación, no de '
                      'cierre. La captura de Zonaprop es un segmento angosto y no trae rasgos de edificio ni de '
                      'descripción; por eso cada segmento se informa por separado.')
    args.salida.mkdir(parents=True, exist_ok=True)
    table.to_csv(args.salida / 'predicciones.csv', index=False)
    args.reporte.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
