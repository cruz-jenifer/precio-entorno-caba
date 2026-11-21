"""Entrenamiento agrupado y persistencia del modelo de precios publicados de venta en USD.

Este script entrena y guarda el artefacto; nunca entra en el Actor de Apify. La carga y la
predicción viven en `precio_entorno/analytics/inference.py`, que es lo único que usa el Actor.
"""

import argparse
import hashlib
import json
import time
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import sklearn
from sklearn.base import clone
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.model_selection import GridSearchCV, GroupKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OrdinalEncoder

from precio_entorno.analytics.inference import load, predict
from precio_entorno.analytics.preprocessing import inputs, validate
from precio_entorno.comparar_modelos import DEFAULT_DATASET, feature_sets, load_dataset, metrics
from precio_entorno.modelo import comparables, group_split

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / 'data/processed/inferencia'


def train(df, seed=42, folds=5):
    """Selecciona en CV de entrenamiento; evalúa una vez y reajusta para operación."""
    validate(df, target=True)
    numeric, categorical = feature_sets(df, control_agency=True)
    x = inputs(df, numeric, categorical)
    a, b = group_split(df, seed)
    dev, test = df.iloc[a], df.iloc[b]
    n = min(folds, dev['grupo'].nunique())
    if n < 2:
        raise ValueError('Se requieren al menos dos grupos de entrenamiento.')
    prep = ColumnTransformer([
        ('num', 'passthrough', numeric),
        ('cat', OrdinalEncoder(handle_unknown='use_encoded_value', unknown_value=np.nan), categorical),
    ])
    pipe = Pipeline([('prep', prep), ('modelo', HistGradientBoostingRegressor(
        loss='absolute_error', learning_rate=0.05, max_iter=300, min_samples_leaf=10,
        early_stopping=False, random_state=seed,
        categorical_features=[False] * len(numeric) + [True] * len(categorical)))])
    # Búsqueda acotada: complejidad y regularización; no consulta la prueba.
    grid = [dict(modelo__max_leaf_nodes=[leaves], modelo__min_samples_leaf=[leaf],
                 modelo__l2_regularization=[l2]) for leaves, leaf, l2 in
            [(31, 10, 0.0), (15, 20, 1.0), (31, 30, 5.0)]]
    splits = list(GroupKFold(n).split(dev, groups=dev['grupo']))
    start = time.perf_counter()
    search = GridSearchCV(pipe, grid, scoring='neg_mean_absolute_error', cv=splits,
                          n_jobs=1, error_score='raise').fit(x.iloc[a], dev['precio_m2'])
    pred = search.predict(x.iloc[b])
    baseline, _ = comparables(dev, test)
    base_cv = [metrics(dev.iloc[j]['precio_m2'].to_numpy(), comparables(dev.iloc[i], dev.iloc[j])[0])['mae']
               for i, j in splits]
    evaluated = metrics(test['precio_m2'].to_numpy(), pred)
    ref = metrics(test['precio_m2'].to_numpy(), baseline)
    basic_fields = ['id', 'neighborhood', 'agency', 'covered_area', 'total_area_m2', 'rooms', 'latitude', 'longitude']
    basic_prediction = search.predict(inputs(test.reindex(columns=basic_fields), numeric, categorical))
    errors = test[['id', 'grupo', 'neighborhood', 'precio_m2']].copy()
    errors['prediccion_usd_m2'] = pred
    errors['baseline_usd_m2'] = baseline
    errors['error_absoluto_usd_m2'] = np.abs(test['precio_m2'].to_numpy() - pred)
    errors['error_relativo'] = errors['error_absoluto_usd_m2'] / errors['precio_m2']
    report = {
        'fecha_utc': datetime.now(timezone.utc).isoformat(), 'sklearn': sklearn.__version__,
        'semilla': seed, 'entrenamiento': len(dev), 'prueba': len(test), 'pliegues': n,
        'grupos_compartidos': len(set(dev['grupo']) & set(test['grupo'])),
        'parametros': search.best_params_, 'variables_numericas': numeric, 'variables_categoricas': categorical,
        'modelo_prueba': evaluated, 'baseline_prueba': ref,
        'prueba_solo_campos_importador': metrics(test['precio_m2'].to_numpy(), basic_prediction),
        'configuracion_fija': {'loss': 'absolute_error', 'learning_rate': 0.05, 'max_iter': 300,
                              'early_stopping': False, 'random_state': seed},
        'mae_entrenamiento': metrics(dev['precio_m2'].to_numpy(), search.predict(x.iloc[a]))['mae'],
        'mae_cv': -float(search.best_score_), 'baseline_mae_cv': float(np.mean(base_cv)),
        'candidatos': [{'parametros': p, 'mae_cv': -float(m), 'desvio_cv': float(s)}
                       for p, m, s in zip(search.cv_results_['params'], search.cv_results_['mean_test_score'],
                                           search.cv_results_['std_test_score'])],
        'mejora_mae_prueba_pct': 100 * (1 - evaluated['mae'] / ref['mae']),
        'dentro_20_pct_prueba': float((errors['error_relativo'] <= .20).mean()),
        'baseline_dentro_20_pct_prueba': float((np.abs(test['precio_m2'].to_numpy() - baseline)
                                                    / test['precio_m2'].to_numpy() <= .20).mean()),
        'errores_por_barrio': errors.groupby('neighborhood')['error_absoluto_usd_m2'].agg(['size', 'mean']).reset_index().to_dict('records'),
        'nota': 'Prueba histórica ya explorada; no mide generalización temporal. Requiere captura futura independiente.',
    }
    # La evaluación es del modelo ajustado con dev; el artefacto operativo usa todos los datos.
    deployed = clone(search.best_estimator_).fit(x, df['precio_m2'])
    report['segundos_entrenamiento_total'] = time.perf_counter() - start
    bundle = {'model': deployed, 'numeric': numeric, 'categorical': categorical,
              'barrios': sorted(df['neighborhood'].unique()), 'report': report}
    return bundle, report, errors


def save(bundle, report, errors, out):
    out.mkdir(parents=True, exist_ok=True)
    version = hashlib.sha256(json.dumps(report, sort_keys=True).encode()).hexdigest()[:16]
    bundle['version'] = report['version'] = version
    joblib.dump(bundle, out / 'modelo.joblib')
    report['artefacto_sha256'] = hashlib.sha256((out / 'modelo.joblib').read_bytes()).hexdigest()
    (out / 'evaluacion.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    errors.to_csv(out / 'errores_prueba.csv', index=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operacion', choices=['entrenar', 'predecir'])
    parser.add_argument('--dataset', type=Path, default=DEFAULT_DATASET)
    parser.add_argument('--edificio', nargs='*', type=Path, default=[])
    parser.add_argument('--salida', type=Path, default=DEFAULT_OUT)
    parser.add_argument('--modelo', type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    try:
        df = load_dataset(args.dataset, args.edificio)
        if args.operacion == 'entrenar':
            bundle, report, errors = train(df)
            report['fuentes'] = [{'archivo': str(p.resolve().relative_to(ROOT)) if p.resolve().is_relative_to(ROOT) else p.name,
                                 'sha256': hashlib.sha256(p.read_bytes()).hexdigest()}
                                for p in [args.dataset] + args.edificio]
            report['capturas'] = sorted(df['captured_at'].dropna().astype(str).unique()) if 'captured_at' in df else []
            save(bundle, report, errors, args.salida)
            print(json.dumps(report['modelo_prueba'], indent=2))
        else:
            bundle = load(args.modelo)
        args.salida.mkdir(parents=True, exist_ok=True)
        predict(bundle, df).to_csv(args.salida / 'predicciones.csv', index=False)
    except (OSError, ValueError, KeyError) as error:
        parser.exit(1, f'Error: {error}\n')


if __name__ == '__main__':
    main()
