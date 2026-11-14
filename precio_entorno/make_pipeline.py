"""Crea y corre por la API de Make el escenario del flujo Analytics.

«Precio y Entorno CABA - Pipeline Analytics» (a pedido, sin programación):

1. Google Drive › Download a file: `01_crudo/avisos_venta_crudo.json`.
2. HTTP › Apify `run-sync` del Actor `precio-entorno-analytics` con `operacion: etl`: devuelve el
   CSV limpio. El Actor baja el Mapa del Delito del portal oficial.
3. Google Drive › Upload a file: `02_limpio/dataset_limpio_AAAA-MM-DD_HHmm.csv` (un único CSV).
4. Google Drive › Download a file: ese mismo CSV, para que el EDA lea lo que quedó en Drive.
5. HTTP › Apify `run-sync` con `operacion: eda`: devuelve las tablas como cuerpo de Sheets.
6. Google Sheets › Make an API call `values:batchClear` y 7. `values:batchUpdate` sobre la
   planilla «Tablas del dashboard» (una pestaña por tabla), que lee Looker Studio.

El token de Apify va en el encabezado del módulo HTTP dentro de Make: se lee del .env al crear el
escenario y nunca se imprime ni se guarda en el repositorio.

Uso: python -m precio_entorno.make_pipeline {crear|correr|estado} --account 2
"""

import argparse
import json

from precio_entorno.apify_analytics import NAME as ACTOR_NAME
from precio_entorno.make_escenarios import TEAM, blueprint, call, last_error, module, scenarios
from precio_entorno.pipeline_analytics import clear_body
from precio_entorno.run_pilot import apify_token

SCENARIO = 'Precio y Entorno CABA - Pipeline Analytics'
# Lectura con la conexión de solo lectura; la subida (y la relectura de lo subido) con la de escritura.
CONN = {'drive': 12116977, 'drive_escritura': 12117191, 'sheets': 12194946}
APIFY_USER = {2: 'peerless_anorthite'}
DRIVE = {
    'carpeta': '1pjfJG1SbhkOUAdpCSmbQU_yGT7HSaZad',
    'crudo': '1-kaIqHPdrL_LT6Nmirt4RhHZn-P4kEtT',
    'limpio': '1fNTM1TAOUtQTuTUwxcqnueJvqnssJl6a',
    'tablas': '16cmEiOBuFcvWpE19qMhV-88YFmqS8a26',
    'avisos_crudos': '1w95uWdo5DT95p3OtlRTK9BTYTfoqljJk',
}
SPREADSHEET = '1_3s-zpZAvhCGF1nu8WlSihdXZiIwQayb6C8Qk6NWLuM'
NOW = '{{formatDate(now; "YYYY-MM-DD_HHmm"; "America/Argentina/Buenos_Aires")}}'
DOWNLOAD_FORMATS = {
    'formatDrawings': 'image/jpeg',
    'formatDocuments': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'formatSpreadsheets': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    'formatPresentations': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
}


def download(id_, file, x, conn='drive'):
    return module(id_, 'google-drive:getAFile', 4, {'file': file, 'select': 'map', **DOWNLOAD_FORMATS}, x,
                  parameters={'__IMTCONN__': CONN[conn]})


def apify(id_, url, token, body, x):
    return module(id_, 'http:MakeRequest', 4, {
        'url': url, 'method': 'post', 'headers': [{'name': 'Authorization', 'value': f'Bearer {token}'}],
        'timeout': '300', 'contentType': 'json', 'inputMethod': 'jsonString', 'jsonStringBodyContent': body,
        'shareCookies': False, 'parseResponse': False, 'allowRedirects': True, 'stopOnHttpError': True,
        'requestCompressedContent': True}, x, parameters={'tlsType': '', 'authenticationType': 'noAuth'})


def sheets_call(id_, path, body, x):
    return module(id_, 'google-sheets:makeAPICall', 2, {
        'url': f'spreadsheets/{SPREADSHEET}/{path}', 'method': 'POST',
        'headers': [{'key': 'Content-Type', 'value': 'application/json'}], 'qs': [], 'body': body}, x,
        parameters={'__IMTCONN__': CONN['sheets']})


def pipeline_blueprint(token, user):
    url = f'https://api.apify.com/v2/acts/{user}~{ACTOR_NAME}/run-sync?timeout=280'
    return blueprint(SCENARIO, [
        download(1, DRIVE['avisos_crudos'], 0),
        apify(2, url, token, '{"operacion":"etl","nombreArchivo":"{{1.name}}",'
                             '"contenidoBase64":"{{base64(toString(1.data))}}"}', 300),
        module(3, 'google-drive:uploadAFile', 4, {
            'data': '{{2.data}}', 'select': 'value', 'convert': False, 'filename': f'dataset_limpio_{NOW}.csv',
            'folderId': f"/{DRIVE['carpeta']}/{DRIVE['limpio']}", 'destination': 'drive'}, 600,
            parameters={'__IMTCONN__': CONN['drive_escritura']}),
        download(4, '{{3.id}}', 900, 'drive_escritura'),
        apify(5, url, token, '{"operacion":"eda","contenidoBase64":"{{base64(toString(4.data))}}"}', 1200),
        sheets_call(6, 'values:batchClear', json.dumps(clear_body()), 1500),
        sheets_call(7, 'values:batchUpdate', '{{toString(5.data)}}', 1800),
    ], instant=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('accion', choices=('crear', 'correr', 'estado'))
    parser.add_argument('--account', type=int, default=2, choices=sorted(APIFY_USER))
    args = parser.parse_args()
    existing = scenarios().get(SCENARIO)
    if args.accion == 'crear':
        bp = pipeline_blueprint(apify_token(args.account), APIFY_USER[args.account])
        if existing:
            call('PATCH', f"scenarios/{existing['id']}", {'confirmed': 'true'},
                 {'blueprint': json.dumps(bp, ensure_ascii=False)})
            print(f"Escenario actualizado: {existing['id']}")
        else:
            created = call('POST', 'scenarios', {'confirmed': 'true'},
                           {'blueprint': json.dumps(bp, ensure_ascii=False), 'teamId': TEAM,
                            'scheduling': json.dumps({'type': 'on-demand'})})['scenario']
            print(f"Escenario creado: {created['id']}")
    elif args.accion == 'correr':
        if not existing:
            raise SystemExit('Primero corré `crear`.')
        result = call('POST', f"scenarios/{existing['id']}/run", body={'responsive': True})
        if result.get('status') != 1:  # 1 = éxito
            raise SystemExit(f"La ejecución falló (estado {result.get('status')}): {last_error(existing['id'])}")
        print(f"Ejecución {result.get('executionId')} correcta.")
    else:
        print(existing and f"{existing['id']} {SCENARIO} {'activo' if existing['isActive'] else 'inactivo'}"
              or 'No existe.')


if __name__ == '__main__':
    main()
