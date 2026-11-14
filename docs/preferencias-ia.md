# Piloto de interpretación de preferencias

El buscador oculta «Describí tu búsqueda» de forma predeterminada. El intérprete propone filtros para revisión y el botón Aplicar no crea alertas.

Para evaluar reglas sin red:

```powershell
python -m precio_entorno.evaluar_preferencias --split desarrollo
python -m precio_entorno.evaluar_preferencias --split prueba
python -m unittest discover -s tests -v
```

El conjunto contiene 120 consultas sintéticas con etiquetas de referencia: 40 de desarrollo y 80 de prueba, con familias de frases separadas. Revisar las etiquetas con el equipo antes de medir el modelo. La métrica de dudas penaliza tanto omisiones como falsas alarmas. Comparar la exactitud, las dudas, las condiciones detectadas y los cambios silenciosos. Para habilitar el piloto se exige 95 % en campos y dudas, cero cambios silenciosos de moneda u operación y mejora sobre reglas.

La evaluación facturable se habilita únicamente tras autorizar un monto y verificar la disponibilidad, tarifas y contrato de GPT-6 Luna en la documentación oficial. Revisar la reserva del código si cambió la tarifa. Configurar `OPENAI_API_KEY` mediante el entorno del proceso, `PRECIO_ENTORNO_IA_TOPE_USD` con el monto autorizado y `PRECIO_ENTORNO_IA=1`. Agregar `--modelo` ejecuta las consultas del conjunto seleccionado a través del mismo control de presupuesto que la API.

El tope incluye evaluaciones y uso de la interfaz, y es acumulativo en `data/local/preferencias-inferencia.sqlite3`. Los fallos sin consumo verificable mantienen la reserva. Conservar ese archivo al reiniciar o actualizar. La reserva usa la tarifa Standard sin herramientas y redondea hacia arriba. La API solicita `store:false`; el proveedor puede conservar datos de monitoreo según sus controles. El texto se depura y no se persiste en el proyecto.

La migración local de búsquedas se ejecuta al abrir cada base. Las anteriores conservan IDs, alertas y cantidad exacta de ambientes. Para verificación manual, usar escritorio y móvil, revisar una propuesta, cancelar, volver a aplicar y comprobar que solo el botón Crear alerta guarda una búsqueda.
