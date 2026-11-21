# Actor de alertas. Contexto de construcción: la raíz del repositorio (ver .dockerignore).
FROM apify/actor-python:3.13

COPY .actor/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Solo los módulos que usa el Actor: ni entrenamiento, ni datos, ni notebooks, ni el .env.
COPY precio_entorno/__init__.py precio_entorno/actor_main.py precio_entorno/actor_alertas.py \
     precio_entorno/inmobiliarias.py precio_entorno/robots.py precio_entorno/importing.py \
     precio_entorno/descripcion.py precio_entorno/matching.py precio_entorno/make_webhook.py \
     ./precio_entorno/

ENV PYTHONUTF8=1
CMD ["python", "-m", "precio_entorno.actor_main"]
