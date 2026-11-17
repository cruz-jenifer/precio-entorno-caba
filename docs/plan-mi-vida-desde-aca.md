# Plan de implementación: «Mi vida desde acá»

**Proyecto:** Precio y Entorno CABA
**Objetivo:** la persona marca hasta 3 lugares habituales (trabajo, facultad, familia) y ve, para cada aviso del barrio, el tiempo estimado **a pie o en bicicleta** por calles, calculado sobre la red de OpenStreetMap.
**Estado:** plan revisado el 2026-11-17 contra el código de `main` + `tratamiento-nulls` y contra las decisiones del usuario. Reemplaza a la propuesta original («Implementation Plan — Mi vida desde acá»). Se avanza por fases con *gates*, no por fechas.

---

## 0. Qué cambió respecto de la propuesta original

| # | Propuesta original | Lo que hay en el repositorio o lo que se decidió | Corrección |
|---|---|---|---|
| 1 | Motor principal: ORS hospedado (piloto) o Valhalla. Grafo propio solo como *fallback* | No hay servidor propio. Vercel corre una función Python con disco de solo lectura salvo `/tmp`: no puede alojar Valhalla, OSRM ni OpenTripPlanner. ORS hospedado exige crear una cuenta, tiene cuotas diarias y recibe los destinos personales | **El motor principal pasa a ser un grafo propio**, armado offline con OSM y consultado en FastAPI. Sin cuotas, sin claves y sin enviar destinos a terceros. ORS queda solo para validar en la fase 1 |
| 2 | Calcular pares origen-destino (2.000 por día) o matrices | Son pocos destinos (≤ 3) y muchos avisos | **Un Dijkstra por destino** da el tiempo a todos los avisos del barrio de una vez. El costo es CPU por pedido, no cantidad de pares. Para bicicleta se corre sobre el grafo invertido, porque respeta los sentidos de circulación |
| 3 | Distinguir pin verificado, pin aproximado, centroide y sin ubicación | No hay pines «verificados» ni centroides. `ubicacion.quality` clasifica `publicada` (dentro del barrio o a < 150 m), `aproximada` (150–500 m) o `None`. Hay coordenadas en el 90 % de los avisos de venta y el 94 % de alquiler. El usuario decidió (2026-11-17) que estas ubicaciones alcanzan | Origen = punto publicado. `aproximada` lleva marca. `None` → «sin ubicación», sin tiempo |
| 4 | Tres clases: `route_estimate`, `approximate_estimate` (haversine × k) y `unavailable` | El explorador de necesidades ya muestra distancias en línea recta, en metros y rotuladas así | Eliminar `approximate_estimate`: no se convierten líneas rectas en minutos. Quedan `ruta` y `no_disponible` |
| 5 | Endpoints `/api/v1/life/route` y `/api/v1/life/compare` | La API usa rutas en castellano y sin versión (`/api/barrios/{barrio}/avisos`, `/api/cocheras`) | `POST /api/barrios/{barrio}/viajes` y `POST /api/viajes/recorrido` (§5). POST para que las coordenadas no queden en la URL ni en los logs |
| 6 | «Ficha de inmueble» y un comparador A/B | Hay ficha de barrio, con tabla de avisos y popup por pin | Una columna por destino en la tabla y en el popup. La tabla ya compara todos los avisos del barrio. El comparador A/B se posterga |
| 7 | Destinos en cualquier lugar | El área del proyecto es CABA (`BBOX` en `osm_apify.py`) | El grafo cubre CABA más un margen de unos 2 km. Un destino fuera de esa zona (p. ej., un trabajo en el conurbano) → «fuera de cobertura». Ampliar la red es una decisión de la fase 1 por su peso |
| 8 | Búsqueda de ubicación «compatible con fuentes permitidas» | No hay geocodificación. Hay un patrón de origen reutilizable: «Mi ubicación actual», «El centro del mapa» y «Aviso X» (`camposOrigen`, `puntoDeBusqueda`) | MVP: clic en el mapa, centro del mapa o mi ubicación. Después: el normalizador de direcciones de USIG (GCBA), que respondió 200 al probarlo; sus términos están por verificar. Nominatim no, porque su política prohíbe el autocompletado |
| 9 | Política de teselas de OSMF | El mapa usa MapLibre 4.7.1 con el estilo Positron de Carto, no teselas de OSMF | Sin cambios de mapa base. La línea de la ruta se dibuja como capa GeoJSON, igual que las que ya existen |
| 10 | Validar con 20 pares contra tiempos cronometrados | El tiempo es la distancia por la red dividida por una velocidad supuesta | Validar por separado **la distancia por la red** (contra ORS y una revisión manual en osm.org) y **la velocidad** (pocos recorridos cronometrados). Así se sabe de dónde viene el error |
| 11 | Transporte público con OpenTripPlanner, en investigación | El GTFS de colectivos del repositorio tiene calendario de **sep.–dic. 2019** (`fuentes.json`). OTP necesita un servidor Java. **Confirmado** en la ficha `api-transporte-publico` (modificada el 2026-06-17): todos los datasets con formato API y GTFS están suspendidos | Se mantiene fuera, sin cambios. Se sigue mostrando la lista de líneas como contexto, con su fecha |

Lo que la propuesta tenía bien y se mantiene: no es navegación en tiempo real; sin Google Routes ni scraping de Google Maps; nada de destinos en Make, Sheets ni alertas; si el motor falla, «no disponible» y no una línea recta en silencio; minutos redondeados y rotulados «estimado»; sin puntaje sintético; pruebas con fixtures, sin red en CI.

---

## 1. Principios

- Reutilizar lo que hay: FastAPI (`precio_entorno/api.py`), la web estática sin build (`web/`), las capas y el despliegue con `scripts/preparar_vercel.py`.
- Costo cero en producción: sin APIs pagas, sin claves nuevas, sin Apify ni Make. La red se descarga una vez, gratis, desde OSM.
- **Los destinos personales no salen del servidor del proyecto ni se guardan en él.** El servidor recibe solo coordenadas (nunca el nombre «Trabajo») y responde por índice de destino.
- OSM es ODbL. La atribución «© colaboradores de OpenStreetMap» va junto a cada tiempo, como ya pasa con gastronomía y gimnasios. El grafo derivado no se publica como descarga.
- No se usa para certificar accesibilidad. No hay perfil para silla de ruedas en el MVP.

---

## 2. Fase 1: factibilidad (gate obligatorio)

**Entregable:** `docs/feasibility_mi_vida_desde_aca.md`. Las pruebas se hacen con scripts en `scripts/` o en el scratchpad, **sin tocar código de producción**.

### 2.1 Estado verificado del repositorio

| Pregunta de la propuesta | Respuesta al 2026-11-17 |
|---|---|
| Frontend y mapa | Vanilla JS sin build, MapLibre 4.7.1, Carto Positron. Ya dibuja capas GeoJSON de tipo `line`, `fill` y `circle` |
| Backend y despliegue | FastAPI. En Vercel corre una función Python (`vercel_app.py`) con dependencias `fastapi`, `numpy`, `matplotlib` y `httpx`. El paquete pesa unos 61 MB |
| Identificador del aviso | `listings.id` con prefijo de fuente (`zonaprop:`, `mob:`…). Estable entre capturas |
| Coordenadas | 90 % en venta (3.823 de 4.257) y 94 % en alquiler (3.152 de 3.356), con la calidad de `ubicacion.quality` |
| Persistencia del lado del cliente | `localStorage` (`precio-entorno-filtros`) con `try/catch`. Patrón reutilizable para los destinos |
| Make y Apify | Sin relación con esta función. No se tocan |
| Herramientas locales | `networkx` 3.6.1 y `scipy` 1.16.3 están instalados localmente (sirven para validar), pero **no** en el despliegue. `osmnx` no está |

### 2.2 Red de calles

- **Fuente:** OSM. Una sola descarga con Overpass (consulta de `highway=*` en el BBOX de CABA más el margen, respetando su política de uso) o el extracto de BBBike para Buenos Aires (la página responde). Registrar fecha, URL, SHA-256 y licencia en `fuentes.json`, como las demás capas.
- **Preprocesamiento offline** (módulo nuevo `precio_entorno/red.py`, solo con la biblioteca estándar y `numpy`):
  - Nodos (lat, lon) y aristas en formato CSR con longitud en metros y banderas `a_pie`, `bici`, `sentido_unico_bici` y `ciclovia`.
  - A pie: grafo no dirigido. Incluye `footway`, `pedestrian`, `path`, `steps` y calles. Excluye `motorway` y `trunk`, salvo que tengan `foot=yes`.
  - Bicicleta: grafo dirigido. Respeta `oneway`, salvo `oneway:bicycle=no` o ciclovía a contramano. Excluye `footway` salvo `bicycle=yes`, y las autopistas.
  - Salida: `data/processed/red/red_caba.npz` más su entrada en `fuentes.json`.
- **Medir:** cantidad de nodos y aristas, peso del `.npz` (objetivo: < 20 MB) y cobertura en una muestra de pasajes, puentes sobre las vías, Puerto Madero, Costanera, Ciudad Universitaria y cruces de la General Paz.

### 2.3 Rendimiento (lo que decide el gate)

- Dijkstra con `heapq` sobre los arrays de `numpy`, con corte temprano al alcanzar todos los nodos de los avisos del barrio o un tope de 60 min.
- Medir en local y **en Vercel** (con un endpoint de prueba en una *preview*, no en producción):
  - arranque en frío con la red cargada;
  - tiempo por destino en el barrio con más avisos y para el destino más lejano dentro de CABA;
  - memoria.
- Umbral sugerido: ≤ 1,5 s por pedido con 3 destinos en el peor caso. Si no se alcanza, en este orden:
  1. Caché en memoria por instancia: (destino redondeado a 25 m, modo) → tiempos por nodo. Es efímera y no se escribe a disco.
  2. `scipy.sparse.csgraph.dijkstra`. Agrega `scipy` al despliegue: medir cuánto pesa el paquete.
  3. Reducir el grafo: contraer los nodos de grado 2 sin perder longitud.
- Verificar los límites vigentes del plan de Vercel (duración, memoria, tamaño de la función e invocaciones incluidas).

### 2.4 Precisión

- **Muestra fija antes de mirar resultados:** 20 pares avisos → destinos repartidos por CABA (centro y periferia, cortos y largos, cerca de las vías, la General Paz, el Riachuelo y parques grandes). Incluir 4 avisos con pin `aproximada`.
- **Distancia por la red:** comparar con ORS hospedado (requiere que el usuario cree una cuenta gratuita y cargue la clave en `.env`; uso puntual, solo pares de prueba sin datos personales) y revisar a mano en osm.org los casos con diferencia > 15 %. Métricas: mediana y p90 del error relativo, a pie y en bici por separado.
- **Velocidad:** 5 recorridos a pie y 3 en bici cronometrados por el equipo. Sirven para elegir las velocidades por defecto, no para prometer precisión.
- **Errores críticos:** rutas imposibles, cruces de vías o de autopistas inexistentes, snapping a la calle equivocada (por ejemplo, la colectora en vez de la avenida). Cero errores críticos en la muestra es condición de GO.
- Google Maps solo se puede mirar a mano para diagnosticar; no se copia ni se guarda.
- Si no hay recorridos cronometrados, la UI dice «velocidad supuesta de 4,5 km/h» y no habla de precisión.

### 2.5 Privacidad

- Ningún log con coordenadas de destino: verificar qué registran FastAPI y Vercel en un POST (no registran el cuerpo).
- La caché en memoria de §2.3 guarda coordenadas redondeadas mientras viva la instancia. Documentarlo. Si se considera excesivo, no usar caché.

### 2.6 Decisión

- **GO:** red con cobertura sin errores críticos, ≤ 1,5 s por pedido en Vercel, paquete dentro del límite.
- **GO limitado:** solo a pie, o solo 1 destino, o solo en la tabla (sin «Ver recorrido»), o calculado solo para los avisos visibles.
- **NO-GO:** Vercel no puede con la red o el error de distancia es alto. Se documenta y se sigue mostrando solo la distancia en línea recta del explorador de necesidades.

---

## 3. Contrato funcional

- **Destinos:** hasta 3, con nombre editable que **queda en el navegador**. Se cargan con un clic en el mapa, con el centro del mapa o con mi ubicación. Opción «Recordar en este navegador» (`localStorage`, clave `precio-entorno-destinos`), apagada por defecto, y botón «Borrar mis lugares».
- **Modo:** a pie (ritmo de 3,5, 4,5 o 5,5 km/h; por defecto 4,5) o bicicleta (por defecto 13 km/h, editable).
- **Resultado por aviso y destino:**
  - `estado`: `ruta` o `no_disponible`, con `motivo`: `sin_ubicacion`, `fuera_de_cobertura`, `sin_conexion_en_la_red` o `error_del_calculo`.
  - `minutos` (redondeado a 1 min por debajo de 20 y a 5 min desde 20) y `metros` (redondeado a 50 m).
  - `ubicacion`: `publicada` o `aproximada`.
  - `acceso_m`: distancia del punto publicado a la calle más cercana. Si supera 150 m → `no_disponible`.
- **Solo ida.** Se aclara «solo ida» y no se suman destinos entre sí.
- **Sin puntaje:** se puede ordenar la tabla por el tiempo a **un** destino elegido, nunca por una suma o un promedio de destinos.
- **Filtro «hasta X min»** a un destino: se puede, e indica cuántos avisos quedaron fuera por falta de ubicación.
- **Advertencias fijas:** «Tiempo estimado sobre calles de OpenStreetMap con una velocidad supuesta. No incluye semáforos, esperas, pendientes ni el estado de las veredas.» En bici, además: «Sigue el sentido de las calles; no indica si el recorrido tiene ciclovía.»

---

## 4. Fase 2: prototipo aislado

1. `precio_entorno/red.py`: construir la red (§2.2), cargarla, ubicar el nodo más cercano (grilla de celdas, como `entorno.py`), `tiempos_desde(destino, modo, nodos_objetivo, tope_min)` y `recorrido(origen, destino, modo)` → GeoJSON.
2. `tests/test_red.py`: red de juguete armada a mano (calle de mano única, escalera, autopista prohibida a pie, nodo aislado), resultados exactos, snapping, corte por tope y consistencia entre `tiempos_desde` y `recorrido`. Sin red real ni internet.
3. Script de la fase 1 que corre la muestra de 20 pares y escribe el informe.

**Gate:** el prototipo alcanza los umbrales de §2.6 con la red real.

---

## 5. Fase 3: integración en FastAPI

```text
POST /api/barrios/{barrio}/viajes
  { "modo": "a_pie" | "bici", "velocidad_kmh": 4.5,
    "destinos": [{"lat": -34.6, "lon": -58.4}],           // 1 a 3, sin nombres
    "filtros": { ...los mismos de /api/barrios/{barrio}/avisos... } }
→ { "avisos": [{ "id": "...", "viajes": [{ "destino": 0, "estado": "ruta", "minutos": 18,
                 "metros": 1350, "ubicacion": "publicada" }] }],
    "red": { "fuente": "OpenStreetMap", "fecha": "2026-11-..", "licencia": "ODbL" } }

POST /api/viajes/recorrido
  { "aviso": "zonaprop:123", "destino": {"lat": ..., "lon": ...}, "modo": "a_pie" }
→ GeoJSON LineString + minutos y metros
```

- El origen sale siempre del `id` del aviso, en el servidor.
- Validaciones con Pydantic: 1 a 3 destinos dentro del área del grafo, velocidad entre 2 y 30 km/h, barrio existente (`check_barrio`) y moneda (`check_currency`).
- Los filtros se aplican **antes** de calcular (`matches`, el mismo de `listings_for`).
- Topes: un pedido calcula solo los avisos del barrio filtrado y corta a los 60 min.
- Errores del motor → `no_disponible` con `motivo`. Nunca se usa la línea recta como reemplazo.
- Modo demo: funciona igual con los avisos ficticios y la red real, con la franja «Datos de ejemplo».
- `scripts/preparar_vercel.py`: sumar `data/processed/red` a `DATA`. Si se adopta `scipy`, sumarlo a `PYPROJECT`.
- Pruebas en `tests/test_api.py`: validación, aviso sin ubicación, destino fuera de cobertura, filtros previos y que la respuesta no contenga nombres de destinos.

---

## 6. Fase 4: interfaz

1. En la ficha de barrio, una sección «Mis lugares», con hasta 3 destinos, el modo y la velocidad. Al elegir un punto, un marcador numerado en el mapa.
2. La tabla de avisos suma una columna por destino («≈ 18 min a pie») con la marca «aprox.» si el pin es `aproximada`, y la opción de ordenar por un destino.
3. Popup del pin: los mismos tiempos y el botón «Ver recorrido», que dibuja la línea (capa `recorrido`, tipo `line`) con su atribución.
4. Filtro «hasta X min» a un destino, con el conteo de excluidos.
5. «Borrar mis lugares» limpia el estado y `localStorage`.
6. Pruebas `tests/test_web_viajes.cjs` (arnés `vm` como en `test_web_delitos.cjs`): guardar y borrar destinos, que el pedido no envíe nombres, orden por un destino y estados `no_disponible`.
7. Detrás de la constante `VIAJES` / `?viajes=1`, igual que el explorador de necesidades.

Verificación:

```powershell
python -m unittest discover -s tests -v
node --test tests/test_web_delitos.cjs tests/test_web_necesidades.cjs tests/test_web_viajes.cjs
```

Además, revisar en el navegador (escritorio y móvil). Para publicar: `python scripts/preparar_vercel.py --desplegar` (mergear no despliega).

---

## 7. Fase 5: ampliaciones opcionales

- **Alcance desde un destino:** el mismo Dijkstra da los tramos alcanzables en 15, 30 y 45 min. Se dibujan **las calles alcanzadas** (líneas), no un polígono, que sugeriría cobertura donde no hay calles. Sirve para preseleccionar barrios; no reemplaza el tiempo de cada aviso.
- **Vista de barrios:** mediana del tiempo de los avisos del barrio a un destino, junto a la mediana de precio. Es un dato por destino, no un puntaje.
- **Preferir ciclovías:** penalizar las calles sin `cycleway` en el perfil bici. Requiere validar de nuevo y explicar la regla.
- **Búsqueda por dirección con USIG**, después de verificar sus términos de uso.
- **Comparador A/B** de 2 o 3 avisos de barrios distintos.

## 8. Transporte público (fuera, sin cambios)

Se mantiene la propuesta original: no se habilita hasta tener un GTFS vigente y autorizado y un lugar donde correr OpenTripPlanner, y ninguna de las dos cosas existe hoy. Mientras tanto se siguen mostrando subte y colectivos como contexto con su fecha (el GTFS del repositorio es de 2019).

## 9. Validación con usuarios

Se mantiene la propuesta (5 personas, tareas de guardar, comparar, corregir y borrar destinos, y revisar un aviso sin ubicación). Se suma una tarea: explicar qué incluye y qué no el «tiempo estimado». Registrar en `docs/plantillas/registro-validacion.csv` o en una copia con las mismas columnas.

**Criterios de cierre:** los de la propuesta, más:
- La respuesta de la API nunca contiene nombres de destinos.
- Ningún tiempo sale de una línea recta.
- Con `VIAJES` apagado, la app se comporta igual que antes.

## 10. Riesgos

| Riesgo | Impacto | Mitigación |
|---|---|---|
| Dijkstra lento en Vercel | Pedidos de varios segundos | Corte temprano, caché por instancia, `scipy`, grafo contraído; *GO limitado* |
| Red OSM incompleta o mal etiquetada | Rutas imposibles o largas | Muestra de §2.4, revisión manual y fecha de la red visible |
| Velocidad única para todos | Sesgo por condición física | Ritmo configurable y la velocidad escrita junto al tiempo |
| Destinos fuera de CABA | Sin resultado para viajes al conurbano | «Fuera de cobertura» explícito; ampliar la red solo si el peso lo permite |
| Pin `aproximada` | Tiempo corrido unos cientos de metros | Marca «aprox.» y `acceso_m` > 150 m → no disponible |
| Paquete de Vercel muy pesado | Despliegue fallido | Medir en la fase 1; contraer el grafo o recortar el margen |
| Privacidad de los destinos | Exposición de lugares personales | Solo coordenadas en el cuerpo del POST, sin logs, sin persistencia en el servidor, nombres solo en el navegador |
| Red desactualizada | Calles nuevas o cerradas | Fecha en `fuentes.json` y en la UI; regenerar con el mismo comando que las capas |

## Instrucción para el agente

> Ejecutá solo la fase 1: medí la red, el rendimiento local y en una *preview* de Vercel, y la precisión con la muestra fija, y escribí `docs/feasibility_mi_vida_desde_aca.md` con la decisión GO / GO limitado / NO-GO. No modifiques código de producción ni agregues dependencias al despliegue. La clave de ORS para validar la crea el usuario, si la autoriza; sin ella, la validación de distancia se hace solo a mano y se informa así.
