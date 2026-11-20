# Estrategia de Lüga: el núcleo

**Fecha:** 20 de noviembre de 2026. Escrita con la skill `good-strategy-bad-strategy` (Richard Rumelt), a partir de la presentación `Precio y Entorno CABA.pptx` del 12/11, de [jtbd.md](jtbd.md) y del [experimento concierge](experimento-concierge.md). Es una hipótesis: se revisa con evidencia.

## 1. Auditoría de la presentación

No hay un plan de negocio de una página en el repositorio. Se auditó la presentación de 9 diapositivas, que cumple ese papel: quiénes somos, el problema, cómo funciona, los datos, el modelo de negocio y el próximo paso.

**1. Relleno**

- **«Una startup proptech: plataforma web de dos lados» (diapositiva 2).** En palabras simples: «una web con dos tipos de clientes». Ninguno de los dos lados existe todavía. Hablar de plataforma de dos lados sugiere efectos de red que nadie vio.
- **«Enterate primero cuando aparece una opción» (diapositiva 1).** No es relleno: es una promesa contra la evidencia. Lüga actualiza cada 2 días, y el [pricing](pricing-busqueda-personal.md) advierte que ser el primero «requiere evidencia frente a las alertas de origen».

**2. No enfrentar el desafío (el más grave)**

- La presentación nunca nombra el obstáculo real: **la alerta gratis de Zonaprop**, donde está la mayor parte de la oferta.
- La diapositiva 3 usa «1.024 avisos en Zonaprop» como prueba de un problema. En realidad prueba la fuerza del competidor: en ese mismo escenario Lüga tiene 63, y cerca del 70 % de sus avisos de inmobiliarias también está en Zonaprop ([jtbd.md, §5.2](jtbd.md#52-la-contratación-que-hay-que-vencer)).
- También oculta que las fuentes dependen de permisos que se pueden cortar: RE/MAX ya responde 403, y los términos de Zonaprop limitan el acceso automatizado.

**3. Metas presentadas como estrategia**

- «Búsquedas que reciben una opción útil en 7 días» y «NPS de 30 o más en los dos lados» (diapositiva 8) son metas. No dicen cómo se llega.

**4. Objetivos malos (una lista de todo)**

- **Demasiado a la vez:** pase para quien busca, SaaS para inmobiliarias, radar de prensa, contexto de delitos, capas del entorno, automatización y modelo de precios, todo junto.
- **Dos arranques en frío:** abrir los dos lados a la vez obliga a empezar de cero dos veces.
- **Objetivo en el aire:** «Pedido a inmobiliarias» necesita un volumen de personas buscando que Lüga no tiene.

**Diagnóstico: 3/10.** Pasan 2 de las 8 filas de la skill:

- un primer objetivo alcanzable: la prueba de 90 días con 20 personas;
- una lista de lo que Lüga no es (diapositiva 2): ni portal, ni inmobiliaria, ni comisión por la venta.

Fallan: el desafío no está nombrado; no hay política guía, ni responsables, ni fechas; Roomix podría copiar el discurso casi sin cambios; no se aprovecha ninguna asimetría; y nadie intentó destruir el plan.

## 2. El núcleo

### Diagnóstico

Quien se muda dentro de CABA ya tiene una herramienta gratis y buena para enterarse de avisos: la alerta de Zonaprop, en el portal donde está la mayor parte de la oferta. Lüga no puede ganarle en cantidad ni en velocidad. En el escenario del benchmark tiene 63 avisos contra 947, cerca del 70 % de lo que trae de inmobiliarias ya está en Zonaprop, y sus fuentes dependen de permisos que se pueden retirar. Lo que el portal **no puede** hacer es decirle a quien compra que un aviso está caro, porque gana su plata con los anunciantes que publican ahí. Por eso el desafío crítico no es juntar avisos: es convertirse en un **juicio creíble e independiente** sobre qué barrio y qué aviso valen la pena, y hoy no hay evidencia de que alguien confíe en ese juicio o pague por él. El plan actual lo empeora al querer arrancar dos lados a la vez sin tener ninguno.

### Política guía

**Ser el juicio independiente de quien busca, del lado del comprador, y cobrarle solo a esa persona.** Lüga compite en criterio (barrio y precio frente a avisos parecidos), no en inventario. Acompaña al portal en lugar de reemplazarlo. Y mientras el juicio sea el producto, no recibe plata de quien publica avisos.

Esto descarta clases enteras de acciones:

- competir en cantidad de avisos o en velocidad;
- vender a inmobiliarias en paralelo;
- cobrar a anunciantes o vender lugares destacados;
- gastar plata para «tener más avisos»;
- sumar funciones que no refuerzan el juicio.

El [lienzo estratégico y la grilla ERRC](oceano-azul.md) bajan esta política a factores concretos: qué eliminar y reducir para bajar el costo, y qué aumentar y crear (la segunda opinión sobre un aviso) para subir el valor.

### Tres acciones coherentes

Los responsables usan los roles del [tablero de Trello](tablero-trello.md).

| # | Acción | Responsable | Terminada cuando | Fecha |
| --- | --- | --- | --- | --- |
| 1 | **Probar que el juicio se paga:** el [experimento concierge](experimento-concierge.md) (correo elegido a mano, USD 9, 20 personas elegibles). | BIZ + dueño del producto | 20 personas recibieron la oferta y el resultado se comparó con el umbral de 5 pagos | 11/12/2026 |
| 2 | **Hacer el juicio defendible.** Cada comparación muestra en qué se basa (cuántos parecidos, qué rango). El corredor de la inmobiliaria de la validación revisa la lectura barato / en línea / caro en 30 avisos. Así se mantiene la validación con una inmobiliaria que pide el capstone, con la inmobiliaria como **validadora, no como cliente**. | DS | Acuerdo con el corredor medido en 30 avisos | 04/12/2026 |
| 3 | **Concentrar el producto en el momento de confianza.** El único trabajo de producto es el correo de alerta con la comparación: una plantilla que el concierge usa a mano y que el [design sprint](sprint-confianza.md) prueba del 14 al 18 de diciembre. | SE | Una plantilla usada en los correos del concierge y en el prototipo del sprint | 30/11/2026 |

Las acciones se refuerzan entre sí:

- la 3 da el correo que usan la 1 y la 2;
- la 2 hace creíble la oferta de la 1;
- la 1 decide si la 3 se construye de verdad.

## 3. Lo que elegimos no hacer

1. **No competir en cantidad de avisos ni en velocidad.** «Enterate primero» sale del discurso.
2. **No vender el lado de las inmobiliarias (USD 39 por mes) en paralelo.** Vuelve solo como pivote si el concierge da 0 a 2 pagos de 20.
3. **No cobrar a anunciantes, ni vender avisos destacados, ni orden pago.** Rompería la independencia, que es toda la asimetría.
4. **No gastar los cerca de USD 2,50 que quedan del presupuesto de Apify en más fuentes.** Como mucho, medir Mob si hace falta.
5. **No construir nada más de la [lista de funciones](experimento-concierge.md#1-la-lista-de-funciones-deseadas) hasta que pase el concierge:** WhatsApp, «Mi vida desde acá», el intérprete con IA, bajas de precio, comparación lado a lado, normalización de direcciones.
6. **No sumar capas al mapa ni ampliar el radar de prensa.**

## 4. Una tensión y lo que falta

**Tensión con la consigna.** [alcance.md](alcance.md) pide probar el negocio con una inmobiliaria. La acción 2 conserva ese requisito, pero cambia el papel de la inmobiliaria: de cliente a validadora experta. Confirmar con la profesora que eso sigue contando.

**Diagnóstico del núcleo: 9/10.** Pasan 7 de las 8 filas. La que falta: nadie intentó destruirlo todavía. Antes de adoptarlo, hacer el ejercicio de crear y destruir: atacarlo como se atacaría el plan de un competidor.
