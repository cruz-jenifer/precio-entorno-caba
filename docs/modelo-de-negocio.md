# Modelo de negocio y costos de Lüga

**Fecha:** 20 de noviembre de 2026. Reúne lo decidido en [jtbd.md](jtbd.md), [estrategia.md](estrategia.md), [oceano-azul.md](oceano-azul.md), [monetizacion.md](monetizacion.md), [oferta.md](oferta.md), [cabeza-de-playa.md](cabeza-de-playa.md) y el [experimento concierge](experimento-concierge.md), y le suma los costos con su fuente. Es el respaldo de la página de precios publicada en la web.

Cada cifra lleva su origen: **[Medido]** sale del proyecto, **[Tarifa]** es un precio público consultado el 20/11/2026 y **[Supuesto]** es una hipótesis a reemplazar con datos.

## 1. Qué vende Lüga y a quién

- **A quién:** quien se muda dentro de CABA. La cabeza de playa es quien compra su primer departamento de 2 ambientes en Caballito o Almagro, hasta USD 150.000 ([cabeza-de-playa.md](cabeza-de-playa.md)).
- **El trabajo:** reducir la ciudad a los barrios donde rinde el presupuesto y la vida diaria funciona, y enterarse a tiempo de los avisos que valen la pena ([jtbd.md](jtbd.md)).
- **La apuesta:** Lüga no compite en cantidad de avisos (tiene 63 contra 947 de Zonaprop en el escenario del benchmark) sino en **juicio independiente**: cada aviso comparado con sus parecidos, y nadie paga para aparecer ([estrategia.md](estrategia.md)).
- **Quién paga:** solo quien busca. Sin plata de anunciantes ni línea para inmobiliarias mientras el juicio sea el producto.

## 2. Precios publicados (primera tanda)

Decididos el 20/11/2026. Se cobra **por búsqueda durante 30 días**, pago único, sin renovación automática.

| Nivel | Precio | Qué incluye |
| --- | --- | --- |
| **Explorar** | Gratis | Barrios donde rinde el presupuesto, entorno en el mapa, avisos con su comparación frente a parecidos. Durante el lanzamiento, la alerta por mail también es gratis. |
| **Buscar** | **ARS 13.000** (≈ USD 9) | Seguimiento de 30 días: hasta 3 avisos nuevos por correo, cada uno con su lectura y el motivo; segunda opinión sobre avisos que encuentres en portales; resumen para reenviar a la familia. |
| **Buscar acompañado** | **ARS 42.000** (≈ USD 29) | Todo lo de Buscar, más una persona que revisa hasta 5 avisos que elijas y te dice qué preguntar antes de visitar. |

- **Moneda:** el precio principal va en pesos, como pide la norma de precios a consumidores, con el valor en dólares de referencia. **[Supuesto]** Tipo de cambio de referencia: ARS 1.450 por USD, el que usa el proyecto en el EDA. Hay que fijar el real antes de cobrar.
- **Garantía «Tres Avisos»:** si en 30 días no llegan al menos 3 avisos nuevos que cumplan lo imprescindible, se devuelve todo ([oferta.md](oferta.md)).
- **Escasez real:** 20 búsquedas por tanda, porque la revisión humana se hace a mano.
- **Hoy no se cobra.** El botón de los niveles pagos anota el interés con la alerta gratis. Cobrar requiere lo de la sección 6.
- **Diferencia con [monetizacion.md](monetizacion.md):** ahí Explorar mostraba solo 3 coincidencias. La web hoy muestra todos los avisos gratis, así que la página no promete un límite que no existe.

## 3. Costos fijos por mes (cuando se cobre)

| Costo | Monto por mes | Fuente |
| --- | --- | --- |
| **Vercel Pro** (el plan Hobby es solo para uso no comercial) | USD 20 | [Tarifa] resúmenes de la tarifa de Vercel ([1](https://www.stork.ai/blog/vercel-pricing-2026), [2](https://costbench.com/software/developer-tools/vercel/)); confirmar en vercel.com/pricing |
| **Monotributo categoría A, servicios** (si no se paga ya por otra actividad) | ARS 49.527,18 ≈ USD 34,16 | [Tarifa] tabla de ARCA de noviembre de 2026 citada por la prensa ([MDZ](https://www.mdzol.com/economia/2026/11/6/monotributo-en-noviembre-cuanto-se-paga-en-cada-categoria-de-arca-1993563.html), [iProfesional](https://www.iprofesional.com/impuestos/469141-monotributo-noviembre-2026-cuanto-se-paga-por-mes-segun-cada-categoria-de-arca)) |
| **Datos de la cabeza de playa** (Caballito y Almagro) | USD 2,24 | [Medido] una captura completa del escenario costó USD 1,49 el 20/11 ([datos.md](datos.md)); se suma una captura de avisos nuevos cada 2 días, a USD 0,001 por aviso, unos USD 0,05 cada vez × 15 = USD 0,75 |
| **Make** | USD 0 hasta unas 19 búsquedas activas; después USD 16 (Core mensual, 10.000 créditos) | [Tarifa] Free tiene 1.000 créditos por mes ([resumen de tarifas](https://www.flowbuilderhq.com/make-com-pricing-2026/)). [Supuesto] cada búsqueda gasta unos 45 créditos por mes (15 corridas × 3 créditos) más unos 150 de la corrida misma |
| **Mantenimiento de conectores** | USD 6 | [Supuesto] 30 minutos por mes a USD 12 por hora, de [entrega-inferencia.md](entrega-inferencia.md) |
| **Dominio** | USD 0 | Se sigue usando `precio-entorno-caba.vercel.app`. Un dominio propio se cotiza aparte |
| **Total** | **USD 62,40** (USD 78,40 con Make Core) | Sin monotributo, si ya se paga: USD 28,24 |

**Presupuesto de extracción:** el proyecto tiene un tope total de USD 25 en Apify y quedan unos USD 2,50 ([memoria de gasto en datos.md](datos.md)). Mantener los datos frescos más de un mes exige cambiar esa regla, pedir a Zonaprop una exportación autorizada o apoyarse en los avisos que trae la gente. El plan Free de Apify da USD 5 de uso por mes por cuenta ([resumen de tarifas](https://use-apify.com/docs/what-is-apify/apify-pricing)).

## 4. Costos por venta

| Costo | Buscar (ARS 13.000) | Buscar acompañado (ARS 42.000) | Fuente |
| --- | --- | --- | --- |
| Comisión de Mercado Pago, link de pago con acreditación inmediata en CABA: 6,29 % + IVA = 7,61 % | USD 0,68 | USD 2,21 | [Tarifa] [calculadoras y pasarelas](https://atempora.studio/herramientas/calculadora-comisiones) ([2](https://talo.com.ar/blogs/mejores-pasarelas-pago-argentina)); confirmar en la tabla oficial. Esperar 35 días baja la comisión a cerca de 1,5 % + IVA |
| Soporte: 10 minutos por búsqueda | USD 2 | USD 2 | [Supuesto] a USD 12 por hora |
| Revisión humana de hasta 5 avisos: 50 minutos | — | USD 10 | [Supuesto] 10 minutos por aviso |
| Reserva para devoluciones (garantía): 10 % | USD 0,90 | USD 2,90 | [Supuesto] |
| Armado del correo en la primera tanda: el sistema arma el correo y una persona agrega el motivo, 5 minutos × 8 correos | USD 8 | USD 8 | [Supuesto] solo mientras sea semi-manual |

**Margen de contribución por venta:**

| | Buscar | Buscar acompañado |
| --- | --- | --- |
| **Primera tanda (semi-manual)** | **−USD 2,58** | **USD 3,89** |
| **Automatizado** (sin armado manual del correo) | **USD 5,42** | **USD 11,89** |

La primera tanda pierde plata en «Buscar» a propósito: es el costo de aprender, el mismo del concierge. Con el correo automatizado, los dos niveles dejan margen.

## 5. Punto de equilibrio (automatizado)

- **Mezcla de ventas supuesta:** 78 % Buscar y 22 % Acompañado, la proporción entre los niveles pagos de la meta 70/20/10. Margen promedio: 0,78 × 5,42 + 0,22 × 11,89 = **USD 6,85 por venta**.
- **Con monotributo y Make Free:** USD 62,40 ÷ 6,85 ≈ **10 ventas por mes**. Con 10 búsquedas activas, Make sigue dentro del plan gratis (unos 600 créditos).
- **Sin monotributo propio** (si ya se paga): USD 28,24 ÷ 6,85 ≈ **5 ventas por mes**.
- **Solo «Buscar»:** USD 62,40 ÷ 5,42 ≈ **12 ventas por mes**.

No incluye el tiempo de desarrollo ni el costo de conseguir cada cliente. Con 20 búsquedas por tanda, el equilibrio pide vender la mitad de cada tanda.

## 6. Antes de cobrar

1. **Monotributo y facturación:** cada venta lleva factura.
2. **Botón de arrepentimiento:** la Resolución 424/2020 obliga a quien vende servicios por la web a publicar un enlace con ese nombre exacto, visible desde la portada y sin pedir registro ([texto oficial](https://www.argentina.gob.ar/normativa/nacional/norma-342869/texto)). La garantía convive con el derecho de revocar dentro de los 10 días.
3. **Vercel Pro:** el plan Hobby no admite uso comercial.
4. **Tipo de cambio real** para los precios en pesos, y fecha de actualización visible.
5. **Datos personales:** informar para qué se usa el mail y la búsqueda, y no compartirlos.
6. **Registrar el interés por nivel:** el botón «Anotarme» manda el nivel elegido a Make (`interes`), pero para que quede en la planilla hay que agregar esa columna al escenario «Búsquedas».

## 7. Cómo se valida

- **Prueba de comportamiento:** publicar los precios y contar cuántas personas se anotan en cada nivel es la primera señal real de disposición a pagar ([monetizacion.md](monetizacion.md), sección 5).
- **Concierge:** 20 personas, umbral de 5 pagos en 7 días ([experimento-concierge.md](experimento-concierge.md)).
- **Disparadores de precio:** si 80 % o más paga sin objeciones, subir el precio para los grupos nuevos; si menos de 25 % paga, revisar valor o segmento antes de bajar el precio.
