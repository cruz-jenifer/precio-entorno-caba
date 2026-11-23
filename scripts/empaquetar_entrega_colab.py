"""Reúne notebook, insumos y resultados ya verificados para la entrega."""

from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

import nbformat

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'data/processed/colab-capstone'


def main():
    trained = BASE / 'capstone_integral_entrenado.ipynb'
    nb = nbformat.read(trained, as_version=4)
    nbformat.validate(nb)
    code = [c for c in nb.cells if c.cell_type == 'code']
    if any(c.execution_count is None for c in code) or any(
            o.output_type == 'error' for c in code for o in c.outputs):
        raise ValueError('La copia entrenada debe estar ejecutada completa y sin errores.')
    files = {
        'capstone_integral_colab.ipynb': ROOT / 'notebooks/capstone_integral_colab.ipynb',
        'capstone_integral_entrenado.ipynb': trained,
        'capstone_bundle.zip': BASE / 'capstone_bundle.zip',
        'salidas_capstone.zip': BASE / 'workspace/salidas_capstone.zip',
        'validacion_temporal.json': ROOT / 'reports/validacion_temporal.json',
    }
    readme = '''# Lüga · Entrega Colab integral

1. Extraer este ZIP en una carpeta.
2. Abrir https://colab.research.google.com/ y elegir Archivo → Subir notebook.
3. Subir capstone_integral_colab.ipynb. Configurar CPU y ejecutar en orden.
4. Cuando lo pida la sección 1, subir capstone_bundle.zip.

REENTRENAR=False reutiliza predicciones externas auditadas y permite leer rápidamente.
REENTRENAR=True repite los 505 ajustes del benchmark; puede tardar varios minutos.

capstone_integral_entrenado.ipynb conserva la ejecución completa con resultados y figuras.
salidas_capstone.zip contiene tablas, figuras, modelo reajustado y manifiesto.
El Anexo A del notebook documenta la evaluación temporal histórica del HGB operativo.
validacion_temporal.json es su evidencia agregada original; el anexo registra su hash.
REENTRENAR no recalcula el anexo ni convierte esa evaluación en una prueba del ganador del benchmark.

El cuaderno usa precios publicados de venta en USD; no tasaciones ni precios de cierre.
El catálogo histórico es real y autorizado. Conservar sus condiciones de acceso al compartirlo.
No se incluyeron claves, contactos de anunciantes ni archivos .env.
La validación se hizo en kernels locales limpios; no se publicó un documento remoto en Google.
'''
    destination = BASE / 'Entrega_Colab_Precio_Entorno_CABA.zip'
    with ZipFile(destination, 'w', ZIP_DEFLATED) as z:
        for name, path in files.items():
            z.write(path, name)
        z.writestr('LEEME.md', readme)
    print(destination)
    print(f'{destination.stat().st_size / 1e6:.2f} MB · notebook, ejecución, datos/código y resultados')


if __name__ == '__main__':
    main()
