# Entrenamiento, evaluación e inferencia · 18/11/2026

El modelo seleccionado es **HistGradientBoostingRegressor**, entrenado desde cero sobre datos tabulares para estimar precio publicado por m² cubierto de departamentos en venta en USD. La comparación previa de seis familias lo favoreció en validación cruzada. Para este entregable se implementó un ajuste acotado, persistencia del modelo y de las transformaciones, inferencia local automática y resultados en el dashboard de Streamlit.

**Alcance de esta ficha:** describe el prototipo operativo con objetivo en escala original. La comparación principal de cinco familias para la defensa es el [benchmark auditado](../reports/benchmark-auditado/resultados.md), con otro preprocesamiento, atributos, objetivo logarítmico y validación anidada. Sus métricas no son intercambiables. Véanse la [matriz de experimentos](auditoria-estadistica.md) y la [memoria matemática](memoria-matematica.md).

Como análisis complementario se realizó el [ANOVA de precios entre barrios](anova-barrios.md), con Welch como prueba principal, ANOVA clásico como referencia y comparaciones por pares corregidas con Holm. Su pregunta es la diferencia de medias barriales; no reemplaza la evaluación de los cinco modelos.

## Evidencia y alcance

| Requisito | Implementación / evidencia |
| --- | --- |
| Elegir estrategia y entrenar | `precio_entorno/inferencia.py`: búsqueda de 3 configuraciones, 5 pliegues agrupados dentro de entrenamiento |
| Configuración, datos y supuestos | Este documento y `reports/evaluacion_inferencia.json`, con SHA-256 de todos los insumos y versión de scikit-learn |
| Evaluación y baseline | MAE, RMSE, R², proporción dentro de ±20 %, errores por barrio y comparación con mediana de comparables |
| Métrica de negocio | Minutos netos ahorrados por revisión; protocolo y objetivo de aceptación definidos abajo, todavía sin medición de cliente |
| Integración automática | `actualizar.py --modelo`, habilitado en `scripts/actualizar.cmd` cuando existe el modelo; CLI de inferencia sobre el CSV limpio del ETL; operación `inferencia` del Actor de Apify, sin entrenamiento (`precio_entorno/analytics/`) |
| Dashboard y costos | Sección de referencias en Streamlit, exportación CSV y presupuesto por escenario |

La interfaz web de búsqueda y el informe remoto de Looker Studio mantienen sus vistas actuales. Al 18/11 la integración era solo local. El 20/11 se sumó la operación `inferencia` al Actor `precio-entorno-analytics`: lee el modelo de un almacén de Apify y no entrena. Quedó subida a Apify y conectada a Make: el escenario «Pipeline Analytics» la corre después del EDA y escribe la pestaña `predicciones` de la planilla del dashboard ([pipeline-analytics.md](pipeline-analytics.md)). Looker Studio todavía no muestra esa pestaña. No se ejecutaron nuevas capturas de avisos.

## Datos, configuración y supuestos

Se usaron 3.806 avisos válidos de 48 barrios del dataset `data/processed/ampliado/modelo-pines-aproximados-poi-control/dataset_modelo.csv`, derivado del catálogo autorizado de noviembre de 2026. Se sumaron por ID antigüedad, cocheras y nueve indicadores de descripción desde cuatro archivos locales: `zonaprop-venta-20261108-edificio`, `inmobiliarias-20261109-edificio`, `zonaprop-venta-20261108-descripcion-completa` y `rasgos-inmobiliarias-20261115`, todos bajo `data/raw/`, archivo `avisos.json`. Los hashes completos están en el reporte agregado. Estos archivos y el modelo binario permanecen fuera de Git.

Variables: superficies cubierta y total, ambientes, coordenadas aproximadas, distancias a transporte, parques y hospitales, gastronomía y escuelas a 500 m, antigüedad, cocheras, nueve rasgos de descripción, barrio e inmobiliaria. No se usan precio, USD/m², identificador ni grupo como predictores. Los delitos registrados de enero–diciembre de 2025 permanecen como contexto del dataset y del flujo; no entran al predictor porque el análisis anterior no mostró mejora robusta frente al placebo. El radar editorial queda separado.

Se supone que los rasgos físicos asociados por ID siguen describiendo el inmueble de la captura original; se toman los últimos valores informados por campo. Esto puede introducir información posterior a la fecha del precio y debe evitarse en una evaluación temporal. Ausencia de mención en una descripción no prueba ausencia del rasgo. Los ceros de antigüedad pueden ser valores por defecto del portal. El catálogo es una muestra de publicación, sin ponderación para representar todas las propiedades de CABA; no acredita vigencia actual de enlaces.

Semilla 42; división agrupada: 3.048 observaciones para desarrollo y 758 para prueba (20 % aproximado). Los posibles duplicados entre fuentes comparten `grupo`; no hay grupos compartidos entre entrenamiento y prueba. La heurística de duplicados usa precio redondeado y puede omitir propiedades duplicadas o agrupar propiedades diferentes; se necesita un identificador físico independiente para una garantía más fuerte.

El preprocesamiento se aprende en cada pliegue: categorías ordinales con faltantes para valores nuevos y manejo nativo de faltantes numéricos en HGB. Se guarda el pipeline completo, evitando recodificar barrios según cada lote de inferencia. No se aplicó escalado, innecesario para árboles. Se exige ID, barrio, superficie cubierta y ambientes válidos; moneda y operación, cuando están presentes, deben ser USD y venta. Los CSV sin esas columnas requieren que quien los produce asegure ese contrato. Variables opcionales ausentes pasan a NaN y se cuentan por aviso.

Configuración fija: `loss=absolute_error`, `learning_rate=0.05`, `max_iter=300`, `early_stopping=False`, semilla 42. Se desactivó la parada temprana para evitar una partición interna aleatoria ajena a los grupos. Tres candidatos `(max_leaf_nodes, min_samples_leaf, l2_regularization)`: `(31,10,0)`, `(15,20,1)`, `(31,30,5)`. Selección por menor MAE medio en GroupKFold de 5 pliegues sobre las 3.048 observaciones de desarrollo. No se consultó la prueba durante esta búsqueda. No es una búsqueda exhaustiva ni un ajuste de un LLM.

## Resultados observados

MAE es la métrica principal: expresa el error absoluto medio en USD/m², en la misma unidad de la decisión de comparación. RMSE penaliza más los errores grandes. R² describe ajuste respecto de la media de prueba; no es una probabilidad de acierto.

Baseline: mediana de USD/m² del barrio y ambientes, con al menos cinco comparables de entrenamiento; respaldo en mediana del barrio y luego mediana global. Se calcula nuevamente dentro de cada pliegue, sin precios de prueba.

| Medida | HGB ajustado | Baseline |
| --- | ---: | ---: |
| MAE de entrenamiento (USD/m²) | 237,2 | — |
| MAE CV en desarrollo (USD/m²) | 406,7 ± 19,7 | 582,1 (media) |
| MAE de prueba (USD/m²) | 442,7 | 627,3 |
| RMSE de prueba (USD/m²) | 737,9 | 1.010,5 |
| R² de prueba | 0,689 | 0,416 |
| Referencias dentro de ±20 % del publicado | 70,2 % | 53,0 % |

Ganó `(31,10,0)`. Los otros candidatos dieron MAE CV de 420,9 y 410,1. La reducción del MAE de prueba frente al baseline es 29,4 %. La tasa dentro de ±20 % aumenta 17,2 puntos porcentuales. Ese umbral es una tolerancia analítica propuesta, no validada todavía con el cliente ni equivalente a exactitud de tasación.

La brecha entre MAE de entrenamiento y prueba es 205,5 USD/m²: hay sobreajuste y errores importantes en la cola. Ejemplos de errores medios por barrio: Puerto Madero 1.903,5 (n=14), Belgrano 1.027,0 (n=30), Colegiales 946,0 (n=11); Almagro 321,8 (n=51), Caballito 454,0 (n=30). Las muestras pequeñas no permiten conclusiones estables por barrio. Los errores individuales de prueba quedan en `data/processed/inferencia/errores_prueba.csv`, fuera de Git.

**Disponibilidad de variables en operación.** Repitiendo la prueba con solo superficie, ambientes, coordenadas, barrio e inmobiliaria disponibles en el importador, el MAE sube a **616,0 USD/m²**, RMSE 1.004,6 y R² 0,423. La ventaja sobre el baseline queda en apenas 1,8 %. No se debe atribuir el MAE de 442,7 a nuevos avisos sin enriquecimiento. El dashboard informa esta diferencia y la cantidad de variables ausentes. Para sostener la mejora completa hace falta enriquecer los avisos nuevos con el mismo contrato y evaluar nuevamente.

La prueba histórica fue usada en comparaciones previas del proyecto, por lo que no es una prueba final independiente. Esta CV también es una estimación de selección de hiperparámetros, sin CV anidada. No se demostró generalización temporal, a alquileres, otras monedas, otras ciudades o fuentes nuevas. La próxima evaluación debe congelar modelo y reglas y utilizar una captura posterior, con rasgos disponibles a su fecha y grupos de inmuebles separados. No se estimaron intervalos de predicción; el MAE no sirve como intervalo individual ni como descuento recomendado.

## Métrica de negocio y objetivo del cliente

Objetivo de la inmobiliaria: reducir el tiempo necesario para revisar candidatos relevantes de una búsqueda guardada. Métrica principal: **minutos netos ahorrados por revisión = tiempo del método habitual − tiempo con app y referencias**, incluyendo descarte de errores y comprobación del aviso. Medir ambos recorridos sobre las mismas 5–10 búsquedas, alternando su orden y registrando versión de modelo, faltantes, fecha y utilidad del candidato. No guardar contactos de anunciantes.

Como control de calidad, medir candidatos relevantes encontrados / candidatos relevantes del conjunto revisado por la inmobiliaria, y comparar con el método habitual; una referencia de precio nunca debe excluir automáticamente un aviso compatible. Separar la utilidad de las alertas y la utilidad incremental del predictor para no atribuir al ML todo el ahorro del flujo.

Hipótesis de aceptación comercial: con 40 revisiones mensuales y costo del tiempo de USD 12/h, ahorrar al menos 5 minutos netos por revisión equivale a USD 40/mes; cubre una cuota propuesta de USD 39, con margen mínimo para el cliente. Un objetivo más exigente de 10 minutos representa USD 80/mes y USD 41 de beneficio neto de cuota. Estos son escenarios, **no resultados medidos**. El 70,2 % dentro de ±20 % es un indicador técnico de utilidad potencial; el ahorro real y la aceptación del cliente siguen pendientes del piloto.

## Operación y reproducción

Desde la raíz del proyecto, usando el Python con `requirements.txt` instalado:

```powershell
$env:OMP_NUM_THREADS='2'
python -m precio_entorno.inferencia entrenar --edificio data/raw/zonaprop-venta-20261108-edificio/avisos.json data/raw/inmobiliarias-20261109-edificio/avisos.json data/raw/zonaprop-venta-20261108-descripcion-completa/avisos.json data/raw/rasgos-inmobiliarias-20261115/avisos.json
python -m precio_entorno.pipeline_analytics inferencia data/processed/pipeline/dataset_limpio.csv
python -m precio_entorno.apify_analytics subir-modelo --account 2
python -m streamlit run app.py
python -m unittest discover -s tests -v
```

El primer comando ajusta, evalúa y después reajusta la configuración elegida con los 3.806 avisos para operación. Guarda `modelo.joblib`, `evaluacion.json`, `errores_prueba.csv` y `predicciones.csv` en `data/processed/inferencia/`. Las predicciones de ese mismo corte son resultados operativos sobre datos ya vistos, no evidencia adicional de generalización. La evaluación reportada corresponde al modelo ajustado solo con desarrollo, no al reajuste final.

El segundo comando carga el modelo, sin entrenarlo, y genera **3.806 referencias** desde el CSV limpio existente. Escribe `data/processed/pipeline/predicciones.csv` y `sheets_predicciones_body.json`. No llama a servicios remotos ni envía el cuerpo a Sheets. Para un dataset enriquecido con el esquema del modelo se puede usar `python -m precio_entorno.inferencia predecir --dataset RUTA.csv --salida CARPETA`.

`scripts/actualizar.cmd`, utilizado por la tarea de Windows existente, añade `--modelo data/processed/inferencia` a la actualización de venta cuando encuentra `evaluacion.json`. Tras una importación exitosa, genera `predicciones.csv` para los avisos de venta activos en USD en la carpeta de la captura y registra estado y versión en el historial. Si falla la inferencia, registra su error sin deshacer importaciones ni alertas; Make sigue recibiendo el estado del flujo de captura/importación. Revisar el campo `inferencia` y el log local para controlar ese fallo. La captura programada no se ejecutó durante esta implementación.

En Streamlit, elegir **Comprar → Datos reales**. La sección «Referencia de precio publicado» muestra métricas, fecha, versión, predicciones para el barrio seleccionado, faltantes y descarga CSV. Demo y alquileres no reciben referencias de este modelo. Se recalcula con el modelo guardado al consultar, sin reentrenar. Se verifican SHA-256 y versión de scikit-learn antes de deserializar; solo se cargan artefactos locales propios. El binario se regenera al cambiar versiones de dependencias.

## Estimación de costos

Separar el costo incremental de inferencia del gasto previo de adquisición. En esta corrida se reutilizaron archivos existentes: **USD 0 de nuevo consumo facturado en APIs o extracciones**. La búsqueda, evaluación y reajuste final tardaron 28,6 s con dos hilos configurados; ese tiempo depende del equipo y de su carga. No se midió memoria máxima, electricidad, amortización ni tiempo humano efectivo de desarrollo.

| Componente | Base de cálculo | Escenario mensual |
| --- | --- | ---: |
| Entrenamiento local | 1 reajuste mensual, equipo existente | USD 0 de servicio cloud; equipo/energía sin medir |
| Inferencia local y Streamlit | 12 corridas/mes, hasta ~4.000 avisos/corrida, equipo existente | USD 0 de alojamiento contratado; disponibilidad depende del equipo |
| Apify Analytics existente | Costo histórico documentado: ETL 0,003 + EDA 0,0003 por corrida; 12 corridas | USD 0,0396 de consumo estimado, sin extracción ni inferencia cloud |
| Make | 7 acciones/corrida del flujo existente × 12 | 84 créditos estimados, más búsquedas y alertas; USD 0 si cabe en Free y su límite de escenarios |
| Alojamiento cloud futuro | Reserva presupuestaria, sin proveedor contratado | USD 5–10 (supuesto, no cotización) |
| Operación y soporte | 40 minutos/mes × USD 12/h | USD 8 (supuesto) |
| Mantenimiento de conectores | 30 minutos/mes × USD 12/h | USD 6 (supuesto) |

Total del escenario local: aproximadamente **USD 14,04/mes**, excluyendo equipo, electricidad, captura nueva, comisiones e impuestos. Con reserva de alojamiento: **USD 19,04–24,04/mes**, antes de un eventual plan pago de Make y sin inferencia en Apify. A USD 39/mes, el margen de contribución ilustrativo sería 64 % local o 38–51 % con esa reserva. No es un margen observado.

Tarifas consultadas el 18/11/2026: [Make](https://www.make.com/en/pricing) anuncia Free con 1.000 créditos mensuales; el precio y período de facturación de Core deben confirmarse al contratar. [Apify](https://apify.com/pricing) ofrece crédito de Free de USD 5; compute, transferencia, almacenamiento y cargos de cada Actor pueden sumarse. No considerar el crédito gratuito como costo económico nulo. No hay estimación medida todavía de inferencia desplegada en Apify. El consumo histórico de Analytics proviene de `docs/pipeline-analytics.md`, no es una garantía de tarifa o consumo futuro.

Presupuesto inicial de desarrollo para planificar el entregable (sin imputarlo como horas observadas): 4 h de modelado y evaluación + 4 h de integración y dashboard + 2 h de documentación y QA, a USD 12/h de referencia = **USD 120**. Reemplazar horas y tarifa por el registro del equipo. El presupuesto de extracción del proyecto conserva su límite de USD 25 y USD 5 por cuenta; no se compromete ninguna nueva extracción con esta estimación.

Para cerrar el despliegue cloud quedan: empaquetar el artefacto y dependencias del Actor, medir su costo y memoria, agregar inferencia al escenario de Make y conectar la pestaña de predicciones en Looker Studio. Para validar el producto quedan: muestra futura independiente y piloto de ahorro de tiempo con el cliente.

## Verificación realizada

`python -m unittest discover -s tests -v`: **251 pruebas aprobadas**. Incluyen separación de grupos, persistencia y detección de artefactos alterados, categorías nuevas, variables opcionales ausentes, rechazo de entradas inválidas, estabilidad de codificación entre lotes, integración del CSV limpio y conservación de alertas ante fallo de inferencia. Las pruebas usan datos ficticios separados de los insumos del entrenamiento real.

Streamlit AppTest ejecutó la app, cambió a Datos reales y comprobó la sección de referencias y sus tres métricas sin excepciones ni mensajes de error. La CLI generó 3.806 filas de predicciones desde el CSV limpio con el modelo persistido. No se probó el disparo real de la tarea de Windows ni un despliegue remoto.
