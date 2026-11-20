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

**Qué se puede «contratar» para el mismo trabajo:**

- Portales (Zonaprop, Argenprop, Mercado Libre) y agregadores como Roomix **[Doc, fase 1, §3.4]**.
- Preguntar a conocidos o recorrer el barrio un fin de semana.
- No hacer nada: renovar el contrato o postergar la mudanza. Probablemente es la competencia más grande.

**Gran contratación y pequeña contratación:**

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

1. **Entrevistas de cronología (la brecha más grande).** Hablar con 10 o más personas que se mudaron en los últimos seis meses. Preguntar solo por hechos pasados: cuándo pensaron en mudarse por primera vez, qué buscaron y dónde, qué alternativas descartaron, qué las decidió y qué temían. Nada de «¿usarías…?».
2. **Confirmar o descartar las dimensiones emocional y social** de la sección 3 con esas entrevistas, usando las palabras exactas de las personas.
3. **Medir la pequeña contratación:** aperturas de alertas y clics a avisos, aparte de las altas y los pagos.
4. **Revisar las funciones que no se conectan con el trabajo.** La mayoría sí se conecta. Algunas no tanto, como la capa «Rampas» (registro de obras 2011–2016, no inventario), las capas de Recreación o el radar editorial. Para cada una, nombrar el subtrabajo que sirve o considerar quitarla.
5. **Elegir un trabajo para el capstone.** Si es el de quien busca vivienda, actualizar [alcance.md](alcance.md) y adaptar el [protocolo de validación](validacion-inmobiliaria.md), que hoy está pensado para una inmobiliaria.
