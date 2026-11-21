"""Corre local las mismas etapas que el Actor `precio-entorno-analytics`, sin Apify.

    python -m precio_entorno.pipeline_analytics etl data/raw/venta-consolidada-20261108/avisos.json
    python -m precio_entorno.pipeline_analytics eda data/processed/pipeline/dataset_limpio.csv
    python -m precio_entorno.pipeline_analytics inferencia data/processed/pipeline/dataset_limpio.csv

La lógica está en `precio_entorno/analytics/` (un módulo por etapa); este archivo solo lee y
escribe archivos locales. Los precios son de publicación, no tasaciones. Los delitos son hechos
registrados, con período y unidad geográfica (barrio), y se muestran como contexto.
"""

import argparse
import json
from pathlib import Path

from precio_entorno.analytics import EDA, ETL, inference, preprocessing, tooling_business

ROOT = Path(__file__).resolve().parents[1]


def write_json(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('operacion', choices=('etl', 'eda', 'inferencia'))
    parser.add_argument('archivo', type=Path, help='etl: avisos crudos (JSON o CSV); eda e inferencia: CSV limpio')
    parser.add_argument('--delitos', type=Path, default=ROOT / 'data/raw/delitos_2025.csv')
    parser.add_argument('--salida', type=Path, default=ROOT / 'data/processed/pipeline')
    parser.add_argument('--modelo', type=Path, default=ROOT / 'data/processed/inferencia')
    args = parser.parse_args()
    args.salida.mkdir(parents=True, exist_ok=True)
    try:
        if args.operacion == 'etl':
            clean, report = ETL.etl(args.archivo.read_bytes(), args.archivo.name, args.delitos)
            (args.salida / 'dataset_limpio.csv').write_bytes(preprocessing.to_csv(clean).encode('utf-8'))
            write_json(args.salida / 'reporte_etl.json', report)
            print(json.dumps(report, ensure_ascii=False, indent=2))
        elif args.operacion == 'inferencia':
            bundle = inference.load(args.modelo)
            clean = preprocessing.read_clean(args.archivo.read_bytes())
            predictions, skipped = inference.predict_clean(clean, bundle)
            table = tooling_business.compare_with_reference(clean, predictions)
            summary = tooling_business.summary(table, bundle, skipped)
            table.to_csv(args.salida / 'predicciones.csv', index=False)
            (args.salida / 'sheets_predicciones_body.json').write_text(
                json.dumps(tooling_business.predictions_body(table), ensure_ascii=False), encoding='utf-8')
            write_json(args.salida / 'resumen_inferencia.json', summary)
            print(json.dumps(summary, ensure_ascii=False, indent=2))
        else:
            report_path = args.salida / 'reporte_etl.json'
            report = json.loads(report_path.read_text(encoding='utf-8')) if report_path.exists() else None
            tables = EDA.eda(preprocessing.read_clean(args.archivo.read_bytes()), report)
            for name, df in tables.items():
                (args.salida / f'{name}.csv').write_bytes(preprocessing.to_csv(df).encode('utf-8'))
            (args.salida / 'sheets_body.json').write_text(
                json.dumps(tooling_business.sheets_body(tables), ensure_ascii=False), encoding='utf-8')
            print(tables['resumen'].T.to_string(header=False))
    except (OSError, ValueError, KeyError) as error:
        parser.exit(1, f'Error: {error}\n')


if __name__ == '__main__':
    main()
