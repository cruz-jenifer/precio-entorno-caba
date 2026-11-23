"""Entrada del Actor «precio-entorno-analytics»: `python -m precio_entorno.analytics.main`.

Este archivo solo arma el Actor: lee la entrada con el SDK, publica en el dataset, guarda registros y
deja el estado. Toda la lógica está en `preprocessing.py`, `ETL.py`, `EDA.py`, `inference.py` y
`tooling_business.py`. El Actor no entrena, no descarga nada y no crea el modelo: lo lee ya hecho de
su carpeta (`modelo/`), junto con el resumen de delitos por barrio (`referencias/`).

Make lo llama con `run-sync`, que devuelve el registro OUTPUT:

- `operacion: "etl"`: avisos crudos (base64) → OUTPUT con el CSV limpio. El reporte de calidad queda
  en REPORTE_ETL y en el almacén con nombre, para el EDA.
- `operacion: "eda"`: CSV limpio → OUTPUT con el cuerpo de `values:batchUpdate` de las seis
  pestañas. Cada tabla queda además como CSV, y la de barrios en el dataset.
- `operacion: "inferencia"`: CSV limpio → OUTPUT con el cuerpo de la pestaña `predicciones`. Las
  referencias completas quedan en `predicciones.csv`; el dataset lleva solo las que conviene revisar
  primero (debajo de la referencia), y el resumen queda en RESUMEN_INFERENCIA.

Si algo falla, la corrida termina en FAILED y `run-sync` responde con error: Make corta el flujo.
"""

import asyncio

from apify import Actor

from precio_entorno.analytics import EDA, ETL, inference, preprocessing, tooling_business

PIPELINE_STORE = 'precio-entorno-pipeline'
CSV = 'text/csv; charset=utf-8'


async def main():
    async with Actor:
        operation, content, filename = preprocessing.read_input(await Actor.get_input() or {})
        pipeline = await Actor.open_key_value_store(name=PIPELINE_STORE)

        if operation == 'etl':
            clean, report = ETL.etl(content, filename, ETL.load_crimes_summary())
            await Actor.set_value('REPORTE_ETL', report)
            await pipeline.set_value('reporte_etl', report)
            await Actor.push_data([ETL.dataset_row(report)])
            await Actor.set_status_message(f"ETL: {report['avisos']} avisos limpios de {report['filas_leidas']} filas")
            await Actor.set_value('OUTPUT', preprocessing.to_csv(clean), content_type=CSV)

        elif operation == 'eda':
            tables = EDA.eda(preprocessing.read_clean(content), await pipeline.get_value('reporte_etl'))
            for name, table in tables.items():
                await Actor.set_value(f'{name}.csv', preprocessing.to_csv(table), content_type=CSV)
            await Actor.push_data(preprocessing.to_records(tables['barrios']))
            await Actor.set_status_message(f"EDA: {len(tables['barrios'])} barrios")
            await Actor.set_value('OUTPUT', tooling_business.sheets_body(tables))

        else:
            clean = preprocessing.read_clean(content)
            bundle = inference.load()
            predictions, skipped = inference.predict_clean(clean, bundle)
            table = tooling_business.compare_with_reference(clean, predictions)
            summary = tooling_business.summary(table, bundle, skipped)
            # El dataset (que cobra por ítem) lleva solo la lista para revisar primero; la tabla completa va a OUTPUT.
            await Actor.push_data(preprocessing.to_records(tooling_business.to_review(table)))
            await Actor.set_value('predicciones.csv', preprocessing.to_csv(table), content_type=CSV)
            await Actor.set_value('RESUMEN_INFERENCIA', summary)
            await Actor.set_status_message(
                f"{summary['avisos_estimados']} referencias · {summary['debajo']} para revisar primero")
            await Actor.set_value('OUTPUT', tooling_business.predictions_body(table))


if __name__ == '__main__':
    asyncio.run(main())
