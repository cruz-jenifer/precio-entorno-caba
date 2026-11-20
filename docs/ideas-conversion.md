# Ideas de conversión: puntaje ICE e hipótesis

**Fecha:** 20 de noviembre de 2026. Hecho con la skill `cro-methodology`, a partir de [monetizacion.md](monetizacion.md), [jtbd.md](jtbd.md), [oceano-azul.md](oceano-azul.md), [estrategia.md](estrategia.md) y el [experimento concierge](experimento-concierge.md). No hay investigación con visitantes todavía: los puntajes de confianza son bajos a propósito.

## 1. Puntaje ICE

Impacto, confianza y facilidad, de 1 a 10 cada uno. La confianza se apoya solo en el benchmark, la medición frente a Zonaprop y el razonamiento de los documentos.

| # | Idea | De dónde sale | I | C | F | **ICE** |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | **Pedir la alerta justo al elegir el barrio**, con el motivo de la elección escrito | [JTBD §5.2](jtbd.md#52-la-contratación-que-hay-que-vencer) | 8 | 6 | 8 | **7,3** |
| 2 | **Titular de resultado y niveles en el idioma de quien busca** | [Monetización §6](monetizacion.md) | 7 | 6 | 9 | **7,3** |
| 3 | Tabla de objeciones con cada respuesta en su lugar | Monetización §6 | 8 | 6 | 7 | 7,0 |
| 4 | Pruebas reales junto al precio | Monetización §6 | 7 | 7 | 6 | 6,7 |
| 5 | Mostrar el precio solo después de la vista previa con coincidencias | [Pricing](pricing-busqueda-personal.md) | 7 | 6 | 7 | 6,7 |
| 6 | Garantía de devolución | [Concierge](experimento-concierge.md) | 6 | 5 | 8 | 6,3 |
| 7 | Mostrar primero «Buscar acompañado» como ancla | Monetización §4 | 5 | 5 | 9 | 6,3 |
| 8 | «Nadie paga para aparecer acá», visible | [Océano azul](oceano-azul.md) | 5 | 4 | 10 | 6,3 |
| 9 | Cobertura honesta: fuentes, frecuencia, última actualización | Monetización §6 | 5 | 5 | 8 | 6,0 |
| 10 | Correo con hasta 3 avisos, cada uno con su motivo | Océano azul | 7 | 5 | 6 | 6,0 |
| 11 | Segunda opinión gratis como puerta de entrada | Océano azul | 9 | 4 | 4 | 5,7 |
| 12 | Veredicto para reenviar a la pareja | Océano azul | 5 | 4 | 6 | 5,0 |

- **Desempate de las dos primeras:** la 1 gana por impacto. Además se puede probar ya en la web publicada, porque la alerta existe. La 2 depende de una página de precios que todavía no está.
- **La apuesta grande para después:** la 11 es la única que pasa con holgura el filtro de la skill («¿podría multiplicar por 10?»), porque es una oferta nueva. Hoy tiene poca confianza y cuesta construirla.

## 2. Lo que falta para medir

La web no tiene medición de visitas: no hay analytics en `web/`. Las altas de alertas sí se pueden contar, porque llegan a la planilla por Make. Lo que no existe es el denominador, por ejemplo cuántas fichas de barrio se abren. Hace falta un contador simple y respetuoso de la privacidad: solo conteos, sin identificar a nadie y sin datos personales.

## 3. Hipótesis 1: pedir la alerta al elegir el barrio

**Qué hay hoy:** la ficha del barrio abre en la pestaña «Entorno», y la alerta está en la tercera pestaña, «Crear alerta» (`PESTANAS` en `web/app.js`).

> **Si** al elegir un barrio mostramos el pedido de alerta en la primera pantalla de la ficha, con el motivo escrito («Elegiste Caballito: N avisos encajan, mediana USD X/m², subte A. Te avisamos cuando aparezca uno nuevo»), en lugar de dejarlo en una pestaña aparte,
> **entonces** aumentará el porcentaje de quienes abren la ficha de un barrio y crean una alerta,
> **porque** la alerta de Zonaprop recién sirve cuando la persona ya sabe el barrio, y Lüga es donde lo decide. Si se va sin alerta, vuelve al hábito: la alerta del portal, gratis y ya configurada ([JTBD §5.2](jtbd.md#52-la-contratación-que-hay-que-vencer)). Para lo demás, Lüga no puede competir: tiene 63 avisos contra 947 en el escenario del benchmark.

**Métricas:**

- **Principal:** alertas creadas sobre fichas de barrio abiertas.
- **Secundarias:**
  - el tiempo entre elegir el barrio y crear la alerta;
  - el porcentaje de alertas que dejan mail;
  - el porcentaje de quienes abren el primer correo de alerta dentro de los 7 días.
- **Que no deben empeorar:**
  - las bajas de alertas en los primeros 7 días (si suben, se están creando alertas sin intención);
  - las operaciones diarias de Make, dentro del límite del plan gratis;
  - las fichas de barrio abiertas por visita, para que el pedido no corte la exploración.

## 4. Hipótesis 2: titular de resultado en la oferta

> **Si** reemplazamos la tabla de 11 funciones por un titular de resultado («Seguí buscando donde buscás. Nosotros te decimos qué aviso vale la llamada.») y tres renglones por nivel,
> **entonces** aumentará el porcentaje de quienes ven la oferta y eligen «Buscar»,
> **porque** la medición del 20/11 muestra que el valor no es el inventario (cerca del 70 % de los avisos de otras fuentes también está en Zonaprop) sino la lectura de cada aviso. Una tabla de funciones esconde ese resultado, y el pase de la diapositiva 8 cobraba justo por la lista completa, que los portales regalan.

**Dónde probarla, mientras no hay página de precios:** en el correo con la oferta del concierge y en una prueba de 5 segundos durante el acto 3 del [design sprint](sprint-confianza.md). Con 20 personas no alcanza para una prueba A/B, así que se fija el umbral antes y se compara contra él.

**Métricas:**

- **Principal:** porcentaje de personas elegibles que ven la oferta y pagan «Buscar», la misma métrica del concierge (umbral: 5 de 20).
- **Secundarias:**
  - comprensión en 5 segundos: al menos 4 de 5 personas dicen bien qué hace «Buscar»;
  - el reparto entre niveles (meta: cerca de 70/20/10);
  - si los motivos de elección mencionan la lectura de los avisos.
- **Que no deben empeorar:**
  - las altas de la alerta gratis;
  - los pedidos de devolución y los «no era lo que esperaba», que señalarían una promesa más grande que el producto.

## 5. Reglas para cualquier prueba

- Fijar antes la hipótesis, la métrica principal, el umbral y la duración, y reportar el resultado que salga, aunque no sea el esperado.
- Con poco tráfico, probar cambios grandes, no retoques.
- Cuando haya respuestas de las llamadas y del concierge, volver a puntuar la confianza de cada idea.
