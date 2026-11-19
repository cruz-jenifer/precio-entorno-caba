"""Paquete autónomo y permitido para el Colab integral; no extrae datos nuevos."""

import hashlib
import json
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'data/processed/colab-capstone/capstone_bundle.zip'
SOURCES = [
    'precio_entorno/__init__.py', 'precio_entorno/benchmark_inmobiliario.py',
    'precio_entorno/auditoria_estadistica.py', 'precio_entorno/anova_barrios.py',
    'data/processed/eda-colab/eda_bundle.zip',
    'data/processed/auditoria-estadistica/predicciones_oof.csv',
    'reports/benchmark-auditado/ajustes.csv', 'reports/benchmark-auditado/resumen.csv',
    'reports/benchmark-auditado/manifiesto.json',
]


def build(out=OUT):
    sources = {name: (ROOT / name).read_bytes() for name in SOURCES}
    audit = json.loads(sources['reports/benchmark-auditado/manifiesto.json'])
    for name, digest in audit['codigo_sha256'].items():
        if hashlib.sha256(sources[f'precio_entorno/{name}']).hexdigest() != digest:
            raise ValueError(f'Cambió {name}; regenerá la auditoría antes de empaquetar.')
    for path, digest in [
        ('data/processed/eda-colab/eda_bundle.zip', audit['datos']['sha256_bundle']),
        ('data/processed/auditoria-estadistica/predicciones_oof.csv', audit['predicciones_oof_sha256']),
    ]:
        if hashlib.sha256(sources[path]).hexdigest() != digest:
            raise ValueError(f'El archivo no coincide con su manifiesto: {path}')
    manifest = {'formato': 1, 'tipo_datos': 'reales_autorizados',
                'archivos_sha256': {name: hashlib.sha256(content).hexdigest() for name, content in sources.items()},
                'nota': 'Catálogo histórico autorizado. Precios de publicación; no contactos, claves ni texto de notas.'}
    out.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(out, 'w', ZIP_DEFLATED) as z:
        for name, content in sources.items():
            z.writestr(name, content)
        z.writestr('capstone_manifest.json', json.dumps(manifest, ensure_ascii=False, indent=2))
    print(f'{out}\n{out.stat().st_size / 1e6:.2f} MB · {len(sources)} archivos permitidos + manifiesto')
    return out


if __name__ == '__main__':
    build()
