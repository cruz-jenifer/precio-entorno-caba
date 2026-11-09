"""Empaqueta los datos reales para el EDA de oportunidades en Colab.

Arma un .zip con los avisos de venta (con las variables de ubicación del modelo),
los de alquiler, el perfil de entorno de cada barrio, sus polígonos y los delitos
registrados agregados por barrio. No incluye contactos de anunciantes, descripciones
ni fotos: las capturas ya no los guardan y acá solo se copian columnas conocidas.

    python -m precio_entorno.eda_colab

El .zip queda en data/processed/eda-colab/, que Git excluye. Se sube a Colab a mano.
"""

import argparse
import json
import sqlite3
import zipfile
from contextlib import closing
from pathlib import Path

import pandas as pd

from precio_entorno.importing import parse_listings

ROOT = Path(__file__).resolve().parents[1]
MODEL_DATASET = ROOT / 'data/processed/ampliado/modelo-pines-aproximados-poi-control/dataset_modelo.csv'
SALE_DB = ROOT / 'data/local/real.sqlite3'
RENT_DB = ROOT / 'data/local/real-alquiler.sqlite3'
ENTORNO = ROOT / 'data/processed/entorno'
DELITOS = ROOT / 'data/processed/delitos'
OUT = ROOT / 'data/processed/eda-colab/eda_bundle.zip'

SALE_COLUMNS = ['id', 'agency', 'grupo', 'captured_at', 'price', 'currency', 'covered_area', 'total_area_m2',
                'rooms', 'neighborhood', 'expenses', 'latitude', 'longitude', 'precio_m2',
                'dist_transporte_m', 'dist_parque_m', 'dist_hospital_m', 'gastronomia_500m', 'escuelas_500m',
                'radio_delitos', 'radio_robos_hurtos']
RENT_COLUMNS = ['id', 'agency', 'captured_at', 'price', 'currency', 'covered_area', 'total_area_m2', 'rooms',
                'neighborhood', 'expenses', 'latitude', 'longitude', 'url']
ENTORNO_FILES = ('resumen.json', 'barrios.geojson', 'fuentes.json')
DELITOS_FILES = ('barrio_anio.csv', 'barrio_mes.csv', 'franja_categoria.csv')
# Capturas posteriores con datos del edificio (antigüedad, estado, cocheras, piso).
BUILDING_FIELDS = ('age_years', 'condition', 'garages', 'floor')
BUILDING_CAPTURES = sorted(ROOT.glob('data/raw/*-edificio'))


def read_db(path):
    query = """SELECT l.id, d.captured_at, l.price, d.currency, l.covered_area, d.total_area_m2, l.rooms,
                      l.neighborhood, d.expenses, d.latitude, d.longitude, d.url
               FROM listings l JOIN listing_details d ON d.listing_id = l.id"""
    with closing(sqlite3.connect(path)) as db:
        df = pd.read_sql_query(query, db)
    df['agency'] = df['id'].str.split(':').str[0]
    return df


def building_table(folders, catalog='inmobiliarias-autorizadas'):
    """Datos del edificio por ID de aviso, validados como en la app. Gana la captura más reciente."""
    frames = []
    for folder in folders:
        listings, _ = parse_listings((Path(folder) / 'avisos.json').read_bytes(), 'avisos.json', catalog)
        frames.append(pd.DataFrame(listings, columns=['id', 'captured_at', *BUILDING_FIELDS]))
    if not frames:
        return pd.DataFrame(columns=['id', *BUILDING_FIELDS])
    df = pd.concat(frames).sort_values('captured_at')
    return df.drop_duplicates('id', keep='last')[['id', *BUILDING_FIELDS]]


def sale_table(model_dataset, sale_db, building=()):
    """Avisos de venta del modelo, con la URL pública y, si hay, los datos del edificio.

    Los datos del edificio se unen por ID: la muestra sigue siendo la del modelo, y un
    aviso que ya no estaba publicado en la captura posterior queda sin dato.
    """
    df = pd.read_csv(model_dataset)[SALE_COLUMNS]
    urls = read_db(sale_db)[['id', 'url']] if Path(sale_db).exists() else pd.DataFrame(columns=['id', 'url'])
    return df.merge(building_table(building), on='id', how='left').merge(urls, on='id', how='left')


def rent_table(rent_db):
    return read_db(rent_db)[RENT_COLUMNS]


def build(model_dataset=MODEL_DATASET, sale_db=SALE_DB, rent_db=RENT_DB, entorno=ENTORNO, delitos=DELITOS, out=OUT,
          building=BUILDING_CAPTURES):
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    sale, rent = sale_table(model_dataset, sale_db, building), rent_table(rent_db)
    meta = {
        'aviso': 'Precios de publicación, no tasaciones ni precios de cierre. Datos reales del catálogo autorizado.',
        'venta': {'avisos': len(sale), 'origen': str(Path(model_dataset).relative_to(ROOT))
                  if Path(model_dataset).is_relative_to(ROOT) else Path(model_dataset).name},
        'alquiler': {'avisos': len(rent), 'por_moneda': rent['currency'].value_counts().to_dict()},
        'edificio': {'capturas': [Path(f).name for f in building],
                     'con_antiguedad': int(sale['age_years'].notna().sum()),
                     'con_estado': int(sale['condition'].notna().sum())},
        'delitos': 'Mapa del Delito de CABA, hechos registrados por barrio (2024 y 2025).',
        'captura': sorted(set(sale['captured_at'].str[:10]) | set(rent['captured_at'].str[:10])),
    }
    with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED) as z:
        z.writestr('venta.csv', sale.to_csv(index=False))
        z.writestr('alquiler.csv', rent.to_csv(index=False))
        z.writestr('meta.json', json.dumps(meta, ensure_ascii=False, indent=1))
        for name in ENTORNO_FILES:
            z.write(Path(entorno) / name, f'entorno/{name}')
        for name in DELITOS_FILES:
            z.write(Path(delitos) / name, f'delitos/{name}')
    return out, meta


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--salida', default=OUT, type=Path)
    args = parser.parse_args()
    out, meta = build(out=args.salida)
    print(f'{out} · venta {meta["venta"]["avisos"]} · alquiler {meta["alquiler"]["avisos"]}')


if __name__ == '__main__':
    main()
