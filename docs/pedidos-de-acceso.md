# Pedidos de acceso al catálogo de avisos

Borradores para conseguir la fuente inmobiliaria autorizada que exige la consigna. Completá los campos entre corchetes antes de enviar. Conviene que la autorización llegue **por escrito** y conservarla junto al proyecto, fuera de Git si incluye datos de contacto.

---

## 1. Zonaprop

**Para:** [contacto de Zonaprop: área legal, datos o relaciones institucionales]
**Asunto:** Pedido de autorización para uso académico de avisos de venta en CABA

Estimado equipo de Zonaprop:

Mi nombre es [Nombre y apellido]. Curso [programa] en [institución], y estoy desarrollando mi proyecto final sobre el mercado de departamentos en venta en la Ciudad de Buenos Aires. Les escribo para pedirles autorización para usar una muestra de avisos publicados en Zonaprop con fines exclusivamente académicos y no comerciales.

**El proyecto.** Es una aplicación prototipo que ayuda a una persona que quiere comprar un departamento a decidir en qué barrios buscar, según su presupuesto, ambientes y superficie. Le avisa cuando aparece un aviso compatible, con un enlace al aviso original en Zonaprop. El análisis compara precios publicados por m² entre barrios y evalúa si el contexto de los delitos registrados por la Ciudad mejora su predicción. No se estiman tasaciones ni precios de cierre.

**Qué datos necesito.** Solo avisos vigentes de departamentos en venta en CABA, con estos campos:

| Campo | Uso |
| --- | --- |
| ID del aviso y enlace | Evitar duplicados y remitir al aviso original |
| Fecha de captura | Ubicar el aviso en el tiempo |
| Precio publicado y moneda | Precio por m² (solo USD) |
| Superficie cubierta y total, ambientes | Comparar inmuebles similares |
| Barrio y coordenadas, con su precisión si existe | Ubicar el aviso y cruzarlo con datos públicos |

**No necesito ningún dato del anunciante:** ni nombres, ni teléfonos, ni correos.

**Volumen y forma de acceso.**
- **Volumen:** primero, una prueba de hasta 50 avisos de Caballito y Almagro. Después, una muestra única de entre 700 y 2.000 avisos.
- **Forma de acceso:** la que ustedes prefieran. Puede ser una exportación, un feed o una API. Si lo permiten, también puedo hacer una consulta automatizada de bajo volumen, en una sola pasada, sin proxies y respetando los límites que indiquen. Hoy el acceso automatizado devuelve un bloqueo (HTTP 403) y sus términos restringen el uso de herramientas externas, por eso les pido autorización antes de avanzar.

**Compromisos.**
- Uso exclusivamente académico y no comercial.
- Los datos se guardan localmente, no se redistribuyen y se eliminan al terminar el proyecto.
- Solo se publican resultados agregados, como medianas por barrio, y nunca avisos individuales.
- Se cita a Zonaprop como fuente en el informe final.
- Puedo compartirles el informe y el prototipo si les interesan.

Quedo a disposición para darles más detalles o ajustar el pedido a sus condiciones.

Saludos cordiales,
[Nombre y apellido]
[Programa · Institución]
[Correo · Teléfono]

---

## 1b. Zonaprop: pedido de acceso por API (seguimiento)

Para enviar como respuesta al hilo en que Zonaprop autorizó el uso, así la autorización queda a la vista.

**Para:** [la persona o el área que firmó la autorización]
**Asunto:** Re: Pedido de autorización para uso académico de avisos de venta en CABA: acceso por API

Hola, [nombre]:

Les agradezco otra vez la autorización para usar avisos de Zonaprop en mi proyecto final de [programa] en [institución]. Gracias a ella pude armar el prototipo. Hoy compara barrios de CABA según el presupuesto y las preferencias de quien busca, muestra el entorno de cada zona y avisa por correo cuando aparece un aviso compatible, con un enlace al aviso original en Zonaprop.

Para la captura usé un servicio de extracción de terceros, a bajo volumen y en pocas pasadas. Les escribo para pedirles **acceso de solo lectura a una API o a un feed oficial** que reemplace esa captura. Sería más prolijo para ustedes, que no tendrían tráfico automatizado sobre el sitio, y para el proyecto, que trabajaría con datos más precisos y bajo sus condiciones.

**Qué necesitaría.**
- **Avisos vigentes** de departamentos en CABA, en venta y en alquiler.
- **Campos:** ID y enlace, precio publicado y moneda, superficie cubierta y total, ambientes, antigüedad, cocheras, barrio y coordenadas (con su precisión, si existe), fecha de publicación y, si está disponible, fecha de baja o cambio de precio.
- **Frecuencia:** una consulta cada dos días como máximo, respetando los límites que indiquen.
- **Ningún dato del anunciante:** ni nombres, ni teléfonos, ni correos.

**Compromisos.** Mantengo los de la autorización original: uso académico y no comercial, datos guardados localmente y eliminados al terminar el proyecto, publicación solo de resultados agregados y cita a Zonaprop como fuente. Las alertas siempre remiten al aviso en Zonaprop.

Si existe un programa de integración o de socios, me sirve cualquier vía: credenciales de prueba, documentación, una exportación periódica o una reunión breve para ajustar el pedido. Si les interesa, les comparto el informe y una demo del prototipo.

Muchas gracias,
[Nombre y apellido]
[Programa · Institución]
[Correo · Teléfono]

---

## 2. Inmobiliaria

**Para:** [Nombre del responsable] · [Inmobiliaria]
**Asunto:** Propuesta de prueba gratuita: alertas de avisos para compradores en CABA

Hola, [Nombre]:

Soy [Nombre y apellido] y estoy terminando [programa] en [institución]. Como proyecto final desarrollé una herramienta para quienes gestionan búsquedas de departamentos en venta en CABA. Me gustaría proponerles una prueba corta y sin costo.

**Qué hace.**
- Carga los filtros de cada comprador: presupuesto, ambientes y superficie mínima.
- Muestra en qué barrios hay más opciones compatibles y su precio publicado mediano.
- Avisa una sola vez cuando entra un aviso nuevo que coincide con una búsqueda guardada.
- Muestra los delitos registrados por barrio como contexto, con los datos oficiales de la Ciudad.

**Qué les pido.**
1. **Una exportación de sus departamentos en venta vigentes** en CSV o Excel, con ID, enlace, precio y moneda, superficie cubierta y total, ambientes, barrio y, si la tienen, la ubicación. **No hace falta ningún dato de propietarios ni de compradores.** Si pueden repetir la exportación una o dos veces durante la prueba, puedo medir las alertas con avisos nuevos.
2. **Una o dos personas del equipo** que usen la herramienta con algunas búsquedas reales durante [dos semanas] y que respondan una breve entrevista al final.

**Qué mediría.**
- Cuánto tardan en encontrar opciones compatibles, comparado con su forma habitual de trabajar.
- Cuántas alertas resultan útiles.
- Cuánto costaría mantener el seguimiento.
- Si una herramienta así les resultaría valiosa y en qué condiciones.

**Qué ofrezco a cambio.**
- Uso gratuito del prototipo durante la prueba.
- Un informe con los resultados y el análisis de precios publicados por barrio de su propio catálogo.
- Confidencialidad: sus datos se usan solo para este proyecto, no se comparten y se eliminan al terminar. En el informe académico aparecen solo resultados agregados y, si lo prefieren, sin el nombre de la inmobiliaria.

¿Les parece si coordinamos una llamada de 20 minutos para mostrarles la herramienta?

Gracias,
[Nombre y apellido]
[Programa · Institución]
[Correo · Teléfono]

### Versión corta para WhatsApp o LinkedIn

> Hola, [Nombre]. Soy [Nombre], estudiante de [programa] en [institución]. Desarrollé una herramienta que avisa cuando entra un departamento en venta compatible con las búsquedas de sus compradores y compara barrios según presupuesto y ambientes. Busco una inmobiliaria de CABA para una prueba gratuita de dos semanas: necesito una exportación de sus avisos vigentes, sin datos de clientes, y la opinión de alguien del equipo. ¿Les interesa que les cuente más en una llamada corta?

---

## 3. Mob (mob.ar)

**Para:** [contacto de Mob: soporte, alianzas o el formulario de contacto del sitio]
**Asunto:** Pedido de autorización para leer avisos de CABA con fines académicos

Hola, equipo de Mob:

Soy [Nombre y apellido] y curso [programa] en [institución]. Mi proyecto final es una aplicación que ayuda a quien busca comprar o alquilar un departamento en CABA a comparar barrios según su presupuesto. La app avisa cuando aparece un aviso compatible y siempre enlaza al aviso original en Mob.

Les pido autorización para **leer de forma automatizada los avisos de departamentos en venta y en alquiler de Capital Federal** publicados en mob.ar.

**Cómo lo haría:**
- **Identificación:** el cliente se presenta con un nombre propio, `precio-entorno-caba/0.1 (proyecto academico; captura autorizada)`.
- **Alcance:** respeta su robots.txt, no usa `/api/` ni áreas privadas y lee solo las páginas públicas de listado y de aviso.
- **Ritmo:** un pedido cada 3 segundos como mínimo y una actualización cada 2 días, con unos 200 avisos recientes por vez.
- **Sin evasión:** no usa proxies ni técnicas para esquivar bloqueos. Si el sitio responde con un bloqueo, se detiene.

**Datos que tomaría:** ID y enlace del aviso, operación, precio y moneda, expensas, superficie cubierta y total, ambientes, barrio y coordenadas si están publicadas. **No tomaría datos de anunciantes ni de contacto.**

**Compromisos:**
- Uso académico y no comercial.
- Datos guardados en forma local, sin redistribución, y eliminados al terminar el proyecto.
- Solo resultados agregados en el informe, con Mob citado como fuente.

Si prefieren otra vía, como una exportación periódica, un feed o la API con credenciales, me adapto a la que indiquen. Puedo mostrarles el prototipo en una llamada corta.

Saludos,
[Nombre y apellido]
[Programa · Institución]
[Correo · Teléfono]

---

## 4. Properati

**Para:** [contacto de Properati: alianzas, datos o el formulario de contacto del sitio]
**Asunto:** Acceso a avisos de departamentos en CABA para un proyecto académico

Hola, equipo de Properati:

Soy [Nombre y apellido] y curso [programa] en [institución]. Estoy desarrollando una aplicación académica que compara la oferta de departamentos en venta y en alquiler por barrio en CABA, y avisa cuando aparece un aviso compatible con la búsqueda de una persona. Cada alerta enlaza al aviso original.

Hoy su sitio rechaza los accesos automatizados (HTTP 403) y no quiero avanzar sin su autorización. Les consulto si pueden habilitar alguna de estas vías:

1. **Una exportación o un feed** de avisos vigentes de departamentos en Capital Federal, en venta y en alquiler.
2. **Acceso a una API** con credenciales para este proyecto.
3. **Autorización para leer las páginas públicas** con un cliente identificado (`precio-entorno-caba/0.1 (proyecto academico; captura autorizada)`), sin proxies, con un pedido cada 3 segundos como mínimo y una actualización cada 2 días.

**Datos necesarios:** ID y enlace, operación, precio y moneda, expensas, superficie, ambientes, barrio y coordenadas. **Nada de anunciantes ni de contacto.**

**Compromisos:**
- Uso académico y no comercial.
- Datos guardados en forma local, sin redistribución, y eliminados al terminar el proyecto.
- Solo resultados agregados en el informe, con Properati citado como fuente.

Quedo a disposición para ajustar el pedido a sus condiciones.

Saludos,
[Nombre y apellido]
[Programa · Institución]
[Correo · Teléfono]

---

## 5. Mercado Libre (soporte de clasificados)

**Para:** vis-support@mercadolibre.com
**Asunto:** Acceso a la búsqueda de inmuebles (MLA1459) y autorización de uso académico · App [ID de la app]

Hola, equipo de Mercado Libre:

Soy [Nombre y apellido] y curso [programa] en [institución]. Como proyecto final desarrollo una aplicación académica que ayuda a quien busca comprar o alquilar un departamento en la Ciudad de Buenos Aires a comparar barrios según su presupuesto, y le avisa cuando aparece un aviso compatible. Cada alerta enlaza al aviso original.

Para integrar avisos de Mercado Libre registré una aplicación en el DevCenter (ID [ID de la app]) y seguí su guía «Localizar Inmuebles». Les escribo por dos temas.

**1. Acceso a la búsqueda de inmuebles.** Siguiendo la guía, consulté:

```
GET https://api.mercadolibre.com/sites/MLA/search?item_location=lat:-34.71_-34.53,lon:-58.53_-58.33&category=MLA1459&limit=1
```

con un access token válido de la aplicación, y la respuesta fue:

```
403 {"message": "forbidden", "error": "forbidden", "status": 403, "cause": []}
```

Con el mismo token, `GET /users/me` responde correctamente. El token incluye el scope `urn:ml:vis:publish-sync:/read-only` (permiso funcional «Publicación y sincronización») y no tiene scopes de Mercado Pago. Les pido que habiliten la búsqueda de la categoría Inmuebles con el filtro `item_location` para esta aplicación o, si hace falta otro permiso, que me indiquen cuál.

**2. Autorización para el uso de los datos.** Según la cláusula 5.4 de los Términos y Condiciones para desarrolladores, publicar precios promedio o estadísticas requiere autorización expresa. El proyecto usaría los datos así:
- **Datos:** departamentos en venta y en alquiler de Capital Federal. De cada aviso, solo ID, enlace, precio y moneda, expensas, superficie, ambientes, barrio y ubicación. **Ningún dato de vendedores ni de contacto.**
- **Uso:** comparar la oferta entre barrios con medianas de precios publicados, siempre presentados como precios de publicación, y avisar de publicaciones nuevas con enlace a Mercado Libre.
- **Volumen y ritmo:** unos pocos miles de avisos, consultados solo por la API y dentro de sus límites. Si lo requieren, los listados se actualizan al menos cada 6 horas (cláusula 5.3) y se retiran los avisos que dejan de estar activos.
- **Compromisos:** uso académico y no comercial, datos guardados en forma local y sin redistribución, eliminación al terminar el proyecto y Mercado Libre citado como fuente en el informe.

Puedo enviarles el informe y mostrarles el prototipo en una llamada corta. Si prefieren otra vía, como una muestra o una exportación, me adapto a la que indiquen.

Saludos cordiales,
[Nombre y apellido]
[Programa · Institución]
[Correo · Teléfono]
---

## 6. Clarín Inmuebles

**Para:** [contacto de Clarín Inmuebles que habilitó la lectura]
**Asunto:** Acceso técnico para la lectura autorizada de avisos de departamentos en CABA

Hola, [Nombre]:

Gracias por habilitar la lectura de avisos de Clarín Inmuebles para mi proyecto final de [programa] en [institución]. Al probarla, el firewall del sitio (AWS WAF) respondió con un bloqueo (HTTP 403) a las páginas de listado, y detuve la consulta.

**Cómo consulto el sitio.**
- El cliente se identifica como `precio-entorno-caba/0.1 (proyecto academico; captura autorizada)`, sin proxies ni técnicas para ocultarse.
- Respeta robots.txt: lee solo las páginas 1 a 3 de los listados de departamentos por barrio y no usa `/api/`.
- Espera 3 segundos entre pedidos y se detiene ante el primer bloqueo.
- No abre fichas ni copia datos de anunciantes: solo precio, moneda, superficie, ambientes, barrio, expensas y el enlace al aviso.

**Qué les pido.** Cualquiera de estas opciones:
1. Habilitar ese identificador, o la IP [IP pública], en el firewall para las páginas de listado.
2. Una exportación de departamentos en venta y en alquiler vigentes en CABA, con ID, enlace, precio, moneda, superficie cubierta y total, ambientes, barrio y, si es posible, coordenadas.

**Volumen.** Una prueba de 50 avisos y después una muestra de entre 700 y 2.000. Si lo permiten, una actualización cada 2 días con los avisos nuevos.

**Compromisos.** Uso académico y no comercial. Los datos se guardan localmente y no se redistribuyen. Solo publico resultados agregados y cito a Clarín Inmuebles como fuente.

Saludos cordiales,
[Nombre y apellido]
[Programa · Institución]
[Correo · Teléfono]

---

## 7. Qué confirmar en la respuesta

Antes de extraer o cargar datos, verificá que la autorización por escrito diga:

- [ ] **Quién autoriza** y en nombre de qué empresa.
- [ ] **Campos permitidos**, incluidas las coordenadas y su precisión.
- [ ] **Forma de acceso:** exportación, API o consulta automatizada (con Apify, si corresponde) y sus límites de frecuencia.
- [ ] **Volumen y período:** prueba de 50 avisos y muestra de 700 a 2.000.
- [ ] **Uso permitido:** académico, con resultados agregados en el informe.
- [ ] **Conservación:** dónde se guardan los datos y cuándo se eliminan.
- [ ] **Cita de la fuente** en el informe, o anonimato si lo piden.

Con la autorización confirmada, cargá el archivo en **Datos reales** con el nombre del catálogo y corré el modelo con `python -m precio_entorno.modelo`.
