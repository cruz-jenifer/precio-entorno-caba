# Factibilidad: explorador de necesidades

**Fecha:** 2026-11-17 · **Plan evaluado:** [plan-explorador-necesidades.md](plan-explorador-necesidades.md) · **Alcance de esta fase:** sin cambios en el código de producción.

## Cómo se verificó

- **Repositorio:** lectura de `web/app.js`, `web/index.html`, `precio_entorno/api.py`, `entorno.py`, `ubicacion.py`, `importing.py`, `descripcion.py`, `store.py`, `vercel_app.py` y `scripts/preparar_vercel.py`.
- **Bases:** consultas sobre `data/local/real.sqlite3` y `real-alquiler.sqlite3` (avisos con `status = 'activo'`).
- **Fichas de los datasets:** la API de CKAN de BA Data (`/api/3/action/package_show`), leída desde el navegador integrado. El portal rechaza a los clientes automáticos («Request Rejected»), así que no se usó `curl` contra el portal.
- **Archivos:** descargados del CDN `cdn.buenosaires.gob.ar/datosabiertos/datasets/`, el mismo origen que usa `entorno.py`, a una carpeta temporal fuera del repositorio.
- **Rendimiento:** medido con `curl` contra https://precio-entorno-caba.vercel.app, dos pedidos por ruta.

## Estado verificado del repositorio

**Componentes reutilizables**
- Panel «Lo que me importa» (`PREFERENCIAS`, `estado.prefs`, `localStorage` `precio-entorno-filtros`).
- `NOTAS`, una advertencia por capa.
- `fuentes.json`, `/api/fuentes` y el diálogo «Fuentes del entorno».
- `/api/mapa/capas`: capas por barrio y bbox, con caché en el cliente (`estado.capasDatos`).
- `ubicacion.quality` (`publicada`, `aproximada` o `None`).
- `costoMensual()`.
- Los rasgos de la descripción en `listing_details`.
- El arnés `node:test` de `tests/test_web_delitos.cjs`.
- La constante de UI oculta como mecanismo de *flag* (precedente: `#abrir-preferencias-texto`).

**Componentes faltantes**
- Catálogo `NECESIDADES` y la función `resolverNecesidades()`.
- Rasgos, antigüedad, expensas de venta y distancias en la respuesta de `/api/barrios/{barrio}/avisos`.
- `estado.manual`, para que la elección manual sobreviva al cambio de barrio. Hoy `seleccionar()` la pisa con `estado.prefs`.
- La capa `subte_accesible` en la UI.
- En `entorno.py`, las capas `ciclovias`, `ecobici` y `bibliotecas`.

**Riesgos de integración**
- `web/app.js` tiene 1.728 líneas en un solo archivo. El catálogo y las reglas conviene agregarlos como bloque aparte, cerca de `PREFERENCIAS`.
- El paso de `prefs` a `manual` tiene que leer lo que ya está guardado en `localStorage` sin perder preferencias.

## Ubicación de los avisos (activos)

| Base | Activos | `publicada` | `aproximada` | Sin ubicación usable |
|---|---|---|---|---|
| Venta | 4.257 | 3.590 (84 %) | 135 (3 %) | 532 (12 %) |
| Alquiler | 3.356 | 2.937 (88 %) | 139 (4 %) | 280 (8 %) |

Barrios con 30 avisos o más y menor cobertura (venta + alquiler): Villa Crespo 65 % (321 avisos), Almagro 67 % (340), Floresta 74 % (125), Palermo 81 % (643), Balvanera 83 % (260) y Villa Soldati 84 % (56). En esos barrios, la sección «Según lo que elegiste» tiene que decir cuántos avisos quedan sin distancia.

## Datos y permisos

Todas las fichas consultadas declaran licencia **CC-BY-2.5-AR**.

| Variable | Archivo exacto | Fecha del recurso | Elementos | Peso | Observaciones | Decisión |
|---|---|---|---|---|---|---|
| Subte, escuelas, salud, plazas, ruido, riesgo | Ya en `fuentes.json` | Ver `fuentes.json` | — | — | En la app | **Aprobada** |
| Subte accesible | Ya descargado (`estaciones-accesibles.csv`) | Según SBASE | 90 estaciones con ascensores informados | — | Falta solo la capa en la UI | **Aprobada con advertencia** (un ascensor fuera de servicio no figura) |
| Colectivos | GTFS ya descargado | Calendario sep.–dic. 2019 | Líneas por barrio | — | La ficha `api-transporte-publico` (modificada el 2026-06-17) dice que **todos los datasets con formato API y GTFS están suspendidos** «en revisión y corrección» | **Aprobada con advertencia fuerte**: solo la lista de líneas, rotulada «recorridos de 2019» |
| Ciclovías | `transporte-y-obras-publicas/ciclovias/ciclovias.geojson` | 2025-03-17 (actualización semestral declarada) | 2.764 tramos `LineString` en WGS84. Atributos: `nombre`, `tipo` (2.469 «Ciclovías» y 295 «Ciclovías mano única»), `barrio`, `comuna`, `longitud_m` | 960 KB crudo | No indica si cada tramo es bidireccional ni si está protegido | **Aprobada con advertencia** |
| Ecobici (estaciones) | `…/estaciones-bicicletas-publicas/badata_ecobici_estaciones_bicicletas_nuevo_sistema.csv` | 2025-04-04 | 411 estaciones (`latitud`, `longitud`, `nombre`, `direccion`). El campo `barrio` viene vacío | 32 KB | El GeoJSON del mismo dataset tiene 471 estaciones pero es de 2020-11: **se usa el CSV de 2025** y el barrio se asigna por polígono. No informa si la estación está operativa; la API en tiempo real está suspendida | **Aprobada con advertencia** |
| Bibliotecas | `ministerio-de-cultura/bibliotecas/bibliotecas.geojson` | 2025-03-20 | 58 puntos (Red de Bibliotecas del GCBA, incluidas las populares) | 28 KB | Trae teléfono y correo institucionales: se muestran solo nombre, tipo y dirección | **Aprobada** |
| Rampas | `…/rampas-accesibilidad/rampas-de-accesibilidad-relevamiento-2016.csv` (y relevamientos 2011 y 2012–2014) | Relevamientos 2011–2016, publicados en 2019 | 2.955 filas en 2016, con `MES`, `SEMANA`, `ZONA` y `ESTADO = FINALIZADO` | 380 KB | Es un **registro de obras de un período, no un inventario** de la ciudad. Tiene casi 10 años | **Descartada**: no permite afirmar «hay rampas» ni «no hay rampas» |
| Rasgos del aviso | `listing_details` | Fecha de cada captura | Venta 83 %, alquiler 63 % | — | 1 = lo menciona, 0 = no lo menciona, nulo = sin texto | **Aprobada** |
| Expensas | `listing_details.expenses` | Fecha de cada captura | Venta 38 %, alquiler 77 % | — | — | **Aprobada** («no informadas») |
| Antigüedad | `listing_details.age_years` | Fecha de cada captura | 61 % y 60 % | — | En Zonaprop, el 27 % declara 0 años | **Aprobada con advertencia** |
| Piso y estado | `listing_details` | — | 1 a 2 % | — | — | **Descartadas** |

## Costos y rendimiento

**Estado base medido (escritorio, `curl`, 2026-11-17)**

| Ruta | Tamaño (sin compresión → gzip) | Tiempo |
|---|---|---|
| `/` + `app.js` | 7 KB + 106 KB | 0,2–0,5 s |
| `/api/estado` | 375 B | **3,1 s en frío**, 0,6 s en caliente |
| `/api/barrios` (venta) | 35 KB | 0,43–0,45 s |
| `/api/mapa/barrios` | 298 KB | 0,72–0,75 s |
| `/api/barrios/Palermo/avisos` (sin filtros, 359 avisos) | 13,7 KB gzip | 0,62 s |
| `/api/mapa/capas` Palermo: subte + plazas (las predeterminadas) | 1,70 MB → **259 KB** | 1,2–1,5 s |
| `/api/mapa/capas` Palermo: las 6 capas de preferencias | 2,44 MB → **319 KB** | 1,5–1,8 s |
| `/api/mapa/capas` Palermo: estacionamiento | 577 KB | 0,45–0,62 s |

**Incremento esperado (medido en local)**
- **Distancias por aviso:** la más cercana a cada capa, para los 6.801 avisos con pin, tarda 19 ms en subte, 386 ms en escuelas (1.627 puntos), 10 ms en CeSAC y 7 ms en hospitales. Un pedido de un solo barrio es unas 10 veces menor (Palermo: unos 650 avisos entre las dos bases), así que **no hace falta precalcular**. Medianas: subte 697 m, escuela 164 m, CeSAC 1.148 m, hospital 1.167 m.
- **Capas nuevas:** unos 1,0 MB de archivos crudos en total. Procesadas y filtradas por bbox de barrio, se estiman unas decenas de KB por pedido. Se confirma al implementar la etapa B.
- **Paquete de Vercel:** unos 61 MB hoy, más alrededor de 1 MB.
- **Make y Apify:** cero. Ninguna parte del explorador los usa.

**Límites relevantes**
- El cuello actual es `/api/mapa/capas` con plazas: se descargan 1,7 MB antes de comprimir. No depende del explorador, pero activar varias necesidades a la vez lo hace más visible. Conviene simplificar la geometría de `verdes` (redondear coordenadas y reducir vértices) en el mismo PR de la etapa B.
- El arranque en frío (3 s) existe hoy y no cambia.

**Pendiente:** medir en móvil (pane del navegador con el preset 375×812) antes y después del PR 3.

## Alcance aprobado

- **Necesidades, etapa A:** Me muevo sin auto, Escuelas y salud cerca, Trabajo desde casa, Costo mensual.
- **Necesidades, etapa B:** Uso bici (ciclovías + estaciones Ecobici 2025) y bibliotecas para Trabajo desde casa / Estudio.
- **Capas y columnas:** las del plan, con distancias por aviso en línea recta desde el punto publicado.
- **Excluido o postergado:**
  - **Accesibilidad por rampas** (descartada; los datos no son un inventario). Queda solo el subte accesible.
  - Con mascota (decisión del usuario).
  - Piso y estado.
  - Conectividad.
  - Frecuencia del transporte (GTFS suspendido y desactualizado).

## Decisión

**GO CON ALCANCE REDUCIDO**

**Fundamento**
- Las capas de la etapa A ya están en producción.
- Las tres fuentes nuevas de la etapa B tienen licencia CC-BY-2.5-AR, archivos de 2025 y poco peso.
- Las distancias por aviso cuestan decenas de milisegundos por pedido.
- No hay costo en Apify, Make ni Vercel.
- La reducción es una sola: queda afuera la accesibilidad por rampas.

**Bloqueantes:** ninguno para la etapa A.

**Próximo paso autorizado:** PR 1 del plan (rasgos, antigüedad, expensas y distancias en `/api/barrios/{barrio}/avisos`, con pruebas).
