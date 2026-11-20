# Plan de crecimiento de Lüga: web, negocio y precios

**Fecha:** 20 de noviembre de 2026. Reúne todo lo trabajado ese día y propone un plan detallado para las próximas semanas. Cada sección enlaza al documento que tiene el detalle.

**Cómo leerlo:** la sección 1 resume lo aprendido; la 2, lo decidido; las secciones 3 a 6 son el plan (web, negocio, precios y calendario); la 7 son las métricas, y la 8, los riesgos.

---

## 1. Lo que aprendimos hoy

| Tema | Conclusión | Documento |
| --- | --- | --- |
| **El trabajo del cliente** | Quien se muda dentro de CABA quiere reducir la ciudad a los barrios donde le rinde el presupuesto y la vida diaria funciona, y enterarse a tiempo de los avisos que valen la pena, para decidir con confianza y sin pagar de más. Hay dos trabajos en el repositorio (el de quien busca y el de la inmobiliaria); el producto actual sirve al primero. | [jtbd.md](jtbd.md) |
| **La competencia real** | Se mapearon 14 alternativas, de los portales a «no hacer nada». La que hay que vencer es **la alerta gratis de Zonaprop**. | [jtbd.md §5](jtbd.md#5-competencia-y-contratación) |
| **Exclusividad de avisos** | Captura completa del escenario del benchmark (USD 1,49): cerca del **70 %** de los avisos de inmobiliarias también está en Zonaprop. Lüga suma entre 1 % y 2 % de oferta. **No se compite en cantidad.** | [jtbd.md §5.2](jtbd.md#52-la-contratación-que-hay-que-vencer), [datos.md](datos.md) |
| **La ventaja** | El portal cobra a quien publica, así que no puede decir que un aviso está caro. Lüga puede: **juicio independiente del lado del comprador.** | [estrategia.md](estrategia.md) |
| **La suposición más riesgosa** | Que alguien pague por seguir su búsqueda aunque la alerta del portal sea gratis. Sin evidencia todavía. | [experimento-concierge.md](experimento-concierge.md) |
| **El momento de confianza** | El primer correo de alerta: ¿la persona actúa según la comparación o va a verificar a Zonaprop? | [sprint-confianza.md](sprint-confianza.md) |
| **Océano azul** | Eliminar la carrera por inventario; crear la **segunda opinión** sobre avisos de otros portales y el **veredicto para reenviar**. | [oceano-azul.md](oceano-azul.md) |
| **Cabeza de playa** | Primer depto de 2 ambientes en **Caballito y Almagro**, hasta USD 150.000, donde ya está la base de comparación completa. | [cabeza-de-playa.md](cabeza-de-playa.md) |
| **Costos** | Fijos ≈ **USD 62/mes** cuando se cobre (Vercel Pro, monotributo, datos, mantenimiento). Equilibrio ≈ **10 ventas por mes** con el correo automatizado. | [modelo-de-negocio.md](modelo-de-negocio.md) |
| **Evidencia** | Todavía no hay entrevistas, llamadas de precio ni pagos. Todo lo anterior es hipótesis. | — |

## 2. Lo que ya está decidido

1. **Segmento:** quien busca vivienda, no la inmobiliaria. La inmobiliaria del capstone participa como **validadora**, no como cliente (confirmar con la profesora).
2. **Política guía:** competir en juicio, no en inventario; acompañar al portal, no reemplazarlo; no recibir plata de quien publica.
3. **Lo que no se hace:** competir en cantidad o velocidad; vender a inmobiliarias en paralelo; cobrar a anunciantes u orden pago; gastar en más fuentes; construir funciones de la lista hasta que pase el concierge; sumar capas o ampliar el radar.
4. **Precios publicados (primera tanda):** Buscar **ARS 13.000** (≈ USD 9) y Buscar acompañado **ARS 42.000** (≈ USD 29), por búsqueda durante 30 días, pago único, sin renovación automática. Explorar gratis. Tipo de cambio de referencia ARS 1.450 por USD.
5. **Hoy no se cobra:** «Anotarme en la primera tanda» crea la alerta con mail y anota el nivel elegido. La página está publicada en precio-entorno-caba.vercel.app.

---

## 3. Plan para la web

Ordenado por prioridad. Cada ítem dice qué se construye, por qué y cuándo está terminado.

| # | Qué | Por qué | Terminado cuando | Responsable |
| --- | --- | --- | --- | --- |
| W1 | **Contador de visitas sin datos personales** (fichas de barrio abiertas, diálogo de precios abierto, clics en «Anotarme» por nivel) | Sin denominador no se puede medir ninguna conversión | Los conteos diarios se pueden leer en un archivo o endpoint, sin cookies ni identificadores | SE |
| W2 | **Columna `interes` en el escenario «Búsquedas» de Make** | Hoy el nivel elegido llega a Make pero no queda en la planilla | Una alta de prueba aparece en la planilla con su nivel | SE |
| W3 | **Pedir la alerta al elegir el barrio** (hipótesis 1, ICE 7,3): el pedido en la primera pantalla de la ficha, con el motivo escrito | La alerta de Zonaprop recién sirve cuando se sabe el barrio; Lüga es donde se decide | Más alertas por ficha abierta que antes, sin más bajas en 7 días | SE |
| W4 | **Plantilla del correo de alerta con la comparación** (acción 3 de la estrategia) | Es la pieza que usan el concierge y el sprint | Una plantilla usada en los correos del concierge y en el prototipo | SE, 30/11 |
| W5 | **Comparación con su base visible** (cuántos parecidos, qué rango) | Sin evidencia, la lectura no genera confianza | Cada lectura muestra su base | DS |
| W6 | **Tipo de cambio real** en `PRECIOS.tipoCambio`, con fecha | Precios en pesos correctos | Valor actualizado y visible | Dueño del producto |
| W7 | **Segunda opinión** (el usuario carga precio, m², ambientes y barrio) | Factor nuevo del océano azul; convive con el portal | Respuesta con posición frente a parecidos o «no hay suficientes» | SE + DS, solo si pasa el concierge |
| W8 | **Checklist de visita y resumen para la familia** | Bonus de la oferta; dimensión social | Un enlace por aviso con lectura, checklist y barrio | SE, solo si pasa el concierge |
| W9 | **Botón de arrepentimiento y link de pago** | Requisito legal y forma de cobrar | Enlace visible desde la portada y pago probado | Dueño del producto + SE, antes de cobrar |

**No entra en el plan de la web:** WhatsApp, «Mi vida desde acá», intérprete con IA, bajas de precio, comparación lado a lado, nuevas capas. Vuelven a evaluarse con la evidencia del concierge ([monetizacion.md §3](monetizacion.md)).

## 4. Plan para el negocio

### 4.1 Descubrimiento (antes de cobrar)

| # | Qué | Detalle | Meta |
| --- | --- | --- | --- |
| N1 | **Entrevistas Mom Test** | 10 o más personas que se mudaron dentro de CABA en los últimos seis meses, con la [guía](guia-entrevistas.md) y sus [plantillas](plantillas/registro-entrevistas.csv). Reclutar con los mensajes de la sección 1.1 | Revisar las cuatro creencias cada 5 entrevistas |
| N2 | **Llamadas de disposición a pagar** | 10 llamadas (5 compra, 5 alquiler) con el guion de [monetizacion.md §2](monetizacion.md), aparte de las entrevistas | Curva de precios aceptable, caro y prohibitivo |
| N3 | **Validación con el corredor** (acción 2 de la estrategia) | El corredor revisa la lectura barato / en línea / caro en 30 avisos | Porcentaje de acuerdo medido, 04/12 |

### 4.2 Primera tanda (concierge)

| # | Qué | Detalle |
| --- | --- | --- |
| N4 | **Reclutar 20 personas elegibles** | Quienes se anotan desde «Precios», más las entrevistas y los grupos de barrio de Caballito y Almagro |
| N5 | **Primer correo gratis, después la oferta** | Un correo elegido a mano con hasta 3 avisos y su lectura; el segundo trae la oferta |
| N6 | **Dos precios, dos grupos** | La mitad recibe Buscar a USD 9 y la otra mitad a USD 15, con Buscar acompañado visible desde el principio |
| N7 | **Registrar todo** | Pagos, objeciones de precio, «qué barato», motivos de quien no paga y horas de trabajo manual |
| N8 | **Decidir el 11/12** | Con los disparadores de la sección 5 |

### 4.3 Design sprint (14 al 18/12)

Requiere nombrar a quien decide y a quien facilita. Prueba si la gente confía en la comparación que llega en el correo, con 5 personas y la entrevista en cinco actos ([sprint-confianza.md](sprint-confianza.md)).

### 4.4 Canales (en orden)

1. Personas que se anotan desde la web (sin costo de adquisición).
2. Presentaciones de conocidos y de quienes ya se anotaron.
3. Grupos de vecinos de Caballito y Almagro, respetando sus reglas.
4. Comunidades de crédito hipotecario («apto crédito»).
5. Testimonios de la primera tanda, con permiso.

**No se hace todavía:** publicidad paga. Sin evidencia de conversión, cualquier costo de adquisición es dinero a ciegas.

### 4.5 Expansión (bolos)

| Orden | Segmento | Condición para pasar |
| --- | --- | --- |
| 1 | Primer depto en Caballito y Almagro | Cabeza de playa |
| 2 | El mismo avatar en Villa Crespo, Flores y Boedo | 10 referencias del segmento 1 y datos frescos de los barrios nuevos |
| 3 | Compra «apto crédito» en toda CABA | Que el crédito hipotecario repunte |
| 4 | Recién llegados que alquilan | Resolver la velocidad de actualización |

### 4.6 Si el concierge falla (0 a 2 pagos de 20)

No bajar el precio como primera respuesta. Opciones, en orden:

1. **Cambiar el mensaje o el canal** y repetir una tanda.
2. **Cambiar quién paga:** gratis para quien busca, y la inmobiliaria paga por recibir búsquedas que la persona elige compartir.
3. **Cambiar de segmento:** la línea para inmobiliarias como producto principal ([fase-1-mercado-competitividad.md](fase-1-mercado-competitividad.md)).

---

## 5. Formas de ponerle precio al producto

### 5.1 Modelo actual

**Pase por búsqueda de 30 días**, en tres niveles. La métrica sigue al valor (una búsqueda acompañada hasta resolverse) y dar de baja porque la persona encontró dónde vivir es un éxito ([monetizacion.md §4](monetizacion.md)).

### 5.2 Alternativas evaluadas

| Forma | Cómo sería | Ventaja | Problema | Decisión |
| --- | --- | --- | --- | --- |
| **Pase por búsqueda (30 días)** | Pago único por búsqueda | Sigue al valor; sin renovación que moleste | Ingreso no recurrente | **Modelo actual** |
| **Pase de 60 días** | Lo mismo, más largo, con descuento | Las compras tardan meses | Más costo de soporte y de garantía | Probar si las entrevistas muestran búsquedas de más de 30 días |
| **Suscripción mensual** | Cobro recurrente | Ingreso previsible | La baja es el éxito; incentiva retener a quien ya encontró | **Descartada** |
| **Segunda opinión suelta** | Pago por cada aviso analizado | Entrada barata; convive con el portal | Ticket chico frente a la comisión de Mercado Pago | Probar el precio en las llamadas (pregunta de la opinión suelta) |
| **Precio por operación** | Compra y alquiler con precios distintos | Respeta disposiciones a pagar distintas | Dos ofertas que mantener | Activar si las llamadas muestran dos grupos de precio |
| **Precio de fundador** | Precio fijo para la primera tanda, real y con cupo | Urgencia honesta | Ninguno, si el cupo es real | Usar en la tanda 1 |
| **Descuento por referido** | Quien trae a otra persona recibe un descuento | Boca en boca en un segmento que consulta a su entorno | Costo por venta | Evaluar después de la tanda 1 |
| **Tarifa por éxito** | Cobro cuando la persona compra | Alineada al resultado | No se puede verificar la compra; se parece a una comisión, que la estrategia excluye | **Descartada** |
| **Cobro a inmobiliarias o anunciantes** | Destacados, orden pago, abonos | Ingreso grande | Destruye la independencia | **Descartada** (solo como pivote, con la búsqueda compartida por elección) |

### 5.3 Reglas para mover precios

- **Fijar antes los disparadores:** si el 80 % o más paga sin objeciones, subir el precio para los grupos nuevos (9 → 15 → 25); entre 25 % y 80 %, mantener; con menos de 25 %, revisar valor o segmento ([monetizacion.md §5](monetizacion.md)).
- **Nunca bajar el precio como primera respuesta** a una tanda floja.
- **Mantener el precio a quien ya pagó** cuando se sube para los grupos nuevos.
- **Señal sana:** que alguien diga «caro» y pague igual.
- **Comisión de Mercado Pago:** cobrar con acreditación a 35 días baja la comisión de cerca de 7,6 % a cerca de 1,8 % con IVA. Conviene si la caja lo permite.

---

## 6. Calendario

| Semana | Web | Negocio | Precios |
| --- | --- | --- | --- |
| **23 al 29/11** | W1 contador, W2 columna en Make, W6 tipo de cambio | N1 entrevistas (primeras 5), N4 reclutamiento | N2 llamadas (primeras 5) |
| **30/11 al 6/12** | W3 alerta al elegir barrio, W4 plantilla del correo (30/11), W5 base visible | N3 corredor (04/12), N5 primer correo gratis de la tanda | Decidir si se paga Vercel Pro y monotributo antes de la oferta |
| **7 al 11/12** (feriado el 8) | Medir W3 | N5 oferta, N7 registro | **N8 decisión del 11/12** con los disparadores |
| **14 al 18/12** | Prototipo del sprint | Design sprint | Ajustar niveles con la curva de las llamadas |
| **Desde el 21/12** | Si pasa el concierge: W9 cobro legal, W7 segunda opinión, W8 checklist y resumen | Tanda 2 paga; buscar las primeras 10 referencias | Precio de la tanda 2 según los disparadores |

## 7. Métricas a mirar

| Métrica | Qué mide | Fuente |
| --- | --- | --- |
| Anotados por nivel / aperturas del diálogo de precios | Interés por precio | W1 y W2 |
| Alertas creadas / fichas de barrio abiertas | La gran contratación | W1 |
| % de elegibles que pagan | Disposición a pagar real | Concierge |
| Objeciones de precio y «qué barato» | Si el precio está en la zona de valor | Registro del concierge |
| Aperturas del correo y avisos consultados | La pequeña contratación | Correos de alerta |
| Devoluciones y «no era lo que esperaba» | Promesa más grande que el producto | Registro del concierge |
| Horas manuales por búsqueda | Costo real de entregar | Registro del concierge |
| Margen de contribución por venta | Si cada venta suma | [modelo-de-negocio.md §4](modelo-de-negocio.md) |

## 8. Riesgos

| Riesgo | Señal | Respuesta |
| --- | --- | --- |
| Nadie paga | Menos de 3 de 20 pagan | Seguir la sección 4.6 |
| La comparación no genera confianza | En el sprint, la mayoría va a verificar a Zonaprop | Mostrar la base, sumar la revisión del corredor, o cambiar el diferencial |
| Datos viejos en la cabeza de playa | La base tiene más de un mes | Decidir la brecha 1 de [cabeza-de-playa.md](cabeza-de-playa.md): exportación autorizada, cambio de presupuesto o avisos que trae la gente |
| Fuente que corta el acceso | Un 403 o un aviso de la fuente | No evadirlo; pedir acceso o dejar la fuente |
| Uso comercial en Vercel Hobby | La página de precios ya está publicada | Pasar a Pro antes de cobrar |
| Cobrar sin requisitos legales | Ventas sin factura ni botón de arrepentimiento | No abrir la tanda paga hasta completar W9 |
| Segmento que se achica | Escrituras e hipotecas en baja | Seguir el bolo 3 solo si el crédito repunta |

## 9. Índice de documentos del día

[jtbd.md](jtbd.md) · [guia-entrevistas.md](guia-entrevistas.md) · [sprint-confianza.md](sprint-confianza.md) · [experimento-concierge.md](experimento-concierge.md) · [estrategia.md](estrategia.md) · [oceano-azul.md](oceano-azul.md) · [monetizacion.md](monetizacion.md) · [ideas-conversion.md](ideas-conversion.md) · [oferta.md](oferta.md) · [cabeza-de-playa.md](cabeza-de-playa.md) · [modelo-de-negocio.md](modelo-de-negocio.md) · [datos.md](datos.md) (medición de exclusividad)
