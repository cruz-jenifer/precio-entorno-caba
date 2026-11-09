"""Actualización periódica: captura avisos nuevos, los importa y registra las alertas.

Pensado para correr cada dos o tres días desde el Programador de tareas. Cada corrida:
1. lee los IDs que ya están en la base real;
2. captura los avisos más recientes de cada inmobiliaria autorizada (en Migliorisi
   solo pide el detalle de los avisos que no conoce);
3. importa el lote en la base real, que genera una alerta por cada ID nuevo que
   coincide con una búsqueda guardada;
4. si hay alertas nuevas y MAKE_WEBHOOK_URL está configurada, las envía a Make;
5. agrega una línea a data/local/actualizaciones.jsonl con el resultado.
"""

import argparse
import json
from datetime import datetime
from pathlib import Path

from precio_entorno import make_webhook
from precio_entorno.importing import import_listings
from precio_entorno.inmobiliarias import CATALOGS, DEFAULT_SITES, SITES, PoliteClient, run_capture
from precio_entorno.store import Store

ROOT = Path(__file__).resolve().parents[1]
BASES = {'venta': ROOT / 'data/local/real.sqlite3', 'alquiler': ROOT / 'data/local/real-alquiler.sqlite3'}


def update(store, out, sites, max_listings, client=None, history=None, echo=print, webhook=None, post=None,
           operation='venta'):
    known = {item['id'] for item in store.listings()}
    alerts_before = {(a['search_id'], a['id']) for a in store.alerts()}
    _, log = run_capture(sites, max_listings, out, client=client, known=frozenset(known), echo=echo,
                         operation=operation)
    report = import_listings(store, (out / 'avisos.json').read_bytes(), 'avisos.json', CATALOGS[operation], operation)
    new_alerts = [a for a in store.alerts() if (a['search_id'], a['id']) not in alerts_before]
    entry = {
        'fecha': log['captura'], 'operacion': operation,
        'carpeta': str(out.relative_to(ROOT)) if out.is_relative_to(ROOT) else str(out),
        'sitios': {s: v['estado'] for s, v in log['sitios'].items()},
        'leidos': report.read, 'nuevos': report.added, 'repetidos': report.duplicates,
        'descartados': report.discarded, 'alertas_nuevas': report.alerts,
        # `precio_usd` se conserva por compatibilidad con el escenario de Make; la moneda real va en `moneda`.
        'alertas': [{'operacion': operation, 'busqueda': a['search_id'], 'aviso': a['id'], 'barrio': a['neighborhood'],
                     'precio': a['price'], 'moneda': a['currency'], 'precio_usd': a['price'],
                     'expensas_ars': a.get('expenses'), 'superficie_m2': a['covered_area'], 'ambientes': a['rooms'],
                     'url': a['url']} for a in new_alerts],
    }
    if webhook and entry['alertas']:
        kwargs = {'post': post} if post else {}
        entry['make'] = make_webhook.send(webhook, make_webhook.payload(entry, CATALOGS[operation]), **kwargs)
        echo(f"Make: {'enviado' if entry['make']['enviado'] else 'error ' + str(entry['make'].get('error'))}")
    if history is not None:
        history.parent.mkdir(parents=True, exist_ok=True)
        with history.open('a', encoding='utf-8') as stream:
            stream.write(json.dumps(entry, ensure_ascii=False) + '\n')
    return entry


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--max-avisos', type=int, default=200, help='Avisos más recientes por inmobiliaria')
    parser.add_argument('--operacion', choices=sorted(BASES), default='venta')
    parser.add_argument('--base', type=Path, help='Por defecto, la base real de la operación')
    parser.add_argument('--sitios', nargs='+', choices=sorted(SITES), default=list(DEFAULT_SITES))
    parser.add_argument('--autorizacion-confirmada', action='store_true')
    parser.add_argument('--probar-make', action='store_true',
                        help='Envía una alerta ficticia al webhook de Make, sin capturar ni importar')
    args = parser.parse_args()
    try:
        webhook = make_webhook.webhook_url()
    except ValueError as error:
        parser.exit(1, f'Error: {error}\n')
    if args.probar_make:
        if not webhook:
            parser.exit(1, 'Error: falta MAKE_WEBHOOK_URL en el entorno o en .env.\n')
        rent = args.operacion == 'alquiler'
        test = {'fecha': datetime.now().isoformat(timespec='seconds'), 'alertas': [{
            'operacion': args.operacion, 'busqueda': 0, 'aviso': 'prueba:ficticio', 'barrio': 'Caballito',
            'precio': 750000 if rent else 100000, 'moneda': 'ARS' if rent else 'USD',
            'precio_usd': 750000 if rent else 100000, 'expensas_ars': 90000 if rent else None,
            'superficie_m2': 45, 'ambientes': 2, 'url': 'https://example.invalid/aviso-ficticio'}]}
        result = make_webhook.send(webhook, make_webhook.payload(test, 'prueba-ficticia'))
        print(json.dumps(result, ensure_ascii=False))
        return
    if not args.autorizacion_confirmada:
        parser.exit(1, 'Error: falta --autorizacion-confirmada.\n')
    base = args.base or BASES[args.operacion]
    if not base.exists():
        parser.exit(1, f'Error: no existe la base {base}. Importá primero un catálogo en Datos reales.\n')
    suffix = '' if args.operacion == 'venta' else f'-{args.operacion}'
    out = ROOT / f"data/raw/inmobiliarias{suffix}-{datetime.now():%Y%m%d-%H%M}"
    entry = update(Store(base), out, args.sitios, args.max_avisos, client=PoliteClient(),
                   history=base.parent / 'actualizaciones.jsonl', echo=lambda line: print(line, flush=True),
                   webhook=webhook, operation=args.operacion)
    print(json.dumps(entry, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
