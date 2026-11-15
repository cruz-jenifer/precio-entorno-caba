"""Crea por la API de Make los dos escenarios del flujo de alertas.

- «Precio y Entorno CABA - Búsquedas» (webhook): un Router separa `alta` (fila nueva en la
  pestaña «Búsquedas») y `baja` (marca `activa` = no, desde el enlace del correo).
- «Precio y Entorno CABA - Alertas con Apify» (programado): lee las búsquedas activas sin los
  mails, corre el Actor `precio-entorno-alertas`, registra la corrida en «Corridas» y, por cada
  búsqueda con avisos nuevos, busca el mail en la planilla, manda el correo y agrega una fila por
  aviso en la pestaña de alertas.

El token se lee de MAKE_API_TOKEN y nunca se imprime. La URL del webhook de búsquedas se guarda
en el .env (MAKE_BUSQUEDAS_WEBHOOK_URL), fuera de Git. Los blueprints se arman acá, así el flujo
queda documentado en el repositorio sin secretos.

Uso: python -m precio_entorno.make_escenarios {encabezados|crear|estado}
"""

import argparse
import json
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
BASE = 'https://us2.make.com/api/v2'
TEAM = 1056449
SPREADSHEET = '1CMyNpexq3e1xblk5GH7Mvs7D_Z85l1nIUZNKyH-dFtk'
# Sin tildes: Make no lee bien un nombre de pestaña con caracteres no ASCII en el rango.
SHEET_SEARCHES, SHEET_RUNS, SHEET_ALERTS = 'Busquedas', 'Corridas', 'Untitled'
CONN = {'google': 12194946, 'gmail': 12209245, 'apify': 12235451}
ACTOR = '3wcrJJOBg9qg00cHl'
OLD_SCENARIO = 6946933
HOOK_NAME = 'precio-entorno-busquedas'
NAMES = {'busquedas': 'Precio y Entorno CABA - Búsquedas', 'alertas': 'Precio y Entorno CABA - Alertas con Apify'}
EVERY_TWO_DAYS = 2 * 24 * 3600
# Encabezados de las pestañas nuevas. El orden define las columnas que mapean los escenarios.
SEARCH_COLUMNS = ('id', 'fecha_alta', 'operacion', 'barrio', 'presupuesto', 'moneda', 'superficie', 'ambientes',
                  'ambientesOMas', 'descripcion', 'email', 'activa', 'fecha_baja')
RUN_COLUMNS = ('fecha', 'estado', 'mensaje', 'corrida', 'costo_usd')
COL = {name: i for i, name in enumerate(SEARCH_COLUMNS)}
LETTER = {name: chr(ord('A') + i) for i, name in enumerate(SEARCH_COLUMNS)}
NOW = '{{formatDate(now; "YYYY-MM-DD HH:mm"; "America/Argentina/Buenos_Aires")}}'


def env_value(name):
    env = ROOT / '.env'
    for line in env.read_text(encoding='utf-8-sig').splitlines() if env.is_file() else ():
        key, sep, value = line.strip().partition('=')
        if sep and key.strip() == name:
            return value.strip().strip('"\'')
    return None


def call(method, path, params=None, body=None):
    token = env_value('MAKE_API_TOKEN')
    if not token:
        raise SystemExit('Falta MAKE_API_TOKEN en el .env.')
    url = f'{BASE}/{path}' + ('?' + urlencode(params) if params else '')
    request = Request(url, data=json.dumps(body).encode() if body is not None else None, method=method,
                      headers={'Authorization': f'Token {token}', 'Content-Type': 'application/json'})
    try:
        with urlopen(request, timeout=120) as response:
            text = response.read().decode('utf-8')
            return json.loads(text) if text else {}
    except HTTPError as error:
        raise SystemExit(f'Make respondió HTTP {error.code}: {error.read().decode("utf-8", "replace")[:600]}')


# ---------------------------------------------------------------- Piezas de los blueprints

def col(module, name):
    """Referencia a una columna de «Búsquedas» en la salida de un módulo de Sheets: {{n.`3`}}."""
    return f'{{{{{module}.`{COL[name]}`}}}}'


def module(id_, name, version, mapper, x, y=0, parameters=None, filter_=None):
    item = {'id': id_, 'module': name, 'version': version, 'parameters': parameters or {}, 'mapper': mapper,
            'metadata': {'designer': {'x': x, 'y': y}}}
    if filter_:
        item['filter'] = filter_
    return item


def condition(label, left, right, op='text:equal'):
    return {'name': label, 'conditions': [[{'a': left, 'b': right, 'o': op}]]}


def add_row(id_, sheet, values, x, y=0, headers=True, filter_=None):
    return module(id_, 'google-sheets:addRow', 2, {
        'from': 'drive', 'mode': 'select', 'spreadsheetId': f'/{SPREADSHEET}', 'sheetId': sheet,
        'includesHeaders': headers, 'useColumnHeaders': False, 'insertDataOption': 'INSERT_ROWS',
        'valueInputOption': 'RAW', 'insertUnformatted': False,
        'values': {str(i): v for i, v in enumerate(values)}}, x, y, {'__IMTCONN__': CONN['google']}, filter_)


def find_rows(id_, conditions, x, y=0, limit=200):
    """Search rows en «Búsquedas»: `conditions` es una lista de (columna, valor) unidas con Y."""
    return module(id_, 'google-sheets:filterRows', 2, {
        'from': 'drive', 'spreadsheetId': SPREADSHEET, 'sheetId': SHEET_SEARCHES, 'tableFirstRow': 'A1:CZ1',
        'includesHeaders': True, 'valueRenderOption': 'FORMATTED_VALUE',
        'dateTimeRenderOption': 'FORMATTED_STRING', 'sortOrder': 'asc', 'limit': str(limit),
        'filter': [[{'a': LETTER[c], 'b': v, 'o': 'text:equal'} for c, v in conditions]]},
        x, y, {'__IMTCONN__': CONN['google']})


def respond(id_, status, body, content_type, x, y):
    return module(id_, 'gateway:WebhookRespond', 1, {
        'status': str(status), 'body': body, 'headers': [{'key': 'Content-Type', 'value': content_type}]}, x, y)


def blueprint(name, flow, instant):
    return {'name': name, 'flow': flow, 'metadata': {
        'instant': instant, 'version': 1, 'designer': {'orphans': []},
        'scenario': {'roundtrips': 1, 'maxErrors': 3, 'autoCommit': True, 'autoCommitTriggerLast': True,
                     'sequential': False, 'confidential': False, 'dataloss': False, 'dlq': False,
                     'freshVariables': False}}}


# ---------------------------------------------------------------- Escenarios

def searches_blueprint(hook_id):
    b = 'busqueda'
    alta = [
        add_row(3, SHEET_SEARCHES, [
            f'{{{{1.{b}.id}}}}', '{{1.fecha}}', f'{{{{1.{b}.operacion}}}}', f'{{{{1.{b}.barrio}}}}',
            f'{{{{1.{b}.presupuesto}}}}', f'{{{{1.{b}.moneda}}}}', f'{{{{1.{b}.superficie}}}}',
            f'{{{{1.{b}.ambientes}}}}', f'{{{{if(1.{b}.ambientesOMas; "true"; "false")}}}}', '{{1.descripcion}}',
            '{{1.email}}', 'si', ''], 600, -150, filter_=condition('Alta', '{{1.tipo}}', 'alta')),
        respond(4, 200, '{"ok": true}', 'application/json', 900, -150),
    ]
    baja_page = ('<!doctype html><html lang="es"><meta charset="utf-8"><title>Precio y Entorno CABA</title>'
                 '<body style="font-family:sans-serif;max-width:32rem;margin:3rem auto;padding:0 1rem">'
                 '<h1>Listo</h1><p>No vas a recibir más avisos de esta búsqueda.</p></body></html>')
    baja = [
        find_rows(5, [('id', '{{1.id}}')], 600, 150, limit=1) | {
            'filter': condition('Baja', '{{1.tipo}}', 'baja')},
        module(6, 'google-sheets:updateRow', 2, {
            'from': 'drive', 'mode': 'select', 'spreadsheetId': f'/{SPREADSHEET}', 'sheetId': SHEET_SEARCHES,
            'rowNumber': '{{5.`__ROW_NUMBER__`}}', 'includesHeaders': True, 'useColumnHeaders': False,
            'valueInputOption': 'RAW', 'values': {str(COL['activa']): 'no', str(COL['fecha_baja']): NOW}},
            900, 150, {'__IMTCONN__': CONN['google']}),
        respond(7, 200, baja_page, 'text/html; charset=utf-8', 1200, 150),
    ]
    flow = [
        module(1, 'gateway:CustomWebHook', 1, {}, 0, parameters={'hook': hook_id, 'maxResults': 1}),
        {'id': 2, 'module': 'builtin:BasicRouter', 'version': 1, 'mapper': None,
         'metadata': {'designer': {'x': 300, 'y': 0}}, 'routes': [{'flow': alta}, {'flow': baja}]},
    ]
    return blueprint(NAMES['busquedas'], flow, instant=True)


def criteria_json(m):
    """Un objeto JSON por búsqueda, solo con criterios. El mail no sale de la planilla."""
    return ('{"id":"' + col(m, 'id') + '","operacion":"' + col(m, 'operacion') + '","barrio":"' + col(m, 'barrio')
            + '","presupuesto":' + col(m, 'presupuesto') + ',"moneda":"' + col(m, 'moneda')
            + '","superficie":' + col(m, 'superficie') + ',"ambientes":' + col(m, 'ambientes')
            + ',"ambientesOMas":' + col(m, 'ambientesOMas') + '}')


# Al menos una búsqueda con id: sin búsquedas activas, el agregador arma un objeto con celdas vacías
# ({"id":"","presupuesto":,...}), que no es JSON válido.
HAS_SEARCHES = {'name': 'Hay búsquedas activas',
                'conditions': [[{'a': '{{2.text}}', 'b': '"id":"[^"]+"', 'o': 'text:pattern'}]]}


def alerts_blueprint(unsubscribe_url, team_email, max_listings=100):
    actor_input = ('{"busquedas":[{{2.text}}],"autorizacionConfirmada":true,'
                   f'"maxAvisosPorSitio":{max_listings},"alertarPrimeraCorrida":false}}')
    unsubscribe = f'{unsubscribe_url}?tipo=baja&id={{{{5.busqueda}}}}'
    email_body = ('{{5.html}}<p style="color:#666;font-size:12px">Precio y Entorno CABA. '
                  f'<a href="{unsubscribe}">No quiero recibir más avisos de esta búsqueda</a>.</p>')
    run_log = [
        add_row(4, SHEET_RUNS, [NOW, '{{3.status}}', '{{3.statusMessage}}', '{{3.id}}', '{{3.usageTotalUsd}}'],
                1200, -150),
        module(9, 'google-email:sendAnEmail', 4, {
            'to': [team_email], 'subject': 'Precio y Entorno CABA: la corrida de alertas terminó en {{3.status}}',
            'content': '<p>Corrida {{3.id}}: {{3.status}}.</p><p>{{3.statusMessage}}</p>', 'bodyType': 'rawHtml'},
            1500, -150, {'__IMTCONN__': CONN['gmail']},
            condition('Falló', '{{3.status}}', 'SUCCEEDED', 'text:notequal')),
    ]
    emails = [
        module(5, 'apify:fetchDatasetItems', 1, {'type': 'clean', 'format': 'json', 'limit': '200',
                                                 'datasetId': '{{3.defaultDatasetId}}'},
               1200, 150, {'__IMTCONN__': CONN['apify']},
               condition('Terminó bien', '{{3.status}}', 'SUCCEEDED')),
        find_rows(6, [('id', '{{5.busqueda}}'), ('activa', 'si')], 1500, 150, limit=1),
        module(7, 'google-email:sendAnEmail', 4, {
            'to': [col(6, 'email')], 'subject': '{{5.asunto}}', 'content': email_body, 'bodyType': 'rawHtml'},
            1800, 150, {'__IMTCONN__': CONN['gmail']}),
        module(8, 'builtin:BasicFeeder', 1, {'array': '{{5.alertas}}'}, 2100, 150),
        add_row(10, SHEET_ALERTS, [NOW, '{{8.operacion}}', '{{8.busqueda}}', '{{8.aviso}}', '{{8.barrio}}',
                                   '{{8.precio}}', '{{8.moneda}}', '{{8.expensas_ars}}', '{{8.superficie_m2}}',
                                   '{{8.ambientes}}', '{{8.url}}'], 2400, 150),
    ]
    flow = [
        find_rows(1, [('activa', 'si')], 0),
        module(2, 'util:TextAggregator', 1, {'value': criteria_json(1)}, 300,
               parameters={'feeder': 1, 'rowSeparator': 'other', 'otherRowSeparator': ','}),
        # Sin búsquedas activas el agregador sale vacío y el input no es JSON válido: no se corre nada.
        module(3, 'apify:runActorNew', 1, {'actorId': ACTOR, 'runSync': True, 'actor_search_type': 'user',
                                           f'inputBody{ACTOR}': actor_input},
               600, parameters={'__IMTCONN__': CONN['apify']}, filter_=HAS_SEARCHES),
        {'id': 11, 'module': 'builtin:BasicRouter', 'version': 1, 'mapper': None,
         'metadata': {'designer': {'x': 900, 'y': 0}}, 'routes': [{'flow': run_log}, {'flow': emails}]},
    ]
    return blueprint(NAMES['alertas'], flow, instant=False)


def headers_blueprint():
    return blueprint('Precio y Entorno CABA - Encabezados (un solo uso)', [
        add_row(1, SHEET_SEARCHES, list(SEARCH_COLUMNS), 0, headers=False),
        add_row(2, SHEET_RUNS, list(RUN_COLUMNS), 300, headers=False),
    ], instant=False)


# ---------------------------------------------------------------- Operaciones

def create_scenario(bp, scheduling):
    data = call('POST', 'scenarios', {'confirmed': 'true'},
                {'blueprint': json.dumps(bp, ensure_ascii=False), 'teamId': TEAM, 'scheduling': json.dumps(scheduling)})
    return data['scenario']


def scenarios():
    return {s['name']: s for s in call('GET', 'scenarios', {'teamId': TEAM, 'pg[limit]': 100})['scenarios']}


def hook():
    for item in call('GET', 'hooks', {'teamId': TEAM})['hooks']:
        if item['name'] == HOOK_NAME:
            return item
    return call('POST', 'hooks', body={'name': HOOK_NAME, 'teamId': TEAM, 'typeName': 'gateway-webhook',
                                       'method': False, 'headers': False, 'stringify': False})['hook']


def last_error(scenario_id):
    """Mensaje de error de la última ejecución, para diagnosticar sin abrir Make."""
    logs = call('GET', f'scenarios/{scenario_id}/logs', {'pg[limit]': 10}).get('scenarioLogs', [])
    for log in logs:
        if log.get('eventType') == 'EXECUTION_END' and log.get('error'):
            error = log['error']
            return f"{error.get('causeModule', {}).get('appName')}:{error.get('causeModule', {}).get('name')} · " \
                   f"{error.get('message')}"
    return 'sin detalle'


def save_env(name, value):
    env = ROOT / '.env'
    lines = env.read_text(encoding='utf-8-sig').splitlines() if env.is_file() else []
    lines = [l for l in lines if l.strip().partition('=')[0].strip() != name] + [f'{name}={value}']
    env.write_text('\n'.join(lines) + '\n', encoding='utf-8')


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('accion', choices=('encabezados', 'crear', 'estado'))
    args = parser.parse_args()
    if args.accion == 'encabezados':
        bp = headers_blueprint()
        leftover = scenarios().get(bp['name'])
        if leftover:  # Quedó de un intento fallido: se recrea con el blueprint actual.
            call('DELETE', f"scenarios/{leftover['id']}", {'confirmed': 'true'})
        scenario = create_scenario(bp, {'type': 'on-demand'})
        call('POST', f"scenarios/{scenario['id']}/start")
        try:
            result = call('POST', f"scenarios/{scenario['id']}/run", body={'responsive': True})
        finally:
            call('POST', f"scenarios/{scenario['id']}/stop")
        if result.get('status') != 1:  # 1 = éxito; se deja el escenario para revisar el error.
            raise SystemExit(f"La ejecución falló (estado {result.get('status')}): {last_error(scenario['id'])}")
        call('DELETE', f"scenarios/{scenario['id']}", {'confirmed': 'true'})
        print('Encabezados escritos en «Búsquedas» y «Corridas»; el escenario de un solo uso se borró.')
    elif args.accion == 'crear':
        team_email = env_value('MAKE_EQUIPO_EMAIL')
        if not team_email:
            raise SystemExit('Falta MAKE_EQUIPO_EMAIL en el .env: el mail del equipo para avisos de fallo.')
        existing = scenarios()
        target = hook()
        save_env('MAKE_BUSQUEDAS_WEBHOOK_URL', target['url'])
        if NAMES['busquedas'] not in existing:
            existing[NAMES['busquedas']] = create_scenario(searches_blueprint(target['id']), {'type': 'immediately'})
        if NAMES['alertas'] not in existing:
            existing[NAMES['alertas']] = create_scenario(
                alerts_blueprint(target['url'], team_email), {'type': 'indefinitely', 'interval': EVERY_TWO_DAYS})
        for key in ('busquedas', 'alertas'):
            print(existing[NAMES[key]]['id'], NAMES[key])
        print('MAKE_BUSQUEDAS_WEBHOOK_URL quedó en el .env.')
    else:
        for name, s in scenarios().items():
            print(s['id'], name, 'activo' if s['isActive'] else 'inactivo')


if __name__ == '__main__':
    main()
