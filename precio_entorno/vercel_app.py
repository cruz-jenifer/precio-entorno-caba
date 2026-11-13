"""Entrada de la interfaz web en Vercel (`[tool.vercel] entrypoint`).

En Vercel el disco es de solo lectura salvo /tmp. Al arrancar, cada instancia copia las bases reales a /tmp y
las abre desde ahí; la demo se crea también en /tmp. Una búsqueda guardada en Vercel dura lo que dura la
instancia: la base que cuenta sigue siendo la local, que actualiza `actualizar.py`. El alta con mail se manda
a Make igual que en local, así que el aviso por correo no depende de esa copia.

La carpeta que se despliega la arma `scripts/preparar_vercel.py`.
"""

import os
import shutil
from pathlib import Path

TMP = Path(os.environ.get('PRECIO_ENTORNO_TMP', '/tmp/precio-entorno'))
# Matplotlib (solo se usa matplotlib.path) necesita una carpeta de configuración con escritura.
os.environ.setdefault('MPLCONFIGDIR', str(TMP / 'matplotlib'))

from .api import create_app  # noqa: E402 - después de fijar MPLCONFIGDIR
from .bases import ROOT  # noqa: E402

BASES = ('real.sqlite3', 'real-alquiler.sqlite3')


def writable_bases(source=ROOT / 'data/local', target=TMP):
    """Copia a `target` las bases que todavía no están ahí y devuelve la ruta de la base real de venta."""
    target.mkdir(parents=True, exist_ok=True)
    for name in BASES:
        if (source / name).exists() and not (target / name).exists():
            shutil.copyfile(source / name, target / name)
    return target / 'real.sqlite3'


app = create_app(demo_path=TMP / 'demo.sqlite3', real_path=writable_bases())
