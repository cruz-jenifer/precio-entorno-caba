"""Entrada del Actor de Apify «precio-entorno-analytics»: `python -m precio_entorno.actor_analytics`.

Make lo llama dos veces por corrida, con `run-sync`, que devuelve el registro OUTPUT:

- `operacion: "etl"` recibe los avisos crudos que Make bajó de Drive (en base64), baja el Mapa
  del Delito del portal oficial (17 MB, más de lo que Make Free puede mover) y deja en OUTPUT el
  CSV limpio. El reporte de calidad queda en REPORTE_ETL y en el almacén con nombre, para el EDA.
- `operacion: "eda"` recibe el CSV limpio que Make bajó de Drive y deja en OUTPUT el cuerpo de
  `values:batchUpdate` para Google Sheets. Cada tabla queda además como CSV en el almacén de la
  corrida, y la tabla de barrios en el dataset, para exportarla desde Apify (CSV, Excel o JSON).

Si algo falla, la corrida termina en FAILED y `run-sync` responde con error: Make corta el flujo.
"""

import base64
import tempfile
from pathlib import Path
from urllib.request import Request, urlopen

from apify import Actor

from precio_entorno.pipeline_analytics import CRIMES_URL, eda, etl, read_clean, sheets_body, to_csv

STORE = 'precio-entorno-pipeline'


def fetch(url, path=None):
    request = Request(url, headers={'User-Agent': 'precio-entorno-caba (capstone)'})
    with urlopen(request, timeout=120) as response:
        data = response.read()
    if path:
        Path(path).write_bytes(data)
    return data


def content_from(actor_input):
    if actor_input.get('contenidoBase64'):
        return base64.b64decode(actor_input['contenidoBase64'])
    if actor_input.get('contenidoUrl'):
        return fetch(actor_input['contenidoUrl'])
    raise ValueError('Falta contenidoBase64 o contenidoUrl.')


async def main():
    async with Actor:
        actor_input = await Actor.get_input() or {}
        operation = actor_input.get('operacion')
        if operation not in ('etl', 'eda'):
            raise ValueError('operacion debe ser "etl" o "eda".')
        content = content_from(actor_input)
        store = await Actor.open_key_value_store(name=STORE)
        if operation == 'etl':
            with tempfile.TemporaryDirectory() as tmp:
                crimes = Path(tmp) / 'delitos_2025.csv'
                fetch(actor_input.get('delitosUrl') or CRIMES_URL, crimes)
                clean, report = etl(content, actor_input.get('nombreArchivo') or 'avisos.json', crimes)
            Actor.log.info(f"ETL: {report['filas_leidas']} filas leídas, {report['avisos']} avisos limpios.")
            await Actor.set_value('REPORTE_ETL', report)
            await store.set_value('reporte_etl', report)
            await Actor.push_data([{'operacion': 'etl', **{k: v for k, v in report.items() if k != 'delitos'}}])
            await Actor.set_value('OUTPUT', to_csv(clean), content_type='text/csv; charset=utf-8')
        else:
            report = await store.get_value('reporte_etl')
            tables = eda(read_clean(content), report)
            for name, table in tables.items():
                await Actor.set_value(f'{name}.csv', to_csv(table), content_type='text/csv; charset=utf-8')
            await Actor.push_data(tables['barrios'].astype(object).where(tables['barrios'].notna(), None)
                                  .to_dict(orient='records'))
            Actor.log.info(f"EDA: {len(tables['barrios'])} barrios, {int(tables['resumen'].at[0, 'avisos'])} avisos.")
            await Actor.set_value('OUTPUT', sheets_body(tables))


if __name__ == '__main__':
    import asyncio
    asyncio.run(main())
