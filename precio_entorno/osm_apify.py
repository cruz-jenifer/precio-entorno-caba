"""Puntos de interés de OpenStreetMap para CABA con Apify.

OpenStreetMap publica sus datos bajo licencia ODbL: se pueden usar citando
"© OpenStreetMap contributors". El actor consulta la API Overpass. Cada corrida usa
una sola cuenta de Apify, tiene un tope de puntos (maxItems) y un tope de gasto
(maxTotalChargeUsd), y se registra con su costo informado.
"""

import argparse
import json
import re
from datetime import datetime
from pathlib import Path

from precio_entorno.apify_client import ApifyClient
from precio_entorno.run_pilot import apify_token

ROOT = Path(__file__).resolve().parents[1]
ACTOR = 'automation-lab/openstreetmap-poi-extractor'
ACTOR_PATH = 'acts/' + ACTOR.replace('/', '~')
BBOX = '-34.705,-58.531,-34.527,-58.335'  # Sur, oeste, norte, este: rectángulo de CABA.
START_USD, POI_USD = 0.005, 0.0008       # Tarifa FREE verificada antes de correr.
ACCOUNT_BUDGET_USD = 5.0
TRANSIT_QUERY = (
    '[out:json][timeout:180];('
    f'node["station"="subway"]({BBOX});'
    f'node["railway"="station"]({BBOX});'
    f'nwr["public_transport"="station"]["network"~"Metrob"]({BBOX});'
    ');out center;'
)
# (cuenta, nombre, categoría del actor, tope de puntos)
PLAN = [
    (1, 'transporte', 'custom', 500), (1, 'parques', 'parks', 1000), (1, 'hospitales', 'hospitals', 500),
    (2, 'escuelas', 'schools', 2000), (2, 'supermercados', 'supermarkets', 1500), (2, 'farmacias', 'pharmacies', 1000),
    (3, 'restaurantes', 'restaurants', 5500),
    (4, 'cafes', 'cafes', 3500), (4, 'bares', 'bars', 2000),
]
KEEP = ('osmId', 'osmType', 'id', 'type', 'name', 'category', 'subcategory', 'latitude', 'longitude',
        'lat', 'lon', 'amenity', 'shop', 'leisure', 'railway', 'station', 'public_transport', 'network')


def cap_usd(max_items):
    return round(START_USD + max_items * POI_USD + 0.01, 3)


def check_plan(plan):
    by_account = {}
    for account, _, _, items in plan:
        by_account[account] = by_account.get(account, 0) + cap_usd(items)
    over = {a: round(v, 2) for a, v in by_account.items() if v > ACCOUNT_BUDGET_USD}
    if over:
        raise ValueError(f'El plan supera USD {ACCOUNT_BUDGET_USD} en las cuentas {over}.')
    return by_account


def check_pricing(client):
    """Confirma que la tarifa vigente no supera la usada para fijar los topes."""
    actor = client.request(ACTOR_PATH)['data']
    price = (actor.get('pricingInfos') or [{}])[-1]
    events = (price.get('pricingPerEvent') or {}).get('actorChargeEvents') or {}

    def free(name):
        event = events.get(name) or {}
        return event.get('eventPriceUsd', (event.get('eventTieredPricingUsd') or {}).get('FREE', {}).get('tieredEventPriceUsd'))
    start, poi = free('start'), free('poi-extracted')
    if price.get('pricingModel') != 'PAY_PER_EVENT' or price.get('isPPEPlatformUsagePaidByUser') \
            or start is None or poi is None or start > START_USD or poi > POI_USD:
        raise RuntimeError(f'La tarifa del actor cambió (inicio {start}, punto {poi}). Revisá los topes.')


def payload(category, max_items):
    body = {'boundingBox': BBOX, 'category': category, 'maxItems': max_items, 'includeAllTags': True}
    if category == 'custom':
        body['customQuery'] = TRANSIT_QUERY
    return body


def slim(row):
    """Conserva identificación, tipo y coordenadas; descarta teléfonos, sitios web y correos."""
    out = {k: row[k] for k in KEEP if k in row}
    extras = row.get('extras') or row.get('tags') or {}
    for k in ('amenity', 'shop', 'leisure', 'railway', 'station', 'public_transport', 'network'):
        if k in extras and k not in out:
            out[k] = extras[k]
    return out


def run_one(client, name, category, max_items, out, log, account, wait_s=900):
    cap = cap_usd(max_items)
    record = {'cuenta': account, 'nombre': name, 'categoria': category, 'max_items': max_items,
              'tope_usd': cap, 'estado': 'INICIO_SOLICITADO'}
    log.append(record)
    write(out / 'corridas.json', log)
    run = client.request(f'{ACTOR_PATH}/runs', params={'maxTotalChargeUsd': cap, 'timeout': wait_s},
                         payload=payload(category, max_items))['data']
    record.update(run_id=run['id'], estado=run['status'])
    write(out / 'corridas.json', log)
    final = client.wait(run['id'], max_seconds=wait_s + 60)
    record.update(estado=final['status'], dataset_id=final.get('defaultDatasetId'),
                  costo_informado_usd=final.get('usageTotalUsd'))
    write(out / 'corridas.json', log)
    dataset = final.get('defaultDatasetId')
    if final['status'] != 'SUCCEEDED' or not isinstance(dataset, str) or not re.fullmatch(r'[A-Za-z0-9]+', dataset):
        raise RuntimeError(f'Corrida {name}: {final["status"]}. Revisá Apify Console.')
    rows = client.request(f'datasets/{dataset}/items', params={'clean': 'true', 'limit': max_items})
    if not isinstance(rows, list):
        raise RuntimeError('El dataset tiene un formato inesperado.')
    points = [slim(r) for r in rows if isinstance(r, dict)]
    write(out / f'{name}.json', points)
    record['puntos'] = len(points)
    write(out / 'corridas.json', log)
    cost = final.get('usageTotalUsd')
    if type(cost) not in (int, float) or cost > cap + 0.01:
        raise RuntimeError(f'Corrida {name}: el costo informado ({cost}) falta o supera el tope.')
    return points


def write(path, value):
    tmp = path.with_suffix('.tmp')
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    tmp.replace(path)


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--piloto', action='store_true', help='Una corrida de 50 parques con la cuenta 1')
    parser.add_argument('--solo', nargs='*', help='Nombres del plan a correr (por defecto, todos)')
    parser.add_argument('--salida', type=Path)
    parser.add_argument('--ejecutar', action='store_true', help='Sin esta opción solo muestra el plan')
    args = parser.parse_args()
    plan = [(1, 'piloto-parques', 'parks', 50)] if args.piloto else \
        [p for p in PLAN if not args.solo or p[1] in args.solo]
    try:
        budget = check_plan(plan)
        print(json.dumps({'actor': ACTOR, 'bbox': BBOX, 'corridas': [
            {'cuenta': a, 'nombre': n, 'categoria': c, 'max_items': m, 'tope_usd': cap_usd(m)} for a, n, c, m in plan],
            'tope_por_cuenta_usd': {str(k): round(v, 2) for k, v in budget.items()}}, ensure_ascii=False, indent=2))
        if not args.ejecutar:
            return
        out = args.salida or ROOT / f"data/raw/osm-{datetime.now():%Y%m%d-%H%M}"
        out.mkdir(parents=True, exist_ok=False)
        log, clients = [], {}
        for account, name, category, max_items in plan:
            if account not in clients:
                clients[account] = ApifyClient(apify_token(account))
                check_pricing(clients[account])
            try:
                points = run_one(clients[account], name, category, max_items, out, log, account)
                print(f'{name}: {len(points)} puntos · cuenta {account}', flush=True)
            except RuntimeError as error:
                print(f'{name}: {error}', flush=True)
        spent = sum(r.get('costo_informado_usd') or 0 for r in log)
        print(f'Costo informado total: USD {spent:.3f} · Carpeta: {out}')
    except (ValueError, RuntimeError, OSError) as error:
        parser.exit(1, f'Error: {error}\n')


if __name__ == '__main__':
    main()
