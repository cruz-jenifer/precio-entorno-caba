# Auditoría estadística del capstone

Aplicación de la skill local `auditoria-estadistica-capstone`, 18/11/2026. El objetivo de esta revisión es comprobar coherencia entre preguntas, fundamentos, implementaciones y evidencia; sus conclusiones no son una certificación de representatividad ni de utilidad comercial.

La [memoria matemática](memoria-matematica.md) desarrolla las ecuaciones. La [corrida auditada](../reports/benchmark-auditado/resultados.md) conserva los resultados reproducidos. El código está en `precio_entorno/benchmark_inmobiliario.py` y el ejecutor en `precio_entorno/auditoria_estadistica.py`.

## Matriz de experimentos

| Protocolo | Pregunta / objetivo | Datos y variables | Evaluación | Uso en la entrega |
| --- | --- | --- | --- | --- |
| **Benchmark de cinco familias** | Comparar Ridge, KNN, Random Forest, HGB y MLP para USD/m² | Bundle EDA; 3.806 filas, 3.582 grupos; base de 12 variables, ampliación con edad y estado; ajuste de log(USD/m²) | Cinco folds externos agrupados; búsqueda interna de tres folds; MAE seleccionado en escala USD/m² | **Comparación principal** de cinco modelos |
| Comparación histórica de seis | Comparar lineal, árbol, RF, HGB, MLP y ElasticNet | CSV del modelo; rasgos de edificio/descripción según corrida; objetivo en escala original | Parámetros fijos; prueba 80/20 y CV sobre todo el catálogo | Antecedente; no mezclar sus tablas con las del benchmark anidado |
| Prototipo de inferencia | Persistir y aplicar una referencia HGB a nuevos avisos | CSV del modelo más edificio y nueve rasgos; objetivo USD/m² con pérdida absoluta | Búsqueda de tres configuraciones dentro del 80 % de desarrollo; prueba histórica del 20 % | Evidencia de integración local y contrato de variables, no error del ganador del benchmark |
| ANOVA barrial | Comparar medias de publicación entre barrios | Mismo corte de precios por ID; una mediana por grupo; 3.582 unidades | Welch principal, clásico descriptivo, rangos como sensibilidad y Holm en pares | Evidencia descriptiva; no selección de modelo ni causalidad |

Se comprobó que el precio por m² coincide por ID entre el bundle y el CSV del modelo. Coincidir en respuesta y número de filas **no vuelve intercambiables** las evaluaciones: cambian variables, pérdida, particiones y búsqueda. El bundle tiene edad en 2.937 filas y estado informado en 471; ambos atributos tienen cobertura dependiente de fuente.

## Hallazgos y acciones

| Prioridad | Hallazgo | Acción y estado |
| --- | --- | --- |
| Alta | Se enumeraron cinco modelos distintos de los realmente ejecutados en el benchmark | Corregido en esta matriz y en la memoria: Ridge, KNN, RF, HGB y MLP. Las referencias se presentan aparte |
| Alta | El MAE del artefacto operativo y el del benchmark podían interpretarse como el mismo resultado | Separados los protocolos. No se modificó ni sustituyó el artefacto operativo; su migración requeriría validar y persistir la especificación del benchmark |
| Alta | El benchmark guardado tenía una referencia HGB compleja, sin baseline predictivo simple en su tabla principal | Agregadas mediana global y mediana de comparables, estimadas solo en entrenamiento y evaluadas en los mismos folds externos |
| Media | No se conservaba un diagnóstico de convergencia de MLP ni MAE de entrenamiento de cada reajuste externo | Agregados épocas, límite alcanzado, número de advertencias durante búsqueda/refit y MAE de entrenamiento/prueba por fold. Las búsquedas y el límite de 250 épocas se conservan para comparar el mismo protocolo |
| Media | El bootstrap emparejado podía aceptar filas desalineadas, precios diferentes o duplicados | Se rechazan entradas sin filas, grupos y precios observados coincidentes, o con claves repetidas. Verificado con pruebas ficticias |
| Media | El resultado principal pondera propiedades con varios avisos más de una vez en la evaluación | Se conserva MAE por aviso y se agrega MAE con igual peso por grupo para hacer visible la sensibilidad |
| Alta, pendiente de datos | Selección de familia/escenario sobre resultados OOF; no hay confirmación independiente del ganador | Declarado como mejor observado. La CV anidada resuelve selección de hiperparámetros por familia, sin garantizar evaluación independiente de la familia elegida después |
| Alta, pendiente de datos | Los atributos físicos pueden provenir de capturas posteriores al precio y sus faltantes dependen de fuente | Se describe el posible sesgo temporal. Una prueba futura necesita joins disponibles a la fecha de predicción y comparación con/sin enriquecimiento |
| Alta, pendiente de datos | Duplicados aproximados y dependencia espacial no eliminada por `GroupKFold` | Se verifican los grupos detectados, sin afirmar independencia completa. Planificar validación temporal y por edificios/microzonas cuando haya IDs adecuados |
| Alta, pendiente de datos | La ventaja del prototipo cae de MAE 442,7 a 616,0 al retirar enriquecimiento | Se mantiene visible en Streamlit y documentación. No se atribuye el error con atributos completos a predicciones básicas |
| Media | Exponenciar predicción logarítmica podía presentarse como media aritmética del precio | Corregida interpretación mediante desigualdad de Jensen; no se agrega una corrección paramétrica sin justificar sus supuestos |
| Media | Un ANOVA significativo puede sobreinterpretarse como diferencia en todos los pares o efecto causal | Se conservan Welch y Holm; se separan significación, magnitud y causalidad; se explica no rechazo del par Almagro–Caballito tras ajuste |
| Alta, pendiente de cliente | La métrica de concordancia de ranking no prueba utilidad ni ahorro comercial | Se mantiene como proxy; el ahorro de tiempo requiere revisión emparejada con la inmobiliaria |

## Qué verifica la nueva corrida

El ejecutor valida las cinco particiones externas y las quince internas por grupo, que cada fila tenga una predicción externa por modelo y escenario y que las predicciones sean finitas y positivas. Guarda hashes de datos, código y predicciones, versiones de bibliotecas, configuraciones efectivas y parámetros seleccionados en cada fold.

Los archivos `reports/benchmark-auditado/resumen.csv`, `ajustes.csv`, `por_agency.csv`, `por_neighborhood.csv` y `manifiesto.json` contienen evidencia agregada sin contactos. Las predicciones por fila quedan únicamente en `data/processed/auditoria-estadistica/predicciones_oof.csv`, fuera de Git. La corrida usa datos locales autorizados, sin nuevas extracciones ni llamadas pagas.

Se conservó la arquitectura y presupuesto de ajuste de las cinco familias: 5 folds externos × 2 escenarios × 5 familias × (3 configuraciones × 3 folds internos + 1 reajuste) = **500 ajustes**, más cinco ajustes del HGB histórico. Las medianas no entrenan estimadores. Se omitieron importancias por permutación y PDP en esta repetición porque sus resultados históricos ya están documentados y no afectan estas métricas.

La corrida no certifica convergencia global de MLP. Si un refit alcanza el límite o la búsqueda emite advertencias, debe interpretarse con ese presupuesto explícito. Ausencia de advertencias tampoco acredita óptimo global. Aumentar épocas y volver a ajustar constituye un nuevo experimento, que necesita conservar su identificación.

En la ejecución del 18/11, los diez refits de MLP finalizaron entre 100 y 137 épocas, sin llegar a 250 y sin advertencias durante búsquedas/refits. HGB con edificio reprodujo MAE 402,6 y RMSE 614,0, frente a MAE 585,6 de comparables; la mejora de MAE es 31,2 %. El MAE de entrenamiento de HGB fue 154,1 y el MAE con igual peso por grupo 403,9. Los errores por fuente confirman que la mejora no es uniforme: RE/MAX empeora al ampliar con edificio. No se seleccionó otra configuración a partir de esa observación posterior.

Verificación: **258 pruebas aprobadas** con el comando exigido; validador de skill aprobado; figuras generadas desde predicciones verificadas por hash e inspeccionadas visualmente. No se modificaron las predicciones históricas del notebook original ni el binario operativo.

## Protocolo de confirmación pendiente

1. Congelar la familia, escenario, preprocesamiento, configuración y umbrales antes de incorporar otro corte. Conservar fecha, hash y contrato de variables del artefacto.
2. Obtener una captura posterior autorizada y registrar la información disponible a su fecha. Evaluar por separado propiedades conocidas con precio actualizado y propiedades nuevas; aplicar agrupación independiente de precio cuando sea posible.
3. Comparar contra los dos baselines sobre el mismo conjunto, con MAE por aviso y por grupo, errores por fuente/barrio, cobertura y faltantes. Los límites de aceptación técnicos deben acordarse antes de ver el nuevo resultado.
4. Ejecutar el piloto de revisión de búsquedas con la inmobiliaria: tiempo neto, candidatos relevantes, novedad y vigencia. Acordar cuánto error y cuánta pérdida de candidatos son tolerables para su decisión.

No se ejecutó esta confirmación porque no hay una nueva muestra ni tiempos de cliente observados en los insumos disponibles. Tampoco se desplegó un Actor o escenario remoto nuevo como parte de la auditoría.
