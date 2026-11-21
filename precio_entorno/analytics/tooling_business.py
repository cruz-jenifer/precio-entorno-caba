"""Herramientas de negocio: qué hacer con las referencias y cómo llevarlas a Google Sheets.

**Decisión que apoya.** Quien busca o asesora revisa muchos avisos de un barrio. Comparar el USD/m²
publicado con la referencia del modelo ordena la revisión: primero los avisos claramente por debajo
de lo que se publica para inmuebles parecidos. La métrica de negocio del proyecto (minutos ahorrados
por revisión) se mide con el protocolo de `docs/validacion-inmobiliaria.md`; este módulo da la lista
priorizada y su resumen, no los minutos.

Solo se marca una diferencia cuando supera el umbral (20 %), del orden del error relativo del modelo:
el 70 % de los avisos de prueba quedó dentro de ±20 %. Es una referencia de publicación, no una
tasación, un precio de cierre ni una oportunidad garantizada.
"""

import numpy as np
import pandas as pd

# Pestañas de la planilla del dashboard, sin tildes (Make y Looker las leen mejor así).
SHEETS = ('resumen', 'barrios', 'ambientes', 'fuentes', 'distribucion', 'correlaciones')
PREDICTIONS_SHEET = 'predicciones'
THRESHOLD = 0.20
BASIC_NUMERIC = ('covered_area', 'total_area_m2', 'rooms', 'latitude', 'longitude')
LABELS = ('debajo de la referencia', 'cerca de la referencia', 'encima de la referencia', 'sin lectura')
NOTE = ('Referencia de publicación de venta en USD, no tasación ni precio de cierre. '
        'Delitos registrados como contexto aparte; no entran al modelo.')


def compare_with_reference(clean, predictions, threshold=THRESHOLD):
    """Une cada referencia con su aviso y la compara con el USD/m² publicado."""
    columns = [c for c in ('ambientes', 'superficie_cubierta_m2', 'precio', 'precio_m2_usd', 'url') if c in clean]
    table = predictions.rename(columns={'neighborhood': 'barrio'}).join(
        clean.drop_duplicates('id').set_index('id')[columns], on='id')
    for c in ('precio_m2_usd', 'precio', 'url'):
        if c not in table:
            table[c] = np.nan
    table['referencia_publicacion_usd_m2'] = table['referencia_publicacion_usd_m2'].round(0)
    table['referencia_publicacion_usd'] = table['referencia_publicacion_usd'].round(-3)
    ratio = pd.to_numeric(table['precio_m2_usd'], errors='coerce') / table['referencia_publicacion_usd_m2'] - 1
    # La lectura sale del porcentaje que se muestra, para que −20,0 % nunca quede como «cerca».
    table['diferencia_pct'] = diff = (ratio * 100).round(1)
    readable = diff.notna() & ~table['barrio_no_visto'].astype(bool)
    table['lectura'] = np.select(
        [~readable, diff <= -threshold * 100, diff >= threshold * 100],
        [LABELS[3], LABELS[0], LABELS[2]], default=LABELS[1])
    order = ['id', 'barrio', 'ambientes', 'superficie_cubierta_m2', 'precio', 'precio_m2_usd',
             'referencia_publicacion_usd_m2', 'referencia_publicacion_usd', 'diferencia_pct', 'lectura',
             'barrio_no_visto', 'variables_numericas_faltantes', 'modelo_version', 'fecha_prediccion_utc', 'url']
    # Primero lo que conviene revisar: los avisos más por debajo de su referencia.
    rank = table['lectura'].map({label: i for i, label in enumerate(LABELS)})
    return (table.assign(_rank=rank).sort_values(['_rank', 'diferencia_pct'])
            .drop(columns='_rank').reindex(columns=order).reset_index(drop=True))


def to_review(table):
    """Avisos para revisar primero: los que quedan por debajo de su referencia, del más bajo al menos."""
    return table[table['lectura'] == LABELS[0]].sort_values('diferencia_pct').reset_index(drop=True)


def summary(table, bundle, skipped=0):
    """Resumen para el registro OUTPUT y el dashboard: conteos por lectura y el error que aplica."""
    report = bundle.get('report', {})
    enrichment = len([c for c in bundle['numeric'] if c not in BASIC_NUMERIC])
    basic_only = bool(enrichment) and float(table['variables_numericas_faltantes'].median()) >= enrichment
    counts = table['lectura'].value_counts()
    mae = report.get('modelo_prueba', {}).get('mae')
    basic_mae = report.get('prueba_solo_campos_importador', {}).get('mae')
    return {
        'avisos_estimados': int(len(table)),
        'fuera_por_moneda': int(skipped),
        **{label.replace(' de la referencia', '').replace(' ', '_'): int(counts.get(label, 0)) for label in LABELS},
        'pct_a_revisar_primero': round(100 * counts.get(LABELS[0], 0) / len(table), 1) if len(table) else 0.0,
        'umbral_pct': round(THRESHOLD * 100),
        'modelo_version': bundle.get('version', 'sin_version'),
        'solo_campos_basicos': basic_only,
        'mae_aplicable_usd_m2': round(basic_mae if basic_only and basic_mae else mae, 1) if mae else None,
        'mae_modelo_prueba_usd_m2': round(mae, 1) if mae else None,
        'mae_baseline_prueba_usd_m2': round(report.get('baseline_prueba', {}).get('mae', 0), 1) or None,
        'nota': NOTE,
    }


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


def values(df):
    df = df.astype(object).where(df.notna(), None)
    return [list(df.columns)] + [[cell(v) for v in row] for row in df.itertuples(index=False)]


def sheets_body(tables):
    """Cuerpo de `spreadsheets.values:batchUpdate`: una pestaña por tabla del EDA, desde A1."""
    data = [{'range': f'{name}!A1', 'majorDimension': 'ROWS', 'values': values(tables[name])} for name in SHEETS]
    return {'valueInputOption': 'RAW', 'data': data}


def predictions_body(table):
    """Cuerpo de `values:batchUpdate` para la pestaña de referencias."""
    return {'valueInputOption': 'RAW',
            'data': [{'range': f'{PREDICTIONS_SHEET}!A1', 'majorDimension': 'ROWS', 'values': values(table)}]}


def clear_body():
    return {'ranges': list(SHEETS)}
