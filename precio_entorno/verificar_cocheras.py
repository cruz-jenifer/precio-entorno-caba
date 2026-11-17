"""Verifica importes mensuales explícitos en fichas de Century 21."""
import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

from .cocheras import validate
from .inmobiliarias import PoliteClient, clean, local_number


def monthly_evidence(html, price, currency):
    # Los scripts pueden contener avisos relacionados o información obsoleta.
    visible = clean(re.sub(r'<(script|style)\b[^>]*>.*?</\1>', '', html, flags=re.I | re.S))
    matches = re.findall(r'(US\$|USD|\$)\s*([\d.]+(?:,\d{1,2})?)\s*(?:/\s*mes\b|por\s+mes\b|mensuales\b)', visible, re.I)
    amounts = {(('USD' if unit.upper() in ('US$', 'USD') else 'ARS'), local_number(value))
               for unit, value in matches}
    return amounts == {(currency, price)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('archivo', type=Path)
    args = parser.parse_args()
    candidates = json.loads(args.archivo.read_text(encoding='utf-8-sig'))
    client = PoliteClient()
    verified, audit = [], []
    for item in candidates:
        entry = dict(id=item.get('id'), fuente=item.get('fuente'),
                     verificado=datetime.now(timezone.utc).isoformat())
        url = urlsplit(item.get('url') or '')
        if (item.get('fuente') != 'Century 21' or url.scheme != 'https'
                or url.netloc not in ('century21.com.ar', 'www.century21.com.ar')
                or '/alquiler/cochera/' not in url.path):
            entry['estado'] = 'fuente o enlace pendiente de revisión'
        else:
            try:
                html = client.get(item['url'])
                if monthly_evidence(html, item['precio'], item['moneda']):
                    row = dict(item, periodicidad='mensual')
                    verified.extend(validate([row]))
                    entry['estado'] = 'importe mensual explícito coincide con candidato'
                else:
                    entry['estado'] = 'sin evidencia mensual inequívoca del importe'
            except Exception as error:
                # Guardar solo el tipo de error evita volcar respuestas o datos privados.
                entry['estado'] = 'error de consulta o validación'
                entry['error'] = type(error).__name__
                audit.append(entry)
                break  # No insistir en la fuente después de un bloqueo.
        audit.append(entry)
    folder = args.archivo.parent
    for name, content in [('mensuales-verificados.json', verified), ('revision-mensual.json', audit)]:
        (folder / name).write_text(json.dumps(content, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(dict(candidatos=len(candidates), revisados=len(audit), mensuales=len(verified))))


if __name__ == '__main__':
    main()
