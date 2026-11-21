"""Entrada del Actor «precio-entorno-analytics»: `python -m precio_entorno.analytics.main`.

Este archivo solo tiene las herramientas del Actor: leer la entrada, abrir almacenes, publicar en el
dataset y dejar el registro OUTPUT. La lógica está en `ETL.py`, `preprocessing.py`, `EDA.py`,
`inference.py` y `tooling_business.py`. El Actor no entrena: usa el modelo ya guardado.

Make lo llama con `run-sync`, que devuelve el registro OUTPUT:

- `operacion: "etl"`: avisos crudos (base64) → OUTPUT con el CSV limpio. El reporte de calidad queda
  en REPORTE_ETL y en el almacén con nombre, para el EDA.
- `operacion: "eda"`: CSV limpio → OUTPUT con el cuerpo de `values:batchUpdate` de las seis
  pestañas. Cada tabla queda además como CSV, y la de barrios en el dataset.
- `operacion: "inferencia"`: CSV limpio + `almacenModelo` → OUTPUT con el cuerpo de la pestaña `predicciones`. Las
  referencias completas quedan en `predicciones.csv`; el dataset lleva solo las que conviene revisar
  primero (debajo de la referencia), y el resumen queda en RESUMEN_INFERENCIA.

Si algo falla, la corrida termina en FAILED y `run-sync` responde con error: Make corta el flujo.
"""

import asyncio
import base64
import re
import tempfile
from pathlib import Path

from apify import Actor

from precio_entorno.analytics import EDA, ETL, inference, preprocessing, tooling_business

PIPELINE_STORE = 'precio-entorno-pipeline'
OPERATIONS = ('etl', 'eda', 'inferencia')
CSV = 'text/csv; charset=utf-8'


def content_from(actor_input):
    if actor_input.get('contenidoBase64'):
        return base64.b64decode(actor_input['contenidoBase64'])
    if actor_input.get('contenidoUrl'):
        return ETL.download(actor_input['contenidoUrl'])
    raise ValueError('Falta contenidoBase64 o contenidoUrl.')


def records(df):
    return df.astype(object).where(df.notna(), None).to_dict(orient='records')


async def run_etl(actor_input, content):
    with tempfile.TemporaryDirectory() as tmp:
        crimes = Path(tmp) / 'delitos_2025.csv'
        ETL.download(actor_input.get('delitosUrl') or ETL.CRIMES_URL, crimes)
        clean, report = ETL.etl(content, actor_input.get('nombreArchivo') or 'avisos.json', crimes)
    Actor.log.info(f"ETL: {report['filas_leidas']} filas leídas, {report['avisos']} avisos limpios.")
    await Actor.set_value('REPORTE_ETL', report)
    store = await Actor.open_key_value_store(name=PIPELINE_STORE)
    await store.set_value('reporte_etl', report)
    await Actor.push_data([{'operacion': 'etl', **{k: v for k, v in report.items() if k != 'delitos'}}])
    await Actor.set_value('OUTPUT', preprocessing.to_csv(clean), content_type=CSV)


async def run_eda(content):
    store = await Actor.open_key_value_store(name=PIPELINE_STORE)
    tables = EDA.eda(preprocessing.read_clean(content), await store.get_value('reporte_etl'))
    for name, table in tables.items():
        await Actor.set_value(f'{name}.csv', preprocessing.to_csv(table), content_type=CSV)
    await Actor.push_data(records(tables['barrios']))
    Actor.log.info(f"EDA: {len(tables['barrios'])} barrios, {int(tables['resumen'].at[0, 'avisos'])} avisos.")
    await Actor.set_value('OUTPUT', tooling_business.sheets_body(tables))


async def open_model_store(reference):
    """Con permisos limitados, el Actor solo lee el almacén que llega en `almacenModelo` (resourcePicker)."""
    if not reference:
        raise ValueError('Para inferencia, pasá en «almacenModelo» el ID del almacén del modelo '
                         '(lo imprime `python -m precio_entorno.apify_analytics subir-modelo`).')
    if re.fullmatch(r'[A-Za-z0-9]{17}', reference):
        return await Actor.open_key_value_store(id=reference)
    return await Actor.open_key_value_store(name=reference)


async def run_inference(actor_input, content):
    reference = actor_input.get('almacenModelo')
    store = await open_model_store(reference)
    model_bytes = await store.get_value(inference.MODEL_KEY)
    report = await store.get_value(inference.REPORT_KEY)
    if model_bytes is None or report is None:
        raise RuntimeError(f'Falta el modelo en el almacén «{reference}»: '
                           'corré `python -m precio_entorno.apify_analytics subir-modelo`.')
    bundle = inference.load_bytes(model_bytes, report)
    clean = preprocessing.read_clean(content)
    predictions, skipped = inference.predict_clean(clean, bundle)
    table = tooling_business.compare_with_reference(clean, predictions)
    summary = tooling_business.summary(table, bundle, skipped)
    # El dataset (que cobra por ítem) lleva solo la lista para revisar primero; la tabla completa va a OUTPUT.
    await Actor.push_data(records(tooling_business.to_review(table)))
    await Actor.set_value('predicciones.csv', preprocessing.to_csv(table), content_type=CSV)
    await Actor.set_value('RESUMEN_INFERENCIA', summary)
    Actor.log.info(f"Inferencia: {summary['avisos_estimados']} avisos con el modelo {summary['modelo_version']}, "
                   f"{summary['debajo']} debajo de la referencia.")
    await Actor.set_status_message(f"{summary['avisos_estimados']} referencias · {summary['debajo']} para revisar primero")
    await Actor.set_value('OUTPUT', tooling_business.predictions_body(table))


async def main():
    async with Actor:
        actor_input = await Actor.get_input() or {}
        operation = actor_input.get('operacion')
        if operation not in OPERATIONS:
            raise ValueError(f'operacion debe ser una de {", ".join(OPERATIONS)}.')
        content = content_from(actor_input)
        if operation == 'etl':
            await run_etl(actor_input, content)
        elif operation == 'eda':
            await run_eda(content)
        else:
            await run_inference(actor_input, content)


if __name__ == '__main__':
    asyncio.run(main())
