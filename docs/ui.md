# Propuesta de interfaz

Diseño hecho con la skill `frontend-design`. Se eligió el frontend web propio: la página está en `web/` y la sirve `python -m precio_entorno.api`.

## Cambios respecto del primer plan

- **Delitos:** la escala pasó a gris azulado, como estaba previsto, y sus tonos se cortan por quintiles de las celdas a la vista. Con cortes proporcionales al máximo, una sola celda con muchos hechos dejaba casi todo el barrio en el tono más claro.
- **Leyenda:** muestra solo las muestras de color y se puede plegar. Las advertencias de cada capa están en «Cómo leer el mapa», plegado al principio, porque abiertas tapaban medio mapa.
- **Celular:** la marca usa el ancho angosto de Archivo para que entre en la barra, y los botones de capas se desplazan en una sola fila.
- **Coropletas:** el gris de los barrios tiene más contraste que en el plan, porque el mapa es el elemento principal.

## Brief propuesto

- **Tema:** elegir en qué barrio de CABA buscar un departamento para comprar o alquilar, con lo que hay alrededor a la vista.
- **Público:** una persona o una pareja que busca vivienda propia y no conoce todos los barrios. En la validación, también el equipo de una inmobiliaria que atiende varias búsquedas.
- **Tarea principal:** ver dónde rinde el presupuesto, revisar el entorno del barrio que interesa y crear una alerta. El flujo sigue siendo preferencias → comparación de barrios → búsqueda guardada → alerta.

### Lo que condiciona el diseño

- **Avisos sin fotos ni títulos:** solo hay precio, superficie, ambientes, barrio, expensas y enlace. No hay fotos para armar tarjetas como las de Airbnb. La unidad principal de la interfaz es el barrio, y el aviso aparece en segundo plano.
- **Sin puntajes:** el entorno se describe capa por capa y nunca se suma en un puntaje. Los delitos se muestran como hechos registrados, con su período.
- **Ubicación aproximada:** los pines de los avisos no declaran precisión. El mapa ubica barrios y capas públicas, no departamentos.

## Plan de diseño

### Color

| Nombre | Hex | Uso |
| --- | --- | --- |
| Vereda | `#F3F4F1` | Fondo general, gris frío de baldosa |
| Asfalto | `#1E2A32` | Texto y contornos de barrio |
| Jacarandá | `#6A4FB3` | Única acción y selección: barrio elegido, botón de alerta, filtros activos |
| Plátano | `#5E7D4F` | Plazas y parques. Fuera del mapa solo se usa en estados de éxito. |
| Cordón | `#CBD0CC` | Bordes, divisores y celdas vacías |
| Papel | `#FFFFFF` | Paneles sobre el mapa |

El jacarandá florece en noviembre en Buenos Aires y le da a la app un color propio que no es el de un portal inmobiliario. Como acento se usa solo para lo que la persona eligió. Las capas del mapa tienen su propia paleta de datos: los colores oficiales de cada línea de subte, la escala de ruido de amarillo a rojo y una escala gris azulada para delitos. El violeta de delitos actual pasa a gris azulado para no confundirse con el acento.

### Tipografía

- **Archivo**, de Omnibus-Type, una fundidora argentina, en una sola familia variable. Los títulos de barrio van en ancho expandido y peso 650, el cuerpo en ancho normal y peso 400, y precios y superficies con cifras tabulares.
- **Escala:** 13, 15, 18, 24 y 34 px, con interlineado de 1,45 para el cuerpo.
- **Descartada:** Montserrat, aunque lleve el nombre de un barrio porteño. Está en demasiados sitios y no diferencia.

### Layout

En escritorio el mapa ocupa la mitad derecha y la lista de barrios la izquierda, como en Airbnb. Los filtros quedan en una barra superior fija.

```text
┌──────────────────────────────────────────────────────────────────────┐
│ Comprar | Alquilar   Hasta USD 110.000   40 m²+   2 amb.   [Me importa ▾] │
├───────────────────────────────┬──────────────────────────────────────┤
│ 15 barrios con opciones       │ (Subte) (Plazas) (Ruido) (Delitos)   │
│                               │                                      │
│ Almagro              15 avisos│        mapa de CABA                  │
│ USD 84.000 mediana            │   barrios con tono según cantidad    │
│ Subte A y B, 1 plaza          │   de avisos que encajan              │
│ ───────────────────────────── │                                      │
│ Balvanera            12 avisos│                                      │
│ ...                           │                                      │
└───────────────────────────────┴──────────────────────────────────────┘
```

Al elegir un barrio, el mapa se acerca y la lista se reemplaza por su ficha:

```text
┌───────────────────────────────┬──────────────────────────────────────┐
│ ← Todos los barrios           │ (Subte) (Plazas) (Ruido) (Delitos)   │
│ Almagro                       │                                      │
│ 15 avisos, mediana USD 84.000 │     Almagro con sus capas            │
│ [Crear alerta para Almagro]   │                                      │
│                               │                                      │
│ Entorno                       │                                      │
│ Subte A y B, 5 estaciones     │                                      │
│ Ruido ≥70 dBA de día: 82 %    │  leyenda abajo a la izquierda        │
│                               │                                      │
│ Avisos que encajan            │                                      │
│ USD 79.000  45 m²  2 amb.  ↗  │                                      │
└───────────────────────────────┴──────────────────────────────────────┘
```

En el celular el mapa ocupa la pantalla y la lista sube desde abajo como una hoja que se arrastra. Los filtros se abren en una pantalla completa. Todo se alinea a la izquierda, y los precios y superficies a la derecha dentro de su columna.

### Principios

1. **El mapa es el protagonista.** La comparación de barrios se ve en la ciudad y no en una tabla. Esa es la decisión audaz; lo demás queda sobrio.
2. **Cada número trae su fuente al alcance.** El período y la unidad aparecen al pasar el cursor o en la ficha, no en leyendas largas debajo del mapa.
3. **Una sola acción principal por pantalla:** comparar en la lista y crear la alerta en la ficha.
4. **Datos ficticios marcados siempre:** en la demo, una franja fija avisa que los avisos son de ejemplo.

## Ficha de barrio

Propuesta del 12/11/2026 que amplía el boceto de la ficha de más arriba. La maqueta, con datos reales de Almagro en escritorio y celular, está en un lienzo privado: https://claude.ai/artifact/DasWiWtzEEkpBt1xfHvoEf. Todavía no está implementada.

Se tomó como referencia la ficha de barrio que Local Logic y Walk Score muestran en los portales de Estados Unidos. De ahí sale la estructura: un resumen arriba, una fila por tema con una frase que se entiende sin mirar el número y la fuente al pie. No se toman sus puntajes de 0 a 10 ni sus etiquetas («Mostly calm»), por la regla de no usar puntajes.

### Contenido, en orden

1. **Encabezado:** nombre del barrio, comuna y un resumen de una oración armado solo con los datos de la ficha, sin texto editorial. Debajo, la aclaración «Resumen armado con los datos de esta ficha».
2. **Para tu búsqueda:** cantidad de avisos que encajan con los filtros y su mediana; mediana de USD por m² cubierto del barrio y de CABA; la aclaración de que son precios de publicación y la fecha del catálogo.
3. **Tus lugares:** tiempo de viaje desde el barrio a los lugares que la persona carga (trabajo, facultad, familia). Es nuevo: ver Pendientes.
4. **Qué hay en el barrio:** una fila por capa. Arriba, las que la persona marcó en «Me importa», con la etiqueta «Marcaste». El resto va debajo y nunca se oculta.
5. **Dónde comer:** los lugares más valorados en Google, consultados en vivo. Ver su sección.
6. **Avisos que encajan:** precio, superficie, ambientes y fuente, con enlace al aviso original.
7. **Fuentes:** una línea con las fuentes de toda la ficha.
8. **Acción fija abajo:** «Crear alerta para <barrio>». Como acción secundaria, el enlace «Comparar con otro barrio».

En el celular la ficha es la hoja que sube sobre el mapa, con el encabezado, «Para tu búsqueda», las dos primeras capas y la acción fija.

### Filas de capas

Cada fila tiene el tema, el dato principal en negrita con su unidad y, entre paréntesis, el barrio mediano de CABA como referencia. Una segunda línea agrega el detalle o la advertencia. En las capas que son un porcentaje (ruido y riesgo hídrico), una línea de 0 a 100 % marca al barrio con un punto y a la mediana con una raya. Es una comparación, no una barra que se llena como un puntaje.

| Capa | Dato principal | Referencia y advertencia | Fuente |
| --- | --- | --- | --- |
| Transporte | Líneas de subte, con su color oficial, y cantidad de estaciones | Cuántos barrios no tienen estación | Estaciones de SBASE en BA Data |
| Ruido | % de celdas relevadas ≥70 dBA de día | Mediana de CABA; de noche, % ≥65 dBA | Mapa de Ruido, edición 2025 |
| Espacios verdes | Cantidad y hectáreas | Hectáreas cada 100 ha de barrio, con la mediana | Inventario de espacios verdes |
| Gastronomía | Cafés, bares y restaurantes, y su cantidad cada 100 ha | Mediana cada 100 ha; desglose por tipo; fecha de captura y aclaración de que la cobertura de OSM depende de quién mapea cada zona | OpenStreetMap (ODbL), captura `data/raw/osm-20261107/` |
| Escuelas | Cantidad por nivel | Cuántas son de gestión estatal | Mapa Escolar |
| Salud pública | Hospitales y CeSAC | — | Ministerio de Salud |
| Riesgo hídrico | % de la superficie | Mediana de CABA; capa de diciembre de 2020 | Secretaría de Desarrollo Urbano |
| Delitos registrados | Hechos del año y hechos por km² | Mediana por km²; tipos principales; aclaración de que se cuentan por superficie y no por habitante, así que los barrios céntricos y con mucha circulación quedan arriba | Mapa del Delito, por barrio |
| En las noticias | Notas con foco en el barrio en la semana | Medios y cantidad de notas revisadas; se aclara que es una capa editorial y no se mezcla con los demás datos | Radar de tendencias barriales |

Las medianas de referencia se calculan sobre los 48 barrios con `data/processed/entorno/resumen.json`. Los delitos y los avisos salen de la base local.

En Almagro, la captura de OSM da 129 lugares (70 restaurantes, 41 cafés y 18 bares), 32 cada 100 ha. El barrio mediano tiene 14. Para no confundir falta de mapeo con falta de lugares, conviene contrastar la cobertura con un dataset de la Ciudad antes de comparar barrios entre sí.

### Dónde comer (Google Places en vivo)

La lista de los lugares más valorados sale de la API oficial de Places (New), nunca de una extracción de Google Maps: sus términos prohíben extraer contenido, y el proyecto exige fuentes con acceso autorizado. La API impone las reglas que dan forma a la sección:

- **En vivo y a pedido.** El servidor consulta a Google solo cuando la persona toca «Ver los más valorados en Google». La clave va en `.env` y nunca llega al navegador.
- **Nada guardado.** No se guardan calificaciones, listas ni conteos derivados de Google. Como mucho, el `place_id`, que la política permite conservar. Tampoco se alimenta el modelo con estos datos.
- **Lista, no mapa.** Los datos de Places no pueden ir sobre un mapa que no sea de Google, y el de la app es MapLibre. Por eso no hay pines: cada lugar enlaza a Google Maps.
- **Atribución.** El logo de Google Maps junto al título, y la aclaración de que son calificaciones de usuarios de Google.

Contenido:

- Selector de tipo: restaurantes, cafés y bares.
- Por lugar: nombre, calificación, cantidad de reseñas, nivel de precio y enlace «Abrir en Maps».
- Primero se muestran 5 y después hasta 30.
- Orden: calificación y, ante un empate, cantidad de reseñas. Solo entran lugares con al menos 200 reseñas, para que una nota alta con pocas opiniones no encabece la lista.
- El texto aclara el alcance: Google devuelve hasta 60 lugares por búsqueda, ordenados por relevancia. La lista es «los más valorados entre los que devuelve Google», no un ranking de todo el barrio.

Estados, dibujados en el lienzo:

1. Antes de consultar: el botón y la aclaración de que la consulta se hace a pedido.
2. Consultando.
3. Sin lugares con 200 reseñas: se ofrece bajar el mínimo a 50.
4. Cupo del día agotado o Google sin respuesta: un aviso, y la fila de gastronomía de OSM sigue visible.
5. Demo o sin clave: la sección no aparece. Nunca se muestran lugares ni calificaciones ficticias.

Costo y topes: pedir `rating` y `userRatingCount` lleva la búsqueda al nivel Text Search Enterprise. Según la página de precios de Google Maps Platform, tiene 1.000 llamadas gratis por mes y después unos USD 35 cada 1.000; hay que confirmarlo en la consola antes de activarla. Cada búsqueda trae hasta 20 lugares, así que llegar a 30 cuesta 2 llamadas: unas 500 consultas gratis por mes. Hacen falta dos topes:

- Una cuota diaria en la consola de Google Cloud.
- Un contador acumulado en el servidor, como el de `preferencias-inferencia.sqlite3`, que corta antes de salir del tramo gratis.

La pantalla pide estos campos (field mask): `places.id`, `places.displayName`, `places.rating`, `places.userRatingCount`, `places.priceLevel`, `places.googleMapsUri` y `places.location`. La ubicación se usa solo en memoria, para descartar lugares fuera del polígono del barrio.

### Barrios parecidos

Implementado el 13/11/2026. Va en la ficha, después del entorno. Muestra 3 barrios y, en cada uno:
- el nombre como enlace a su ficha;
- los avisos que encajan con la búsqueda y la diferencia de mediana con el barrio elegido;
- hasta 3 capas en las que se parece (marcadas con «=») y hasta 2 en las que difiere («≠»).

Las diferencias se escriben en tono neutro («más espacio verde», «menos ruido»), sin juzgar si son mejores o peores, y no llevan colores de alerta. Una capa solo cuenta como parecida si además está cerca a simple vista: no más de 10 puntos en los porcentajes, o una proporción de al menos 2 a 3 en las densidades. La lista se recalcula al cambiar los filtros, «Me importa» o el nivel escolar.

### Pendientes

- **Tus lugares:** necesita un motor de tiempos de viaje, como un servicio externo (TravelTime) o un cálculo propio con los horarios de subte y colectivos. Hasta tenerlo, la sección muestra solo el estado vacío con el botón «Agregar un lugar» y nunca minutos estimados a mano. Los lugares se guardan como zonas aproximadas, no como direcciones exactas.
- **Dónde comer:** implementado el 13/11/2026 en `precio_entorno/lugares.py`, el endpoint `/api/barrios/{barrio}/lugares?tipo=` y la ficha web, con pruebas sobre respuestas grabadas en `tests/test_lugares.py`. El 13/11/2026 el equipo decidió no pagar nada a Google: la cuenta nueva pedía un prepago de USD 30 para activar el crédito de prueba. Sin `GOOGLE_MAPS_API_KEY` la sección no aparece y la app no consulta a Google. El código y sus pruebas quedan listos por si se habilita más adelante. En ese caso falta además reemplazar el texto «Google Maps» por el logo oficial. Nunca se hizo una llamada real a Google. La gastronomía de la ficha sale de OpenStreetMap.
- **Gastronomía de OSM:** desde el 13/11/2026, `python -m precio_entorno.entorno` la cuenta por barrio en `resumen.json` (`gastronomia`), y la ficha web la muestra con la mediana cada 100 ha y la cita de OpenStreetMap. Falta la capa de puntos en el mapa, que no se hizo para no sumar peso a `puntos.json`, y el contraste con un dataset de la Ciudad.
- **«Me importa»:** el orden personal depende de ese filtro de la barra superior. Sin selección, las capas siguen el orden de la tabla.
- **API:** `/api/barrios` ya entrega el entorno de cada barrio (`entorno`, tomado de `resumen.json`), los avisos que encajan y su mediana. Faltan tres cosas: las medianas de CABA que sirven de referencia, el USD por m² del barrio y de CABA, y el total de delitos del barrio con su valor por km². Hoy `/api/delitos` solo devuelve celdas para el mapa.

## Revisión contra los valores por defecto

- **Separadores con punto medio:** la app actual los usa en todos sus textos («Catálogo X · N avisos»), y es uno de los rasgos genéricos que la skill pide evitar. En el diseño nuevo se reemplazan por frases completas o por comas.
- **Tarjetas idénticas con sombra:** la lista de barrios usa filas separadas por una línea de color cordón, sin tarjetas ni sombras. El único elemento elevado es el panel sobre el mapa.
- **Acento terracota o verde ácido:** el acento es jacarandá, tomado de la ciudad y de la época del año.
- **Etiquetas en mayúsculas y números de paso:** los pasos 1, 2 y 3 de la app actual desaparecen. La barra de filtros y la selección en el mapa ya ordenan el recorrido.

## Plataforma

Streamlit no permite una lista y un mapa vinculados al pasar el cursor, paneles flotantes sobre el mapa ni una hoja deslizable en el celular. Hay dos caminos:

| Opción | Qué implica | Costo |
| --- | --- | --- |
| **A. Frontend web propio** | Una página HTML con MapLibre y deck.gl, servida por una API chica en Python que reutiliza `store`, `matching` y `entorno`. Streamlit queda para importar datos y probar. | Mayor: API, página y pruebas nuevas |
| **B. Streamlit con estilos** | Tema propio, tipografía, CSS y diseño ancho con columnas. Mapa y lista en paralelo, pero sin vínculo al pasar el cursor ni hoja móvil. | Menor: se mantiene todo lo actual |

La recomendación es la A, porque el diseño depende del vínculo entre la lista y el mapa. La B sirve si la prioridad es llegar rápido a la entrega del capstone.
