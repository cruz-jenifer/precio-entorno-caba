"""Envío del resumen de cada corrida a un escenario de Make mediante un webhook.

La URL se lee de MAKE_WEBHOOK_URL (entorno o .env, fuera de Git) y debe ser https en
un dominio de Make (*.make.com). Se envía un cuerpo por corrida, haya alertas o no, y
también cuando la corrida falla: Make lo registra y avisa si hace falta. Las alertas
viajan agrupadas por búsqueda, con un resumen listo para el correo. Solo viajan datos
del aviso: búsqueda, ID, barrio, precio, superficie, ambientes y enlace; nunca datos
personales. Un fallo de envío no detiene la actualización: queda registrado.
"""

import html
import json
import os
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
ALERT_FIELDS = ('operacion', 'busqueda', 'aviso', 'barrio', 'precio', 'moneda', 'precio_usd', 'expensas_ars',
                'superficie_m2', 'ambientes', 'url')
COUNTS = ('leidos', 'nuevos', 'repetidos', 'descartados')
ESTADOS = ('ok', 'parcial', 'error')


def webhook_url(env=ROOT / '.env', variable='MAKE_WEBHOOK_URL'):
    """URL de un webhook de Make: MAKE_WEBHOOK_URL (alertas) o MAKE_BUSQUEDAS_WEBHOOK_URL (altas)."""
    url = os.environ.get(variable, '').strip()
    if not url and env.is_file():
        for line in env.read_text(encoding='utf-8-sig').splitlines():
            name, sep, value = line.strip().partition('=')
            if sep and name.strip().removeprefix('export ').strip() == variable:
                url = value.strip().strip('"\'')
    if not url:
        return None
    parts = urlsplit(url)
    host = parts.hostname or ''
    if parts.scheme != 'https' or not (host == 'make.com' or host.endswith('.make.com')):
        raise ValueError(f'{variable} debe ser una URL https de un dominio de Make (*.make.com).')
    return url


def subscription(search_id, operation, search, email, now):
    """Alta de una búsqueda con aviso por correo. El mail viaja solo a Make, que lo guarda en la planilla.

    `search_id` es aleatorio: identifica la búsqueda ante el Actor y sirve de clave para la baja.
    """
    criteria = {'id': search_id, 'operacion': operation, 'barrio': search['barrio'],
                'presupuesto': search['presupuesto'], 'moneda': search['moneda'], 'superficie': search['superficie'],
                'ambientes': search['ambientes'], 'ambientesOMas': bool(search.get('ambientes_o_mas', search.get('ambientesOMas')))}
    description = describe_search({'neighborhood': search['barrio'], 'budget': search['presupuesto'],
                                   'currency': search['moneda'], 'min_area': search['superficie'],
                                   'rooms': search['ambientes'], 'or_more': criteria['ambientesOMas']})
    return {'tipo': 'alta', 'fecha': now, 'busqueda': criteria, 'descripcion': description, 'email': email}


def money(value, currency):
    """Monto con separador de miles argentino: USD 110.000."""
    if value is None:
        return '—'
    return f"{currency or 'USD'} {value:,.0f}".replace(',', '.')


def describe_search(search):
    """Texto corto de una búsqueda guardada, para el asunto y el cuerpo del correo."""
    rooms = f"{search['rooms']} ambientes" + (' o más' if search.get('or_more', search.get('rooms_or_more')) else '')
    return (f"{search['neighborhood']} · hasta {money(search['budget'], search.get('currency'))} · "
            f"{search['min_area']:g} m² o más · {rooms}")


def _line(alert):
    parts = [alert['barrio'], money(alert['precio'], alert['moneda'])]
    if alert.get('expensas_ars'):
        parts.append(f"expensas {money(alert['expensas_ars'], 'ARS')}")
    parts += [f"{alert['superficie_m2']:g} m²" if alert.get('superficie_m2') is not None else '— m²',
              f"{alert['ambientes']} amb."]
    return ' · '.join(str(p) for p in parts)


def _link(url):
    """Enlace solo si la URL es http(s); el texto del aviso nunca se interpreta como HTML."""
    if url and urlsplit(url).scheme in ('http', 'https'):
        return f'<a href="{html.escape(url, quote=True)}">Ver aviso</a>'
    return ''


def group(alerts, searches=()):
    """Agrupa las alertas por búsqueda y arma asunto, texto y HTML para un solo correo por búsqueda."""
    known = {s['id']: s for s in searches}
    groups = {}
    for alert in alerts:
        groups.setdefault(alert['busqueda'], []).append(alert)
    result = []
    for search_id, items in groups.items():
        search = known.get(search_id)
        description = describe_search(search) if search else f'Búsqueda {search_id}'
        noun = 'aviso nuevo' if len(items) == 1 else 'avisos nuevos'
        rows = ''.join(f'<li>{html.escape(_line(a))} {_link(a.get("url"))}</li>' for a in items)
        result.append({
            'busqueda': search_id, 'descripcion': description, 'cantidad': len(items),
            'asunto': f'{len(items)} {noun} · {description}',
            'texto': '\n'.join(f"- {_line(a)}\n  {a.get('url') or ''}" for a in items),
            'html': (f'<p><strong>{html.escape(description)}</strong></p><ul>{rows}</ul>'
                     '<p>Precios de publicación, no tasaciones.</p>'),
            'avisos': [a['aviso'] for a in items],
        })
    return result


def payload(entry, catalog, searches=()):
    """Cuerpo de una corrida: estado, conteos, alertas sueltas (una fila cada una) y alertas por búsqueda."""
    alerts = [{k: a.get(k) for k in ALERT_FIELDS} for a in entry.get('alertas', [])]
    sites = entry.get('sitios') or {}
    return {
        'tipo': 'corrida', 'fecha': entry['fecha'], 'operacion': entry.get('operacion'), 'catalogo': catalog,
        'estado': entry.get('estado', 'ok'), 'error': entry.get('error'),
        'sitios': ' · '.join(f'{site}: {status}' for site, status in sites.items()),
        **{k: entry.get(k) for k in COUNTS},
        'cantidad': len(alerts), 'alertas': alerts, 'busquedas': group(alerts, searches),
    }


def _post(url, body, timeout=20):
    request = Request(url, data=json.dumps(body, ensure_ascii=False).encode('utf-8'),
                      headers={'Content-Type': 'application/json; charset=utf-8',
                               'User-Agent': 'precio-entorno-caba/0.1'}, method='POST')
    with urlopen(request, timeout=timeout) as response:
        return response.status


def send(url, body, post=_post, retries=1, sleep=time.sleep):
    """Envía el cuerpo al webhook. Devuelve un resumen del resultado, sin lanzar errores."""
    last = None
    for attempt in range(retries + 1):
        try:
            status = post(url, body)
            if 200 <= status < 300:
                return {'enviado': True, 'http': status, 'intentos': attempt + 1}
            last = f'HTTP {status}'
        except HTTPError as error:
            last = f'HTTP {error.code}'
        except (URLError, TimeoutError, OSError) as error:
            last = type(error).__name__
        if attempt < retries:
            sleep(5)
    return {'enviado': False, 'error': last, 'intentos': retries + 1}
