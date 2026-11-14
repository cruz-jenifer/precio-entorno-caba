"""Compara interpretaciones sobre etiquetas sintéticas sin guardar texto de las llamadas."""
import argparse
import json
from pathlib import Path

from .preferencias import ErrorPreferencias, Interprete, reglas

ROOT = Path(__file__).resolve().parents[1]


def evaluar(casos, interpretar):
    correctos = total = dudas_ok = dudas_total = silenciosos = condiciones = 0
    for caso in casos:
        try:
            propuesta = interpretar(caso['texto'])
        except ErrorPreferencias as error:
            raise SystemExit(f"{caso['id']}: {error}") from None
        actual = {}
        for campo in propuesta.campos:
            if campo.clave in ('barrio', 'capa'):
                actual.setdefault(campo.clave, []).append(campo.valor)
            else:
                actual[campo.clave] = campo.valor
        gold = caso['campos']
        claves = actual.keys() | gold.keys()
        for clave in claves:
            a, b = actual.get(clave), gold.get(clave)
            correctos += sorted(a) == sorted(b) if isinstance(a, list) and isinstance(b, list) else a == b
        total += len(claves)
        dudas = {d.campo for d in propuesta.dudas}
        esperadas = set(caso['dudas'])
        dudas_ok += len(dudas & esperadas)
        dudas_total += len(dudas | esperadas)
        silenciosos += sum(k in actual and actual[k] != gold.get(k) and k not in dudas
                           for k in ('moneda', 'operacion'))
        condiciones += sorted(c.obligatoria for c in propuesta.no_soportadas) == sorted(caso['condiciones'])
    return {'casos': len(casos), 'exactitud': correctos / max(1, total),
            'deteccion_dudas': dudas_ok / max(1, dudas_total), 'cambios_silenciosos': silenciosos,
            'condiciones_correctas': condiciones}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--split', choices=('desarrollo', 'prueba'), default='prueba')
    parser.add_argument('--modelo', action='store_true', help='Usa el proveedor y consume el presupuesto autorizado.')
    args = parser.parse_args()
    data = json.loads((ROOT / 'data/fixtures/preferencias_sinteticas.json').read_text(encoding='utf-8'))
    casos = [caso for caso in data['casos'] if caso['split'] == args.split]
    print(json.dumps({'reglas': evaluar(casos, reglas)}, ensure_ascii=False))
    if args.modelo:
        service = Interprete.from_env(ROOT / 'data/local')
        if not service.enabled:
            parser.error('La inferencia no está habilitada.')
        print(json.dumps({'modelo': evaluar(casos, service.interpretar)}, ensure_ascii=False))


if __name__ == '__main__':
    main()
