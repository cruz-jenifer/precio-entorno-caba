# Design sprint: el momento de confianza de Lüga

**Fecha del plan:** 20 de noviembre de 2026. Plan armado con la skill `design-sprint`, a partir de [jtbd.md](jtbd.md) y la [guía de entrevistas](guia-entrevistas.md). Todavía no se hizo.

## 1. Qué se prueba y por qué

**Momento objetivo:** llega el primer correo de alerta con un aviso nuevo y la comparación de Lüga frente a avisos parecidos. ¿La persona confía en esa comparación lo suficiente para actuar (consultar o descartar el aviso) sin ir antes a verificar en Zonaprop?

Es el momento más riesgoso por lo que ya se midió:

- **La cantidad de avisos no ayuda.** En el escenario del benchmark, Lüga tiene 63 avisos contra 947 de Zonaprop, y cerca del 70 % de sus avisos de inmobiliarias también está en Zonaprop ([jtbd.md, §5.2](jtbd.md#52-la-contratación-que-hay-que-vencer)).
- **La comparación es la apuesta.** Lo único con lo que Lüga puede ganarle a la alerta gratis de Zonaprop es su comparación de cada aviso con los parecidos. Si la persona no la cree, el posicionamiento se cae.
- **Dos cosas pueden minar la confianza.** Los precios son de publicación, no de cierre. Y si hay menos de 8 avisos parecidos (`comparables.MINIMO`), Lüga no muestra comparación.
- **El correo depende de esto.** Pedir el mail (la gran contratación) solo funciona si la alerta que llega después vale la pena. Probar primero la alerta dice si vale la pena pedir el alta.

## 2. Antes del lunes

- **Roles.** Quien decide (*Decider*) es el dueño del producto, presente toda la semana. Hace falta además alguien que facilite (*Sprint Master*) que no sea esa persona: alguien del equipo del capstone o un compañero. Sin equipo, usar la variante de 4 días.
- **Fechas.** Reclutar desde ya y hacer el sprint **del lunes 14 al viernes 18 de diciembre de 2026**. La semana del 7 tiene feriado el martes 8.
- **Entrevistas primero.** Hacer al menos 5 entrevistas Mom Test antes del lunes. Sirven como aporte de expertos del lunes, y el cierre de la guía («¿Puedo escribirte en dos semanas para mostrarte algo…?») recluta a los participantes del viernes.
- **Participantes.** Reclutar 5 y agendar un sexto por si alguien falta, con el filtro de la guía (mudanza dentro de CABA en los últimos seis meses, o búsqueda en las últimas dos semanas). Ofrecer un agradecimiento concreto, como una tarjeta de regalo.

## 3. Lunes: mapa

**Meta a dos años:** «Quien se muda dentro de CABA busca con Lüga abierto al lado del portal y consulta los avisos que Lüga le marcó, no todos.»

**Preguntas del sprint:**

1. ¿La persona va a creer la comparación («18 % debajo de los parecidos») lo suficiente para consultar o descartar sin ir a verificar a Zonaprop?
2. ¿Va a entender que se compara contra precios de publicación, y eso le va a bajar la confianza o no?
3. Al ver muchos menos avisos que en Zonaprop, ¿lo va a leer como «filtrado para mí» o como «incompleto»?
4. Cuando un aviso dice «no hay suficientes parecidos para comparar», ¿eso suma honestidad o resta valor?
5. ¿Va a dejar su mail para la alerta justo después de elegir un barrio?
6. ¿Va a usar la comparación para justificar la elección ante su pareja o su familia?

**Mapa del recorrido.** Actores: quien busca, su pareja o familia, Zonaprop (el hábito) y el anunciante.

```
1 Decide mudarse → 2 Busca en Zonaprop → 3 Llega a Lüga → 4 Carga presupuesto y lo que le importa →
5 Ve dónde le rinde → 6 Elige un barrio → 7 Crea la alerta (gran contratación) →
[8 Llega el primer correo con un aviso y su comparación → 9 Consulta, descarta o va a verificar a Zonaprop] ← OBJETIVO →
10 Visita y negocia → 11 Firma o abandona
```

**Expertos a consultar:**

- El dueño del producto: qué promete Lüga.
- Quien conozca `comparables.py`: sus límites son 8 parecidos como mínimo, ±25 % de superficie, ±1 ambiente y precios de publicación.
- Un corredor de la inmobiliaria de la validación: cómo reaccionan los compradores ante «está caro».
- Las notas de las entrevistas Mom Test: cómo controlan hoy un precio (pregunta 8) y qué abren primero (pregunta 3).

**Ejemplos de «¿Cómo podríamos…?»:**

- «¿Cómo podríamos mostrar en qué se basa la comparación sin una clase de estadística?»
- «¿Cómo podríamos convertir "pocos avisos" en "los tuyos"?»
- «¿Cómo podríamos hacer que "no hay suficientes parecidos" genere confianza?»
- «¿Cómo podríamos lograr que el correo se pueda reenviar a la pareja tal cual?»

## 4. Martes a jueves

**Martes: bocetos**

- **Demostraciones rápidas:**
  - el correo de alerta de Zonaprop y su orden «Bajaron de precio»;
  - las alertas de Roomix por WhatsApp con USD/m²;
  - el «los precios están altos/normales para esta ruta» de Google Flights, un veredicto con su evidencia;
  - el «precio más bajo en 30 días» de Mercado Libre.
- **Boceto en cuatro pasos:** cada persona trabaja sola y termina con un boceto de solución anónimo, en 3 cuadros.

**Miércoles: decisión**

- Museo, mapa de calor, votación de prueba y después el **supervoto** de quien decide.
- **Borrador del guion gráfico (12 cuadros):**
  1. Un amigo le pasa el link.
  2. La portada.
  3. Carga presupuesto y ambientes.
  4. La lista de barrios donde le rinde.
  5. Elige uno.
  6. El entorno del barrio.
  7. «Crear alerta» con su mail.
  8. **Tres días después: el correo con 3 avisos.** Uno «18 % debajo de los parecidos», uno «en línea» y uno «no hay suficientes parecidos».
  9. Abre un aviso y ve contra qué se lo comparó.
  10. Decide a cuál llamar.
  11. Se lo reenvía a la pareja.
  12. Mantiene la alerta.

**Jueves: prototipo**

- **Qué construir:** un prototipo cliqueable en Figma o Keynote con la portada, la ficha del barrio, «Crear alerta», **el correo dentro de un marco de correo genérico** y una ficha de aviso de Lüga.
- **Datos:** usar avisos reales de la base, con precios de publicación y sin contactos. No copiar la interfaz de Zonaprop. Si la persona quiere verificar en Zonaprop, que lo abra en su propio celular: ese comportamiento es justo lo que se quiere observar.
- **Antes del viernes:** hacer una prueba con alguien de fuera del equipo.

## 5. Viernes: entrevista en cinco actos

Nunca explicar el prototipo. Si algo confunde, eso es el dato.

**Acto 1: bienvenida (5 min)**

> «Gracias por venir. Te voy a mostrar algo en lo que estamos trabajando. No hay respuestas correctas: estamos probando esto, no a vos. Si algo confunde, es culpa nuestra. Te pido que pienses en voz alta: qué mirás, qué intentás hacer, qué se te pasa por la cabeza. ¿Te parece bien que grabemos la pantalla y el audio?»

**Acto 2: contexto (5 min)**

> «Contame cómo fue tu última búsqueda de vivienda. ¿Dónde buscabas?» … «Del último departamento que fuiste a ver, ¿cómo decidiste si el precio era razonable?»

Anotar el barrio y el presupuesto que mencione, y usarlos en las tareas.

**Acto 3: presentar el prototipo (5 min)**

> «Te voy a mostrar algo. Algunas partes funcionan y otras no. No lo diseñé yo, así que podés ser totalmente sincero.» [mostrar la portada] «Sin tocar nada: ¿qué es esto? ¿Qué te parece que podés hacer acá? ¿Para quién es?»

Después, silencio. No definir «parecidos», «precio de publicación» ni «alerta».

**Acto 4: tareas (15 min)**, planteadas como situaciones, no como instrucciones:

1. «Estás buscando un dos ambientes en [su barrio] con hasta [su presupuesto]. Alguien te pasó este link.»
2. «Querés enterarte si aparece algo.»
3. «Pasaron tres días y te llegó este correo. Leelo como leerías un correo así.»
4. «Elegí un aviso para consultar hoy y uno para descartar. Contame por qué.»
5. «Tu pareja te pregunta por qué ese. Escribí el mensaje que le mandarías.»

**Empujones:**

- Se queda en silencio: «¿Qué estás pensando?»
- Pide ayuda: «¿Qué probarías si yo no estuviera?»
- Llega a un callejón sin salida: «En la versión real eso funcionaría. Vamos a la próxima pantalla.»
- Quiere verificar en Zonaprop: «Dale, hacelo como lo harías.» Y observar qué busca.

**Acto 5: cierre (5 min)**, sin «¿lo usarías?»:

> «¿Qué fue lo primero que pensaste al ver el correo?» · «¿En qué momento dudaste?» · «¿Para quién te parece que es esto?» · «Si un amigo te pregunta, ¿de qué le advertirías?» · «¿Qué hiciste hoy distinto de tu última búsqueda?»

**Compromiso real, opcional:** «Si querés, la dejamos configurada con tu búsqueda real.» Que cree la alerta real con su propio mail es un dato real. Hacerlo solo con su consentimiento.

## 6. Notas y cierre

**Grilla de observación.** Una fila por ítem y una columna por participante, con ✓ (funcionó), ✗ (falló) o ~ (mixto):

| Ítem | P1 | P2 | P3 | P4 | P5 |
| --- | --- | --- | --- | --- | --- |
| Primera impresión | | | | | |
| Deja el mail | | | | | |
| Abre el correo | | | | | |
| Entiende la comparación | | | | | |
| Confía en «18 % debajo» sin verificar | | | | | |
| Verifica en Zonaprop | | | | | |
| Reacción a «no hay suficientes parecidos» | | | | | |
| Reacción a ver menos avisos | | | | | |
| Lo reenvía | | | | | |
| Mantiene la alerta | | | | | |

Tres participantes con el mismo patrón son una señal; cinco son una decisión.

**Cierre del sprint.** Ordenar los resultados en qué funcionó, qué falló y qué fue mixto, y decidir:

- **La comparación genera confianza:** construir el correo de alerta con la comparación, o hacer otro sprint sobre los detalles.
- **Problemas importantes:** rediseñar la comparación o cambiar el argumento, y volver a probar.
- **Nadie confía:** volver al posicionamiento de [jtbd.md](jtbd.md). Lüga necesita otro diferencial frente a la alerta de Zonaprop.

## 7. Diagnóstico: 9/10 en el papel

Cumple todos los puntos de la skill salvo el 1, **quien decide y quien facilita**. Depende de que el dueño del producto se comprometa toda la semana y de que otra persona facilite. Sin los dos, la skill limita el sprint a 6.

En el acto 5 se reemplazó la pregunta de la skill «¿Lo usarías?» por preguntas sobre lo que la persona hizo, porque es hipotética y rompe las reglas de la [guía de entrevistas](guia-entrevistas.md).
