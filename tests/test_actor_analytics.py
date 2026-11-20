"""Actor de Analytics: inferencia sin entrenamiento, lectura de negocio y archivos que entran al Actor.

Todos los avisos son ficticios.
"""

import ast
import hashlib
import io
import json
import re
import unittest
from pathlib import Path

import joblib
import pandas as pd

from precio_entorno import apify_analytics
from precio_entorno.analytics import inference, tooling_business

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / 'precio_entorno'
TRAINING = {'inferencia', 'modelo', 'comparar_modelos', 'auditoria_estadistica', 'benchmark_inmobiliario'}


def imports(path):
    """Módulos de `precio_entorno` que importa un archivo."""
    found = set()
    for node in ast.walk(ast.parse(path.read_text(encoding='utf-8'))):
        if isinstance(node, ast.ImportFrom) and node.module:
            # `from precio_entorno.analytics import EDA` importa el submódulo analytics.EDA.
            names = [node.module] + [f'{node.module}.{a.name}' for a in node.names]
        elif isinstance(node, ast.Import):
            names = [a.name for a in node.names]
        else:
            names = []
        found |= {n.split('.', 1)[1] for n in names if n.startswith('precio_entorno.')}
    return {m for m in found if (PACKAGE / (m.replace('.', '/') + '.py')).exists()
            or (PACKAGE / m.replace('.', '/')).is_dir()}


def closure(module):
    """Módulos de `precio_entorno` que necesita un módulo, incluido él mismo."""
    seen, pending = set(), [module]
    while pending:
        name = pending.pop()
        if name in seen:
            continue
        seen.add(name)
        path = PACKAGE / (name.replace('.', '/') + '.py')
        if not path.exists():
            path = PACKAGE / name.replace('.', '/') / '__init__.py'
        if path.exists():
            pending += imports(path)
    return seen


def copied(dockerfile):
    """Rutas de `precio_entorno` que copia un Dockerfile."""
    text = dockerfile.read_text(encoding='utf-8').replace('\\\n', ' ')
    paths = set()
    for line in text.splitlines():
        if line.startswith('COPY '):
            paths |= {p for p in line.split()[1:-1] if p.startswith('precio_entorno')}
    return paths


def as_files(modules):
    files = set()
    for m in modules:
        path = m.replace('.', '/')
        files.add(f'precio_entorno/{path}/__init__.py' if (PACKAGE / path).is_dir() else f'precio_entorno/{path}.py')
    return files


class FakeModel:
    def predict(self, x):
        return x['covered_area'].to_numpy() * 0 + 2000.0


def bundle(numeric=('covered_area', 'rooms', 'dist_parque_m')):
    return {'model': FakeModel(), 'numeric': list(numeric), 'categorical': ['neighborhood'],
            'barrios': ['Caballito', 'Almagro'], 'version': 'ficticio',
            'report': {'modelo_prueba': {'mae': 400.0}, 'baseline_prueba': {'mae': 600.0},
                       'prueba_solo_campos_importador': {'mae': 580.0}}}


def clean():
    return pd.DataFrame([
        {'id': 'a:1', 'barrio': 'Caballito', 'ambientes': 2, 'superficie_cubierta_m2': 50, 'precio': 75000,
         'moneda': 'USD', 'precio_m2_usd': 1500.0, 'url': 'https://example.invalid/1'},   # 25 % debajo.
        {'id': 'a:2', 'barrio': 'Caballito', 'ambientes': 2, 'superficie_cubierta_m2': 50, 'precio': 105000,
         'moneda': 'USD', 'precio_m2_usd': 2100.0, 'url': 'https://example.invalid/2'},   # 5 % encima: cerca.
        {'id': 'a:3', 'barrio': 'Almagro', 'ambientes': 3, 'superficie_cubierta_m2': 40, 'precio': 100000,
         'moneda': 'USD', 'precio_m2_usd': 2500.0, 'url': 'https://example.invalid/3'},   # 25 % encima.
        {'id': 'a:4', 'barrio': 'Palermo', 'ambientes': 1, 'superficie_cubierta_m2': 30, 'precio': 60000,
         'moneda': 'USD', 'precio_m2_usd': 2000.0, 'url': 'https://example.invalid/4'},   # Barrio no visto.
        {'id': 'a:5', 'barrio': 'Almagro', 'ambientes': 2, 'superficie_cubierta_m2': 45, 'precio': 90000000,
         'moneda': 'ARS', 'precio_m2_usd': None, 'url': 'https://example.invalid/5'},     # Fuera: moneda.
    ])


class InferenceAndBusinessTests(unittest.TestCase):
    def test_reads_each_listing_against_its_reference(self):
        data = clean()
        predictions, skipped = inference.predict_clean(data, bundle())
        self.assertEqual(skipped, 1)
        ordered = tooling_business.compare_with_reference(data, predictions)
        self.assertEqual(ordered['lectura'].tolist(), ['debajo de la referencia', 'cerca de la referencia',
                                                       'encima de la referencia', 'sin lectura'])
        table = ordered.set_index('id')
        self.assertEqual(table.at['a:1', 'lectura'], 'debajo de la referencia')
        self.assertEqual(table.at['a:1', 'diferencia_pct'], -25.0)
        self.assertEqual(table.at['a:2', 'lectura'], 'cerca de la referencia')
        self.assertEqual(table.at['a:3', 'lectura'], 'encima de la referencia')
        self.assertEqual(table.at['a:4', 'lectura'], 'sin lectura')
        self.assertEqual(table.at['a:1', 'referencia_publicacion_usd'], 100000)
        self.assertNotIn('a:5', table.index)

    def test_summary_counts_and_uses_basic_error_without_enrichment(self):
        data = clean()
        predictions, skipped = inference.predict_clean(data, bundle())
        table = tooling_business.compare_with_reference(data, predictions)
        summary = tooling_business.summary(table, bundle(), skipped)
        self.assertEqual((summary['debajo'], summary['cerca'], summary['encima'], summary['sin_lectura']),
                         (1, 1, 1, 1))
        self.assertEqual(summary['fuera_por_moneda'], 1)
        self.assertEqual(summary['pct_a_revisar_primero'], 25.0)
        self.assertTrue(summary['solo_campos_basicos'])          # dist_parque_m no vino en el CSV.
        self.assertEqual(summary['mae_aplicable_usd_m2'], 580.0)
        enriched = tooling_business.summary(table.assign(variables_numericas_faltantes=0), bundle(), skipped)
        self.assertFalse(enriched['solo_campos_basicos'])
        self.assertEqual(enriched['mae_aplicable_usd_m2'], 400.0)

    def test_predictions_body_is_plain_json(self):
        data = clean()
        table = tooling_business.compare_with_reference(data, inference.predict_clean(data, bundle())[0])
        body = tooling_business.predictions_body(table)
        self.assertEqual(body['data'][0]['range'], 'predicciones!A1')
        self.assertEqual(len(body['data'][0]['values']), 5)
        self.assertNotIn('NaN', json.dumps(body))

    def test_model_does_not_see_dashboard_imputations(self):
        from precio_entorno.analytics.preprocessing import model_frame
        data = clean().assign(latitud=-34.61, longitud=-58.43, superficie_total_m2=60.0,
                              ubicacion_origen=['publicada', 'mediana_barrio', 'publicada', 'mediana_comuna', 'publicada'],
                              superficie_total_imputada=['False', 'True', 'False', 'False', 'True'])
        frame, _ = model_frame(data)
        rows = frame.set_index('id')
        self.assertEqual(rows.at['a:1', 'latitude'], -34.61)
        self.assertTrue(pd.isna(rows.at['a:2', 'latitude']) and pd.isna(rows.at['a:2', 'longitude']))
        self.assertTrue(pd.isna(rows.at['a:4', 'latitude']))
        self.assertTrue(pd.isna(rows.at['a:2', 'total_area_m2']))
        self.assertEqual(rows.at['a:3', 'total_area_m2'], 60.0)

    def test_rejects_batch_without_usd_listings(self):
        with self.assertRaisesRegex(ValueError, 'USD'):
            inference.predict_clean(clean().assign(moneda='ARS'), bundle())

    def test_load_bytes_checks_fingerprint_and_sklearn_version(self):
        import sklearn
        buffer = io.BytesIO()
        joblib.dump({'numeric': [], 'version': 'x'}, buffer)
        data = buffer.getvalue()
        report = {'artefacto_sha256': hashlib.sha256(data).hexdigest(), 'sklearn': sklearn.__version__}
        self.assertEqual(inference.load_bytes(data, report)['version'], 'x')
        with self.assertRaisesRegex(ValueError, 'huella'):
            inference.load_bytes(data + b'alterado', report)
        with self.assertRaisesRegex(ValueError, 'scikit-learn'):
            inference.load_bytes(data, {**report, 'sklearn': '0.0'})


class ActorPackagingTests(unittest.TestCase):
    def test_analytics_actor_never_needs_training_code(self):
        needed = closure('analytics.main')
        self.assertFalse(needed & TRAINING, needed & TRAINING)
        for path in (PACKAGE / 'analytics').glob('*.py'):
            text = path.read_text(encoding='utf-8')
            with self.subTest(path=path.name):
                self.assertFalse(re.search(r'GridSearchCV|GroupKFold|\.fit\(|partial_fit|batch_size|DataLoader', text))

    def test_main_only_does_actor_input_and_output(self):
        main = PACKAGE / 'analytics/main.py'
        self.assertEqual(imports(main), {'analytics', 'analytics.EDA', 'analytics.ETL', 'analytics.inference',
                                         'analytics.preprocessing', 'analytics.tooling_business'})
        tree = ast.parse(main.read_text(encoding='utf-8'))
        third_party = {a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names}
        third_party |= {n.module for n in ast.walk(tree) if isinstance(n, ast.ImportFrom) and n.module}
        self.assertFalse({'pandas', 'numpy', 'sklearn', 'joblib'} & third_party)

    def test_uploaded_files_and_dockerfile_match_what_the_actor_imports(self):
        needed = as_files(closure('analytics.main')) | {'precio_entorno/__init__.py', 'precio_entorno/analytics/__init__.py'}
        uploaded = {f['name'] for f in apify_analytics.source_files() if f['name'].startswith('precio_entorno/')}
        self.assertEqual(uploaded, needed)
        docker = copied(ROOT / 'actores/analytics/.actor/Dockerfile')
        expanded = {p for p in needed if not p.startswith('precio_entorno/analytics/')} | {'precio_entorno/analytics'}
        self.assertEqual(docker, expanded)

    def test_alerts_dockerfile_copies_its_modules_and_no_training(self):
        needed = as_files(closure('actor_main')) | {'precio_entorno/__init__.py'}
        docker = copied(ROOT / '.actor/Dockerfile')
        self.assertEqual(docker, needed)
        self.assertFalse(docker & as_files(TRAINING))


if __name__ == '__main__':
    unittest.main()
