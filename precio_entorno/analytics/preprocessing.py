"""Preprocesamiento: lectura y escritura del CSV limpio y su paso a las variables del modelo.

El modelo guardado ya trae su propio codificador de categorías, aprendido en el entrenamiento: acá
no se ajusta nada, solo se renombran columnas, se filtra lo que el modelo admite (venta en USD) y se
convierten los tipos. Así los códigos de barrio no dependen del lote que llega a inferencia.
"""

import io

import numpy as np
import pandas as pd

# Columnas del CSV limpio del ETL → nombres de las variables del modelo.
CLEAN_TO_MODEL = {
    'barrio': 'neighborhood', 'ambientes': 'rooms', 'moneda': 'currency',
    'superficie_cubierta_m2': 'covered_area', 'superficie_total_m2': 'total_area_m2',
    'latitud': 'latitude', 'longitud': 'longitude', 'fuente': 'agency',
}
REQUIRED = ['id', 'neighborhood', 'covered_area', 'rooms']


def read_clean(content):
    """CSV limpio (bytes o texto) → DataFrame."""
    return pd.read_csv(io.BytesIO(content) if isinstance(content, bytes) else io.StringIO(content))


def to_csv(df):
    return df.to_csv(index=False, lineterminator='\n')


def validate(df, target=False):
    """Contrato de entrada del modelo. Con `target`, también exige el objetivo y el grupo de partición."""
    required = REQUIRED + (['grupo', 'precio_m2'] if target else [])
    missing = set(required) - set(df)
    if missing or df.empty:
        raise ValueError(f'Entrada vacía o faltan columnas: {sorted(missing)}')
    if df[['id', 'neighborhood']].isna().any().any():
        raise ValueError('ID y barrio son obligatorios.')
    for c in ['covered_area', 'rooms'] + (['precio_m2'] if target else []):
        x = pd.to_numeric(df[c], errors='coerce')
        if not (np.isfinite(x) & (x > 0)).all():
            raise ValueError(f'{c} debe ser numérico, finito y positivo.')
    if target and df['grupo'].isna().any():
        raise ValueError('Todos los avisos deben tener grupo.')
    if 'currency' in df and not df['currency'].eq('USD').all():
        raise ValueError('El modelo admite únicamente venta en USD.')
    if 'operation' in df and not df['operation'].eq('venta').all():
        raise ValueError('El modelo admite únicamente venta.')


def inputs(df, numeric, categorical):
    """Matriz de variables en el orden del modelo. Las opcionales ausentes quedan en NaN."""
    out = df.reindex(columns=numeric + categorical).copy()
    for c in numeric:
        out[c] = pd.to_numeric(out[c], errors='coerce')
        if np.isinf(out[c]).any():
            raise ValueError(f'{c} contiene infinitos.')
    for c in categorical:
        out[c] = out[c].fillna('sin_dato').astype(str)
    return out


def model_frame(clean):
    """CSV limpio → (avisos en USD con nombres del modelo, cantidad que quedó afuera por moneda).

    Acepta también un CSV que ya traiga los nombres del modelo y variables de entorno
    (distancias, conteos, rasgos): las que estén presentes se usan tal cual.
    """
    frame = clean.rename(columns=CLEAN_TO_MODEL)
    # El ETL imputa para el dashboard (centro del barrio, superficie total = cubierta). El modelo se
    # entrenó con esos campos faltantes y los trata de forma nativa: se le devuelven como faltantes.
    if 'ubicacion_origen' in frame:
        imputed_pin = frame['ubicacion_origen'].ne('publicada')
        frame[['latitude', 'longitude']] = frame[['latitude', 'longitude']].mask(imputed_pin, np.nan)
    if 'superficie_total_imputada' in frame:
        imputed_area = frame['superficie_total_imputada'].astype(str).str.lower().eq('true')
        frame['total_area_m2'] = frame['total_area_m2'].mask(imputed_area, np.nan)
    if 'currency' in frame:
        usd = frame['currency'].eq('USD')
        skipped, frame = int((~usd).sum()), frame[usd]
    else:
        skipped = 0
    if frame.empty:
        raise ValueError('No hay avisos de venta en USD para estimar.')
    return frame.reset_index(drop=True), skipped
