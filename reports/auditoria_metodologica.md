# Auditoría metodológica del EDA inmobiliario

## Catálogo y unidad de análisis

El bundle contiene 3.806 avisos de venta en USD, correspondientes a 3.582 grupos de propiedades aproximados. La captura abarca del 7 al 9 de noviembre de 2026. Zonaprop aporta 2.272 avisos (59,7 %) bajo un tope de 50 por barrio. Los resultados caracterizan el catálogo observado. El diseño de muestreo y la ausencia de capturas sucesivas impiden estimar representatividad, tasas de entrada al mercado o desempeño de una alerta en el tiempo.

El precio analizado es el publicado por m² cubierto. El cociente `price / covered_area` coincide con el objetivo en todas las filas, salvo redondeo de máquina. La mediana es USD 2.411/m² y el rango va de USD 341 a 13.869/m². El notebook complementario informa cuantiles, faltantes por agencia y barrio, y grupos con más de un aviso. Las señales de superficie o precio atípicos se usan para revisión, sin borrar las observaciones de la evaluación predictiva.

| Fuente | Avisos | Antigüedad | Estado | Coordenadas |
| --- | ---: | ---: | ---: | ---: |
| Century 21 | 545 | 415 | 471 | 540 |
| Clarín | 18 | 0 | 0 | 0 |
| Migliorisi | 388 | 388 | 0 | 0 |
| RE/MAX | 583 | 0 | 0 | 582 |
| Zonaprop | 2.272 | 2.134 | 0 | 2.259 |
| Total | 3.806 | 2.937 | 471 | 3.381 |

Faltan 72 superficies totales y 425 pares de coordenadas. Las cinco variables de proximidad tienen el mismo número de faltantes que los pines. Hay 690 pares de coordenadas repetidos después de la primera aparición entre los 3.381 avisos con pin. Se identificaron 220 grupos con varios avisos, todos con más de una fuente. La validación agrupada conserva la separación para los duplicados detectados. La exhaustividad de esa detección y la generalización a barrios, agencias o fechas nuevas requieren otra validación.

La cobertura de antigüedad depende de la fuente. Todos los estados informados provienen de Century 21. El modelo ampliado trata el estado como categoría nominal y puede aprovechar diferencias de fuente o ausencia de datos. Atribuir el cambio de error a la antigüedad por sí sola requeriría una ablación separada. Ambas variantes se evalúan sobre las mismas filas, también al restringir la tabla a avisos con edad informada.

## EDA y contexto espacial

El EDA usa Pearson para asociación lineal, Spearman para asociación monótona y LOWESS para describir formas locales con ponderación tricúbica. Los suavizados se limitan a los cuantiles centrales de la variable explicativa. Conviene leerlos junto con el número de observaciones, los cuantiles y la sensibilidad de Pearson a excluir las colas. Los p-valores ordinarios del EDA no ajustan por réplicas de un mismo inmueble, dependencia espacial ni múltiples comparaciones. Los intervalos agrupados del benchmark cuantifican otra pregunta, la diferencia de MAE entre predicciones emparejadas.

Dividir el precio por la mediana de cada barrio atenúa diferencias de nivel entre barrios. La correlación resultante describe precio relativo, sin controlar todas las diferencias de composición dentro de cada barrio. El notebook compara esa asociación con la del precio absoluto y la de las medianas barriales. La relación entre superficie y USD/m² también puede reflejar que la superficie está en el denominador. Ninguna de estas asociaciones identifica un efecto causal.

En los 3.381 avisos con dato de gastronomía a 500 m, Spearman pasa de 0,285 con el precio absoluto a 0,009 con el precio relativo. Entre las medianas de los 48 barrios es 0,423. La antigüedad conserva una asociación negativa aun con el precio relativo (−0,515 en 2.937 avisos). Para superficie cubierta, Pearson con el precio absoluto es 0,131 y Spearman es −0,053 en 3.806 avisos. La diferencia justifica revisar la forma y las colas antes de resumirla con una única pendiente. El 98 % central del precio por m² queda aproximadamente entre USD 778 y 7.273.

El bundle registra hechos agregados por barrio en 2024 y 2025, con 48 barrios en cada año. La densidad por hectárea es una densidad territorial. Haría falta un denominador que represente población expuesta o actividad para estimar tasas de exposición. La fuente oficial publica coordenadas y un campo `cantidad` por registro. El código histórico de radio usa una aproximación plana alrededor del pin y cuenta filas, mientras que el agregado barrial suma `cantidad`. La documentación local identifica la ventana como enero–diciembre de 2025. Queda pendiente reconciliar conteos y posiciones a nivel de registro antes de interpretar el radio de 500 m. El benchmark usa los hechos por barrio y año como contexto separado. [Ficha oficial de Delitos](https://data.buenosaires.gob.ar/dataset/delitos) · [Diccionario del recurso 2025](https://data.buenosaires.gob.ar/fr/dataset/6976d312-54e9-4398-b721-1504aedcce89/resource/1a1a977e-b5b8-402c-bdea-93240f4af851) · [Procedencia local](../docs/modelo.md)

## Validación y ranking

La mediana barrial usada para el EDA es descriptiva. El HGB original predice el log del precio por m² con `GroupKFold(5)`. El código de comparables posterior usa todo el catálogo para calcular mediana, MAD, percentil 1 de precio y mediana de cubierta. Restar uno al recuento no retira el propio precio ni excluye copias del grupo. Por ello las oportunidades del EDA describen el catálogo y no constituyen una medición fuera de muestra del ranking. La inspección del código separa esta contaminación del ranking de la evaluación predictiva del HGB.

La salida guardada del EDA conserva MAE de USD 448/m², 76 propiedades marcadas y 68 avisos con señales de carga. El 12,9 % que imprime como error porcentual mediano divide por la predicción. El indicador MdAPE del benchmark divide por el precio observado. Las dos definiciones responden a preguntas diferentes y sus valores no se comparan directamente.

El benchmark ajusta vocabulario, imputación y escalado dentro de cada partición de entrenamiento. La búsqueda interna usa tres folds agrupados sobre el entrenamiento de cada fold externo. Los comparables externos se calculan por barrio y ambientes usando solo grupos de entrenamiento, con una mediana por grupo y segmento. El conjunto externo aporta únicamente las características y el precio publicado del aviso que se puntúa, y ese precio integra el resultado de la evaluación.

La precisión top-20 mide coincidencia con un criterio de comparables, que exige soporte de al menos diez grupos, MAD positivo y ausencia de señales de revisión. También se computan cobertura, coincidencia de candidatos entre modelos y sensibilidad a tres cortes de brecha. Las señales de carga son chequeos mecánicos y falta confirmar los casos contra las fichas. La estabilidad entre capturas y la utilidad de los avisos para usuarios requieren una evaluación prospectiva.

Para preferencias y comparación de barrios, la evidencia describe la oferta observada y la cobertura de cada variable. Una búsqueda guardada conserva los filtros del usuario. En una alerta por aviso nuevo, una brecha negativa podría ayudar a priorizar revisiones si se sostiene en capturas posteriores. La brecha compara precios de publicación y un valor esperado para el catálogo.
