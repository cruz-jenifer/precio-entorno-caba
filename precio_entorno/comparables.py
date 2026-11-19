"""Cada aviso frente a avisos parecidos del mismo barrio.

Compara el precio publicado por m² cubierto de un aviso con el de los avisos vigentes del mismo barrio,
operación y moneda que tienen tamaño y ambientes parecidos. Es una comparación entre precios de
publicación, no una tasación: no dice cuánto vale la propiedad ni si conviene.

Criterios (en este orden):
- Mismo barrio, operación y moneda; avisos vigentes.
- Ambientes: ±1. Superficie cubierta: ±25 % de la del aviso.
- Antigüedad: si el aviso la declara, solo avisos que declaran una antigüedad de ±10 años. Si así quedan
  menos de `MINIMO`, se compara sin antigüedad y se avisa. En Zonaprop, 0 años se toma como no informado,
  porque el 27 % de sus avisos declara 0 y puede ser el valor por defecto del portal.
- Posibles duplicados: avisos de fuentes distintas con mismos ambientes, m² cubiertos redondeados y
  precio redondeado a miles cuentan una sola vez, y no se compara un aviso con su posible copia en otra
  fuente (mismo criterio que `modelo.duplicate_groups`).

Con menos de `MINIMO` avisos parecidos no se informa posición.
"""

from statistics import median, quantiles

MINIMO = 8
TOLERANCIA_SUPERFICIE = 0.25
TOLERANCIA_AMBIENTES = 1
TOLERANCIA_ANTIGUEDAD = 10


def _clave(item):
    return (item['rooms'], round(item['covered_area']), round(item['price'], -3))


def _fuente(item):
    return str(item['id']).split(':', 1)[0] if ':' in str(item['id']) else ''


def antiguedad(item):
    """Antigüedad declarada en años, o None si no se informa o no es confiable."""
    age = item.get('age_years')
    if age is None or age < 0 or (age == 0 and _fuente(item) == 'zonaprop'):
        return None
    return age


def _precio_m2(item):
    return item['price'] / item['covered_area']


def _parecidos(aviso, pool):
    area, rooms = aviso['covered_area'], aviso['rooms']
    # Clave → fuente que la aportó. Dos avisos de la misma fuente con igual clave son unidades distintas;
    # de fuentes distintas, una posible copia.
    vistos, out = {_clave(aviso): _fuente(aviso)}, []
    for item in pool:
        if item['id'] == aviso['id'] or not item.get('covered_area') or not item.get('price'):
            continue
        if abs(item['rooms'] - rooms) > TOLERANCIA_AMBIENTES:
            continue
        if abs(item['covered_area'] - area) > TOLERANCIA_SUPERFICIE * area:
            continue
        clave = _clave(item)
        if clave in vistos and vistos[clave] != _fuente(item):  # posible copia del aviso o de otro ya contado
            continue
        vistos.setdefault(clave, _fuente(item))
        out.append(item)
    return out


def comparar(aviso, pool):
    """Comparación de un aviso con los parecidos de `pool` (avisos del mismo barrio, operación y moneda)."""
    if not aviso.get('covered_area') or not aviso.get('price'):
        return {'n': 0, 'posicion': None, 'motivo': 'El aviso no informa precio o superficie cubierta.'}
    candidatos = _parecidos(aviso, pool)
    criterios = ['mismo barrio y moneda', f'±{TOLERANCIA_AMBIENTES} ambiente',
                 f'superficie cubierta ±{round(TOLERANCIA_SUPERFICIE * 100)} %']
    edad = antiguedad(aviso)
    sin_antiguedad = False
    if edad is not None:
        con_edad = [i for i in candidatos
                    if antiguedad(i) is not None and abs(antiguedad(i) - edad) <= TOLERANCIA_ANTIGUEDAD]
        if len(con_edad) >= MINIMO:
            candidatos = con_edad
            criterios.append(f'antigüedad ±{TOLERANCIA_ANTIGUEDAD} años')
        else:
            sin_antiguedad = True
    n = len(candidatos)
    if n < MINIMO:
        return {'n': n, 'posicion': None, 'criterios': criterios,
                'motivo': f'Hay {n} avisos parecidos; hacen falta al menos {MINIMO} para comparar.'}
    valores = sorted(_precio_m2(i) for i in candidatos)
    p25, _, p75 = quantiles(valores, n=4, method='inclusive')
    mediana = median(valores)
    propio = _precio_m2(aviso)
    posicion = 'debajo' if propio < p25 else 'arriba' if propio > p75 else 'dentro'
    return {
        'n': n, 'posicion': posicion, 'criterios': criterios, 'sin_antiguedad': sin_antiguedad,
        'precio_m2': round(propio), 'mediana_m2': round(mediana), 'p25_m2': round(p25), 'p75_m2': round(p75),
        'diferencia_pct': round((propio / mediana - 1) * 100),
    }


def comparar_todos(avisos, listings):
    """{id: comparación} para `avisos`, usando como referencia todos los `listings` de su barrio y moneda."""
    grupos = {}
    for item in listings:
        grupos.setdefault((item['neighborhood'], item.get('currency') or 'USD'), []).append(item)
    return {a['id']: comparar(a, grupos.get((a['neighborhood'], a.get('currency') or 'USD'), [])) for a in avisos}
