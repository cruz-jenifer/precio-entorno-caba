"""Envío de alertas nuevas a un escenario de Make mediante un webhook.

La URL se lee de MAKE_WEBHOOK_URL (entorno o .env, fuera de Git) y debe ser https en
un dominio de Make (*.make.com). Solo viajan datos del aviso: búsqueda, ID, barrio,
precio, superficie, ambientes y enlace; nunca datos personales. Un fallo de envío
no detiene la actualización: queda registrado.
"""

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


def webhook_url(env=ROOT / '.env'):
    url = os.environ.get('MAKE_WEBHOOK_URL', '').strip()
    if not url and env.is_file():
        for line in env.read_text(encoding='utf-8-sig').splitlines():
            name, sep, value = line.strip().partition('=')
            if sep and name.strip().removeprefix('export ').strip() == 'MAKE_WEBHOOK_URL':
                url = value.strip().strip('"\'')
    if not url:
        return None
    parts = urlsplit(url)
    host = parts.hostname or ''
    if parts.scheme != 'https' or not (host == 'make.com' or host.endswith('.make.com')):
        raise ValueError('MAKE_WEBHOOK_URL debe ser una URL https de un dominio de Make (*.make.com).')
    return url


def payload(entry, catalog):
    alerts = [{k: a.get(k) for k in ALERT_FIELDS} for a in entry['alertas']]
    return {'fecha': entry['fecha'], 'catalogo': catalog, 'cantidad': len(alerts), 'alertas': alerts}


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
