# Trabajo por hacer (JTBD) de Lüga

**Fecha:** 20 de noviembre de 2026. Análisis hecho con la skill `jobs-to-be-done`, a partir de la portada y el brief de [ui-rediseno.md](ui-rediseno.md) y [ui.md](ui.md), del [pricing de búsqueda personal](pricing-busqueda-personal.md), de los planes del [explorador de necesidades](plan-explorador-necesidades.md) y de [«Mi vida desde acá»](plan-mi-vida-desde-aca.md), y del JTBD anterior en [fase-1-mercado-competitividad.md](fase-1-mercado-competitividad.md#26-trabajo-principal-jtbd).

**Estado de la evidencia.** Todavía no hay entrevistas con personas reales. Salvo que se indique otra fuente, todo lo que sigue es **[Hip]**, una hipótesis que las entrevistas de la sección 6 tienen que confirmar o descartar.

## 1. Dos trabajos distintos

El repositorio describe dos trabajos y dos personas que los hacen:

| | Quien busca vivienda | La asesora inmobiliaria («Carla») |
| --- | --- | --- |
| Dónde aparece | Portada («Elegí el barrio antes que el departamento»), web pública, pase de 30 días, explorador de necesidades, tiempos de viaje | [alcance.md](alcance.md), [protocolo de validación](validacion-inmobiliaria.md), [fase 1, §2.6](fase-1-mercado-competitividad.md#26-trabajo-principal-jtbd) |
| Quién paga | La misma persona (hipótesis de USD 9 a 15 por búsqueda) | La inmobiliaria (hipótesis de USD 39 por mes) |
| Competencia principal | Portales, Roomix, consultar a conocidos, no mudarse | Método habitual, Tokko, alertas de portal |

Son trabajos distintos, con competencia y pagador distintos. El producto actual está hecho para **quien busca vivienda**, así que este documento analiza ese trabajo. El de la asesora queda en la fase 1. Para el capstone conviene elegir uno y alinear el alcance y la validación con esa elección (sección 7).

## 2. Enunciado del trabajo

> **Cuando** tengo que mudarme dentro de CABA, para comprar o alquilar, y conozco bien solo unos pocos barrios,
> **quiero** reducir la ciudad a los lugares donde mi presupuesto rinde y mi vida diaria funciona, y enterarme a tiempo de las opciones que encajan ahí,
> **para** decidir dónde vivir con confianza, sin semanas de avisos que no eran para mí ni el miedo a pagar de más o equivocarme de barrio.

El enunciado no nombra mapas, alertas ni portales. La frase de la portada «de cada 6 avisos publicados, 5 no son para vos» es la frustración de este trabajo dicha con las palabras de quien busca.

**Comprar y alquilar.** El núcleo del trabajo es el mismo, pero las circunstancias cambian el peso de cada parte:

- **Compra:** son ahorros en dólares y una decisión difícil de deshacer. Pesan más evitar el arrepentimiento y no pagar de más.
- **Alquiler:** hay un vencimiento de contrato y los avisos duran poco. Pesan más la velocidad y el miedo a perder una opción.

## 3. Las tres dimensiones

### 3.1 Funcional: qué necesita lograr

| Subtrabajo | Qué ofrece Lüga hoy |
| --- | --- |
| Separar lo imprescindible de lo deseable | Filtros y «Lo que me importa» |
| Ver dónde alcanza el presupuesto | Barrios ordenados por avisos que encajan y mediana de USD/m² publicada |
| Comprobar cómo funcionaría la vida diaria | Subte, escuelas, salud, plazas, ruido, ciclovías. Tiempos de viaje planificados |
| Saber si un precio es razonable | «Frente a parecidos»: el aviso comparado con avisos parecidos del barrio, con precios de publicación |
| Enterarse de opciones nuevas sin revisar cada portal | Búsqueda guardada y una alerta por aviso nuevo |
| Evitar repetidos y avisos que ya no están | Agrupación de posibles duplicados entre fuentes. La vigencia no se verifica todavía |

### 3.2 Emocional: cómo quiere sentirse

- **Con confianza, sin arrepentimiento.** Para la mayoría es la compra más grande o el contrato más largo que firma.
- **Sin sentirse estafada.** Los precios están en dólares y el 27 % de los avisos bajó su precio en los últimos seis meses **[Doc, Index Zonaprop, E9 de la fase 1]**. La duda «¿estoy pagando de más?» acompaña toda la búsqueda.
- **Aliviada, no abrumada.** Buscar cansa. Ver menos opciones y mejor elegidas es parte del valor.
- **Segura.** El modelo muestra que los delitos registrados no mejoran la predicción del precio publicado **[Doc, [modelo.md](modelo.md)]**, pero la seguridad sigue siendo una preocupación fuerte. Por eso el contexto de delitos tiene lugar en el producto aunque no esté en el modelo: responde a una necesidad emocional, no a una variable de precio. Se sigue mostrando como hechos registrados, con período y unidad geográfica.
- **Con control.** Llegar a la inmobiliaria o al dueño con datos propios, sin depender del discurso de otro.

### 3.3 Social: cómo quiere que la vean

- **Su pareja o su familia:** como alguien que tomó una decisión sensata y bien investigada. El brief de la interfaz ya habla de «una persona o una pareja», y la decisión suele ser compartida.
- **Quienes ayudan con el anticipo o la garantía:** poder justificar la elección («este barrio, este precio, por esto»).
- **La inmobiliaria o el dueño:** informada, no ingenua. Poder decir «está arriba de la mediana de los parecidos» cambia la conversación.
- **Ella misma y su entorno:** vivir en un lugar que la represente. Es la hipótesis más débil y hay que tratarla con cuidado.

## 4. Fuerzas del cambio

| Fuerza | Cómo se ve acá |
| --- | --- |
| **Empuje** | Avisos repartidos entre portales, el mismo departamento publicado por varias inmobiliarias, alertas que se acumulan |
| **Atracción** | Elegir el barrio primero, un conteo honesto de lo que encaja, una referencia de precio |
| **Ansiedad** | «¿Los datos están completos y al día?», «¿Quién ve mi búsqueda?» |
| **Hábito** | Las alertas de Zonaprop son gratis y ya están configuradas |

Reducir la ansiedad y el hábito puede rendir más que sumar atracción. La portada ya muestra la fuente de los datos y la hora de comprobación. Falta decir de forma explícita qué pasa con el correo y la búsqueda de la persona.

## 5. Competencia y contratación

### 5.1 Todo lo que se puede «contratar» para el mismo trabajo

| # | Alternativa | Tipo | Por qué se contrata (dimensión) | Qué le falta para este trabajo |
| --- | --- | --- | --- | --- |
| 1 | **Zonaprop, con búsqueda guardada y alerta** | Directa | Más avisos, gratis, ya está donde la persona mira. Según un corredor de Caballito citado en la prensa, más del 80 % de sus clientes llega por ahí **[Doc, E24]** (funcional) | Hay que elegir el barrio antes. Avisa solo sobre su propia oferta. La alerta pide iniciar sesión **[Obs, E5]** |
| 2 | Alerta de Argenprop | Directa | Alerta por correo sin cuenta **[Obs, E13]** | Las mismas faltas, con menos oferta |
| 3 | Mercado Libre Inmuebles | Directa | La cuenta ya existe | Las mismas faltas. No se pudo filtrar por barrio en la prueba **[NV, E14]** |
| 4 | Cabaprop | Directa | Solo publican corredores matriculados, lo que da tranquilidad (emocional) | Menos conocido. No se recorrió en detalle |
| 5 | **Roomix** | Directa, la más parecida | Varias fuentes, USD/m² por aviso y alertas por WhatsApp **[Doc, E16]** | Usa subbarrios no oficiales. El lenguaje natural no aplicó los filtros en la prueba **[Obs, E17]** |
| 6 | Marketplace de Facebook y grupos de WhatsApp o Facebook por barrio | Indirecta | Avisos de dueños, sin comisión (funcional y emocional) | Dispersos y con riesgo de estafa **[Hip]** |
| 7 | Google Maps, Street View o recorrer la zona un fin de semana | Indirecta | Percepción directa de la vida diaria y de la seguridad (emocional) | Lento, de a una zona por vez **[Hip]** |
| 8 | Hilos de Reddit, guías de barrios en la prensa, Index Zonaprop | Indirecta | «¿Qué barrio me recomiendan?» respondido por gente real (social) | Genérico y sin relación con el presupuesto de la persona **[Hip]** |
| 9 | **Una planilla** (Google Sheets compartida con la pareja) | Solución casera | Control y un registro común para una decisión de a dos (social) | Se carga a mano, se desactualiza y no trae avisos nuevos **[Hip]** |
| 10 | Pestañas abiertas, favoritos en cada portal, capturas, mensajes de WhatsApp a sí misma o a la pareja | Solución casera | No requiere preparar nada | Se pierde y acumula repetidos **[Hip]** |
| 11 | **Contratar a una inmobiliaria** para que busque | Contratar a alguien | Delega el trabajo en alguien que conoce la zona (funcional y emocional) | Poco habitual del lado del comprador en CABA, donde la inmobiliaria suele representar al vendedor. Prioriza su cartera **[Hip]** |
| 12 | Un amigo o familiar que conoce la zona o trabaja en el rubro | Contratar a alguien, gratis | Confianza (emocional y social) | La mirada de una persona sobre pocos barrios **[Hip]** |
| 13 | **No hacer nada**: renovar el contrato, seguir en lo de los padres, esperar precios o crédito | Sin consumo | Cero esfuerzo y cero riesgo. Las escrituras con hipoteca cayeron 15,5 % interanual en septiembre **[Doc, E25]** | El trabajo no se hace |
| 14 | **Buscar solo donde ya vive** | Sin consumo parcial | No hay que decidir barrio | Se saltea justo el paso con el que abre la portada de Lüga **[Hip]** |

### 5.2 La contratación que hay que vencer

Para ganar la gran contratación (crear una alerta o pagar el pase), el rival es **la alerta gratis de Zonaprop**, junto con las pestañas o la planilla que la acompañan. No es Roomix ni no hacer nada.

- **No hacer nada compite antes.** Compite con la decisión de mudarse, no con Lüga. Cuando alguien está por crear una alerta, ya decidió mudarse, y lo que usaría en su lugar es la alerta del portal que ya tiene abierto.
- **Zonaprop ya cubre la mayor parte de lo que alertaría Lüga.** Base local al 20/11/2026 **[Obs]**:
  - en venta, 2.272 de 4.257 avisos activos (53 %) son de Zonaprop;
  - en alquiler, 2.869 de 4.183 (69 %);
  - Lüga trae hasta unos 50 avisos de Zonaprop por barrio. En el escenario del benchmark mostró 59 avisos contra 1.024 de Zonaprop **[Obs, E1, E28]**;
  - la actualización es cada 2 días.

  En cantidad de avisos y en velocidad, Lüga pierde contra una alerta gratis que ya está configurada.
- **Roomix es la competencia a vigilar, no la que hay que vencer.** No hay evidencia de que quienes buscan en CABA lo conozcan. Pelea contra el mismo hábito y por las mismas personas dispuestas a cambiar.

**Cómo ganarle:**

1. **Pedir la alerta antes de que la persona vuelva a Zonaprop.** La alerta de Zonaprop sirve recién cuando se sabe el barrio, y Lüga es donde se elige. Ofrecer la alerta justo después de elegir el barrio: «elegiste Caballito por esto; lo seguimos por vos».
2. **Mandar un juicio con cada aviso, no solo el aviso.** Dónde queda frente a los parecidos y cómo encaja con la vida diaria. Responde al miedo a pagar de más, que es emocional. La alerta de Zonaprop solo resuelve lo funcional.
3. **Contar lo que Zonaprop no tiene.** Mob es el caso más claro: 876 avisos de dueños en alquiler, el 21 % de la base. Los sitios de inmobiliarias suman poco: en venta, cerca del 70 % de sus avisos también está en Zonaprop (ver la medición más abajo). Medir Mob antes de anunciarlo.
4. **Presentar Lüga como complemento, no como reemplazo.** Pedir que la persona abandone un hábito es el cambio más difícil. La alerta sigue gratis y sin cuenta. Un pase pago, si llega, va después de que la persona haya visto el valor.

**Posicionamiento:** para quien se muda dentro de CABA sin conocer todos los barrios, Lüga es la compañera de búsqueda que muestra dónde funcionan su presupuesto y su vida diaria y qué avisos nuevos vale la pena consultar. A diferencia de la alerta de un portal, que solo avisa que apareció algo en ese portal, compara cada aviso con sus parecidos y sigue fuentes que el portal no cubre.

**Medición del 20/11/2026: cuántos avisos tiene Lüga que no están en Zonaprop.** Se buscó, para cada aviso activo de otra fuente, un aviso de Zonaprop con la misma clave de posible duplicado que usan `modelo.duplicate_groups` y `comparables.py`: barrio, ambientes, m² cubiertos redondeados y precio redondeado a miles, además de la moneda.

| Fuente | Venta: activos | Venta: con par en Zonaprop | Alquiler: activos | Alquiler: con par en Zonaprop |
| --- | --- | --- | --- | --- |
| RE/MAX | 917 | 192 (20,9 %) | 23 | 5 (21,7 %) |
| Century 21 | 654 | 35 (5,4 %) | 366 | 58 (15,8 %) |
| Migliorisi | 396 | 7 (1,8 %) | 49 | 8 (16,3 %) |
| Mob | — | — | 876 | 69 (7,9 %) |
| Clarín | 18 | 0 | — | — |
| **Total** | **1.985** | **234 (11,8 %)** | **1.314** | **140 (10,7 %)** |

**La medición no alcanza para afirmar exclusividad.** La copia de Zonaprop en Lüga es una muestra con tope: en venta, entre 20 y 50 avisos por barrio (mediana 48); en alquiler, entre 3 y 73 (mediana 68). Para comparar: solo en el escenario del benchmark (2 ambientes en Caballito y Almagro, hasta USD 150.000, desde 40 m²), Zonaprop mostró 1.024 avisos **[Obs, E1]**. Hay dos sesgos en sentidos opuestos:

- **El tope esconde duplicados.** Un aviso cuya copia en Zonaprop no entró en la muestra parece exclusivo sin serlo.
- **La clave puede juntar avisos distintos.** Dos unidades del mismo barrio con iguales ambientes, m² y precio redondeado, como las de un emprendimiento, cuentan como par.

Que RE/MAX tenga par en el 21 % de los casos aun contra una muestra tan chica sugiere que buena parte de su oferta también está en Zonaprop.

**Medición con la oferta completa de Zonaprop (20/11/2026).** Se capturó completo el escenario del benchmark en Zonaprop, sin fichas, por USD 1,49 ([detalle en datos.md](datos.md)). En el escenario estricto hay 947 avisos de Zonaprop (517 en Caballito y 430 en Almagro), cerca de los 1.024 del 9/11. Lüga tiene 63 en ese escenario: 18 de Zonaprop y 45 de otras fuentes (16 de RE/MAX, 15 de Century 21 y 14 de Migliorisi). Cada uno de esos 45 se buscó en la captura completa:

| Criterio de par | Con par en Zonaprop |
| --- | --- |
| Clave exacta (ambientes, m² redondeados, precio a miles) | 35 de 45 (78 %) |
| Prueba nula: la misma clave con el precio corrido ±8 % o los m² ±6 | entre 6 y 14 de 45 (13 % a 31 %) |
| Clave exacta y a 200 m o menos (solo avisos con coordenadas) | 18 de 31 (58 %) |
| ±2 m², ±5 % de precio y a 200 m o menos (solo avisos con coordenadas) | 25 de 31 (81 %) |

La prueba nula mide cuántos pares aparecen por azar en un escenario tan denso: alrededor de uno de cada cuatro. Descontando ese azar, la clave exacta indica que **cerca del 70 % de los avisos de otras fuentes también está en Zonaprop**. Los criterios con ubicación, que casi no dejan lugar al azar, dan entre 58 % y 81 %. Los 14 avisos de Migliorisi no tienen coordenadas y quedan solo con la clave exacta (13 de 14 con par).

**Lectura.** En este escenario de venta, los avisos que Lüga tiene y Zonaprop no son entre 9 y 19, frente a 947 de Zonaprop: entre 1 % y 2 % de oferta adicional. Además, la copia de Zonaprop en Lüga es el 2 % de lo que Zonaprop publica en el escenario (18 de 947), y 3 de esos 18 ya no aparecen en la captura. Para venta y con estas fuentes, **«avisos que Zonaprop no tiene» no es un argumento**: Lüga tiene que ganar con los puntos 1, 2 y 4. Falta medir lo mismo para Mob en alquiler, que es oferta de dueños y puede comportarse distinto.

Las preguntas 3, 5 y 6 de la [guía de entrevistas](guia-entrevistas.md) ponen a prueba que la alerta de Zonaprop sea de verdad el hábito a vencer.

### 5.3 Gran contratación y pequeña contratación

- **Gran contratación:** activar una alerta o pagar el pase.
- **Pequeña contratación:** abrir el correo de la alerta y entrar a un aviso.
- En este mercado, dar de baja suele ser un éxito, porque la persona encontró dónde vivir. El [pricing](pricing-busqueda-personal.md) ya lo señala. La métrica de éxito es «encontró vivienda», no la retención.

## 6. Diagnóstico: 5/10

| Pregunta del diagnóstico | Estado |
| --- | --- |
| ¿El trabajo se puede enunciar sin nombrar el producto? | Sí (sección 2) |
| ¿Están las cuatro fuerzas? | Sí, como hipótesis (sección 4) |
| ¿Se conocen las dimensiones emocional y social? | No: son hipótesis sin entrevistas |
| ¿Se identificó la competencia no evidente? | Sí, incluida no hacer nada (sección 5) |
| ¿Se mide la pequeña contratación aparte de la grande? | No |
| ¿Cada función responde al trabajo? | En parte (ver abajo) |
| ¿Hubo entrevistas sobre la cronología de la búsqueda? | No |

Puntos de profundidad: el enunciado no nombra el producto (+1) y la competencia incluye no hacer nada (+1). Las tres dimensiones todavía no tienen evidencia (0).

## 7. Qué hacer

1. **Entrevistas de cronología (la brecha más grande).** Hablar con 10 o más personas que se mudaron en los últimos seis meses. Preguntar solo por hechos pasados: cuándo pensaron en mudarse por primera vez, qué buscaron y dónde, qué alternativas descartaron, qué las decidió y qué temían. Nada de «¿usarías…?». Las preguntas están en la [guía de entrevistas](guia-entrevistas.md).
2. **Confirmar o descartar las dimensiones emocional y social** de la sección 3 con esas entrevistas, usando las palabras exactas de las personas.
3. **Medir la pequeña contratación:** aperturas de alertas y clics a avisos, aparte de las altas y los pagos.
4. **Revisar las funciones que no se conectan con el trabajo.** La mayoría sí se conecta. Algunas no tanto, como la capa «Rampas» (registro de obras 2011–2016, no inventario), las capas de Recreación o el radar editorial. Para cada una, nombrar el subtrabajo que sirve o considerar quitarla.
5. **Elegir un trabajo para el capstone.** Si es el de quien busca vivienda, actualizar [alcance.md](alcance.md) y adaptar el [protocolo de validación](validacion-inmobiliaria.md), que hoy está pensado para una inmobiliaria.
