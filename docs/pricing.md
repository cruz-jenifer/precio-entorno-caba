# Estrategia de pricing · Precio y Entorno CABA

Hipótesis comercial para el capstone · 9 de noviembre de 2026. Los importes están expresados en USD de referencia para comparar escenarios. La oferta al cliente debería indicar el importe final, moneda, condiciones y vigencia por escrito.

Esta propuesta cubre el seguimiento de búsquedas gestionadas por una inmobiliaria. La [propuesta para quien busca departamento](pricing-busqueda-personal.md) desarrolla el pase personal y la línea de demanda agregada.

## Quién paga y por qué

El comprador inicial es el dueño o gerente de una inmobiliaria de CABA con varias búsquedas simultáneas de compradores. La persona usuaria es quien revisa portales, filtra candidatos y arma listas para enviar. La hipótesis es que una inmobiliaria pagará si puede dedicar menos tiempo a esa revisión y encuentra avisos relevantes que su método habitual pasaba por alto.

Una alerta aislada tiene poco poder de venta. Zonaprop ya ofrece alertas de propiedades nuevas, y el cliente puede combinar esas alertas con su CRM o una planilla. Tokko Broker comercializa un CRM con funciones más amplias. Su tarifa puede orientar una conversación sobre el presupuesto disponible, pero el piloto debe compararse con el flujo que la inmobiliaria realmente usa. [Zonaprop](https://www.zonaprop.com.ar/blog/zonaprop/) · [Planes de Tokko Broker](https://www.tokkobroker.com/es-ar/planes-y-precios)

El valor a demostrar es **seguimiento de búsquedas de compradores en un solo flujo**, con comparación por barrio y un resumen de avisos compatibles de fuentes autorizadas. La frecuencia de las capturas define cuándo puede aparecer una alerta. Si la inmobiliaria descubre los mismos avisos antes en su portal, la utilidad incremental dependerá del ahorro de revisión. El mapa de delitos queda como contexto. La referencia de precio publicado por m² queda para una prueba posterior de utilidad y error.

## Oferta para probar

| Oferta | Alcance propuesto | Precio a probar |
| --- | --- | --- |
| Piloto acompañado | 14 días, una inmobiliaria, hasta 10 búsquedas de compra en CABA, configuración, captura cada dos o tres días según disponibilidad y devolución final | **USD 25**, acreditables al primer mes si continúa |
| Seguimiento | Una inmobiliaria, hasta 20 búsquedas activas simultáneas, comparación por barrio, resumen agrupado y soporte básico de configuración | **USD 39 por mes**, con renovación mensual |
| Mayor volumen | Más de 20 búsquedas o necesidades de integración. Relevar operación, costos y demanda antes de comprometer alcance | Cotización después de validar |

La unidad de cobro es la **inmobiliaria por mes**. Las búsquedas activas marcan la capacidad del plan. Una búsqueda activa es una combinación de filtros habilitada para seguimiento y puede pausarse al cerrar el pedido. El límite es una condición comercial del piloto que se administra durante el acompañamiento. Cobrar por alerta incentivaría volumen aunque las coincidencias aportaran poco. Cobrar por usuario dificultaría que otra persona del mismo equipo ayude a revisar la cartera. Los créditos de Make y el consumo de Apify sirven para medir costos internos.

La oferta inicial se prueba con un único plan mensual. La expansión por volumen se considera cuando haya renovaciones y solicitudes repetidas de mayor capacidad. Las integraciones a medida se presupuestan por separado. Analytics e Inference son entregables del capstone y su monetización requiere su propia evidencia. [Marco pricing-strategy](https://github.com/sickn33/agentic-awesome-skills/blob/main/skills/pricing-strategy/SKILL.md)

## Cuándo cierra el precio

**Para la inmobiliaria.** Medí revisiones efectivas al mes, no solo búsquedas guardadas. Una misma búsqueda activa puede requerir varias revisiones. El beneficio directo es revisiones mensuales × minutos netos ahorrados por revisión × costo laboral por minuto. Los minutos incluyen el tiempo de revisar alertas y descartar coincidencias irrelevantes. El ejemplo usa USD 12/h como supuesto para el costo del tiempo.

| Escenario | Revisiones al mes | Minutos netos ahorrados por revisión | Ahorro mensual | Saldo después de USD 39 |
| --- | ---: | ---: | ---: | ---: |
| Uso bajo | 20 | 8 | USD 32 | −USD 7 |
| Caso de prueba | 40 | 10 | USD 80 | USD 41 |
| Uso intensivo | 75 | 12 | USD 180 | USD 141 |

Con USD 12/h, el precio de USD 39 exige **3 h 15 min de ahorro mensual** para cubrir la cuota. Con 40 revisiones equivale a unos 5 minutos por revisión. En el caso de prueba, el retorno mensual sobre la cuota sería de aproximadamente 105%, antes de otros costos de la inmobiliaria. Una hora liberada solo aporta el valor imputado si el equipo puede aprovecharla. Registrar los avisos útiles y nuevos por separado evita imputar comisiones de ventas hipotéticas.

**Para el proveedor.** Separá infraestructura, captura autorizada, Make, soporte, mantenimiento de conectores y comisiones de cobro. Las extracciones del capstone y el tope de USD 25 corresponden a investigación y presupuesto autorizado. El costo mensual del servicio se mide con la cadencia y el volumen comercial. Make publica sus planes y cobra créditos según las acciones ejecutadas, por lo que el costo por cuenta depende también de cómo se agrupan y entregan las alertas. [Precios de Make](https://www.make.com/en/pricing) · [Consumo de créditos](https://help.make.com/credits)

A USD 39, un objetivo de margen de contribución del 50% deja **USD 19,50 por cuenta al mes** para costos directos. Como presupuesto de prueba, USD 9 de servicios y operación más 40 minutos de soporte a USD 12/h darían USD 17 de costo y 56% de margen. Con 90 minutos de soporte, ese costo sube a USD 27 y el margen cae a 31%. Son supuestos que deben reemplazarse por tiempos y facturas. Medí el alta por separado. Si el cliente usa el crédito, el piloto y el primer mes generan USD 39 en conjunto, con dos períodos de atención. Cualquier trabajo de alta que exceda el presupuesto debe entrar en el costo de adquisición o cobrarse en una futura oferta.

## Cómo ponerlo a prueba

1. Usá el [protocolo de validación](validacion-inmobiliaria.md) con 5 a 10 búsquedas reales. Alterná el orden del flujo habitual y la app. Definí de antemano qué cuenta como revisión y qué hace que una opción sea relevante. Registrá fecha de captura, detección por el método habitual, detección en la app y minutos de revisión.
2. Registrá **utilidad y novedad como dos campos**. Un aviso puede ser útil y ya conocido. La métrica principal de alertas es avisos útiles y desconocidos antes de la alerta / alertas revisadas. Informá también cuántos candidatos relevantes se perdieron frente al método habitual y la proporción de enlaces aún disponibles al revisar.
3. Al terminar, preguntá qué paso abandonaría del método habitual y qué herramienta seguiría pagando. El cuestionario de cuatro precios puede orientar, con la unidad «por inmobiliaria por mes» y el mismo alcance. Con una sola inmobiliaria, las respuestas describen ese caso. La prueba de precio es una propuesta concreta de continuación a USD 39, con aceptación y pago o rechazo registrado.
4. Buscá tres pilotos con inmobiliarias que gestionen compradores en CABA. Conservá alcance y precio durante esa primera ronda. Si la objeción dominante es el importe, probá USD 29 o USD 49 con nuevas cuentas comparables y registrá por qué se cotizó ese precio. A USD 29, el costo directo debería quedar en USD 14,50 o menos para sostener el mismo margen. USD 49 requiere al menos 4 h 5 min de ahorro mensual con el costo horario supuesto. Tres pilotos sirven para decidir el siguiente paso y ampliar la muestra.
5. Usá como criterio preliminar para seguir **dos renovaciones pagas de tres pilotos**, costo directo medido de hasta USD 19,50 por cuenta y ahorro mensual estimado del doble de la cuota en los clientes que renueven. Confirmá además que las alertas útiles y nuevas aparecen con suficiente regularidad para que las vuelvan a consultar. Si falla el valor, revisá fuentes, vigencia y frecuencia. Si falla el margen, reducí el trabajo manual antes de ampliar. Si falla el pago pese al uso, revisá comprador, presupuesto y oferta.

## Riesgos que pueden invalidar la oferta

| Riesgo | Evidencia a buscar |
| --- | --- |
| Los portales ya resuelven la tarea | Avisos útiles realmente nuevos o reducción de tiempo frente a alertas nativas y CRM. |
| La frecuencia o vigencia reduce el valor | Tiempo hasta la detección, enlaces activos al revisar y comparación con el método habitual. |
| La fuente cambia, bloquea o retira el permiso | Autorización y cobertura operativa verificadas antes de cotizar. Medición de corridas parciales y costo de mantener conectores. |
| El servicio requiere demasiado trabajo manual | Minutos de alta, soporte y mantenimiento separados por cuenta y por incidente. |
| El usuario valora el producto, pero el dueño no aprueba la cuota | Confirmar quién tiene presupuesto y registrar su decisión con una oferta concreta. |

**Decisión para el capstone.** Llevar a la defensa USD 39/mes como hipótesis, el ahorro mínimo necesario y el diseño del piloto. Presentar por separado los datos observados, el costo estimado y los supuestos. La renovación paga y el costo medido determinan si el precio puede sostenerse.

