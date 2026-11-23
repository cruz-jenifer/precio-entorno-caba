# Actor de Analytics (ETL, EDA e inferencia). Contexto de construcción: la raíz de los archivos subidos.
FROM apify/actor-python:3.13

COPY .actor/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Solo los módulos que usa el Actor. Nada de entrenamiento (inferencia.py, modelo.py,
# comparar_modelos.py), ni datos crudos, ni el .env.
COPY precio_entorno/__init__.py precio_entorno/importing.py precio_entorno/descripcion.py \
     precio_entorno/eda_delitos.py ./precio_entorno/
COPY precio_entorno/analytics ./precio_entorno/analytics

# Artefactos ya hechos fuera del Actor: el modelo entrenado y el resumen de delitos por barrio.
# El Actor los lee de su carpeta; no los crea, no los entrena y no los descarga.
COPY modelo ./modelo
COPY referencias ./referencias

ENV PYTHONUTF8=1
CMD ["python", "-m", "precio_entorno.analytics.main"]
