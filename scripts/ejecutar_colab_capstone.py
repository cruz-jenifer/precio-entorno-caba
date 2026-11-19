"""Ejecuta el Colab integral en un kernel limpio y guarda sus salidas."""

import argparse
from pathlib import Path

import nbformat
from nbclient import NotebookClient

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reentrenar', action='store_true')
    args = parser.parse_args()
    source = ROOT / 'notebooks/capstone_integral_colab.ipynb'
    nb = nbformat.read(source, as_version=4)
    nbformat.validate(nb)
    if args.reentrenar:
        cell = next(c for c in nb.cells if c['id'] == 'configuracion')
        cell.source = cell.source.replace('REENTRENAR = False', 'REENTRENAR = True', 1)
    suffix = 'entrenado' if args.reentrenar else 'lectura'
    destination = ROOT / f'data/processed/colab-capstone/capstone_integral_{suffix}.ipynb'
    destination.parent.mkdir(parents=True, exist_ok=True)

    def progress(cell, cell_index, **kwargs):
        if cell.cell_type == 'code':
            print(f'[{cell_index + 1}/{len(nb.cells)}] {cell.id}', flush=True)

    client = NotebookClient(nb, timeout=1200, kernel_name='python3', allow_errors=False,
                            resources={'metadata': {'path': str(ROOT)}}, on_cell_start=progress)
    try:
        client.execute()
    finally:
        nbformat.write(nb, destination)
        print('Notebook con salidas:', destination, flush=True)
    errors = [o for c in nb.cells if c.cell_type == 'code' for o in c.outputs if o.output_type == 'error']
    if errors:
        raise RuntimeError(f'La ejecución contiene {len(errors)} errores.')
    print('Ejecución completa sin errores.', flush=True)


if __name__ == '__main__':
    main()
