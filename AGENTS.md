# Instrucciones del proyecto

- Este proyecto es independiente de Humo en la temporada. Limitar los cambios a esta carpeta.
- El flujo del producto es preferencias → comparación de barrios → búsqueda guardada → alerta por aviso nuevo.
- El análisis del capstone usa dos fuentes: un catálogo autorizado de avisos vigentes y el Mapa del Delito de CABA. Apify y Make son herramientas del flujo.
- Mantener separados los datos ficticios de los reales. Presentar precios de publicación, no tasaciones ni precios de cierre. Mostrar delitos registrados como contexto, con su período y unidad geográfica.
- No ejecutar extracciones pagas sin un tope explícito y una fuente con acceso autorizado. Piloto: hasta 50 avisos de Caballito y Almagro, hasta USD 5 en una sola cuenta de Apify. Presupuesto total de extracción: hasta USD 25. Se pueden usar varias cuentas de Apify, cada una con un tope de USD 5.
- Nunca registrar claves, contactos de anunciantes ni archivos `.env` en Git.
- Verificar con `python -m unittest discover -s tests -v`.
- La interfaz web arranca con `python -m precio_entorno.api` y se abre en http://127.0.0.1:8000. Necesita las capas de `data/processed/entorno/`, que se generan con `python -m precio_entorno.entorno`.
- La app de Streamlit, para importar datos y probar la actualización, arranca con `python -m streamlit run app.py`.
