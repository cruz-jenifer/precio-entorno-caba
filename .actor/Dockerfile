# Actor de alertas. Contexto de construcción: la raíz del repositorio (ver .dockerignore).
FROM apify/actor-python:3.13

COPY .actor/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Solo el paquete: ni datos, ni notebooks, ni el .env.
COPY precio_entorno ./precio_entorno

ENV PYTHONUTF8=1
CMD ["python", "-m", "precio_entorno.actor_main"]
