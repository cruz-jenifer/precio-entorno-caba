"""Actor «precio-entorno-analytics» de Apify: ETL, EDA e inferencia, sin entrenamiento.

`main.py` solo tiene la entrada y salida de Apify. La lógica está en un módulo por etapa:

- `ETL.py`: avisos crudos + Mapa del Delito → CSV limpio y reporte de calidad.
- `preprocessing.py`: lectura y escritura del CSV limpio, y su paso a las variables del modelo.
- `EDA.py`: tablas del dashboard a partir del CSV limpio.
- `inference.py`: carga del modelo ya entrenado (con control de huella) y predicción.
- `tooling_business.py`: lectura de negocio de las referencias y cuerpos para Google Sheets.

El entrenamiento vive en `precio_entorno/inferencia.py` y nunca entra en el Actor.
"""
