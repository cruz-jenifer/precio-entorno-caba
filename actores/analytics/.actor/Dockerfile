# Actor de Analytics (ETL, EDA e inferencia). Contexto de construcción: la raíz de los archivos subidos.
FROM apify/actor-python:3.13

COPY .actor/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Solo los módulos que usa el Actor. Nada de entrenamiento (inferencia.py, modelo.py,
# comparar_modelos.py), ni datos, ni el .env. El modelo entrenado se lee del almacén
# con nombre «precio-entorno-modelo».
COPY precio_entorno/__init__.py precio_entorno/importing.py precio_entorno/descripcion.py \
     precio_entorno/eda_delitos.py ./precio_entorno/
COPY precio_entorno/analytics ./precio_entorno/analytics

ENV PYTHONUTF8=1
CMD ["python", "-m", "precio_entorno.analytics.main"]
