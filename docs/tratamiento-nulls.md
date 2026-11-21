# Tratamiento de nulls

La base del análisis es el CSV limpio del pipeline (`dataset_limpio.csv`). Lo genera el ETL ([`analytics/ETL.py`](../precio_entorno/analytics/ETL.py)) a partir de la captura consolidada de venta y del Mapa del Delito 2025. Ese es el archivo que Make guarda en Drive y del que salen las tablas de Looker Studio.

**El CSV limpio tiene 0 nulls.** Si una corrida dejara alguno, el ETL termina con error, Make corta el flujo y el archivo no llega a Drive. Lo verifica `tests/test_pipeline_analytics.py`.

Se reproduce con:

```powershell
python -m precio_entorno.pipeline_analytics etl data/raw/venta-consolidada-20261108/avisos.json
```

El reporte (`data/processed/pipeline/reporte_etl.json`) tiene un bloque `tratamiento_nulls` con los conteos de cada regla y `nulls_finales: 0`.

## Resumen

Las cifras son de la corrida del 17/11/2026: 4.007 filas leídas y 3.806 avisos en la base.

| Columna | Nulls | % | Por qué falta | Tratamiento | Marca que queda |
| --- | ---: | ---: | --- | --- | --- |
| Precio, moneda, superficie cubierta, ambientes, barrio | 201 filas descartadas (con los valores inválidos) | 5 % de lo leído | El aviso no lo publica o el valor no se puede leer | **Se descarta el aviso** | El conteo por campo en `reporte_etl.json` |
| `superficie_total_m2` | 72 | 1,9 % | Clarín no la muestra en el listado (18 de 18); Century 21 no la publica en algunos avisos (48 de 545) | **Se imputa con la superficie cubierta** | `superficie_total_imputada` = si |
| `expensas_ars` | 2.200 | 57,8 % | RE/MAX, Century 21 y Migliorisi no las publican: les faltan al 100 % | **Se elimina la columna** | `expensas_informadas` (si/no) |
| `latitud` / `longitud` | 425 | 11,2 % | Migliorisi no publica el pin (388 de 388), Clarín tampoco (18 de 18); en el resto faltan casos sueltos | **Se imputa con la mediana de los pines publicados del barrio** | `ubicacion_origen` y `tiene_pin` |
| Columnas de delitos, comuna y USD/m² | 0 | 0 % | — | Regla preventiva (ver abajo) | — |

## Antes de tratar: lo inválido pasa a null

La validación ([`importing.parse_listings`](../precio_entorno/importing.py)) convierte en faltante cualquier valor que no se puede creer. Así, cada caso se trata una sola vez y con la misma regla:

- Precios de relleno (888.888, 999.999).
- Expensas menores a ARS 1.000, para no leer «95.000» como 95 (42 casos).
- Coordenadas fuera del rectángulo de CABA (5 latitudes y 4 longitudes).
- Superficie total menor que la cubierta (4 casos).

## Decisiones, una por una

### 1. Campos obligatorios: se descarta el aviso

Son el ID, el enlace, la fecha de captura, el precio, la moneda, la superficie cubierta, los ambientes y el barrio. Faltaron así: superficie cubierta 100, barrio 59, precio 19, ambientes 13 y moneda 9. Un aviso puede faltar en más de un campo. Con los valores inválidos (moneda o superficie fuera de rango, USD/m² implausible), se descartan **201 filas de 4.007 (5 %)**.

**Por qué no se imputan:**

- El precio es lo que se analiza. Imputarlo sería inventar la variable que se quiere describir.
- La superficie cubierta es el denominador del USD/m².
- Sin barrio, el aviso no se puede cruzar con los delitos ni ubicar en la comparación, que se hace por barrio.
- Los ambientes son uno de los criterios de búsqueda.

Los descartes no pesan igual en todas las fuentes:

| Fuente | Leídos | Descartados | % |
| --- | ---: | ---: | ---: |
| Century 21 | 600 | 55 | 9,2 |
| Migliorisi | 428 | 40 | 9,3 |
| Clarín | 20 | 2 | 10,0 |
| Zonaprop | 2.359 | 87 | 3,7 |
| RE/MAX | 600 | 17 | 2,8 |

La composición casi no se mueve: Zonaprop pasa del 58,9 % de lo leído al 59,7 % de la base.

### 2. Superficie total: se imputa con la cubierta

En una propiedad, la superficie total es la cubierta más la descubierta (balcón, patio, terraza). Es siempre mayor o igual que la cubierta: la validación ya anula las que dan menos.

**Por qué la cubierta:** es la cota inferior segura. Supone que no hay superficie descubierta, en lugar de inventar metros. Imputar con la mediana del barrio, o con el cociente total/cubierta, le daría balcón o patio a un departamento que quizá no lo tiene.

**Por qué no se descarta:** son solo 72 avisos (1,9 %) con todos los datos obligatorios. Además, el análisis usa la superficie cubierta, no la total.

**Qué se ve:** en la tabla `fuentes`, `pct_con_superficie_total` mide lo publicado, no lo imputado: Clarín da 0 % y Century 21 da 91,2 %.

### 3. Expensas: se elimina la columna y queda si se informaron

Faltan en el 57,8 % de los avisos, y no al azar. Tres de las cinco fuentes no las publican nunca, así que el faltante depende de la fuente, no del departamento.

**Por qué no se imputan:**

- Más de la mitad de la columna sería inventada.
- Para RE/MAX, Century 21 y Migliorisi el 100 % saldría de la distribución de Zonaprop y Clarín, otros edificios y otro público.
- Cualquier análisis con esa columna mostraría la regla de imputación, no el mercado.

**Por qué no se usa 0:** 0 quiere decir «no paga expensas», que es otro dato y es falso para casi todos los departamentos.

**Por qué se puede eliminar:** ningún resultado del análisis la usa. El USD/m², la comparación por barrio, las correlaciones y el dashboard no dependen de las expensas.

**Qué se conserva:** `expensas_informadas` deja ver la cobertura por fuente (`pct_con_expensas` en la tabla `fuentes`). La base operativa de la app guarda el monto cuando existe, y la ficha dice «Expensas no informadas» cuando no.

### 4. Coordenadas: se imputan con la mediana de los pines del barrio

Al 11,2 % de los avisos le falta el pin. Casi todos son de Migliorisi y Clarín, que no lo publican. Un aviso de Zonaprop traía la longitud sin la latitud: **medio par cuenta como sin pin**, porque un solo eje no ubica nada.

**La regla:**

1. Al aviso sin pin se le asignan la latitud y la longitud medianas de los pines publicados de su barrio (`ubicacion_origen = mediana_barrio`).
2. Si su barrio no tuviera ningún pin publicado, se usa la mediana de la comuna (`mediana_comuna`).

Hoy los 48 barrios tienen pines, así que los 425 casos se resolvieron por barrio.

**Por qué no se descartan:** se perdería el 11 % de la base. Desaparecerían Migliorisi (10 % del catálogo) y Clarín, y la muestra quedaría sesgada hacia las fuentes que publican pin. El precio, la superficie y el barrio de esos avisos son válidos.

**Por qué la mediana del barrio:**

- Es una ubicación que respeta el dato que sí se tiene, el barrio. Ese barrio es además la unidad geográfica del análisis y del contexto delictivo.
- Es la mediana de donde está la oferta real, no el centro geométrico del polígono, que puede caer en un parque o en vías.
- Es robusta a pines mal cargados.
- Se calcula con los mismos datos, así que el Actor de Apify no necesita archivos de geometría.

**Cómo se evita que la imputación distorsione:**

- `tiene_pin` sigue diciendo si el pin fue publicado.
- Las correlaciones con latitud y longitud usan solo los 3.381 pines publicados. Las imputadas se apilan en el centro de cada barrio y achatarían la relación.
- La mediana de cada barrio en la tabla `barrios` no cambia: sumarle copias de su propia mediana no la mueve.
- `pct_con_pin` informa la cobertura publicada (Migliorisi y Clarín, 0 %).
- **Una coordenada imputada no sirve para análisis finos**, como distancias o conteos a 500 m. Para eso, filtrar `ubicacion_origen = publicada`.

### 5. Delitos, comuna y USD/m²: regla preventiva

Hoy no tienen nulls, pero podrían tenerlos en otra corrida:

| Columna | Cuándo podría faltar | Qué se hace |
| --- | --- | --- |
| `pct_con_arma_barrio` | Un barrio con 0 delitos registrados (0/0) | Vale 0: sin delitos, no hay delitos con arma |
| `comuna`, `delitos_barrio`, `robos_hurtos_barrio` | Un barrio que no figura en el archivo de delitos | **La corrida falla.** Poner 0 delitos afirmaría algo que el archivo no dice, y el caso señala un error de nombres o de archivo que hay que corregir |
| `precio_m2_usd` | Un precio que no está en USD | No pasa: en venta solo se aceptan USD |

En el archivo de delitos, de 133.203 hechos se descartan 2.785 sin barrio (2,1 %), porque no se pueden asignar a ninguna unidad geográfica. Los 155 sin franja horaria se conservan como franja desconocida. La base del análisis usa los totales por barrio, que no tienen nulls.

## Qué capa tiene nulls y cuál no

| Capa | ¿Tiene nulls? | Por qué |
| --- | --- | --- |
| Crudos (`data/raw/`) | Sí | Son la copia fiel de lo publicado; no se tocan |
| Base operativa de la app (`real.sqlite3`) | Sí, en campos opcionales | Ahí `NULL` significa «la fuente no lo publicó», y la app lo muestra así («Expensas no informadas»). Inventar un valor sería mostrarle al usuario un dato falso |
| **CSV limpio del análisis (`dataset_limpio.csv`)** | **No** | Aplica las reglas de este documento y la corrida falla si queda alguno |
| Tablas del dashboard (`resumen`, `barrios`, `ambientes`, `fuentes`, `distribucion`, `correlaciones`) | No | Salen del CSV limpio |
