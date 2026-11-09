# Plan de entrega · Precio y Entorno CABA

Actualizado el 9 de noviembre de 2026. Las fechas y los roles vienen del cronograma de alumnos. Las clases aportan los requisitos técnicos y comerciales. El capítulo 11 orienta el método de trabajo. Los responsables nominales, el feedback de Diana y los acuerdos comerciales se completan con evidencia del equipo.

## Propuesta para Diana

**Rubro.** Intermediación inmobiliaria de departamentos en venta en CABA. Proponemos que Diana represente a una intermediaria que gestiona búsquedas de varios compradores. Esta adaptación queda por contrastar con su ficha y el feedback del 5/11.

**Problema.** El equipo revisa avisos dispersos y puede enterarse tarde de una opción compatible. Necesita decidir en qué barrios concentrar la búsqueda y qué avisos nuevos revisar primero.

**Flujo.** Preferencias → comparación de barrios → búsqueda guardada → alerta por aviso nuevo. El dashboard analítico agrega una vista de oferta, precio publicado por m² y hechos registrados por período y unidad geográfica. Para la entrega, usar venta en USD. Alquiler y las capas adicionales de la app quedan como extensiones.

**Métrica de negocio.** Mediana de los minutos ahorrados por búsqueda frente al método habitual. Medir además opciones relevantes encontradas, utilidad de alertas y tiempo operativo. Usar el [protocolo de validación](validacion-inmobiliaria.md). El MAE en USD/m² mide el error predictivo y se reporta por separado.

**Guion del pitch inicial.** «Somos [equipo]. Ayudamos a intermediarias inmobiliarias a encontrar antes departamentos que encajan con sus compradores. Reunimos avisos vigentes autorizados, mostramos qué barrios tienen más coincidencias para cada presupuesto y avisamos cuando aparece una opción nueva. Vamos a medir cuántos minutos ahorra una búsqueda frente al método habitual».

## Calendario y criterios de cierre

| Fecha | Responsable por rol | Trabajo y evidencia de cierre |
| --- | --- | --- |
| 3/11 · recuperar registro | Equipo + BIZ | Adjuntar ensayo corregido y reflexión individual de la clase 42. Registrar formación del equipo, evolución del problema, reparto, contribuciones y aprendizajes. Recuperar al menos cinco ideas evaluadas, selección del rubro, análisis competitivo, fuentes tentativas y alcance inicial. |
| 5/11 · recuperar registro | Líder + equipo | Recuperar ficha de Diana, pitch de dos minutos y su interés, duda y condición. Completar el diagrama inicial de entradas, procesos y salidas y registrar el estado de los primeros tres nodos de Make con Apify. |
| 10/11 · asincrónico | DS + SE + BIZ | Entregar correlaciones lineales y no lineales, métricas justificadas, diseño ETL y tratamiento de faltantes, duplicados y normalización. BIZ ensaya filtros, lectura de gráficos y decisiones del dashboard. |
| 12/11 · Producto 1 | Equipo | Demostrar Analytics con ETL, EDA, automatización, dashboard, diccionario y manejo de errores. Mostrar una decisión comercial derivada de los datos. La gerente lee el mensaje de Diana. Registrar sus tres pedidos, clasificación, justificación, concesiones y alcance acordado para Producto 2. |
| 17/11 · diseño de Inference | DS + SE + BIZ | Justificar objetivo, variables, transformaciones, enfoque y sesgos. Registrar el feedback técnico de Samsung sobre reglas de negocio, configuración, permisos y protección de datos, con acciones y responsables. |
| 20/11 · Producto 2 | Equipo | Mostrar entrenamiento reproducible, baseline, error, generalización y limitaciones. Guardar el modelo y sus transformaciones, correr inferencia con avisos nuevos sin reentrenar y mostrar el resultado en Insights Dashboard. Vincular una métrica de negocio con la decisión y estimar costos de herramientas, infraestructura y operación. |
| 24/11 · defensa | Equipo + líder | Preparar seis minutos de exposición y dos de preguntas. Mostrar ambos productos, decisiones habilitadas, pedidos del 12/11, ROI, costos y recuperación de inversión. Demostrar experimentación, entrenamiento y evaluación en Google Colab, el flujo de Make de punta a punta y la extracción documentada en Apify. Entregar el repositorio GitHub con README, manual breve, resultados y limitaciones. Registrar nota 0–10, justificación, decisión comercial, condiciones y próximo paso. |

**Roles.** DS responde por datos, ETL analítico, EDA y modelo. SE responde por conectores, contratos, Actor, automatización, pruebas y despliegue. BIZ responde por mercado, alcance, dashboard, métricas, presupuesto y validación. Asignar nombres y suplentes. El equipo mantiene su tablero y calendario, y el líder canaliza la comunicación equipo → líder → gerente → Diana.

**Seguimiento.** Mantener un registro visible de decisiones, riesgos, problemas, acuerdos y cambios. El parte semanal debe incluir tareas completadas, trabajo en curso, trabas, riesgos y próximos pasos. Cada quince días el líder presenta al gerente avances, cambios de planificación y acciones correctivas. Confirmar la frecuencia operativa con la docente, ya que la lámina de seguimiento también muestra cadencias de dos y tres actualizaciones por semana. Registrar cada interacción de Diana en la pestaña «Seguimiento cliente».

## Matriz de evidencias y pendientes

| Requisito | Evidencia existente | Para cerrar |
| --- | --- | --- |
| Problema, usuario, alcance y mercado | [Alcance](alcance.md), [protocolo](validacion-inmobiliaria.md) y [Fase 1 · mercado y competitividad](fase-1-mercado-competitividad.md) | Completar Guía Business y Alcance servicio con la ficha. El mapa de competidores y el benchmark fechado están en la Fase 1. Falta hacer la entrevista y la prueba con una inmobiliaria y cargar sus resultados. Documentar cinco ideas y motivos de selección o descarte. |
| Dos fuentes, calidad y muestra analítica | [Datos](datos.md), [EDA avisos](eda-avisos.md), [EDA delitos](eda-delitos.md) | Congelar un catálogo autorizado y una edición del Mapa del Delito. Adjuntar evidencia de permiso, captura, cobertura, conteos y criterios de selección. Cumplir el alcance local de 700–2.000 filas y unas diez variables interpretables por dataset analítico. El volumen bruto y la base operativa se reportan por separado. |
| ETL y reglas | [Arquitectura](arquitectura.md), [importación](../precio_entorno/importing.py) | Entregar diagrama, diccionario con tipo, unidad, origen y nulos, y corrida con filas leídas, aceptadas, descartadas y duplicadas. Mostrar entrada inválida y reimportación sin duplicar alertas. |
| Correlaciones, EDA y Analytics Dashboard | [Notebook](../notebooks/eda_oportunidades.ipynb), [web](ui.md) e informes EDA | El notebook ya usa Spearman. Para el 10/11, añadir Pearson y dispersión con ajuste lineal y curva suavizada para detectar patrones no monotónicos, con unidad, n y faltantes. Separar análisis por aviso y por barrio. Para el 12/11, mostrar gráficos, filtros y hallazgos del mismo corte analítico. |
| Make + Apify para Analytics | [Apify y Make](arquitectura.md#8-make) | La arquitectura documenta Apify para captura y Make para alertas. Demostrar la orquestación de Analytics en el flujo de entrega con registro de ejecución, salida y fallo controlado. La automatización de alertas tiene su propia prueba. |
| Modelado y evaluación | [Modelo](modelo.md), [pruebas](../tests/test_modelo.py) | Congelar versión de datos y comparar mediana por comparables, regresor base y regresor con delitos en la misma partición por aviso. Reportar MAE en prueba y cinco pliegues, placebo y alcance de generalización. Documentar la sensibilidad por radio aparte del cruce principal por barrio. |
| Inference e Insights Dashboard | [Pipeline de evaluación](../precio_entorno/modelo.py) | Persistir modelo y transformaciones versionados, validar esquema y aplicar a avisos nuevos sin volver a entrenar. Mostrar referencia estimada de precio publicado por m² y error de evaluación en una vista de resultados con muestra y fecha. Usar el modelo base si la evaluación final no muestra una mejora robusta con delitos. |
| Actor comercial | Clases 42–44, págs. 10–12 | Un Actor con dos operaciones. GET de documentación y POST con `operation=analytics` o `operation=inference`. Documentar parámetros, ejemplos, esquemas, errores, precios y límites. Medir CU, memoria, duración y costo por operación. Preparar publicación en Apify Store y registrar difusión y feedback. |
| Validación, propuesta comercial y cierre | [Protocolo](validacion-inmobiliaria.md) y [registro](plantillas/registro-validacion.csv) | Completar presupuesto por etapa, operación mensual, responsabilidades, exclusiones, uso de datos y código. Contrastar disposición a pagar y cálculo de ROI con la ficha. Confirmar con la docente si el pago del 12/11 corresponde a Producto 1 o a un adelanto del Producto 2. |

## Contratos para las demos

| Operación | Entrada | Proceso | Salida y prueba |
| --- | --- | --- | --- |
| Analytics | Exportación autorizada de avisos vigentes y corte del Mapa del Delito, ambos con origen y fecha | Adaptar campos, validar precio y superficie, deduplicar, normalizar barrios, calcular USD/m² y preparar agregados con cobertura y período | Dataset limpio, reporte de calidad y dashboard con oferta, precio por m² y contexto por barrio. Repetir un lote y probar campos inválidos o faltantes. |
| Inference | Avisos nuevos con esquema validado y versión del modelo | Aplicar las transformaciones guardadas y predecir con el modelo cargado | Referencia de precio publicado en USD/m² y versión del modelo. Probar una entrada nueva y una inválida, y verificar que la corrida funciona con el modelo guardado. |
| Recorrido de producto | Preferencias y lote incremental de avisos | Comparar barrios, guardar una búsqueda, importar y cruzar coincidencias | Una alerta por aviso nuevo compatible y búsqueda. Reimportar el lote para mostrar que no se repite. Identificar los datos ficticios durante la prueba. |

Aplicar el capítulo 11 como secuencia CRISP-DM. Partir de la decisión de negocio, comprender datos con el EDA, preparar contratos y muestras, modelar, evaluar y desplegar. Usar el protocolo de inmobiliaria para probar el prototipo e iterar. Para cada tramo nuevo, definir entrada, salida y casos de prueba antes de implementar. Validación, monedas, deduplicación y alertas son reglas explícitas. El modelo estima una referencia de publicación. Los delitos registrados llevan período y unidad geográfica y se interpretan como contexto. Una asociación predictiva no establece causalidad.

## Presupuesto y defensa comercial

- Separar costo observado de Apify, horas DS/SE/BIZ, operación recurrente de Make e infraestructura. Reemplazar los ejemplos de la planilla por horas y tarifas justificadas. Medir costo por corrida de cada operación antes de fijar precio en Store. Margen bruto = (precio − costo) / precio.
- ROI del cliente con horizonte declarado = (beneficios del período − costos del período) / costos del período. Beneficio bruto mensual = búsquedas mensuales × minutos ahorrados por búsqueda × costo por minuto. Recuperación en meses = inversión inicial / (beneficio bruto mensual − operación mensual), si el beneficio neto mensual es positivo. Separar observaciones, datos de la ficha y supuestos.
- Para el mensaje del 12/11, registrar pedido literal, categoría imprescindible/deseable/fuera de alcance, límite de datos/plazo/costo y ajuste ofrecido. Para la defensa, preparar respuestas sobre qué se pierde al dejar el servicio, costo mensual y recuperación, confiabilidad ante cambios de fuente y qué información competitiva está disponible.
- Registrar la nota individual de Diana y el acuerdo según el cronograma: 9–10 piloto, 7–8 con condiciones, 0–6 sin contrato por el momento. Calcular NPS agregado solo cuando estén las respuestas correspondientes.
- Trabajar con capturas autorizadas ya disponibles para preparar la entrega. Si hace falta otra extracción, aplicar los topes del proyecto: piloto de hasta 50 avisos en Caballito y Almagro, USD 5 por cuenta y USD 25 totales. Mantener datos ficticios separados, excluir contactos y proteger credenciales.

## Material de referencia

- `capstone_project_cronograma_alumnos.xlsx` · Resumen, Roles, Cronograma, Guía Business, Alcance servicio, Presupuesto, Guion pitch y Seguimiento cliente.
- `Capstone Project_Clases 42 a 47.pdf` · El archivo adjunto contiene las clases 42 a 44. Las páginas 5–9 cubren reflexión y equipo, 10–15 los productos y el negocio, 16–22 el diseño por entradas y salidas y 23–25 las expectativas del cliente. Para los hitos posteriores se usó el cronograma.
- `SIC_AI_Cap_11_Starting_AI_Project_.pdf` · Marco de planificación, CRISP-DM y pensamiento de diseño.
