"""Inferencia: carga el modelo ya entrenado y estima la referencia de publicación de cada aviso.

No entrena, no reajusta y no itera por lotes: recibe el CSV limpio entero y lo pasa una vez por el
pipeline guardado (codificador + HistGradientBoostingRegressor). El artefacto se genera fuera del
Actor con `python -m precio_entorno.inferencia entrenar` y se sube al almacén con nombre
`precio-entorno-modelo` con `python -m precio_entorno.apify_analytics subir-modelo`. Como el Actor
corre con permisos limitados, ese almacén le llega en la entrada `almacenModelo` (solo lectura).

Antes de cargarlo se controla que su SHA-256 coincida con el de `evaluacion.json` y que la versión
de scikit-learn sea la del entrenamiento. Solo se cargan artefactos propios, nunca uno subido por
quien usa el Actor.
"""

import hashlib
import io
import json
from datetime import datetime, timezone

import joblib
import pandas as pd
import sklearn

from precio_entorno.analytics.preprocessing import inputs, model_frame, validate

MODEL_STORE = 'precio-entorno-modelo'
MODEL_KEY = 'modelo.joblib'
REPORT_KEY = 'evaluacion'


def load_bytes(model_bytes, report):
    """Artefacto en bytes + su evaluación → modelo listo para predecir."""
    if hashlib.sha256(model_bytes).hexdigest() != report.get('artefacto_sha256'):
        raise ValueError('La huella del modelo no coincide con la evaluación.')
    if report.get('sklearn') != sklearn.__version__:
        raise ValueError(f"El modelo se entrenó con scikit-learn {report.get('sklearn')} y este entorno tiene "
                         f'{sklearn.__version__}: regenerá el modelo o fijá la versión.')
    return joblib.load(io.BytesIO(model_bytes))


def load(folder):
    """Carga el modelo desde una carpeta local con `modelo.joblib` y `evaluacion.json`."""
    report = json.loads((folder / 'evaluacion.json').read_text(encoding='utf-8'))
    return load_bytes((folder / 'modelo.joblib').read_bytes(), report)


def predict(bundle, df):
    """Avisos con nombres del modelo → referencia de publicación en USD/m² y en USD."""
    validate(df)
    x = inputs(df, bundle['numeric'], bundle['categorical'])
    pred = bundle['model'].predict(x)
    out = df[['id', 'neighborhood']].copy()
    out['referencia_publicacion_usd_m2'] = pred
    out['referencia_publicacion_usd'] = pred * pd.to_numeric(df['covered_area'])
    out['barrio_no_visto'] = ~df['neighborhood'].isin(bundle['barrios'])
    out['variables_numericas_faltantes'] = x[bundle['numeric']].isna().sum(axis=1)
    out['modelo_version'] = bundle.get('version', 'sin_version')
    out['fecha_prediccion_utc'] = datetime.now(timezone.utc).isoformat()
    return out


def predict_clean(clean, bundle):
    """CSV limpio del ETL → (predicciones de los avisos en USD, cantidad que quedó afuera por moneda)."""
    frame, skipped = model_frame(clean)
    return predict(bundle, frame), skipped
