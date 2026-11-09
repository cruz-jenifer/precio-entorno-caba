"""Reporte de una corrida del ETL: filas leídas, aceptadas, descartadas, duplicadas y faltantes.

Reproduce la carga con las mismas funciones que usa la app, sobre una base temporal (la base real no se toca):

1. Avisos: la captura consolidada de venta (`data/raw/venta-consolidada-20261108`).
2. Delitos: el CSV oficial del Mapa del Delito de 2025.
3. Reimportación del mismo lote de avisos: no agrega filas ni alertas.
4. Un lote ficticio con errores de carga: muestra qué se descarta y por qué.

    python -m precio_entorno.etl_reporte

Escribe `data/processed/etl/reporte.json` (fuera de Git) y muestra un resumen.
"""

import argparse
import json
import tempfile
from collections import Counter
from pathlib import Path

from precio_entorno.importing import import_crimes, import_listings, parse_listings
from precio_entorno.inmobiliarias import CATALOG
from precio_entorno.store import Store

ROOT = Path(__file__).resolve().parents[1]
CAPTURE = ROOT / 'data/raw/venta-consolidada-20261108'
CRIMES = ROOT / 'data/raw/delitos_2025.csv'
OUT = ROOT / 'data/processed/etl/reporte.json'

# Lote ficticio: cada fila tiene un error de carga típico, salvo la primera.
INVALID_BATCH = [
    {'listing_id': 'ficticio:ok', 'url': 'https://example.invalid/ok', 'captured_at': '2026-11-09T12:00:00',
     'price': 120000, 'currency': 'USD', 'covered_area_m2': 50, 'rooms': 2, 'neighborhood': 'Caballito'},
    {'listing_id': 'ficticio:miles', 'url': 'https://example.invalid/1', 'captured_at': '2026-11-09T12:00:00',
     'price': '120.000', 'currency': 'USD', 'covered_area_m2': 50, 'rooms': 2, 'neighborhood': 'Caballito'},
    {'listing_id': 'ficticio:pesos', 'url': 'https://example.invalid/2', 'captured_at': '2026-11-09T12:00:00',
     'price': 120000000, 'currency': 'ARS', 'covered_area_m2': 50, 'rooms': 2, 'neighborhood': 'Caballito'},
    {'listing_id': 'ficticio:barrio', 'url': 'https://example.invalid/3', 'captured_at': '2026-11-09T12:00:00',
     'price': 120000, 'currency': 'USD', 'covered_area_m2': 50, 'rooms': 2, 'neighborhood': 'Gotham'},
    {'listing_id': 'ficticio:m2', 'url': 'https://example.invalid/4', 'captured_at': '2026-11-09T12:00:00',
     'price': 120000, 'currency': 'USD', 'covered_area_m2': 5, 'rooms': 2, 'neighborhood': 'Caballito'},
    {'listing_id': 'ficticio:usd_m2', 'url': 'https://example.invalid/5', 'captured_at': '2026-11-09T12:00:00',
     'price': 15000, 'currency': 'USD', 'covered_area_m2': 200, 'rooms': 5, 'neighborhood': 'Caballito'},
    {'listing_id': 'ficticio:url', 'url': 'javascript:alert(1)', 'captured_at': '2026-11-09T12:00:00',
     'price': 120000, 'currency': 'USD', 'covered_area_m2': 50, 'rooms': 2, 'neighborhood': 'Caballito'},
]


def report_dict(report):
    return {'leidas': report.read, 'aceptadas': report.added, 'duplicadas': report.duplicates,
            'descartadas': report.discarded, 'alertas': report.alerts,
            'faltantes': dict(report.missing), 'invalidas': dict(report.invalid)}


def capture_stage(log):
    """Lo que el adaptador ya dejó afuera antes de escribir el lote (fuera de alcance, barrio ambiguo...)."""
    omitted = Counter()
    for site in log['sitios'].values():
        omitted.update(site.get('omitidos', {}))
    groups = log.get('posibles_duplicados_entre_inmobiliarias') or []
    return {'avisos_escritos': log.get('avisos'), 'omitidos_en_captura': dict(omitted),
            'posibles_duplicados_entre_inmobiliarias': {'grupos': len(groups), 'avisos': sum(map(len, groups))},
            'sitios': {s: v.get('avisos') for s, v in log['sitios'].items()}}


def run(capture=CAPTURE, crimes=CRIMES):
    content = (capture / 'avisos.json').read_bytes()
    log = json.loads((capture / 'registro.json').read_text(encoding='utf-8'))
    with tempfile.TemporaryDirectory() as temp:
        store = Store(Path(temp) / 'etl.sqlite3')
        store.save_search('Caballito', 130_000, 40, 2)  # Una búsqueda, para mostrar que la reimportación no alerta.
        first = import_listings(store, content, 'avisos.json', CATALOG)
        again = import_listings(store, content, 'avisos.json', CATALOG)
        crime = import_crimes(store, crimes.read_bytes(), crimes.name) if crimes.exists() else None
    listings, _ = parse_listings(content, 'avisos.json', CATALOG)
    invalid_listings, invalid = parse_listings(json.dumps(INVALID_BATCH).encode(), 'lote.json', CATALOG)
    return {
        'captura': {'carpeta': capture.name, **capture_stage(log)},
        'avisos': report_dict(first),
        'avisos_validados_con_repeticiones': len(listings),
        'reimportacion': report_dict(again),
        'delitos': report_dict(crime) | {'archivo': crimes.name} if crime else None,
        # Sin base: se informan los IDs que pasarían la validación, no un conteo de filas guardadas.
        'lote_invalido': {**report_dict(invalid), 'aceptadas': [l['id'] for l in invalid_listings]},
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.parse_args()
    result = run()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
