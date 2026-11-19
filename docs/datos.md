# Contrato de datos

## Avisos vigentes

Una observación por aviso en cada captura. Conservar `source`, `listing_id`, `captured_at`, `price`, `currency`, `covered_area_m2`, `total_area_m2`, `rooms`, `neighborhood`, `latitude`, `longitude` y `url` cuando estén disponibles. Registrar las coordenadas como aproximadas si la fuente no aporta precisión verificable. Los datos del anunciante no hacen falta para el prototipo.

Para el primer análisis, trabajar con venta residencial publicada en USD, superficie cubierta positiva e inmuebles comparables. El precio por m² usa siempre superficie cubierta. Eliminar avisos duplicados y documentar cuándo dos publicaciones podrían representar un mismo inmueble. La fecha de captura permite distinguir la primera observación de una supuesta fecha de publicación.

### Catálogo consolidado de inmobiliarias

RE/MAX, Century 21 y Migliorisi autorizaron la lectura de sus sitios y se tratan como un único catálogo, `inmobiliarias-autorizadas`.

- **IDs:** cada ID lleva el prefijo de su inmobiliaria.
- **Duplicados:** se buscan posibles duplicados entre inmobiliarias con mismo barrio, ambientes, m² cubiertos redondeados y precio redondeado a miles. Se informan, pero no se eliminan.
- **Barrios:** las subzonas comerciales con un único barrio oficial se asignan a ese barrio, como Palermo Hollywood a Palermo. Las ambiguas (Congreso, Centro, Parque Centenario) quedan sin barrio y se descartan.
- **Precios de relleno:** valores como 888.888 se tratan como precio no publicado.
- **Coordenadas:** RE/MAX y Century 21 traen coordenadas sin precisión declarada, así que el cruce es por barrio salvo en el análisis de sensibilidad del modelo. Migliorisi no publica coordenadas.
- **Datos del edificio y la unidad (opcionales, desde el 9 de noviembre de 2026):** un dato inválido se informa y queda vacío, pero el aviso no se descarta.

  | Campo | Alias | Rango | Century 21 | Migliorisi | Zonaprop |
  | --- | --- | --- | --- | --- | --- |
  | `age_years` | `antiguedad` | 0 a 200 años, al momento de la captura | Sale de `construction_year`. Un año futuro (en construcción) cuenta como 0. | Sale de "Antigüedad N años" en la ficha. "A estrenar" cuenta como 0. | Sale de la característica `CFT5`. El 27 % declara 0, que puede ser el valor por defecto. |
  | `condition` | `estado` | a estrenar, en construcción, excelente, muy bueno, bueno, regular, reciclado, a reciclar | Sale de `property_condition`. «Nuevo» cuenta como a estrenar y «De pozo» como en construcción. Una etiqueta desconocida queda vacía. | No lo publica como campo. | No lo publica. |
  | `garages` | `cocheras` | 0 a 10 | Sale de `garage`. | — | Sale de `CFT7`. El listado la omite cuando es 0; se completa con la ficha. |
  | `floor` | `piso` | 0 a 80. "PB" cuenta como 0. | Sale del número inicial de `addr_floor`. | — | — |

  - **RE/MAX:** su búsqueda no publica estos campos.
  - **Zonaprop, captura del 8 de noviembre:** la antigüedad y las cocheras se tomaron releyendo los resultados de esas mismas corridas en Apify (`--releer`), sin correr el actor de nuevo. Quedaron en `data/raw/zonaprop-venta-20261108-edificio/`: 2.359 avisos, 2.218 con antigüedad. La relectura generó unos USD 0,04 de uso de plataforma en las cuentas 1 y 4, y ningún evento del actor. Apify conserva esos resultados solo por un tiempo limitado, que depende del plan, así que no siempre se puede repetir con capturas viejas.
  - **Descripciones:** el texto no se guarda. Desde el 15 de noviembre de 2026, en Zonaprop se leen de él los rasgos de la tabla siguiente.

- **Rasgos de la descripción (opcionales, desde el 15 de noviembre de 2026; Zonaprop, RE/MAX y Migliorisi):** `precio_entorno/descripcion.py` lee el título y la descripción completa de la ficha en memoria, los convierte en indicadores y descarta el texto, que suele traer teléfonos o correos del anunciante. Cada indicador vale 1 si el aviso lo menciona y 0 si hay texto pero no lo menciona o lo niega («sin balcón», «no apto crédito», «no tiene balcón»). Sin texto, queda sin dato. **Un 0 no prueba que la unidad no lo tenga:** solo indica que el aviso no lo dice. Son menciones del anunciante, no verificadas.

  | Columna | Alias | Qué cuenta | Venta | Alquiler |
  | --- | --- | --- | --- | --- |
  | `new_build` | `a_estrenar` | «a estrenar», «para estrenar», «nunca habitado» | 15 % | 10 % |
  | `needs_renovation` | `a_reciclar` | «a reciclar», «a refaccionar», «necesita refacciones». «Reciclado» no cuenta. | 2 % | 0 % |
  | `mortgage_eligible` | `apto_credito` | «apto crédito», «apto crédito hipotecario», «acepta crédito» | 20 % | 0 % |
  | `balcony` | `balcon` | «balcón» | 67 % | 63 % |
  | `terrace` | `terraza` | «terraza». Incluye terrazas comunes del edificio. | 24 % | 16 % |
  | `patio` | `patio` | «patio». «Patio de luz» o «de aire» no cuentan. | 13 % | 9 % |
  | `amenities` | `amenities` | «amenities», pileta, piscina, gimnasio, solarium, SUM | 32 % | 28 % |
  | `bright` | `luminoso` | «luminoso», «mucha luz», «excelente luminosidad» | 48 % | 52 % |
  | `rear_facing` | `contrafrente` | «contrafrente», «c/frente» | 19 % | 19 % |

  - **Relectura del 15 de noviembre:** las corridas del 8 de noviembre se releyeron con `--releer` (sin eventos del actor) en `data/raw/zonaprop-venta-20261108-descripcion-completa/` y `data/raw/zonaprop-alquiler-20261108-descripcion-completa/`, y se sumaron a las bases con `--completar-base`, que solo completa datos vacíos. Quedaron con rasgos los 2.272 avisos de Zonaprop de la base de venta y los 2.042 de la de alquiler. En la misma pasada, la base de venta sumó la antigüedad y las cocheras de Zonaprop (2.197 avisos con antigüedad), que hasta entonces solo estaban en la carpeta `-edificio`.
  - **Cuenta 4 de Apify:** su token se había invalidado, también en la conexión de Make. Con un token nuevo de esa cuenta, guardado como cuarta línea `APIFY_TOKEN` del `.env`, se leyeron sus 26 corridas (1.057 avisos). La quinta línea es otra cuenta, sin corridas.
  - **RE/MAX y Migliorisi (15 de noviembre):** las capturas leen la descripción de la ficha. En RE/MAX, el listado no la trae, así que se pide la ficha (`findBySlug`) solo de los avisos nuevos. En Migliorisi sale del bloque `div-descripcion` de la ficha, que la captura ya baja. Los avisos que ya estaban en las bases se completaron con `python -m precio_entorno.rasgos_inmobiliarias --autorizacion-confirmada --operacion venta` (y `alquiler`), que usa el mismo cliente educado, guarda solo los rasgos en `data/raw/rasgos-inmobiliarias[-alquiler]-20261115/` y no pisa datos. Quedaron con rasgos 888 de 917 avisos de RE/MAX y 389 de 394 de Migliorisi en venta, y 24 de 25 y 49 de 49 en alquiler. Los que faltan estaban dados de baja o no tenían descripción.
  - **Century 21, Clarín y Mob:** todavía sin rasgos. El 15 de noviembre la búsqueda de Century 21 respondía HTTP 504 y sus fichas venían sin la descripción en el HTML.
  - Los porcentajes de la tabla son sobre todos los avisos con descripción de cada base (3.549 en venta y 2.115 en alquiler).
  - **Calibración:** los patrones se revisaron sobre 300 descripciones reales, mirando solo conteos y fragmentos cortos con los números tapados.

#### Zonaprop (con Apify)

Zonaprop autorizó por escrito la consulta automatizada. Sus avisos se obtienen con el actor de Apify `igolaizola/zonaprop-scraper` (`precio_entorno/zonaprop_apify.py`) y entran a `inmobiliarias-autorizadas` con el prefijo `zonaprop:`.

- **Campos:**
  - Precio y moneda salen de `pricing`.
  - Ambientes, superficie total, superficie cubierta y expensas salen de las características `CFT1`, `CFT100`, `CFT101` y `CFT6`.
  - Las expensas solo se toman si están en pesos.
  - Antigüedad y cocheras salen de `CFT5` y `CFT7` (ver la tabla de datos del edificio).
  - Los rasgos (a estrenar, apto crédito, balcón...) salen de `_details.description`, la descripción completa de la ficha. El listado trae solo un resumen de unos 150 caracteres.
- **Barrio:** se recorre la jerarquía de ubicación de Zonaprop (subbarrio → barrio → ciudad) hasta encontrar un barrio oficial. Caballito Sur y Parque Rivadavia se asignan a Caballito, y Almagro Norte y Almagro Sur a Almagro. Solo se aceptan avisos cuya jerarquía llega a Capital Federal.
- **Coordenadas:** vienen de la geolocalización de la ficha. Zonaprop la marca con visibilidad «EXACT», pero no informa la precisión en metros.
- **Fuera del registro:** el actor devuelve el nombre, los correos y los teléfonos del anunciante, además de la descripción y las fotos. Nada de eso se guarda. De la descripción solo quedan los rasgos de la tabla anterior. En el piloto, el crudo quedó en una carpeta temporal fuera del proyecto y se borró después de adaptarlo.
- **Piloto del 8 de noviembre de 2026:**
  - **Captura:** 2 corridas (Caballito y Almagro, 25 departamentos en venta cada una, ordenados por más recientes, con ficha), en la cuenta 1 de Apify con un tope de USD 0,50 por corrida. Se cobraron 102 eventos de USD 0,001, unos USD 0,05.
  - **Validación:** pasaron 49 avisos. Uno se descartó por no tener superficie cubierta.
- **Captura completa del 8 de noviembre de 2026:** 48 barrios en venta y en alquiler, con hasta 50 avisos con ficha por barrio.
  - **Venta:** se leyeron 2.359 avisos y entraron 2.223 nuevos a `real.sqlite3`. Los 49 restantes ya estaban por el piloto.
  - **Alquiler:** se leyeron 2.142 avisos y entraron 2.042 a `real-alquiler.sqlite3`, 1.797 en pesos y 245 en dólares.
  - **Descartes:** sobre todo por superficie faltante o por expensas y precios fuera de rango.
  - **Nombres de búsqueda:** el buscador de Zonaprop reconoce «Monserrat», «Nuñez» y «Pompeya» en lugar de los nombres oficiales. «Pompeya» aparece así en la jerarquía de ubicación y se asigna a Nueva Pompeya.
  - **Costo:** unos USD 8,70 en total. El comando revisa el gasto de cada cuenta antes de cada barrio y pasa a la siguiente cuando una corrida completa más USD 0,25 de margen superaría los USD 5.
- **Actualización de alquiler del 18 y 19 de noviembre de 2026:** 48 barrios, los 25 departamentos en alquiler más recientes por barrio, con ficha, en la cuenta 5 de Apify, con un tope de USD 0,08 por corrida.
  - **Carpetas:** `data/raw/zonaprop-alquiler-20261118-2309/` (17 barrios hasta Mataderos; la conexión se cortó), `-montecastro/` (relectura sin cobro de una corrida que terminó durante el corte), `-reintento/` (los 30 barrios restantes, más Boedo y Colegiales) y `-villaluro/`. Boedo, Colegiales y Villa Luro fallaron primero con un 401 de Zonaprop dentro del actor y salieron bien al reintentarlos.
  - **Resultado:** se adaptaron 1.128 avisos y entraron 827 nuevos a `real-alquiler.sqlite3` (727 en pesos y 100 en dólares), que pasó de 3.359 a 4.186. Ya había 226 avisos en la base, y 30 de ellos cambiaron de precio. Barrios con poca oferta, como Villa Real (4), Villa Riachuelo (9) y Villa Soldati (9), no llegaron a 25.
  - **Costo:** unos USD 2,32 en la cuenta 5. El total del proyecto queda en unos USD 21 de USD 25.

### Catálogo de alquileres

`inmobiliarias-alquiler` reúne los departamentos en alquiler de las mismas inmobiliarias, en una base separada de la de venta.

- **Precio:** alquiler mensual publicado, en ARS (de 50.000 a 50.000.000) o en USD (de 100 a 30.000), sin conversión entre monedas.
- **Precio por m²:** de 1.000 a 2.000.000 ARS, o de 1 a 1.000 USD.
- **Expensas:** opcionales, en pesos, de 1.000 a 10.000.000. Un "95.000" leído como 95 se descarta.
- **Búsquedas:** cada búsqueda guarda su moneda y solo recibe alertas de avisos publicados en esa moneda.
- **Alcance:** los alquileres son una extensión del producto. El análisis del capstone (los informes exploratorios y el modelo) sigue centrado en venta.

#### Mob (mob.ar)

Mob es un portal de alquileres publicados en su mayoría por dueños. Autorizó la lectura de sus páginas públicas, y sus avisos entran al mismo catálogo `inmobiliarias-alquiler` con el prefijo `mob:`. Mob no publica avisos de venta.

- **Recorrido:** cada página de listado trae completos sus primeros 20 avisos. La paginación ocurre en el navegador contra `/api/`, que robots.txt excluye. Por eso el adaptador recorre las páginas de listado de Capital Federal que publica el sitemap, por barrio, ambientes y filtros, primero las de departamentos, y deduplica por ID.
- **Precio:** se toma `rentPrice`, el alquiler en su moneda (ARS o USD). El campo `price` suma alquiler y expensas en pesos, así que se descarta.
- **Expensas:** se publican siempre en pesos. Un valor de 0 se toma como no informado.
- **Superficie:** Mob publica una sola superficie, que se registra como cubierta.
- **Barrio:** cuando el barrio viene con subzona ("Las Cañitas, Palermo"), se usa el barrio oficial. Las zonas ambiguas, como Congreso o Distrito Quartier, quedan sin barrio y se descartan.
- **Coordenadas:** se publican sin precisión declarada, y varios avisos de un mismo barrio comparten el mismo punto. Se tratan como aproximadas.
- **Captura del 8 de noviembre de 2026:**
  - **Lectura:** 871 departamentos en 417 pedidos y 21 minutos, sin bloqueos. Se omitieron 64 avisos que no eran departamentos y 4 de barrio ambiguo.
  - **Validación:** pasaron 835 avisos, 503 en pesos y 332 en dólares, en 31 barrios. Se descartaron 36, sobre todo por superficie faltante (27).
  - **Expensas:** 12 valores se descartaron por estar fuera de rango.
  - **Coordenadas:** 63 avisos no traen coordenadas.
- **Fuera del registro:** solo se toman departamentos. No se copian la dirección, la descripción, las fotos, el tipo de anunciante ni ningún dato de contacto.

#### Clarín Inmuebles (inmuebles.clarin.com)

Según el usuario, Clarín Inmuebles habilitó la lectura. El adaptador `clarin` lee solo las tarjetas de los listados de departamentos por barrio y nunca abre las fichas. Toma precio, moneda, m² cubiertos y totales, ambientes, barrio y expensas, sin coordenadas. No forma parte de la actualización programada y se pide con `--sitios clarin`.

- **robots.txt:** permite solo las páginas 1 a 3 de cada listado y prohíbe `/api/` y las URL con `&`. El cliente lee esos comodines desde el 8 de noviembre de 2026 (`precio_entorno/robots.py`). Antes usaba `urllib.robotparser`, que compara prefijos literales y los ignoraba.
- **Prueba del 8 de noviembre de 2026:** el listado general de venta en Capital Federal respondió 200, y las 20 tarjetas guardadas se leyeron completas, salvo una sin ambientes. La ficha de un aviso respondió 403 (AWS WAF). En el piloto de `data/raw/clarin-piloto-20261108/`, el sitemap respondió 200 y el primer listado por barrio, 403. La captura se detuvo con 0 avisos y 8 pedidos en total, y no se reintentó.
- **Avisos importados:** las 20 tarjetas de la primera página del listado general se guardaron en `data/raw/clarin-20261108/` y se importaron a `data/local/real.sqlite3` en el catálogo consolidado. Entraron 18: 7 de Palermo, 7 de Recoleta y 4 de Caballito. Se descartaron 2, uno sin superficie y otro sin ambientes. La base de venta pasó de 1.517 a 1.535 avisos.
- **Para seguir:** hace falta que Clarín habilite el identificador del proyecto en su WAF o entregue una exportación. El borrador del pedido está en [pedidos-de-acceso.md](pedidos-de-acceso.md#6-clarín-inmuebles).

## Puntos de interés (OpenStreetMap)

- **Origen:** extraídos el 7 de noviembre de 2026 con el actor de Apify `automation-lab/openstreetmap-poi-extractor` (API Overpass), dentro del rectángulo de CABA.
- **Licencia:** ODbL, con cita obligatoria "© OpenStreetMap contributors".
- **Campos conservados:** ID de OpenStreetMap, nombre, categoría y coordenadas. Teléfonos, sitios web y correos se descartan.
- **Costo:** USD 9,04 en 9 corridas, más USD 0,045 del piloto, repartidos en 4 cuentas y siempre por debajo de USD 5 por cuenta.

| Categoría | Puntos | ¿Completa? |
| --- | --- | --- |
| Transporte (subte, tren, Metrobús) | 178 | Sí |
| Restaurantes | 2.738 | Sí |
| Cafés | 1.731 | Sí |
| Bares | 595 | Sí |
| Parques, hospitales, escuelas, supermercados, farmacias | Llegaron a su tope (1.000, 500, 2.000, 1.500 y 1.000) | No: el modelo no las usa |

### Complemento oficial (Buenos Aires Data)

Parques, escuelas y hospitales se completaron con datasets oficiales gratuitos, descargados el 7 de noviembre de 2026 a `data/raw/badata-poi/` (licencia CC-BY 2.5 AR). `python -m precio_entorno.badata_poi` los convierte a `data/processed/poi-badata/`.

| Dataset | Archivo | Uso |
| --- | --- | --- |
| Espacios Verdes Públicos | `espacio_verde_publico.geojson` (18,4 MB) | 487 plazas, parques, jardines y paseos. Se excluyen 755 canteros centrales, 906 plazoletas y los patios. Se usan los vértices para medir la distancia al borde. |
| Establecimientos Educativos | `establecimientos_educativos.geojson` (1,8 MB) | 2.767 puntos, convertidos de EPSG:9498 a latitud y longitud |
| Hospitales | `hospitales.geojson` (24 KB) | 36 hospitales públicos, también convertidos de EPSG:9498 |

Supermercados y farmacias no tienen un dataset oficial equivalente y quedan fuera del modelo.

## Capas del entorno (Buenos Aires Data)

El mapa y las columnas de entorno de la app usan datasets abiertos de Buenos Aires Data (licencia CC-BY 2.5 AR). Los siguientes se descargaron el 8 de noviembre de 2026 a `data/raw/badata-entorno/`. El portal rechaza los pedidos automatizados a sus páginas, así que las direcciones se tomaron de su API desde un navegador y los archivos se bajaron del CDN oficial. `python -m precio_entorno.entorno` los combina con los de `data/raw/badata-poi/` y escribe `data/processed/entorno/`, con un `fuentes.json` que registra archivo, enlace y SHA-256 de cada capa.

| Dataset | Archivo | SHA-256 (inicio) | Uso |
| --- | --- | --- | --- |
| Barrios | `barrios.geojson` (764 KB) | `c24fabd0…` | 48 polígonos oficiales. Unidad geográfica de todo el resumen. |
| Estaciones de subte | `estaciones_de_subte.geojson` (17 KB) | `e392abf0…` | 90 estaciones de las líneas A, B, C, D, E y H |
| Estaciones accesibles | `estaciones-accesibles.csv` (4 KB) | `fe632fc9…` | Ascensores informados. Coinciden 62 de las 90 estaciones por línea y nombre. |
| CeSAC | `centros_salud_nivel_1_cesac.geojson` (32 KB) | `c6e49f49…` | 50 centros |
| Mapa de Ruido 2025, diurno | `medicion_de_ruido_diurno.geojson` (106 MB) | `73c0a28f…` | Bandas de 5 dBA. 15.731 celdas de 100 m con dato. |
| Mapa de Ruido 2025, nocturno | `medicion_de_ruido_nocturno.geojson` (85 MB) | `4a4d12e9…` | 16.806 celdas de 100 m con dato |
| Riesgo hídrico | `riesgo-hidrico.geojson` (96 KB) | `b782800f…` | 51 áreas de prevención, publicadas en diciembre de 2020 |
| Clubes (17/11/2026) | `clubes.csv` (104 KB) | `62ac8212…` | 310 sedes de clubes de barrio; se descartan las administrativas |
| Polideportivos (17/11/2026) | `polideportivos.geojson` (8 KB) | `ec27835d…` | 16 polideportivos de la Ciudad |
| Colectivos: GTFS (17/11/2026) | `data/raw/colectivos-gtfs-20261117/colectivos-gtfs.zip` (204 MB) | `e87bbce4…` | Trazados de 1.052 ramales del AMBA; 145 líneas pasan por CABA |

Decisiones de preparación:
- **Asignación a barrios:** cada punto se asigna al barrio cuyo polígono lo contiene. Un espacio verde se asigna por el centro de su anillo exterior. Las escuelas y los hospitales se convierten antes desde EPSG:9498.
- **Escuelas:** se cuentan los niveles inicial, primario y secundario comunes, por tipo de gestión. Quedan 1.627 establecimientos. La educación de adultos, la superior y los servicios complementarios no se muestran.
- **Espacios verdes:** 486 plazas, parques, jardines y paseos, con los mismos criterios que el modelo. Se excluyen canteros centrales, plazoletas y patios.
- **Ruido:** cada celda de 100 m tiene 9 muestras. Su nivel típico es la banda mediana de las muestras con dato, y también se guarda el máximo. El porcentaje de un barrio se calcula sobre sus celdas con dato. Con menos de 30 celdas se informa sin dato: es el caso de Puerto Madero de día, con 4 celdas. El mapa usa una escala secuencial propia, de amarillo a rojo oscuro, para que las calles sigan legibles. El visor oficial usa otra paleta.
- **Riesgo hídrico:** la capa viene en Gauss-Krüger Buenos Aires (Campo Inchauspe, falso origen 100.000 m) y se convierte a latitud y longitud. Por barrio, las mayores proporciones aparecen en los que atraviesan los arroyos Maldonado (Villa Santa Rita, Villa Crespo, Villa General Mitre, La Paternal) y Cildáñez (Villa Riachuelo, Villa Lugano), y los barrios del centro quedan en cero. En el mapa de Villa Crespo, la franja sigue el trazado de Juan B. Justo y sus bordes coinciden con las manzanas del mapa base. No se comparó contra el visor oficial. El porcentaje de un barrio es la parte de su superficie que cae en un área de prevención.
- **Clubes:** se usa el CSV, porque el GeoJSON del portal trae los acentos dañados. Se suman los polideportivos y quedan 317 puntos. No se guardan teléfonos, correos ni redes de los clubes. La capa del mapa muestra toda la ciudad.
- **Gimnasios (OpenStreetMap):** no hay dataset oficial. Se consultó una vez la API pública Overpass (sin Apify ni costo) el 17/11/2026 por `leisure=fitness_centre` y centros deportivos con `sport=fitness|crossfit|gym` dentro de CABA, y se guardó en `data/raw/osm-gimnasios-20261117/gimnasios.json` (338 elementos, 337 dentro de algún barrio). Licencia ODbL. La cobertura depende de quién mapea cada zona.
- **Colectivos:** `precio_entorno/colectivos.py` lee rutas, viajes y trazados del GTFS oficial. Agrupa los ramales por número de línea (`60C` → 60), densifica cada trazado cada 50 m y considera que una línea pasa por un barrio si algún punto cae dentro del polígono. Las líneas que van por una avenida límite cuentan para los dos barrios. El recorrido se simplifica a unos 8 m para el mapa y se guarda en `data/processed/entorno/colectivos.json` (1,9 MB). **El calendario del feed es de septiembre a diciembre de 2019**, aunque el portal lo actualizó el 1/7/2026: los recorridos pueden haber cambiado y la interfaz lo advierte. El portal también publica «Colectivos: recorridos», pero solo trae las 26 líneas de jurisdicción porteña, así que no se usa.
- **Delitos en el mapa:** no se preparan de antemano. La app lee el CSV cargado y suma los hechos registrados por celda de 200 m para el mes, el tipo y la zona del barrio.
- **Gastronomía (OpenStreetMap):** `python -m precio_entorno.entorno` también cuenta por barrio los restaurantes, cafés y bares de la captura OSM más reciente (`data/raw/osm-AAAAMMDD/`, hoy la del 7/11/2026), y la registra en `fuentes.json` con licencia ODbL. De los 5.064 puntos, 4.781 caen dentro de algún barrio. Si una categoría llegó al tope de su corrida, la captura no se usa. Con `--sin-osm` se omite. Solo se guardan conteos, no se dibujan en el mapa. La cobertura de OSM depende de quién mapea cada zona: Villa Lugano tiene 25 lugares registrados y Almagro, 129.

Límites de interpretación: la cercanía a una escuela o a un CeSAC no indica vacantes ni turnos. El ruido es un nivel exterior y no describe el interior de un departamento. Que una dirección caiga en un área de prevención es un dato para investigar. Las estaciones y las líneas de colectivo indican conectividad, no tiempos de viaje ni frecuencias. Un club o un gimnasio en el mapa no informa cuotas, cupos ni horarios.

## Delitos registrados

Fuente: [Buenos Aires Data](https://data.buenosaires.gob.ar/dataset/delitos). Conservar período, barrio o unidad geográfica, tipo, franja horaria y cantidad de hechos. Registrar la versión del archivo y distinguir cero hechos registrados de falta de cobertura. Elegir una ventana anterior a la captura para el modelo y cruzar por barrio si los pines no admiten mayor detalle.

### Validación del CSV oficial de 2024

El archivo [delitos_2024.csv](https://cdn.buenosaires.gob.ar/datosabiertos/datasets/ministerio-de-justicia-y-seguridad/delitos/delitos_2024.csv) se descargó a `data/raw/` y se validó en una base temporal. SHA-256 `0f5df5a362fb600d2123b30acca4f8b87ecf5e4a3ad4411514cf909b376dcea3`.

- 158.838 filas leídas y 154.916 válidas para el contexto de barrio. Las 3.922 restantes tenían el barrio faltante.
- Los registros válidos abarcan 48 barrios, 12 meses y 6 tipos de hecho. En 41 de esos registros faltaba la franja horaria y se conservó como desconocida.
- La segunda carga del mismo archivo incorporó cero filas. Se normalizó la abreviatura oficial «VILLA GRAL. MITRE» y se interpretó `NULL` como faltante.

### CSV oficial de 2025

El archivo [delitos_2025.csv](https://cdn.buenosaires.gob.ar/datosabiertos/datasets/ministerio-de-justicia-y-seguridad/delitos/delitos_2025.csv) se descargó a `data/raw/` el 7 de noviembre de 2026. SHA-256 `1ed67c3346eb4f42635cc44bc78e00ec2b023370f1ff6df0e7f309c72a6b45df`. Tiene las mismas columnas que 2024: 133.203 filas leídas y 130.418 válidas. Las 2.785 restantes tenían el barrio faltante. Ningún ID se repite con 2024. El catálogo oficial no publica todavía datos de 2026.

El [informe exploratorio](eda-delitos.md) describe los dos años por tipo, mes, franja y barrio, y propone el dataset `barrio_mes.csv`, con 1.152 filas. Cualquiera de los dos archivos sirve como contexto de la app, que muestra un archivo por vez. Para el dataset del capstone queda pendiente definir la ventana anterior a las capturas inmobiliarias y el criterio de selección de 700 a 2.000 registros válidos según la cobertura de ese catálogo.

## Datos de prueba

`data/fixtures/demo.json` contiene exclusivamente ejemplos ficticios. El modelo y los indicadores de negocio de la entrega se calcularán con las dos fuentes verificadas.
