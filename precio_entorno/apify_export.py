"""Prepare an authorized automatic/zonaprop-ar-scraper JSON export offline."""

import argparse
import json
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.parse import urlsplit

from precio_entorno.importing import BARRIOS, import_listings, key, usable_pin
from precio_entorno.store import Store


def adapt_export(rows, captured_at):
    capture = datetime.fromisoformat(captured_at).isoformat()
    if not isinstance(rows, list) or not 1 <= len(rows) <= 50:
        raise ValueError('El piloto requiere un JSON con una lista de 1 a 50 avisos.')

    listings = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        url = urlsplit(str(row.get('url', '')))
        hierarchy = row.get('locationHierarchy')
        neighborhood = BARRIOS.get(key(hierarchy[0])) if isinstance(hierarchy, list) and hierarchy else None
        if (row.get('portal') != 'zonaprop' or row.get('country') != 'AR'
                or row.get('operation') != 'sale' or row.get('propertyType') != 'departamentos'
                or row.get('postingType') != 'PROPERTY' or neighborhood not in ('Caballito', 'Almagro')
                or url.scheme != 'https' or url.netloc not in ('www.zonaprop.com.ar', 'zonaprop.com.ar')
                or not url.path.startswith('/propiedades/')
                or not str(row.get('listingKey', '')).startswith('zonaprop.com.ar:')):
            continue
        listings.append({
            'listing_id': row['listingKey'],
            'source': 'zonaprop',
            'url': url._replace(query='', fragment='').geturl(),
            'captured_at': capture,
            'price': row.get('price'),
            'currency': row.get('currency'),
            'covered_area_m2': row.get('coveredAreaM2'),
            'total_area_m2': row.get('totalAreaM2'),
            'rooms': row.get('rooms'),
            'neighborhood': neighborhood,
            'latitude': row.get('latitude'),
            'longitude': row.get('longitude'),
        })
    return listings


def main():
    parser = argparse.ArgumentParser(description='Revisá un lote exportado de Apify sin tocar la base real.')
    parser.add_argument('input', type=Path, help='JSON exportado desde Storage')
    parser.add_argument('--captured-at', required=True, help='Fecha u hora ISO 8601 de la captura')
    parser.add_argument('--output', type=Path, help='Ruta nueva para el JSON preparado')
    args = parser.parse_args()
    try:
        rows = json.loads(args.input.read_text(encoding='utf-8-sig'))
        listings = adapt_export(rows, args.captured_at)
        content = json.dumps(listings, ensure_ascii=False, indent=2)
        with TemporaryDirectory() as temp:
            store = Store(Path(temp) / 'preview.sqlite3')
            report = import_listings(store, content.encode(), 'preview.json', 'zonaprop')
            pins = sum(map(usable_pin, store.listings()))
        if args.output is not None and report.added:
            with args.output.open('x', encoding='utf-8') as stream:
                stream.write(content + '\n')
    except (ValueError, OSError) as error:
        parser.exit(1, f'Error: {error}\n')
    print(f'Filas leídas: {len(rows)}. Fuera del alcance o esquema: {len(rows) - len(listings)}.')
    print(f'Aptas: {report.added}. Pines utilizables: {pins}. '
          f'Duplicadas: {report.duplicates}. Descartadas por validación: {report.discarded}.')
    print(f'Faltantes: {dict(report.missing)}. Inválidos: {dict(report.invalid)}.')
    if args.output is not None and report.added:
        print(f'Archivo preparado: {args.output}')
    return 0 if report.added else 1


if __name__ == '__main__':
    raise SystemExit(main())

