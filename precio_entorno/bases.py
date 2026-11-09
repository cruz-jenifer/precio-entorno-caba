"""Ubicación de las bases de la demo y de los datos reales, compartida por las interfaces."""

import json
import os
from pathlib import Path

from .store import Store

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / 'data/fixtures/demo.json'
REAL_BASE = ROOT / 'data/local/real.sqlite3'


def demo_base():
    return Path(os.environ.get('PRECIO_ENTORNO_DB', ROOT / 'data/local/demo.sqlite3'))


def operation_path(base, operation):
    """Venta usa la base original; alquiler, una base hermana con sufijo -alquiler."""
    return base if operation == 'venta' else base.with_name(f'{base.stem}-alquiler{base.suffix}')


def demo_rentals(items):
    """Completa los avisos ficticios de alquiler con los campos que guarda la base."""
    return [dict(item, url=f"https://example.invalid/{item['id']}", captured_at='2026-11-07',
                 total_area_m2=None, latitude=None, longitude=None, location_accuracy_m=None) for item in items]


def fixtures():
    return json.loads(FIXTURES.read_text(encoding='utf-8'))


def open_store(demo, operation, demo_path=None, real_path=None):
    """Abre la base de la operación. La demo se completa con su lote inicial ficticio."""
    demo_path = operation_path(demo_path or demo_base(), operation)
    real_path = operation_path(real_path or REAL_BASE, operation)
    if demo_path.resolve() == real_path.resolve():
        raise ValueError('Las bases de la demo y de datos reales deben usar rutas distintas.')
    store = Store(demo_path if demo else real_path)
    if demo:
        data = fixtures()
        if operation == 'venta':
            store.seed(data['initial'])
        else:
            store.ingest(demo_rentals(data['alquiler']['initial']), source='demo-alquiler')
    return store
