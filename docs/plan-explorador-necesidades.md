# Plan de implementación: explorador de necesidades

**Proyecto:** Lüga
**Objetivo:** ampliar «Lo que me importa» para que la persona declare necesidades concretas («me muevo sin auto», «trabajo desde casa») y la app le muestre las capas, los datos del aviso y las advertencias que corresponden, sin puntajes, rankings ni inferencias sobre la persona.
**Estado:** encendido para todos desde el 2026-11-24 (`?explorador=0` lo apaga). Plan revisado el 2026-11-17 contra el código de `main` + `tratamiento-nulls`. Reemplaza a la propuesta original («Implementation Plan — Explorador de necesidades concretas»).

---

## 0. Qué cambió respecto de la propuesta original

La propuesta suponía que casi todo estaba por verificar. Buena parte ya existe, y dos supuestos chocan con reglas del proyecto.

| # | Propuesta original | Lo que hay en el repositorio | Corrección |
|---|---|---|---|
| 1 | Crear una entrada nueva, «Personalizá tu entorno», con un catálogo y un motor nuevos | El panel **«Lo que me importa»** (`web/index.html`, `PREFERENCIAS` en `web/app.js`) ya traduce preferencias en capas, las guarda en `localStorage` (`precio-entorno-filtros.prefs`) y aclara «No se combinan en un puntaje» | Evolucionar ese panel. El catálogo de necesidades se arma sobre `PREFERENCIAS`; no se crea un componente paralelo |
| 2 | Agregar metadatos por dato urbano | `data/processed/entorno/fuentes.json` ya tiene capa, título, archivo, período, URL, SHA-256 y licencia. `/api/fuentes` y el diálogo «Fuentes del entorno» los muestran. `NOTAS` en `app.js` tiene una advertencia por capa | Reutilizar. Solo agregar las entradas de las capas nuevas y el campo `unidad` (barrio, celda de 100 m, punto) |
| 3 | Ficha de inmueble con la sección «Según tus prioridades» | No hay ficha de inmueble: hay ficha de **barrio** con una tabla de avisos y un popup por pin | Poner los datos del aviso como columnas opcionales de la tabla y del popup del pin. No crear una vista nueva en el MVP |
| 4 | «Se registra una ciclovía a X m en línea recta» del inmueble | Ningún aviso tiene precisión declarada (`location_accuracy_m` vacío en el 100 %). `usable_pin` es siempre falso, y la regla del proyecto exige precisión declarada para analizar el entorno de un aviso (`ubicacion.py`) | **Decisión del usuario (2026-11-17): se muestran distancias por aviso**, porque los pines funcionan bien en la práctica. Se calculan desde el punto que publica la fuente y se rotulan así. La regla de precisión declarada sigue rigiendo solo para el cruce con delitos (`usable_pin`) |
| 5 | Separar `distancia_en_linea_recta_m` de `distancia_por_red_m` | El proyecto calcula distancias planas o por haversine (`concentracion.distance_m`). No hay ruteo ni presupuesto para él | Eliminar `distancia_por_red_m`. Toda distancia es en línea recta y se rotula así |
| 6 | ~7.100 avisos | Activos al 2026-11-17: 4.257 de venta + 3.356 de alquiler = **7.613** | Actualizar el número y medir sobre activos |
| 7 | Perfil «Con mascota» | No se extrae la admisión de mascotas y la descripción no se guarda | **Descartado por decisión del usuario** (2026-11-17) |
| 8 | Familia y Accesibilidad para después | Familia usa solo capas que ya existen (escuelas por nivel, CeSAC, hospitales, plazas). Accesibilidad tiene `subte_accesible` cargado | Familia entra en el MVP. Bicicleta pasa a la segunda etapa porque necesita dos fuentes nuevas |
| 9 | «Primera mudanza» con costo total | `costoMensual()` en `app.js` ya suma por moneda sin convertir y avisa «Falta informar expensas» | Reutilizar esa función. Renombrar el atajo a «Costo mensual» (es una necesidad, no una etapa de vida) |
| 10 | Feature flag «o equivalente» | No hay sistema de flags. El precedente es `#abrir-preferencias-texto`, oculto con `hidden` | Constante `EXPLORADOR` en `app.js` más `?explorador=1` para probar en producción sin mostrarlo |
| 11 | Tests «a localizar» | Python con `unittest` y JS con `node:test` en una VM sin navegador (`tests/test_web_delitos.cjs`) | `resolverNecesidades()` va en `app.js` como función pura y se prueba en `tests/test_web_necesidades.cjs`. Verificar con los dos comandos (§5) |
| 12 | Sin ML | Existe un intérprete de texto (`/api/preferencias/interpretar`, oculto) que ya marca «mascotas», «balcón» y «expensas» como `no_soportadas` | No tocarlo en el MVP. Más adelante, mapear esas condiciones a necesidades del catálogo |

Lo que la propuesta tenía bien y se mantiene: sin puntajes ni rankings, filtros excluyentes solo a pedido, «no informado» en lugar de «no tiene», precios de publicación, sin persistencia remota de perfiles, sin cambios en Apify ni Make.

---

## 1. Principios (sin cambios de fondo)

- Reutilizar lo que hay: FastAPI (`precio_entorno/api.py`), web estática sin build (`web/`, MapLibre 4.7.1), capas en `data/processed/entorno/`, despliegue con `scripts/preparar_vercel.py`.
- Solo fuentes abiertas o autorizadas. BA Data es CC-BY 2.5 AR. OSM es ODbL y ya se atribuye en la ficha (gastronomía y gimnasios). Nada de Google Places pago ni de calificaciones scrapeadas.
- Presupuesto: el MVP no gasta Apify, no suma operaciones de Make y no agrega funciones a Vercel.
- Sin puntajes, sin recomendaciones demográficas, sin garantías de seguridad ni de accesibilidad.
- Los datos ficticios quedan separados: en modo «Ejemplo» la sección de necesidades muestra solo capas reales y avisa que los avisos son ficticios (franja actual).
- Los atajos son combinaciones de capas y columnas que la persona puede editar. No son identidades.

---

## 2. Factibilidad: estado verificado y lo que falta

**Entregable:** `docs/feasibility_explorador_necesidades.md`, con el formato del final. No se toca código de producción en esta fase.

### 2.1 Datos urbanos

| Variable | Fuente | Estado al 2026-11-17 | Unidad | Vigencia | Decisión preliminar |
|---|---|---|---|---|---|
| Subte | BA Data · SBASE | **En la app** (capa y resumen) | Estación | Red publicada | Aprobada |
| Subte accesible | BA Data · `estaciones-accesibles.csv` | **Descargada**, sin capa en la UI | Estación | Ascensores y escaleras informados | Aprobada con advertencia: un ascensor fuera de servicio no figura |
| Colectivos | BA Data · GTFS | **En `resumen.json`** (líneas por barrio) | Recorrido | **Feed de sep.–dic. 2019** | Aprobada con advertencia fuerte: «fuente_desactualizada»; solo lista de líneas, nunca frecuencia |
| Plazas y parques | BA Data · espacios verdes | **En la app** | Polígono | Inventario oficial | Aprobada |
| Escuelas por nivel | BA Data · Mapa Escolar | **En la app** | Punto | — | Aprobada (nota existente: cercanía ≠ vacante) |
| CeSAC y hospitales | BA Data · Salud | **En la app** | Punto | — | Aprobada (nota: cercanía ≠ turno) |
| Ruido diurno y nocturno | BA Data · APRA | **En la app** | Celda de 100 m | Edición 2025 | Aprobada (nota existente: no describe el interior) |
| Riesgo hídrico | BA Data | **En la app** | Polígono | Dic. 2020 | Aprobada |
| Clubes, polideportivos y gimnasios | BA Data y OSM | **En `resumen.json`**, sin capa en la UI | Punto | Trimestral / captura 2026-11-17 | Aprobada como conteo por barrio |
| Ciclovías | BA Data · `ciclovias.geojson` | **Verificado** (ver la factibilidad): 2.764 tramos, CC-BY-2.5-AR | Línea | 2025-03-17 | Aprobada con advertencia (etapa B) |
| Ecobici | BA Data · CSV del nuevo sistema | **Verificado**: 411 estaciones, sin campo de barrio | Punto | 2025-04-04 | Aprobada con advertencia (etapa B). La API en tiempo real está suspendida |
| Bibliotecas | BA Data · `bibliotecas.geojson` | **Verificado**: 58 puntos | Punto | 2025-03-20 | Aprobada (etapa B) |
| Rampas | BA Data · relevamientos 2011–2016 | **Verificado**: es un registro de obras de un período, no un inventario | Punto | 2016 | **Descartada** |

Para cada fuente nueva, anotar la URL del archivo (no la del portal), la fecha de relevamiento (distinta de la de publicación), la licencia, la cantidad de elementos y el peso en MB. El paquete de Vercel pesa hoy unos 61 MB (`.vercel-build`) y todo lo que entra en `data/processed/entorno` se suma.

### 2.2 Datos del aviso (activos, medidos el 2026-11-17)

| Campo | Venta (4.257) | Alquiler (3.356) | Cómo se muestra |
|---|---|---|---|
| Coordenadas | 90 % | 94 % | Distancias desde el punto publicado. Pin «publicado» o «aproximado» según `ubicacion.quality` |
| Precisión declarada | 0 % | 0 % | No bloquea las distancias del explorador; se aclara que el punto lo publica la fuente |
| Superficie total | 98 % | 73 % | Columna opcional |
| Expensas | 38 % | 77 % | «No informadas» cuando falten. En venta no se muestra hoy: sumar la columna |
| Antigüedad | 61 % | 60 % | Advertir que en Zonaprop el 27 % declara 0 años, que puede ser el valor por defecto |
| Cocheras | 52 % | 43 % | Ya en la tabla |
| Piso / estado | 1 % / 2 % | 1 % / 1 % | **Descartados**: cobertura insuficiente |
| Rasgos del texto (balcón, terraza, patio, amenities, luminoso, contrafrente, a estrenar, apto crédito) | 83 % | 63 % | 1 = «lo menciona», 0 = «el texto no lo menciona», nulo = «sin texto». **Nunca** «no tiene» |
Los rasgos ya están en la base, pero `/api/barrios/{barrio}/avisos` no los devuelve. Esa respuesta, más las distancias de §2.3, es el único cambio de backend del MVP.

### 2.3 Distancias por aviso

- Se calculan en `listings_for`, solo para los avisos del barrio pedido y solo para las capas de las necesidades activas (parámetro `capas`). No se precalculan sobre los 7.613 avisos ni se crea un endpoint.
- Método: haversine en línea recta (`concentracion.distance_m`) al punto más cercano (subte, escuela del nivel elegido, CeSAC, hospital, estación Ecobici, biblioteca). Para plazas y ciclovías, distancia al borde o al tramo más cercano (`ubicacion.distance_to_polygons_m` como base). Para el ruido, el valor de la celda de 100 m que contiene el punto.
- Se redondea a decenas de metros, para no sugerir más exactitud de la que tiene el pin.
- Avisos sin coordenadas o con pin descartado por `ubicacion.quality` (a más de 500 m del barrio): «sin ubicación», sin distancia. Avisos con pin `aproximada`: distancia con la marca «punto aproximado».
- Medir en la fase 1 el tiempo de respuesta de `listings_for` en el barrio con más avisos y más puntos (p. ej., Palermo con escuelas). Si supera unos 300 ms en Vercel, precalcular las distancias en `actualizar.py`.

### 2.4 Rendimiento y costos

- Las capas ya se piden por barrio y bbox (`/api/mapa/capas`, `point_features`) y quedan en caché en `estado.capasDatos`. Las capas nuevas entran por ese mismo endpoint: **sin endpoints nuevos**.
- Medir antes y después en la URL pública: tiempo hasta el mapa, cantidad de solicitudes al elegir un barrio con 4 necesidades activas y peso de `/api/mapa/capas` por capa. Repetir en móvil (preset 375×812).
- Vercel: verificar el peso de `.vercel-build` después de sumar capas. Si alguna capa supera unos MB (rampas), precalcular conteos por barrio en `resumen.json` y no publicar los puntos.
- Make y Apify: costo cero en el MVP. Las búsquedas guardadas y las alertas no cambian.

### 2.5 Matriz de decisión

Se mantiene la de la propuesta (legalidad, calidad de geodatos, rendimiento, costos, transparencia, privacidad, mantenibilidad), con un criterio más concreto de geodatos:

> Toda distancia por aviso se mide en línea recta desde el punto que publica la fuente y se rotula así. Sin punto utilizable, no hay distancia.

---

## 3. Catálogo de necesidades

**Entregable:** `NECESIDADES` en `web/app.js`, junto a `PREFERENCIAS`. Es configuración declarativa. Si crece, se pasa a `web/necesidades.json`; se sirve estático, sin endpoint.

### Etapa A: MVP, solo con datos que ya existen

| id | Etiqueta en la UI | Capas | Datos del barrio | Columnas del aviso | Advertencias | No inferir |
|---|---|---|---|---|---|---|
| `sin_auto` | Me muevo sin auto | `subte`, `subte_accesible`* | Líneas de subte; líneas de colectivo (GTFS 2019) | Distancia al subte más cercano (y su línea) | Conectividad, no tiempos de viaje. Colectivos: recorridos de 2019 | Frecuencia ni calidad del transporte |
| `familia` | Escuelas y salud cerca | `escuelas` (con nivel), `salud`, `verdes` | Escuelas por nivel y gestión; CeSAC; hospitales; plazas | Distancia a la escuela del nivel, al CeSAC, al hospital y a la plaza más cercanos; ambientes, superficie, patio, balcón | Cercanía ≠ vacante ni turno | «Barrio familiar» |
| `teletrabajo` | Trabajo desde casa | `ruido` (diurno) | % de celdas de 70 dBA o más | Ruido de día de la celda del punto; ambientes, superficie, luminoso, contrafrente | Ruido exterior en la calle; no describe el interior | Silencio ni lugar de trabajo en la vivienda |
| `costo_mensual` | Quiero ver el costo mensual | — | — | Precio publicado, expensas, cocheras | Subtotal por moneda, sin conversión. «Falta informar expensas» | Costo total si faltan datos |

\* `subte_accesible` requiere sumar la capa a la UI: el dato ya está en `fuentes.json`.

### Etapa B: fuentes nuevas de BA Data (después de aprobarlas en la fase 1)

| id | Capas nuevas | Advertencias |
|---|---|---|
| `bicicleta` | `ciclovias` (líneas), `ecobici` (estaciones, listado estático); distancia a la ciclovía y a la estación más cercanas | Que haya ciclovía cerca no garantiza un recorrido continuo ni protegido |
| `teletrabajo` y `estudio` | `bibliotecas`; distancia a la más cercana | Horarios y servicios por confirmar con cada biblioteca |

### Etapa C: después de validar

Las condiciones `no_soportadas` del intérprete de texto, mapeadas a necesidades.

**Descartado:** accesibilidad por rampas (los datos de BA Data son un registro de obras de 2011–2016, no un inventario; queda solo el subte accesible), «Con mascota» (decisión del usuario), «conectividad» para Estudio (no hay fuente abierta por dirección), piso y estado del inmueble (1 a 2 % de cobertura), isócronas y ruteo.

---

## 4. Reglas: función pura, sin puntajes

```js
// web/app.js
function resolverNecesidades(seleccion, manual) {
  // seleccion: ids de NECESIDADES; manual: { encendidas: Set, apagadas: Set }
  // → { capas, columnas, datosBarrio, advertencias, origen }
}
```

- `capas` = (unión de las capas de cada necesidad ∪ `manual.encendidas`) − `manual.apagadas`. Sin duplicados.
- `origen[capa]` = las necesidades que la sugieren o `'manual'`, para mostrar «Sugerida por: Me muevo sin auto».
- `advertencias` se toman de `NOTAS` (no se duplican textos) más las propias de cada necesidad.
- Ninguna necesidad agrega filtros. Los filtros siguen siendo los del formulario (presupuesto, superficie, ambientes). «Trabajo desde casa» **no** cambia ambientes.
- `columnas` incluye las distancias que pide cada necesidad (`dist_subte_m`, `dist_escuela_m`, etc.). El cliente las pide a `listings_for` con `capas=` y no las calcula.
- Estados de cada valor: `disponible`, `no_informado` (nulo), `no_mencionado` (rasgo = 0), `sin_ubicacion`, `ubicacion_aproximada`, `fuente_desactualizada` (colectivos). No se agrega `no_aplicable` mientras no tenga un caso real.

**Cambio de comportamiento necesario:** hoy `seleccionar()` hace `estado.capas = new Set(estado.prefs)` y pierde lo que la persona encendió o apagó a mano en los chips al cambiar de barrio. Para que gane la elección manual, `estado.capas` pasa a calcularse con `resolverNecesidades(estado.necesidades, estado.manual)`, y los chips escriben en `estado.manual`.

**Compatibilidad:** `estado.prefs` (capas sueltas) sigue funcionando. Las preferencias guardadas en `localStorage` se leen como `manual.encendidas`. No hay migración remota porque no hay persistencia remota.

---

## 5. Integración técnica

Orden de los PR, chicos y revisables:

1. **PR 1 · Datos del aviso en la API.** `listings_for` suma `rasgos` (ocho indicadores 1/0/nulo), `antiguedad`, `expensas` también en venta y, con el parámetro opcional `capas`, las distancias de §2.3 y el ruido de la celda. Pruebas en `tests/test_api.py`: nulo ≠ 0, el modo demo no inventa rasgos, aviso sin ubicación → sin distancia, distancia conocida en un caso armado a mano, redondeo a decenas. Sin cambios de UI.
2. **PR 2 · Catálogo y reglas.** `NECESIDADES` y `resolverNecesidades()` en `app.js`, detrás de `EXPLORADOR` / `?explorador=1`. `tests/test_web_necesidades.cjs`, con el mismo arnés `vm` de `test_web_delitos.cjs`, cubre: ninguna, una o varias necesidades; la elección manual que gana; apagar y volver a encender; capas sin duplicados.
3. **PR 3 · Interfaz.** Dentro de `#importa`, un grupo «Necesidades» (casillas con descripción breve) sobre las capas sueltas que ya existen. Muestra en vivo qué capas y columnas se activan. Botón «Restablecer». La tabla de avisos suma las columnas pedidas y el popup del pin, los rasgos mencionados. Sección «Según lo que elegiste» en la ficha de barrio, con hechos y advertencias lado a lado.
4. **PR 4 · Subte accesible** (hecho): en lugar de una capa aparte, la capa de subte marca con borde oscuro las estaciones con ascensores informados (`elevators` en `puntos.json`) y la cercanía suma la estación con ascensor más cercana, columna de «Me muevo sin auto».
5. **Etapa B** (hecha; ciclovías, Ecobici y bibliotecas como capas opcionales de `entorno.py`, con la necesidad «Me muevo en bici» y bibliotecas en «Trabajo desde casa»): `ciclovias`, `ecobici` y `bibliotecas` en `entorno.py` (`SOURCES`, conversión, `fuentes.json`, conteos en `resumen.json`), pruebas en `tests/test_entorno.py`, regenerar con `python -m precio_entorno.entorno` y desplegar con `python scripts/preparar_vercel.py --desplegar`.

Verificación de cada PR:

```powershell
python -m unittest discover -s tests -v
node --test tests/test_web_delitos.cjs tests/test_web_necesidades.cjs
```

Además, revisar en el navegador con `python -m precio_entorno.api`: escritorio, móvil, teclado y modos Ejemplo y Reales.

**Fuera del MVP:** distancias por red peatonal, ruteo e isócronas, ML, cambios al intérprete de texto, cambios al Actor de Apify, escenarios o disparadores nuevos de Make, necesidades guardadas en las búsquedas o las alertas, endpoints nuevos.

**Despliegue:** mergear no despliega. Hay que correr `python scripts/preparar_vercel.py --desplegar` (empaqueta lo confirmado en `HEAD`).

---

## 6. Microcopy

| Correcto | Incorrecto |
|---|---|
| «En Almagro hay 5 estaciones de subte (líneas A y B).» | «Ideal sin auto.» |
| «Ciclovía a unos 120 m en línea recta del punto que publica el aviso.» | «Ciclovía a 120 m» (sin método) o «A 2 cuadras de la ciclovía». |
| «Sin ubicación publicada: no se calcula la distancia.» | «Lejos del subte.» |
| «El texto del aviso menciona balcón.» | «Tiene balcón.» |
| «Ruido de día de 70 dBA o más en el 82 % de las celdas relevadas (edición 2025).» | «Barrio ruidoso para teletrabajar.» |
| «Subtotal conocido: USD 120.000 + ARS 95.000 por mes. Falta informar expensas.» | «Costo total: USD 120.066.» |
| «Líneas de colectivo según recorridos de 2019. Confirmá el recorrido vigente.» | «Te llevan 43 líneas.» |

---

## 7. Validación y QA

### Pruebas técnicas

- Ninguna, una y varias necesidades; activar y desactivar repetido; cambiar de barrio sin perder la elección manual.
- Avisos sin coordenadas, sin expensas, sin superficie total, con rasgos nulos y con rasgos en 0.
- Capas vacías en un barrio y fuentes desactualizadas (colectivos): mensaje explícito y sin errores en consola.
- Regresión: filtros, «Describí tu búsqueda» (oculto), Mis alertas, alta con mail hacia Make (sin enviar en las pruebas), estacionamientos y cocheras, delitos y radar.
- Rendimiento contra la base medida en §2.4.
- Atribución de cada capa nueva en «Fuentes del entorno».

### Validación con 5 personas

Se mantiene la propuesta: tres avisos sin y con el explorador, orden alternado, tiempo, comprensión y qué dato se tomó como certeza. Registrar en `docs/plantillas/registro-validacion.csv` (o una copia con las mismas columnas) para no inventar otro formato. Cinco entrevistas sirven para detectar confusiones, no para probar mejoras.

### Criterios de aceptación

Los de la propuesta, más:

- Toda distancia por aviso dice «en línea recta» y «desde el punto que publica el aviso»; los avisos sin ubicación no muestran distancia.
- Ningún rasgo en 0 aparece como «no tiene».
- Con `EXPLORADOR` apagado, la app se comporta igual que antes (prueba de regresión del panel).

---

## 8. Lanzamiento

1. Publicar con `EXPLORADOR = false` y probar en producción con `?explorador=1`.
2. Encenderlo por defecto después de la validación. Volver atrás = cambiar la constante y redesplegar.
3. Revisar los errores de consola y API de Vercel en la primera semana, sin registrar datos personales.
4. Después: etapa B, etapa C y alertas enriquecidas solo si se confirma la identidad estable de los avisos y hay margen de operaciones en Make Free.

---

## Formato del informe de factibilidad

```markdown
# Factibilidad — Explorador de necesidades

## Estado verificado del repositorio
- Componentes reutilizables:
- Componentes faltantes:
- Riesgos de integración:

## Datos y permisos
| Variable | Archivo exacto (URL) | Licencia | Fecha de relevamiento | Cobertura / elementos | Peso | Decisión |
|---|---|---|---|---|---|---|

## Costos y rendimiento
- Estado base medido (URL pública, escritorio y móvil):
- Incremento probado:
- Peso de .vercel-build antes y después:

## Alcance aprobado
- Necesidades incluidas:
- Capas y columnas:
- Excluido o postergado:

## Decisión
GO / GO CON ALCANCE REDUCIDO / NO-GO
Fundamento:
Bloqueantes:
Próximo paso autorizado:
```
