# Comparativa de modelos para precios publicados de venta

Esta ficha conserva la corrida histórica. La [reproducción auditada](benchmark-auditado/resultados.md) agrega baselines simples, métricas por grupo y diagnóstico de convergencia, manteniendo las cinco familias y su búsqueda. Ver [matriz de protocolos](../docs/auditoria-estadistica.md) y [memoria matemática](../docs/memoria-matematica.md).

Ejecutado sobre 3.806 avisos, 3.582 grupos y 48 barrios de CABA, con scikit-learn 1.7.2. El escenario base usa 12 variables y el ampliado suma antigüedad y estado. Las once comparaciones usan las mismas filas y los mismos cinco folds externos. El HGB fijo conserva la configuración del EDA con el vocabulario ajustado por fold y reproduce su MAE redondeado de USD 448/m².

| Modelo | MAE base | MAE ampliado | RMSE ampliado | MdAPE ampliado | Desvío de MAE ampliado entre folds |
| --- | ---: | ---: | ---: | ---: | ---: |
| HGB fijo EDA | 448,26 |  |  |  |  |
| Ridge | 588,30 | 524,54 | 827,88 | 15,52 % | 23,90 |
| KNN | 515,14 | 467,73 | 743,37 | 13,14 % | 16,06 |
| Random Forest | 460,50 | 418,32 | 648,41 | 12,05 % | 17,72 |
| HistGradientBoosting | 451,04 | **402,63** | **614,04** | **11,81 %** | 13,54 |
| MLP | 505,36 | 443,87 | 659,07 | 13,12 % | 13,28 |

MAE, RMSE y desvío en USD/m² publicados. El HGB fijo obtuvo RMSE de 680,02 y MdAPE de 12,86 %. En el HGB ampliado, la diferencia emparejada de MAE frente al HGB fijo fue de −45,63 USD/m², aproximadamente 10,2 %. El intervalo percentil del 95 % con 600 remuestreos de grupos fue [−55,42, −35,90]. El intervalo remuestrea los errores ya calculados y su alcance es la captura analizada. La elección del mejor modelo usa el conjunto de predicciones externas de las cinco familias y queda pendiente una prueba confirmatoria en otra captura.

En los mismos 2.937 avisos con edad informada, MAE de HGB ajustado pasó de 447,23 con las variables base a 377,87 con las variables de edificio. El HGB fijo tuvo 442,65 en esas mismas filas. La ampliación introduce dos variables y los patrones de faltantes de ambas. Las dos variantes se entrenaron con la misma muestra completa dentro de cada fold. No se estima un efecto de la edad aislado.

El HGB ampliado promedió 6,86 s por fold para búsqueda, refit y predicción, frente a 12,16 s de Random Forest ampliado, 9,11 s del MLP ampliado, 0,48 s de KNN, 0,23 s de Ridge y 1,83 s del HGB fijo. Esos tiempos excluyen interpretabilidad. La MLP usa capas ocultas de 48 y 24 neuronas. La extrapolación `exp(predicción log)` transforma de vuelta a USD/m². La no linealidad de la función hace que esta predicción pueda diferir de la media condicional en USD. El HGB ampliado subestimó el precio publicado en promedio por 45,93 USD/m².

## Diferencias por fuente

| Fuente | Avisos | MAE HGB fijo | MAE HGB ampliado |
| --- | ---: | ---: | ---: |
| Century 21 | 545 | 467,46 | 412,98 |
| Clarín | 18 | 1.125,78 | 1.058,64 |
| Migliorisi | 388 | 488,47 | 369,56 |
| RE/MAX | 583 | 456,11 | 480,38 |
| Zonaprop | 2.272 | 429,40 | 380,65 |

RE/MAX, sin antigüedad ni estado en el bundle, empeora con la ampliación. La mejora agregada está ponderada por aviso y Zonaprop aporta cerca del 60 % de la muestra. Los 18 casos de Clarín tienen escaso peso en el error agregado y no permiten caracterizar el rendimiento de la fuente con precisión. El notebook calcula también MAE, RMSE, sesgo, MdAPE y tamaño por barrio. Jupyter muestra una vista abreviada por defecto. La variable `profile` al final de la celda de ranking contiene la tabla barrial completa.

## Priorización de avisos

| Indicador | HGB fijo | HGB ampliado |
| --- | ---: | ---: |
| Coincidencia con comparables en top-20 por fold | 25 % | 29 % |
| Desvío de la coincidencia entre folds | 8,7 pp | 6,5 pp |
| Jaccard promedio del top-20 frente al HGB fijo | 1,00 | 0,33 |
| Cobertura del criterio de comparables | 81,5 % | 81,5 % |
| Señales de revisión entre los 100 primeros antes de filtros | 38 | 35 |
| Candidatos con brecha ≤ −15 % | 93 | 81 |
| Candidatos con brecha ≤ −20 % | 74 | 56 |
| Candidatos con brecha ≤ −25 % | 58 | 38 |

El criterio de referencia usa mediana y MAD de comparables de entrenamiento, con al menos diez grupos y filtros de carga. Cada lista cuenta una fila por grupo. KNN base (34 %) y Ridge base (39 %) tuvieron mayor concordancia con el criterio, a pesar de MAE más alto. El 39 % de Ridge coexistió con 53 señales de revisión entre los 100 primeros antes de filtrar. El top-20 mide acuerdo con una definición operativa de precio bajo. El resultado no mide ventas, rentabilidad ni valor para quien recibe la alerta. Sigue pendiente confirmar las señales contra los avisos y medir la precisión comercial y la estabilidad en capturas futuras.

## Interpretación

El coeficiente medio de Ridge ampliado para un año adicional de edad es −0,0066 en log, equivalente a −0,66 % en la predicción al mantener constantes los demás regresores. El notebook devuelve los coeficientes numéricos a su unidad original. Los cambios por grado de latitud o longitud abarcan una escala mayor que la observada y requieren interpretar incrementos locales.

En el HGB ampliado, permutar barrio elevó el MAE en 391 USD/m², superficie total en 250, cubierta en 235 y antigüedad en 171, en promedio entre folds externos. La importancia puede redistribuirse entre variables correlacionadas. La dependencia parcial de cubierta cae de aproximadamente 3.136 a 2.122 USD/m² entre los cuantiles 10 y 90 de cubierta, con dispersión amplia en las predicciones individuales. Variar la cubierta con otras entradas fijas puede generar combinaciones poco habituales. Estos resultados describen el modelo y sus asociaciones.

Pasaron las 203 pruebas del proyecto, incluidas cinco nuevas del benchmark inmobiliario. También se verificaron sobre el bundle las cinco separaciones externas y quince internas por grupo, la estabilidad del soporte de comparables al variar el precio externo y la cobertura de predicciones únicas del notebook. El notebook original conserva su SHA-256 y sus resultados guardados. [Pruebas del benchmark](../tests/test_benchmark_inmobiliario.py)

[Notebook reproducible](../notebooks/benchmark_modelos.ipynb) · [Copia ejecutada](../data/processed/eda-colab/salidas-benchmark/benchmark_ejecutado.ipynb) · [Auditoría metodológica](auditoria_metodologica.md) · [Instrucciones de reproducción](README.md)
