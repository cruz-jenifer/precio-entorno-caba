# Actor de Analytics. Contexto de construcción: la raíz de los archivos subidos.
FROM apify/actor-python:3.13

COPY .actor/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Solo los módulos que usa el Actor: ni datos, ni el .env.
COPY precio_entorno ./precio_entorno

ENV PYTHONUTF8=1
CMD ["python", "-m", "precio_entorno.actor_analytics"]
