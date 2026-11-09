"""Entrada del Actor de Apify «precio-entorno-alertas»: `python -m precio_entorno.actor_main`.

Lee la entrada, recupera los IDs ya vistos de un almacén con nombre (persiste entre
corridas), corre `actor_alertas.run`, publica un ítem del dataset por búsqueda con avisos
nuevos y deja el resumen en el registro OUTPUT. Si la corrida falla, igual deja el
resumen y termina en FAILED, para que Make tome la ruta de error.
"""

import asyncio

from apify import Actor

from precio_entorno.actor_alertas import parse_input, run
from precio_entorno.inmobiliarias import PoliteClient

SEEN_STORE = 'precio-entorno-vistos'


async def main():
    async with Actor:
        try:
            config = parse_input(await Actor.get_input() or {})
        except ValueError as error:
            await Actor.set_value('OUTPUT', {'estado': 'error', 'error': f'Entrada inválida: {error}'})
            raise
        store = await Actor.open_key_value_store(name=SEEN_STORE)
        operations = sorted({s['operation'] for s in config['searches']})
        seen = {}
        for operation in operations:
            record = await store.get_value(f'vistos-{operation}')
            seen[operation] = record['ids'] if record else None
        items, new_seen, summary = await asyncio.to_thread(
            run, config, seen, PoliteClient(), lambda line: Actor.log.info(line))
        for operation, ids in new_seen.items():
            await store.set_value(f'vistos-{operation}', {'actualizado': summary['fecha'], 'ids': ids})
        if items:
            await Actor.push_data(items)
        await Actor.set_value('OUTPUT', summary)
        message = (f"{summary['estado']} · {summary['alertas']} alertas en "
                   f"{summary['busquedas_con_avisos']} de {summary['busquedas']} búsquedas")
        await Actor.set_status_message(message)
        if summary['estado'] == 'error':
            raise RuntimeError(summary['error'])


if __name__ == '__main__':
    asyncio.run(main())
