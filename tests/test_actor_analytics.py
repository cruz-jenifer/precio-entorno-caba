"""Actor de Analytics: inferencia sin entrenamiento, lectura de negocio y archivos que entran al Actor.

Todos los avisos son ficticios.
"""

import ast
import base64
import hashlib
import io
import json
import re
import tempfile
import unittest
from pathlib import Path
from unittest import mock

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
        self.assertEqual(tooling_business.to_review(ordered)['id'].tolist(), ['a:1'])

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
        # R4: main.py solo arma el Actor con el SDK e importa la lógica.
        main = PACKAGE / 'analytics/main.py'
        self.assertEqual(imports(main), {'analytics', 'analytics.EDA', 'analytics.ETL', 'analytics.inference',
                                         'analytics.preprocessing', 'analytics.tooling_business'})
        tree = ast.parse(main.read_text(encoding='utf-8'))
        modules = {a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names}
        modules |= {n.module for n in ast.walk(tree) if isinstance(n, ast.ImportFrom) and n.module}
        self.assertEqual(modules - {'precio_entorno.analytics'}, {'asyncio', 'apify'})
        functions = [n.name for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
        self.assertEqual(functions, ['main'])
        sdk = {n.func.attr for n in ast.walk(tree) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
               and isinstance(n.func.value, ast.Name) and n.func.value.id == 'Actor'}
        self.assertEqual(sdk, {'get_input', 'open_key_value_store', 'set_value', 'push_data', 'set_status_message'})

    def test_actor_reads_data_only_through_the_sdk(self):
        # R1: ningún módulo del Actor baja datos de afuera; el archivo llega solo en la entrada.
        for path in [ROOT / f for f in as_files(closure('analytics.main'))]:
            text = path.read_text(encoding='utf-8')
            with self.subTest(path=path.name):
                self.assertFalse(re.search(r'urllib\.request|urlopen|import requests|httpx|aiohttp|https?://cdn', text))
        schema = json.loads((ROOT / 'actores/analytics/.actor/input_schema.json').read_text(encoding='utf-8'))
        self.assertEqual(set(schema['properties']), {'operacion', 'contenidoBase64', 'nombreArchivo'})

    def test_input_is_decoded_from_base64_only(self):
        from precio_entorno.analytics.preprocessing import read_input
        data = b'id,barrio\n1,Caballito\n'
        encoded = base64.b64encode(data).decode()
        self.assertEqual(read_input({'operacion': 'eda', 'contenidoBase64': encoded}), ('eda', data, 'avisos.json'))
        wrapped = encoded[:8] + '\n' + encoded[8:]
        self.assertEqual(read_input({'operacion': 'eda', 'contenidoBase64': wrapped})[1], data)
        with self.assertRaisesRegex(ValueError, 'contenidoBase64'):
            read_input({'operacion': 'eda', 'contenidoUrl': 'https://example.invalid/a.csv'})
        with self.assertRaisesRegex(ValueError, 'base64'):
            read_input({'operacion': 'eda', 'contenidoBase64': 'no es base64!'})
        with self.assertRaisesRegex(ValueError, 'operacion'):
            read_input({'operacion': 'entrenar', 'contenidoBase64': encoded})

    def test_model_is_read_from_the_actor_folder_not_from_a_store(self):
        # R3: el modelo ya existe en la carpeta del Actor; no se crea ni se baja de un almacén.
        main = (PACKAGE / 'analytics/main.py').read_text(encoding='utf-8')
        self.assertIn('inference.load()', main)
        self.assertNotIn('almacenModelo', main)
        self.assertEqual(inference.ACTOR_MODEL_DIR, ROOT / 'modelo')
        docker = (ROOT / 'actores/analytics/.actor/Dockerfile').read_text(encoding='utf-8')
        self.assertIn('COPY modelo ./modelo', docker)
        self.assertIn('COPY referencias ./referencias', docker)
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(FileNotFoundError, 'apify_analytics subir'):
                inference.load(Path(tmp))

    def test_artifacts_travel_inside_the_actor_with_checked_fingerprints(self):
        import sklearn
        from precio_entorno.analytics import ETL
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            buffer = io.BytesIO()
            joblib.dump({'numeric': [], 'version': 'x'}, buffer)
            (folder / 'modelo.joblib').write_bytes(buffer.getvalue())
            report = {'artefacto_sha256': hashlib.sha256(buffer.getvalue()).hexdigest(), 'sklearn': sklearn.__version__}
            (folder / 'evaluacion.json').write_text(json.dumps(report), encoding='utf-8')
            summary = {'barrios': [], 'calidad': {'sha256': ETL.CRIMES_SHA256, 'periodo': ['a', 'b']}}
            with mock.patch.object(ETL, 'crimes_summary', return_value=summary):
                files = {f['name']: f for f in apify_analytics.artifact_files(folder, folder / 'delitos.csv')}
            self.assertEqual(set(files), {'modelo/modelo.joblib', 'modelo/evaluacion.json',
                                          'referencias/delitos_barrio.json'})
            self.assertEqual(files['modelo/modelo.joblib']['format'], 'BASE64')
            # Lo que viaja se carga igual que en el Actor.
            out = folder / 'actor/modelo'
            out.mkdir(parents=True)
            (out / 'modelo.joblib').write_bytes(base64.b64decode(files['modelo/modelo.joblib']['content']))
            (out / 'evaluacion.json').write_text(files['modelo/evaluacion.json']['content'], encoding='utf-8')
            self.assertEqual(inference.load(out)['version'], 'x')
            with mock.patch.object(ETL, 'crimes_summary', return_value={**summary, 'calidad': {'sha256': 'otro'}}):
                with self.assertRaisesRegex(SystemExit, 'SHA-256'):
                    apify_analytics.artifact_files(folder, folder / 'delitos.csv')
            (folder / 'modelo.joblib').write_bytes(buffer.getvalue() + b'alterado')
            with self.assertRaisesRegex(SystemExit, 'huella'):
                apify_analytics.artifact_files(folder, folder / 'delitos.csv')

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
