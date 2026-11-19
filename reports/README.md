# Reproducir el benchmark inmobiliario

Para una exposición completa con teoría intercalada y visualizaciones, usar el [Colab integral](../notebooks/capstone_integral_colab.ipynb) y su [guía de uso](../docs/colab-integral.md).

La entrega actual incluye una [memoria matemática](../docs/memoria-matematica.md) y una [auditoría de protocolos](../docs/auditoria-estadistica.md). Para reproducir la comparación de cinco familias con baselines simples y diagnósticos:

```powershell
python -m precio_entorno.auditoria_estadistica
python scripts/graficar_auditoria.py
```

Los [resultados auditados](benchmark-auditado/resultados.md), ajustes, métricas por subgrupo y manifiesto quedan en `reports/benchmark-auditado/`. Las predicciones individuales quedan fuera de Git en `data/processed/auditoria-estadistica/`. Los comandos siguientes reproducen el notebook histórico, que conserva su propio alcance.

Desde la raíz del proyecto, con Python y las dependencias de `requirements.txt`, abrí [benchmark_modelos.ipynb](../notebooks/benchmark_modelos.ipynb) en un entorno Jupyter con el kernel de ese Python. El notebook usa SciPy y threadpoolctl, dependencias de scikit-learn. Para ejecutarlo por consola, el entorno necesita además `nbformat`, `nbclient` e `ipykernel`.

El benchmark lee `data/processed/eda-colab/eda_bundle.zip` y muestra su SHA-256 junto con la versión de scikit-learn. Si falta el bundle, preparalo desde los insumos locales autorizados siguiendo la [documentación del EDA](../README.md) antes de ejecutar. No se requieren extracciones.

```powershell
python -c "import nbformat; from nbclient import NotebookClient; from pathlib import Path; n=nbformat.read('notebooks/benchmark_modelos.ipynb',as_version=4); nbformat.validate(n); NotebookClient(n,timeout=900,kernel_name='python3').execute(); dst=Path('data/processed/eda-colab/salidas-benchmark'); dst.mkdir(parents=True,exist_ok=True); nbformat.write(n,dst/'benchmark_ejecutado.ipynb')"
python -m unittest discover -s tests -v
```

La ejecución ajusta hasta 505 modelos en un hilo y puede tardar varios minutos. En la copia ejecutada quedan las métricas por muestra y subgrupo, parámetros elegidos, tablas de ranking y explicaciones por fold. [Auditoría metodológica](auditoria_metodologica.md)
