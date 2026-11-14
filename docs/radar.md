# Radar de tendencias barriales

Capa editorial de la comparación de barrios. Cada semana reúne las notas inmobiliarias de Clarín, LA NACION y TN, identifica los barrios porteños de los que tratan y separa dos indicadores:

- **Notas publicadas:** notas centradas en el barrio que los medios monitoreados publicaron en el período.
- **Aperturas reportadas:** locales cuya apertura informa una nota, con local, dirección y fecha de apertura verificable dentro del período.

La cobertura de prensa mide lo que publicaron esos medios. No mide demanda inmobiliaria, no es un censo de aperturas y no ordena los barrios por popularidad: la tabla va en orden alfabético. El radar no usa ni modifica los avisos, los delitos registrados ni los datos de ejemplo, y se muestra igual en los dos modos.

## Uso

```bash
python -m precio_entorno.radar                     # siete días calendario anteriores a hoy
python -m precio_entorno.radar --hasta 2026-11-09  # período del 2 al 8 de noviembre
python -m precio_entorno.radar --resumen           # muestra el último boletín sin recolectar
python -m precio_entorno.radar --validar URL       # clasifica una nota sin guardarla
python -m precio_entorno.radar --reclasificar      # vuelve a leer las notas ya guardadas
```

`--hasta` es la fecha de corte y queda excluida. El período va de `hasta - 7` a `hasta - 1`, en hora de Buenos Aires. La interfaz web lee el resultado desde `GET /api/radar`, que acepta `?periodo=AAAA-MM-DD` con la fecha de inicio.

## Fuentes y permisos

Revisado el 10 de noviembre de 2026.

| Medio | Cómo se lee | robots.txt | Términos de uso |
| --- | --- | --- | --- |
| Clarín | [Feed RSS de Propiedades](https://www.clarin.com/rss/propiedades/) y el sitemap oficial de noticias ([índice](https://www.clarin.com/sitemaps/index_news.xml)), filtrado por `/propiedades/`. El feed trae solo 10 notas y el sitemap completa la semana. | Permite `/propiedades/`, `/rss/` y `/sitemaps/` | No encontramos cláusulas sobre acceso automatizado en [la página de términos](https://www.clarin.com/ayuda/terminos-condiciones.html). |
| LA NACION | [Feed RSS de la categoría Propiedades](https://www.lanacion.com.ar/arc/outboundfeeds/rss/category/propiedades/?outputType=xml), paginado con `&from=` hasta pasar el inicio del período | Permite `/arc/outboundfeeds/` y `/propiedades/` | No encontramos la página de términos desde la sección. Usamos el feed que publica el medio. |
| TN | No publica feed de Propiedades: `/arc/outboundfeeds/rss/category/economia/propiedades/` responde 404, y el feed de Economía cubre unos dos días. Se usa ese feed filtrado y [la página pública de la sección](https://tn.com.ar/economia/propiedades/). | Permite `/economia/propiedades/` | [Los términos](https://tn.com.ar/terminos-y-condiciones/) prohíben sistemas automáticos que envíen más pedidos de los que enviaría una persona. El recolector hace unos 7 pedidos por semana, con 4 segundos entre pedidos. |

El enlace de TN del pedido (`/2026/11/07/dos-barrios-...-cool-del-mundo...`) está en la sección y entra en el período del 3 al 9 de noviembre.

De cada nota se lee la página para tomar del JSON-LD la URL canónica, la fecha de publicación original, el titular, la bajada y el texto. El texto se usa solo si el medio no marca la nota con `isAccessibleForFree: false`. En ese caso se clasifica con el titular y la bajada, y la nota queda con `acceso: restringido`. No se eluden muros de pago ni controles de acceso.

El cliente se identifica como `precio-entorno-caba/0.1 (proyecto academico; radar semanal de noticias)`, respeta robots.txt con comodines, espera 4 segundos entre pedidos al mismo sitio, reintenta tres veces con espera creciente ante errores de red, HTTP 429 o 5xx, y se detiene ante un 401, 403, 451 o un desafío anti-robots. Tiene un tope de 80 pedidos por fuente y corrida. No usa servicios pagos.

## Qué se guarda

En `data/local/radar/`, fuera de Git:

- `fuentes/<medio>.json`: notas por URL canónica y un registro por período con estado, motivo, fecha de recolección, cobertura y último intento. Cada medio tiene su propio archivo, que se escribe de forma atómica.
- `corridas.jsonl`: una línea por fuente y corrida, con pedidos, reintentos, notas nuevas y fallas.

Por nota: medio, titular, URL canónica, direcciones vistas en los listados, fecha de publicación original, fecha de modificación, fecha en el listado, fecha de recolección, acceso, barrios principales, incidentales y ambiguos, alcance (CABA u otro lugar), tema, aperturas, fecha del hecho y un resumen. No se guardan el texto, la bajada ni el `content:encoded` de los feeds.

El resumen se arma con reglas y frases propias. Por ejemplo: «Nota de TN sobre la transformación y el perfil de los barrios con foco en Chacarita y Colegiales. Nombra al pasar Belgrano, Palermo y Villa Crespo.» Describe de qué trata la nota y no resume sus argumentos.

## Fallas, duplicados y republicaciones

- **Una fuente falla:** las demás siguen. Si el período ya tenía una recolección buena de esa fuente, se conserva y solo se anota el intento fallido. Si no la tenía, el período queda como `error` o `restringido`, y la interfaz dice «Sin datos de… la recolección falló y eso no significa que no hubo notas».
- **Cobertura parcial:** si los listados no llegan a una fecha anterior al inicio del período, la fuente queda `parcial` y el motivo dice hasta dónde llegaron.
- **Segunda corrida del mismo período:** las notas ya guardadas no se vuelven a pedir y no se duplican. La clave es la URL canónica, sin parámetros de seguimiento.
- **Republicación de la misma URL:** se toma la fecha de publicación original del JSON-LD, no la del feed. Una nota de agosto que vuelve a la portada queda en agosto y no entra en el boletín actual.
- **Republicación con otra URL o en otro medio:** dos titulares con 80 % o más de palabras en común se agrupan. La primera publicación cuenta una vez y las demás se muestran como enlaces.

## Barrios

- Se reconocen los 48 barrios oficiales y sus variantes («Monserrat», «Paternal», «Pompeya», «Villa Gral. Mitre»), sin importar las tildes.
- Alias resueltos, los mismos que usa el catálogo de avisos: Palermo Soho, Hollywood, Chico y Viejo, Las Cañitas y Villa Freud → Palermo. Belgrano R y C, y Barrio Chino → Belgrano. Barrio Norte → Recoleta. Abasto y Once → Balvanera. Microcentro y Tribunales → San Nicolás. Distrito Tecnológico → Parque Patricios. Distrito del Diseño → Barracas. «Chacagiales» → Chacarita y Colegiales.
- Ambiguos, sin asignar: Parque Centenario, Distrito Audiovisual, Distrito de las Artes y Distrito Arcos. Tampoco se asignan Congreso ni Centro.
- No cuentan como barrio: calles («Av. Belgrano»), personas («Luis Almagro», «Cornelio Saavedra»), «Constitución Nacional», «Boca Juniors», «Belgrano Cargas», «once» como número y lugares homónimos («Villa Belgrano», en Córdoba).
- Una nota sobre otra ciudad (Montevideo, Córdoba, Bariloche, Zona Norte…) no asigna barrios porteños, aunque compare con Palermo.
- **Principal**, que suma al indicador: el barrio aparece en el titular, la bajada o un subtítulo («Saavedra: …»), o se lo nombra al menos dos veces sin usarlo como comparación ni dentro de la sección de otro barrio. Si el titular ya nombra un barrio, otro barrio necesita tres menciones propias.
- **Incidental**, que no suma: comparaciones («cerca de Palermo», «más barato que en Belgrano», «el derrame de Palermo») y menciones sueltas. La ficha del barrio informa cuántas hubo.

## Aperturas

Se buscan oraciones con un comercio (bar, restaurante, café, panadería, tienda, hotel…) y un verbo de apertura.

- Pasado («abrió», «inauguró») → **reportada**. Futuro («abrirá», «planea abrir») → **anuncio**. Presente → lo decide la fecha.
- Fecha del hecho: explícita («el 5 de noviembre») o relativa a la publicación («ayer», «el sábado»). Se guarda aparte de la fecha de publicación.
- Local: nombre entre comillas, después del tipo de comercio («el bar La Vermutera») o antes del verbo. Dirección: calle con altura («en Bulnes 900», «en Av. Corrientes 5000») o esquina.
- Las aperturas se agrupan por local y dirección normalizados en todas las notas guardadas, y conservan todos los enlaces que las respaldan.
- Una apertura cuenta en el período si es reportada, tiene local, dirección y una fecha verificable, y esa fecha cae dentro del período. Las demás aparecen como «Cobertura de aperturas que no suma», con el motivo: anuncio, sin fecha verificable o sin local y dirección identificables.

## Interfaz

En la lista de barrios, un bloque plegable muestra el período, la última actualización, el estado de cada fuente y la tabla de barrios con «Notas publicadas» y «Aperturas reportadas». Cada número abre las notas o aperturas que lo respaldan. Cada fila de la comparación suma «En la prensa: N notas» cuando corresponde. La ficha del barrio tiene la sección «En la prensa» con fecha, medio, tema, resumen y enlace al original.

## Programación semanal

La tarea de Windows **PrecioEntornoCABA\Radar de noticias** corre los lunes a las 9:00 y ejecuta [scripts/radar.cmd](../scripts/radar.cmd), que agrega la salida a `data/local/radar.log`. Windows está en «Argentina Standard Time», equivalente a America/Argentina/Buenos_Aires. Si la computadora estaba apagada, la tarea corre apenas se pueda. Como la tarea de actualización de avisos, necesita la sesión de Windows iniciada.

Para crearla o recrearla:

```bash
powershell -ExecutionPolicy Bypass -File scripts/programar-radar.ps1
```

Make no puede ejecutar Python en esta computadora, así que la programación queda en el Programador de tareas, igual que la actualización de avisos. La búsqueda automática configurada en Codex es independiente y no se modificó.

## Caso histórico

[Barrios revelación de CABA](https://www.clarin.com/propiedades/barrios-revelacion-caba-6-lugares-reconvirtieron-hoy-buscados-vivir_0_MIXnoDHYRg.html) (Clarín, 3 de agosto de 2026) sirve para validar la clasificación:

```bash
python -m precio_entorno.radar --validar https://www.clarin.com/propiedades/barrios-revelacion-caba-6-lugares-reconvirtieron-hoy-buscados-vivir_0_MIXnoDHYRg.html
```

El 10 de noviembre de 2026 devolvió como principales a Almagro, Chacarita, La Paternal, Núñez, Saavedra y Villa Crespo, los seis de la nota. Belgrano, Palermo, Puerto Madero y Recoleta quedaron como incidentales. El tema fue «transformación» y `en_periodo_actual` fue `false`: la nota no se guarda ni entra en el boletín. La prueba `test_historical_case_shape_finds_the_six_neighborhoods` reproduce la estructura de la nota con texto propio.

## Límites

- Las reglas son deterministas y se pueden auditar, pero no entienden el texto: una comparación con una redacción que no está en la lista puede contar como mención propia. La versión de las reglas queda en cada nota (`clasificacion_version`) y `--reclasificar` vuelve a aplicarlas.
- La detección de aperturas depende de que la nota nombre el local y la dirección en la misma oración que el verbo.
- Si un medio cambia su feed, su sitemap o la estructura de la sección, la fuente queda `parcial` o `error` y la interfaz lo informa.
