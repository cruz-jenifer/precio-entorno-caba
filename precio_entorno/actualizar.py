"""Actualización periódica: captura avisos nuevos, los importa y registra las alertas.

Pensado para correr cada dos o tres días desde el Programador de tareas. Cada corrida:
1. lee los IDs que ya están en la base real;
2. captura los avisos más recientes de cada inmobiliaria autorizada (en Migliorisi
   solo pide el detalle de los avisos que no conoce);
3. importa el lote en la base real, que genera una alerta por cada ID nuevo que
   coincide con una búsqueda guardada y guarda los cambios de precio de los conocidos;
   en los sitios que se recorrieron de punta a punta (--barrido-completo lo asegura),
   marca como no vistos o dados de baja los avisos que faltaron (docs/etl.md, sección 4 bis);
4. si MAKE_WEBHOOK_URL está configurada, envía a Make el resumen de la corrida, haya
   alertas o no, con las alertas agrupadas por búsqueda; si la corrida falla, envía el error;
5. agrega una línea a data/local/actualizaciones.jsonl con el resultado.

Termina con código 1 si la corrida falló, para que el Programador de tareas lo muestre.
"""

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from precio_entorno import make_webhook
from precio_entorno.importing import import_listings
from precio_entorno.inmobiliarias import CATALOGS, DEFAULT_SITES, SITES, PoliteClient, run_capture
from precio_entorno.store import Store

ROOT = Path(__file__).resolve().parents[1]
BASES = {'venta': ROOT / 'data/local/real.sqlite3', 'alquiler': ROOT / 'data/local/real-alquiler.sqlite3'}
# Tope de un barrido completo por inmobiliaria: alto para recorrer todo el sitio, pero finito.
BARRIDO_MAX = 20_000


def _capture_and_import(store, out, sites, max_listings, client, echo, operation):
    # Los dados de baja también cuentan como conocidos: si reaparecen, el barrido los reactiva.
    known = {item['id'] for item in store.listings(include_inactive=True)}
    alerts_before = {(a['search_id'], a['id']) for a in store.alerts()}
    _, log = run_capture(sites, max_listings, out, client=client, known=frozenset(known), echo=echo,
                         operation=operation)
    report = import_listings(store, (out / 'avisos.json').read_bytes(), 'avisos.json', CATALOGS[operation], operation)
    vigencia = apply_sweeps(store, out / 'vistos.json', log['captura'], echo)
    new_alerts = [a for a in store.alerts() if (a['search_id'], a['id']) not in alerts_before]
    sites_status = {s: v['estado'] for s, v in log['sitios'].items()}
    return {
        'fecha': log['captura'],
        # Un sitio detenido o con error no frena la corrida, pero la marca como parcial.
        'estado': 'ok' if all(v == 'completo' for v in sites_status.values()) else 'parcial',
        'sitios': sites_status,
        'leidos': report.read, 'nuevos': report.added, 'repetidos': report.duplicates,
        'descartados': report.discarded, 'alertas_nuevas': report.alerts,
        'cambios_de_precio': report.price_changes, 'reactivados': report.reactivated,
        'no_vistos': sum(v['no_vistos'] for v in vigencia.values()),
        'bajas': sum(v['bajas'] for v in vigencia.values()), 'vigencia': vigencia,
        # `precio_usd` se conserva por compatibilidad con el escenario de Make; la moneda real va en `moneda`.
        'alertas': [{'operacion': operation, 'busqueda': a['search_id'], 'aviso': a['id'], 'barrio': a['neighborhood'],
                     'precio': a['price'], 'moneda': a['currency'], 'precio_usd': a['price'],
                     'expensas_ars': a.get('expenses'), 'superficie_m2': a['covered_area'], 'ambientes': a['rooms'],
                     'url': a['url']} for a in new_alerts],
    }


def apply_sweeps(store, seen_path, captured_at, echo=print):
    """Aplica a la base los barridos completos de la corrida. Los sitios recorridos solo en parte no cambian
    ninguna vigencia: que falte un aviso entre los más recientes no significa que se haya dado de baja."""
    seen = json.loads(seen_path.read_text(encoding='utf-8')) if seen_path.exists() else {}
    result = {}
    for site, sweep in seen.items():
        if not sweep['barrido_completo']:
            continue
        result[site] = store.apply_sweep(site, sweep['ids'], captured_at)
        r = result[site]
        echo(f"{site}: vigencia {'aplicada' if r['aplicado'] else 'no aplicada: ' + r['motivo']}"
             f" · {r['no_vistos']} no vistos · {r['bajas']} bajas · {r['reactivados']} reactivados")
    return result


def update(store, out, sites, max_listings, client=None, history=None, echo=print, webhook=None, post=None,
           operation='venta'):
    """Corre una actualización. Nunca lanza por un fallo de captura o importación: lo devuelve con estado
    `error`, lo registra en el historial y lo envía a Make, para que el fallo quede a la vista."""
    started = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    folder = str(out.relative_to(ROOT)) if out.is_relative_to(ROOT) else str(out)
    try:
        entry = {'operacion': operation, 'carpeta': folder,
                 **_capture_and_import(store, out, sites, max_listings, client, echo, operation)}
    except Exception as error:  # noqa: BLE001 - el fallo se informa, no se oculta
        entry = {'fecha': started, 'operacion': operation, 'carpeta': folder, 'estado': 'error',
                 'error': f'{type(error).__name__}: {error}'[:300], 'alertas': []}
        echo(f"Error en la corrida: {entry['error']}")
    if webhook:
        kwargs = {'post': post} if post else {}
        searches = store.searches() if entry['alertas'] else []
        entry['make'] = make_webhook.send(webhook, make_webhook.payload(entry, CATALOGS[operation], searches),
                                          **kwargs)
        echo(f"Make: {'enviado' if entry['make']['enviado'] else 'error ' + str(entry['make'].get('error'))}")
    if history is not None:
        history.parent.mkdir(parents=True, exist_ok=True)
        with history.open('a', encoding='utf-8') as stream:
            stream.write(json.dumps(entry, ensure_ascii=False) + '\n')
    return entry


PRUEBAS = ('alertas', 'sin-novedades', 'error')


def test_run(kind, operation):
    """Corrida ficticia para probar cada ruta del escenario de Make. Nada de esto sale de una captura."""
    rent = operation == 'alquiler'
    currency, price = ('ARS', 750000) if rent else ('USD', 100000)
    entry = {'fecha': datetime.now(timezone.utc).replace(microsecond=0).isoformat(), 'operacion': operation,
             'estado': 'ok', 'sitios': {'ficticia': 'completo'},
             'leidos': 0, 'nuevos': 0, 'repetidos': 0, 'descartados': 0, 'alertas': []}
    searches = []
    if kind == 'error':
        entry.update(estado='error', error='Prueba: fallo ficticio', sitios={})
        for k in make_webhook.COUNTS:
            entry.pop(k)
    elif kind == 'alertas':
        searches = [{'id': 0, 'neighborhood': 'Caballito', 'budget': price * 1.1, 'min_area': 40, 'rooms': 2,
                     'currency': currency}]
        entry['alertas'] = [{'operacion': operation, 'busqueda': 0, 'aviso': f'prueba:ficticio-{n}',
                             'barrio': 'Caballito', 'precio': price - 5000 * n, 'moneda': currency,
                             'precio_usd': price - 5000 * n, 'expensas_ars': 90000 if rent else None,
                             'superficie_m2': 45, 'ambientes': 2,
                             'url': f'https://example.invalid/aviso-ficticio-{n}'} for n in (1, 2)]
        entry.update(leidos=2, nuevos=2)
    return entry, searches


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--max-avisos', type=int, default=200, help='Avisos más recientes por inmobiliaria')
    parser.add_argument('--barrido-completo', action='store_true',
                        help=f'Recorre todos los avisos de cada inmobiliaria (hasta {BARRIDO_MAX}) para detectar '
                             'bajas. Es más lento; conviene una vez por semana')
    parser.add_argument('--operacion', choices=sorted(BASES), default='venta')
    parser.add_argument('--base', type=Path, help='Por defecto, la base real de la operación')
    parser.add_argument('--sitios', nargs='+', choices=sorted(SITES), default=list(DEFAULT_SITES))
    parser.add_argument('--autorizacion-confirmada', action='store_true')
    parser.add_argument('--probar-make', nargs='?', const='alertas', choices=sorted(PRUEBAS),
                        help='Envía a Make una corrida ficticia (alertas, sin-novedades o error), '
                             'sin capturar ni importar')
    args = parser.parse_args()
    try:
        webhook = make_webhook.webhook_url()
    except ValueError as error:
        parser.exit(1, f'Error: {error}\n')
    if args.probar_make:
        if not webhook:
            parser.exit(1, 'Error: falta MAKE_WEBHOOK_URL en el entorno o en .env.\n')
        test, searches = test_run(args.probar_make, args.operacion)
        result = make_webhook.send(webhook, make_webhook.payload(test, 'prueba-ficticia', searches))
        print(json.dumps(result, ensure_ascii=False))
        return
    if not args.autorizacion_confirmada:
        parser.exit(1, 'Error: falta --autorizacion-confirmada.\n')
    base = args.base or BASES[args.operacion]
    if not base.exists():
        parser.exit(1, f'Error: no existe la base {base}. Importá primero un catálogo en Datos reales.\n')
    suffix = '' if args.operacion == 'venta' else f'-{args.operacion}'
    out = ROOT / f"data/raw/inmobiliarias{suffix}-{datetime.now():%Y%m%d-%H%M}"
    max_listings = BARRIDO_MAX if args.barrido_completo else args.max_avisos
    entry = update(Store(base), out, args.sitios, max_listings, client=PoliteClient(),
                   history=base.parent / 'actualizaciones.jsonl', echo=lambda line: print(line, flush=True),
                   webhook=webhook, operation=args.operacion)
    print(json.dumps(entry, ensure_ascii=False, indent=2))
    if entry['estado'] == 'error':
        raise SystemExit(1)


if __name__ == '__main__':
    main()
