"""Sube, construye y prueba el Actor «precio-entorno-analytics» por la API de Apify, sin el CLI.

    python -m precio_entorno.apify_analytics subir --account 2
    python -m precio_entorno.apify_analytics probar --account 2
    python -m precio_entorno.apify_analytics gasto

`subir` crea el Actor (privado) si no existe, reemplaza su código por los archivos de
`actores/analytics/.actor/`, el paquete `precio_entorno/analytics/` y los módulos compartidos que
usa, y lo construye. No sube nada de entrenamiento. En la carpeta del Actor van además, ya hechos:

- `modelo/`: el modelo entrenado (`data/processed/inferencia/modelo.joblib`) y su `evaluacion.json`,
  con la huella verificada. El binario no va a Git.
- `referencias/delitos_barrio.json`: el resumen por barrio de `data/raw/delitos_2025.csv`, con el
  SHA-256 del archivo oficial verificado.

Así el Actor no descarga nada ni carga el modelo desde un almacén. `probar` corre ETL,
EDA e inferencia con `run-sync`, igual que Make, y guarda las salidas en
`data/processed/pipeline-apify/`. Antes de cada operación paga se controla que la cuenta quede
debajo del tope de USD 5. El token nunca se imprime.
"""

import argparse
import base64
import hashlib
import json
import time
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from precio_entorno.run_pilot import apify_token

ROOT = Path(__file__).resolve().parents[1]
NAME = 'precio-entorno-analytics'
VERSION = '0.1'
ACTOR_DIR = ROOT / 'actores/analytics/.actor'
# Módulos compartidos que usa el Actor, además de todo `precio_entorno/analytics/`.
SHARED_MODULES = ['__init__.py', 'importing.py', 'descripcion.py', 'eda_delitos.py']
MODEL_DIR = ROOT / 'data/processed/inferencia'
CRIMES = ROOT / 'data/raw/delitos_2025.csv'
ACCOUNT_CAP_USD = 5.0
MARGIN_USD = 0.05  # Lo que puede costar una construcción o una prueba de ETL, EDA e inferencia.
RAW = ROOT / 'data/raw/venta-consolidada-20261108/avisos.json'


class Apify:
    def __init__(self, token):
        self.token = token

    def call(self, method, path, params=None, body=None, raw=None, content_type='application/json', timeout=60):
        url = f'https://api.apify.com/v2/{path}' + ('?' + urlencode(params) if params else '')
        data = raw if raw is not None else (json.dumps(body).encode() if body is not None else None)
        request = Request(url, data=data, method=method,
                          headers={'Authorization': f'Bearer {self.token}', 'Content-Type': content_type})
        try:
            with urlopen(request, timeout=timeout) as response:
                payload = response.read()
                return payload, response.headers.get('Content-Type', '')
        except HTTPError as error:
            detail = error.read().decode('utf-8', 'replace')[:500]
            raise SystemExit(f'Apify respondió HTTP {error.code} en {path.split("?")[0]}: {detail}') from None

    def json(self, method, path, **kw):
        return json.loads(self.call(method, path, **kw)[0])['data']

    def usage_usd(self):
        data = self.json('GET', 'users/me/usage/monthly')
        return float(data.get('totalUsageCreditsUsdAfterVolumeDiscount') or 0), data['usageCycle']


def source_files():
    """Código del Actor: su carpeta `.actor/`, el paquete de Analytics y los módulos compartidos."""
    files = [{'name': f'.actor/{p.name}', 'format': 'TEXT', 'content': p.read_text(encoding='utf-8')}
             for p in sorted(ACTOR_DIR.iterdir()) if p.is_file()]
    modules = [ROOT / 'precio_entorno' / m for m in SHARED_MODULES]
    modules += sorted((ROOT / 'precio_entorno/analytics').glob('*.py'))
    files += [{'name': p.relative_to(ROOT).as_posix(), 'format': 'TEXT', 'content': p.read_text(encoding='utf-8')}
              for p in modules]
    return files


def artifact_files(model_dir=MODEL_DIR, crimes=CRIMES):
    """Lo que el Actor necesita ya hecho en su carpeta: el modelo entrenado y el resumen de delitos."""
    from precio_entorno.analytics import ETL, inference

    model = (model_dir / inference.MODEL_FILE).read_bytes()
    report_text = (model_dir / inference.REPORT_FILE).read_text(encoding='utf-8')
    if hashlib.sha256(model).hexdigest() != json.loads(report_text).get('artefacto_sha256'):
        raise SystemExit('La huella de modelo.joblib no coincide con evaluacion.json: no se sube nada.')
    summary = ETL.crimes_summary(crimes)
    if summary['calidad']['sha256'] != ETL.CRIMES_SHA256:
        raise SystemExit(f'{crimes} no es el archivo oficial esperado (SHA-256 distinto): no se sube nada.')
    return [
        {'name': f'modelo/{inference.MODEL_FILE}', 'format': 'BASE64', 'content': base64.b64encode(model).decode()},
        {'name': f'modelo/{inference.REPORT_FILE}', 'format': 'TEXT', 'content': report_text},
        {'name': ETL.PACKAGED_CRIMES.relative_to(ROOT).as_posix(), 'format': 'TEXT',
         'content': json.dumps(summary, ensure_ascii=False, indent=1)},
    ]


def check_budget(api):
    used, cycle = api.usage_usd()
    print(f'Gasto de la cuenta en el ciclo {cycle["startAt"][:10]} a {cycle["endAt"][:10]}: USD {used:.3f}')
    if used + MARGIN_USD > ACCOUNT_CAP_USD:
        raise SystemExit(f'La cuenta quedaría cerca del tope de USD {ACCOUNT_CAP_USD}: no se corre nada.')
    return used


def find_actor(api):
    for actor in api.json('GET', 'acts', params={'my': 'true', 'limit': 100})['items']:
        if actor['name'] == NAME:
            return actor
    return None


def upload(api):
    check_budget(api)
    version = {'versionNumber': VERSION, 'sourceType': 'SOURCE_FILES', 'buildTag': 'latest',
               'sourceFiles': source_files() + artifact_files()}
    actor = find_actor(api)
    if actor is None:
        actor = api.json('POST', 'acts', body={
            'name': NAME, 'title': 'Lüga · Analytics (ETL, EDA e inferencia)', 'isPublic': False, 'versions': [version],
            'defaultRunOptions': {'build': 'latest', 'timeoutSecs': 300, 'memoryMbytes': 1024}})
        print(f'Actor creado: {actor["id"]}')
    else:
        api.json('PUT', f'acts/{actor["id"]}/versions/{VERSION}', body=version)
        print(f'Código actualizado: {actor["id"]}')
    build = api.json('POST', f'acts/{actor["id"]}/builds', params={'version': VERSION, 'waitForFinish': 60})
    while build['status'] in ('READY', 'RUNNING'):
        time.sleep(5)
        build = api.json('GET', f'actor-builds/{build["id"]}', params={'waitForFinish': 30})
    print(f'Construcción {build["id"]}: {build["status"]}')
    if build['status'] != 'SUCCEEDED':
        log = api.call('GET', f'logs/{build["id"]}')[0].decode('utf-8', 'replace')
        raise SystemExit(log[-3000:])
    user = api.json('GET', 'users/me')['username']
    print(f'Para Make: https://api.apify.com/v2/acts/{user}~{NAME}/run-sync')
    return actor


def run_sync(api, actor_id, actor_input):
    payload, content_type = api.call('POST', f'acts/{actor_id}/run-sync', params={'timeout': 280},
                                     body=actor_input, timeout=300)
    return payload, content_type


def probe(api, out):
    check_budget(api)
    actor = find_actor(api)
    if actor is None:
        raise SystemExit('El Actor no existe: corré primero `subir`.')
    out.mkdir(parents=True, exist_ok=True)
    raw = RAW.read_bytes()
    start = time.monotonic()
    csv_bytes, kind = run_sync(api, actor['id'], {'operacion': 'etl', 'nombreArchivo': RAW.name,
                                                  'contenidoBase64': base64.b64encode(raw).decode()})
    (out / 'dataset_limpio.csv').write_bytes(csv_bytes)
    print(f'ETL: {len(csv_bytes):,} bytes ({kind}) en {time.monotonic() - start:.0f} s')
    start = time.monotonic()
    body, kind = run_sync(api, actor['id'], {'operacion': 'eda',
                                             'contenidoBase64': base64.b64encode(csv_bytes).decode()})
    (out / 'sheets_body.json').write_bytes(body)
    tabs = [d['range'] for d in json.loads(body)['data']]
    print(f'EDA: {len(body):,} bytes ({kind}) en {time.monotonic() - start:.0f} s · pestañas {tabs}')
    start = time.monotonic()
    body, kind = run_sync(api, actor['id'], {'operacion': 'inferencia',
                                             'contenidoBase64': base64.b64encode(csv_bytes).decode()})
    (out / 'sheets_predicciones_body.json').write_bytes(body)
    rows = len(json.loads(body)['data'][0]['values']) - 1
    print(f'Inferencia: {rows} referencias ({kind}) en {time.monotonic() - start:.0f} s')
    for run in api.json('GET', f'acts/{actor["id"]}/runs', params={'desc': 'true', 'limit': 3})['items']:
        detail = api.json('GET', f'actor-runs/{run["id"]}')
        print(f'Corrida {run["id"]}: {detail["status"]} · USD {detail.get("usageTotalUsd") or 0:.4f}')


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('accion', choices=('subir', 'probar', 'gasto'))
    parser.add_argument('--account', type=int, required=True, help='Cuenta de Apify según el orden del .env')
    parser.add_argument('--salida', type=Path, default=ROOT / 'data/processed/pipeline-apify')
    args = parser.parse_args()
    api = Apify(apify_token(args.account))
    if args.accion == 'subir':
        upload(api)
    elif args.accion == 'probar':
        probe(api, args.salida)
    else:
        check_budget(api)


if __name__ == '__main__':
    main()
