# Evaluación del modelo · Metodología

Este documento responde la pregunta analítica del capstone: ¿la información sobre delitos registrados mejora la predicción del **precio publicado por m² cubierto**, frente a un modelo que solo usa características inmobiliarias y ubicación?

## Resultados con la base ampliada · 8 de noviembre de 2026

**Datos:**
- **Avisos:** 3.806 departamentos en venta válidos, sumando a las inmobiliarias y Clarín los 2.272 avisos de Zonaprop (48 barrios, con autorización). Antes eran 1.516.
- **Pines:** 3.381 avisos tienen pin para el cruce por radio, con coordenadas tratadas como aproximadas. Antes eran 1.122.
- **Delitos:** los de 2025, la ventana de 12 meses anterior a las capturas.
- **Partición:** 758 avisos de prueba y validación cruzada de 5 pliegues.
- **Datos guardados:** en `data/processed/ampliado/`.

**Cambio de método: posibles duplicados.** Una misma propiedad puede estar publicada por una inmobiliaria y en Zonaprop. Los avisos de fuentes distintas con mismo barrio, ambientes, m² cubiertos redondeados y precio redondeado a miles ahora comparten grupo en la partición y en la validación cruzada (columna `grupo`). Así una copia no queda en entrenamiento y la otra en prueba. Son 444 avisos en 220 grupos.

Cada celda muestra el MAE en USD/m² de la partición de prueba y el de la validación cruzada, separados por una barra. La última columna dice si el entorno mejora al modelo inmobiliario en los 5 pliegues y si le gana al placebo en los 5.

| Especificación | Inmobiliario | Con delitos | Placebo (CV) | ¿Mejora en todos? / ¿Gana al placebo? |
| --- | --- | --- | --- | --- |
| Cruce por barrio | 560 / 525 | 560 / 525 | 525 | No / No |
| Cruce por barrio + control por inmobiliaria | 561 / 521 | 560 / 524 | 523 | No / No |
| Pines aproximados | 522 / 482 | 522 / 476 | 493 | Sí / Sí |
| Pines aproximados + control | 519 / 481 | 521 / 476 | 492 | Sí / Sí |
| + transporte y gastronomía (OSM) | 524 / 475 | 519 / 472 | 483 | No / Sí |
| + transporte y gastronomía + control | 521 / 475 | 514 / 471 | 483 | No / Sí |
| + puntos de interés completos | 521 / 472 | 520 / 468 | 477 | No / No |
| **+ puntos de interés completos + control** | **514 / 469** | **514 / 467** | 476 | No / No |

**Lectura:**
1. **Con el cruce por barrio, los delitos no aportan nada.** El MAE de validación cruzada es el mismo con delitos y con placebo (525). Con la base chica había una mejora aparente que ya se explicaba por el placebo; con la base ampliada, ni eso.
2. **Con pines aproximados y sin puntos de interés, los delitos a 500 m mejoran unos 5 a 6 USD/m²** en la validación cruzada, en los 5 pliegues y por encima del placebo. Es alrededor del 1 % del error. En la partición de prueba no mejoran.
3. **Al sumar los puntos de interés, el aporte desaparece.** Con la especificación final, los delitos bajan el MAE de 469 a 467 en la validación cruzada. La mejora cambia de signo entre pliegues, no le gana al placebo y en la partición de prueba es nula (514 en los dos modelos). Igual que con la base chica, el aporte inicial de los delitos parece medir actividad urbana y cercanía a servicios.
4. **La ubicación sí mejora la predicción.** Con control por inmobiliaria, el modelo inmobiliario baja de 481 a 469 USD/m² en la validación cruzada al sumar la distancia a transporte, parques y hospitales, y la cantidad de escuelas y gastronomía cerca. Es alrededor del 19 % de la mediana de 2.411 USD/m².
5. **Comparación con la base chica:**
   - **Validación cruzada:** el error del mejor modelo baja de 502 a 469.
   - **Partición de prueba:** sube de 488 a 514. Ahora tiene 758 avisos en vez de 304 y una composición distinta: Zonaprop aporta hasta 50 avisos por barrio, también en los barrios del sur, donde el precio por m² es más variable.
   - **Cuál pesa más:** la validación cruzada promedia 5 particiones, así que es la referencia más estable.

**Conclusión:** la base ampliada confirma la del 7 de noviembre. No hay evidencia de que los delitos registrados mejoren la predicción del precio publicado por m². La ubicación respecto de transporte, parques y servicios, en cambio, sí la mejora.

**Para reproducirlo:**

```powershell
python -m precio_entorno.consolidar data/raw/inmobiliarias-20261107 data/raw/clarin-20261108 data/raw/zonaprop-venta-piloto-20261108 data/raw/zonaprop-venta-20261108 data/raw/zonaprop-venta-20261108-reintento --salida data/raw/venta-consolidada-20261108
```

```powershell
python -m precio_entorno.modelo data/raw/venta-consolidada-20261108/avisos.json --catalogo inmobiliarias-autorizadas --pines-aproximados --control-inmobiliaria --osm data/raw/osm-20261107 data/processed/poi-badata --salida data/processed/ampliado/modelo-pines-aproximados-poi-control
```

## Resultados · 7 de noviembre de 2026

**Datos:**
- **Avisos:** 1.516 avisos válidos del catálogo consolidado `inmobiliarias-autorizadas` (RE/MAX 583, Century 21 545 y Migliorisi 388), que cubren los 48 barrios.
- **Ventana de delitos:** enero a diciembre de 2025, con 10 meses de desfase respecto de la captura.
- **Partición:** 1.212 avisos de entrenamiento y 304 de prueba, con semilla 42.

**Resultados:**

| Especificación | Comparables | Inmobiliario | Con entorno | Placebo | ¿Supera al placebo? |
| --- | --- | --- | --- | --- | --- |
| **Principal:** cruce por barrio | 643 / 631 | 603 / 580 | 604 / 561 | — / 569 | **No** |
| **Sensibilidad:** pines aproximados y radio de 500 m | 643 / 631 | 534 / 519 | 518 / 509 | — / 529 | Sí, en los 5 pliegues |

Cada celda muestra el MAE en USD/m² de la partición de prueba y el MAE medio de la validación cruzada de 5 pliegues, separados por una barra. El placebo solo se calcula en la validación cruzada.

**Lectura:**
1. **Los modelos superan a los comparables.** El modelo inmobiliario baja el error de 631 a 580 USD/m². Con coordenadas, aunque sean aproximadas, baja a 519. La ubicación dentro del barrio pesa mucho en el precio publicado.
2. **Con el cruce por barrio, los delitos no aportan.** En la partición de prueba el MAE empeora levemente (de 603 a 604). En la validación cruzada mejora (de 580 a 561), pero un placebo con números al azar constantes por barrio logra casi lo mismo (569). Esa mejora viene de codificar el barrio como número, no de los delitos registrados.
3. **Con pines aproximados, el entorno aporta poco pero algo.** Los delitos a 500 m bajan el MAE de 519 a 509 en la validación cruzada (−10 USD/m², alrededor del 2 % del error y del 0,4 % de un precio típico de 2.500 USD/m²). Mejoran en los 5 pliegues y le ganan al placebo con conteos mezclados al azar (529). La mejora es pequeña frente al desvío entre pliegues (14 a 16 USD/m²).

**Robustez: control por inmobiliaria.** La composición del catálogo cambia por barrio: Migliorisi aporta el 62 % de los avisos de Almagro y Villa Crespo. Por eso se repitió la evaluación con la inmobiliaria como variable en ambos modelos (`--control-inmobiliaria`):

| Especificación | Inmobiliario | Con entorno | Placebo | Mejora del entorno por pliegue | ¿Supera al placebo? |
| --- | --- | --- | --- | --- | --- |
| Cruce por barrio | 594 / 570 | 587 / 557 | — / 565 | 7 a 18 | **No** |
| Pines aproximados | 530 / 515 | 528 / 510 | — / 531 | 1 a 12 | Sí |

Igual que arriba, cada celda muestra el MAE de la partición de prueba y el de la validación cruzada, separados por una barra.

- **La inmobiliaria explica parte del precio.** Controlar por ella baja el error del modelo inmobiliario unos 4 a 10 USD/m², lo que refleja diferencias de segmento o de criterio de publicación entre fuentes.
- **Con el cruce por barrio, la conclusión no cambia:** el entorno sigue sin superar al placebo en todos los pliegues.
- **Con pines aproximados, la mejora se reduce a la mitad:** pasa de −10 a −5 USD/m² en la validación cruzada (alrededor del 1 % del error), y de −16 a −2 en la partición de prueba. Parte del aporte aparente del entorno venía de la composición del catálogo. Lo que queda sigue siendo positivo en los 5 pliegues y mejor que el placebo, pero es muy chico.

**Robustez: transporte y actividad urbana (OpenStreetMap).** Los delitos a 500 m pueden estar midiendo actividad urbana más que delitos. Para probarlo, se sumaron al modelo inmobiliario dos variables de OpenStreetMap (`--osm data/raw/osm-20261107`), solo para avisos con pin:
- `dist_transporte_m`: distancia a la estación de subte, tren o Metrobús más cercana;
- `gastronomia_500m`: restaurantes, cafés y bares a 500 m.

Las categorías que llegaron a su tope de puntos (parques, hospitales, escuelas, supermercados y farmacias) quedaron afuera porque están incompletas.

| Pines aproximados | Inmobiliario | Con entorno | Placebo | Mejora del entorno por pliegue | ¿Supera al placebo? |
| --- | --- | --- | --- | --- | --- |
| Sin OpenStreetMap | 534 / 519 | 518 / 509 | — / 529 | 4 a 18 | Sí |
| Con OpenStreetMap | 511 / 506 | 512 / 500 | — / 518 | −1 a 15 | Sí |
| Sin OpenStreetMap, con control | 530 / 515 | 528 / 510 | — / 531 | 1 a 12 | Sí |
| Con OpenStreetMap y control | 512 / 507 | 499 / 496 | — / 518 | 3 a 18 | Sí |

Cada celda muestra el MAE de la partición de prueba y el de la validación cruzada, separados por una barra.

- **Mejor modelo inmobiliario:** el transporte y la gastronomía cercanos bajan su error entre 9 y 14 USD/m² en la validación cruzada.
- **Aporte inestable de los delitos:**
  - sin control por inmobiliaria, la mejora se vuelve inconsistente: es negativa o nula en 2 de 5 pliegues, y en la partición de prueba el error empeora levemente;
  - con control por inmobiliaria, la mejora es positiva en los 5 pliegues (unos 11 USD/m²).
- **Lectura:** el aporte de los delitos registrados a 500 m depende de la especificación, va de 0 a unos 11 USD/m² (como máximo, alrededor del 2 % del error) y no es robusto.

**Especificación final: puntos de interés completos (OpenStreetMap y Buenos Aires Data).** Las categorías que habían quedado incompletas en OpenStreetMap se completaron con datasets oficiales gratuitos de Buenos Aires Data (licencia CC-BY 2.5 AR), con `--osm data/raw/osm-20261107 data/processed/poi-badata`:
- **Parques:** 487 plazas, parques, jardines y paseos, sin canteros centrales ni plazoletas. La distancia se mide al borde del espacio.
- **Escuelas:** 2.767 establecimientos educativos.
- **Hospitales:** 36 hospitales públicos.

El modelo inmobiliario suma cinco variables de ubicación: distancia a transporte, a parques y a hospitales, y gastronomía y escuelas a 500 m. Supermercados y farmacias siguen afuera porque están incompletos.

| Pines aproximados | Inmobiliario | Con entorno | Placebo | Mejora del entorno por pliegue | ¿Mejora en todos los pliegues? |
| --- | --- | --- | --- | --- | --- |
| Puntos de interés completos | **488 / 501** | 501 / 500 | — / 514 | −7 a 10 | **No** |
| Puntos de interés completos y control | 498 / 502 | 505 / 499 | — / 512 | −3 a 11 | **No** |

Cada celda muestra el MAE de la partición de prueba y el de la validación cruzada, separados por una barra.

- **Mejor modelo inmobiliario:** con los puntos de interés, el error baja de 519 a 501 en la validación cruzada y a 488 en la partición de prueba, el mejor resultado de todo el análisis.
- **Los delitos no aportan:** con esa base, sumar los delitos no mejora el error medio (de 501 a 500), la mejora cambia de signo entre pliegues y en la partición de prueba el error **empeora** entre 7 y 13 USD/m².
- **Interpretación:** el pequeño aporte que se veía antes reflejaba la cercanía al transporte, a los parques y a la actividad urbana, no los delitos registrados.
- **Sobre el placebo:** los delitos le siguen ganando al placebo, pero solo porque los conteos mezclados al azar empeoran el modelo. Por eso el pipeline informa también si el entorno mejora al modelo inmobiliario en todos los pliegues, que es el criterio decisivo.

**Conclusión para el capstone:** con la especificación de la consigna, que cruza por barrio cuando los pines no tienen precisión verificable, no hay evidencia de que los delitos registrados mejoren la predicción del precio publicado por m². El análisis de sensibilidad con pines aproximados mostraba un aporte chico del entorno inmediato, pero ese aporte desaparece al controlar por transporte, parques, hospitales, escuelas y actividad gastronómica. Lo que sí mejora la predicción es la ubicación precisa del aviso respecto de esos servicios. Estas conclusiones están sujetas a tres reservas:
- los pines no declaran su precisión;
- los conteos de hechos registrados también reflejan actividad urbana y circulación;
- una mejora predictiva no implica un efecto causal.

Los resultados completos están en `data/processed/modelo*/`. Hay una carpeta por especificación, con y sin `-control`.

## Cómo correrlo

```powershell
python -m precio_entorno.modelo data/raw/<carpeta>/avisos.json --catalogo zonaprop
```

- Acepta uno o varios CSV o JSON del catálogo, en el mismo formato que la app.
- Por defecto usa todos los `data/raw/delitos_20*.csv`.
- Escribe `dataset_modelo.csv` y `resultados.json` en `data/processed/modelo/`.
- Opciones: `--radio-m` (500 por defecto), `--semilla` (42) y `--pines-aproximados` (ver la sección 3).

## 1. Datos y objetivo

- **Validación de avisos:** es la misma que en la app. Solo entran avisos en USD, con superficie cubierta de 10 a 2.000 m² y precio por m² de USD 200 a 20.000.
- **Variable objetivo:** precio publicado / superficie cubierta, en USD/m². No es una tasación ni un precio de cierre.
- **Capturas repetidas:** a diferencia de la base de la app, el pipeline conserva cada captura distinta de un mismo aviso. Solo descarta las capturas idénticas en ID y fecha.
- **Mínimo:** hacen falta 30 avisos distintos para correrlo. Por debajo de 700, el resultado se marca como exploratorio.

## 2. Ventana de delitos

Para cada captura se usan los **últimos 12 meses publicados, consecutivos y anteriores al mes de captura**. El resultado informa el desfase entre el fin de la ventana y la captura. Por ejemplo, para una captura de noviembre de 2026 la ventana es enero a diciembre de 2025, con 10 meses de desfase. Si no hay 12 meses consecutivos previos, la captura queda sin variables de entorno.

El informe exploratorio encontró un corte entre los archivos de 2024 y 2025. Con capturas de 2026, la ventana cae entera en 2025 y no cruza ese corte.

## 3. Variables

| Grupo | Variables | Cuándo están |
| --- | --- | --- |
| Inmobiliarias | Superficie cubierta y total, ambientes, barrio | Siempre; la superficie total, si el aviso la trae |
| Ubicación | Latitud y longitud | Solo si el pin es apto para el cruce por radio |
| Entorno por barrio | Delitos, robos y hurtos, y % con arma del barrio en la ventana | Si el barrio tiene filas válidas en la ventana; si no, quedan sin dato y no en cero |
| Entorno por radio | Delitos, y robos y hurtos, a 500 m del pin en la ventana | Solo si el pin es apto |

- **Pin apto:** tiene coordenadas dentro de CABA y la fuente declara una precisión de hasta 100 m, igual que en la app. Si no, el cruce se hace por barrio, como pide la consigna.
- **`--pines-aproximados`:** usa también los pines sin precisión declarada. Zonaprop, por ejemplo, no la declara. Es un análisis de sensibilidad y hay que reportarlo así.
- **Siniestros viales:** se excluyen de los delitos.

**Limitación conocida:** con una sola ventana, las variables por barrio valen lo mismo para todos los avisos de ese barrio. Repiten la información de la variable `barrio` y no pueden mejorar el modelo. El pipeline lo detecta y lo anota en `resultados.json`. Solo las variables por radio cambian dentro del barrio, así que el aporte del entorno depende de cuántos avisos tengan pin apto. El resultado informa cuántos avisos de prueba lo tienen.

## 4. Referencias comparadas

1. **Comparables:** mediana del precio por m² en entrenamiento para el mismo barrio y ambientes. Si hay menos de 5 comparables, usa el barrio, y si tampoco alcanza, toda la muestra. El resultado informa cuántas predicciones usó cada nivel.
2. **Modelo inmobiliario:** gradient boosting (`HistGradientBoostingRegressor` de scikit-learn), con pérdida de error absoluto, sobre las variables inmobiliarias y de ubicación.
3. **Modelo con entorno:** el mismo modelo e hiperparámetros, con las variables de entorno disponibles.

## 5. Partición y métrica

- **Partición:** se separa el 20 % de los **avisos** para prueba (`GroupShuffleSplit` por ID). Todas las capturas de un aviso quedan del mismo lado. Las tres referencias se evalúan sobre la misma partición.
- **Métrica principal:** error absoluto medio (MAE) en USD/m² sobre esa partición.
- **Robustez:** validación cruzada de 5 pliegues agrupada por aviso. Informa el MAE medio, su desvío y la mejora del entorno en cada pliegue. Si la mejora cambia de signo entre pliegues, no hay evidencia de que el entorno aporte.
- **Placebo:** en cada pliegue se entrena el mismo modelo con el entorno reemplazado por valores sin información sobre delitos. Las variables por barrio pasan a ser números al azar constantes dentro de cada barrio, y los conteos por radio se reasignan al azar entre los avisos con pin. La mejora solo se atribuye a los delitos si el modelo con entorno le gana al placebo en todos los pliegues.

## 6. Interpretación

Una mejora en el MAE indica capacidad predictiva sobre precios publicados, no un efecto causal de los delitos sobre los precios. Los delitos registrados dependen también de la denuncia, la circulación y el patrullaje. Los conteos se presentan como hechos registrados y no se convierten en un puntaje de seguridad.

## Verificación

`tests/test_modelo.py` usa datos sintéticos y ficticios para comprobar:
- la ventana previa y el desfase;
- los conteos por radio y por barrio, sin inventar ceros;
- que las capturas repetidas quedan en la misma partición;
- que el pipeline detecta una señal de entorno cuando existe.

Una corrida con precios al azar no mostró una mejora espuria del modelo con entorno.
