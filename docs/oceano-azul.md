# Océano azul: lienzo estratégico y grilla ERRC de Lüga

**Fecha:** 20 de noviembre de 2026. Hecho con la skill `blue-ocean-strategy` (Kim y Mauborgne), a partir del benchmark de la [fase 1](fase-1-mercado-competitividad.md#4-benchmark), de [jtbd.md](jtbd.md) y del [núcleo de estrategia](estrategia.md). Es una hipótesis hasta que el [design sprint](sprint-confianza.md) y el [experimento concierge](experimento-concierge.md) den evidencia.

## 1. Las alternativas del lienzo

Lo que usa hoy quien se muda dentro de CABA, según el [mapa de alternativas](jtbd.md#51-todo-lo-que-se-puede-contratar-para-el-mismo-trabajo):

- **Portales:** Zonaprop con su alerta (Argenprop se comporta casi igual).
- **Roomix:** el más parecido.
- **Método casero:** planilla, pestañas y grupos de barrio.
- **Inmobiliaria contratada.**
- **Lüga hoy.**

## 2. Lienzo estratégico

Escala: 1 = bajo, 5 = alto. Los puntajes salen del benchmark del 9/11 y de las mediciones de [jtbd.md](jtbd.md#52-la-contratación-que-hay-que-vencer). Donde no hubo observación, son estimaciones.

| Factor | Portales | Roomix | Casero | Inmobiliaria | **Lüga hoy** | **Lüga con ERRC** |
| --- | --- | --- | --- | --- | --- | --- |
| Precio para quien busca (5 = caro) | 1 | 1 | 1 | 5 | 1 | 2 |
| Cantidad de avisos | 5 | 5 | 3 | 2 | **1** (63 contra 947) | 1 |
| Velocidad de aviso nuevo | 4 | 4 | 2 | 3 | 2 | 2 |
| Filtros y búsqueda | 5 | 4 | 3 | 3 | 3 | 2 |
| Fotos y detalle del aviso | 5 | 4 | 4 | 4 | 1 | 1 |
| Contacto directo con el anunciante | 5 | 3 | 4 | 5 | 1 | 1 |
| Quitar repetidos entre fuentes | 1 | 3 | 1 | 2 | 3 | 3 |
| Comparar barrios con mi presupuesto | 1 | 2 | 2 | 3 | 5 | 5 |
| Juicio de precio frente a parecidos | 2 | 2 | 2 | 2 | 4 | **5** |
| Entorno y vida diaria | 2 | 2 | 3 | 3 | 5 | 4 |
| Independencia del anunciante | 1 | 2 | 5 | 1 | 5 | **5, y dicha** |
| Segunda opinión sobre un aviso que ya encontré | 1 | 1 | 2 | 2 | 1 | **5 (nuevo)** |
| Veredicto para reenviar a la pareja | 1 | 1 | 2 | 2 | 1 | **4 (nuevo)** |

**Cómo leerlo:**

- **El océano rojo:** portales y Roomix tienen casi la misma curva, alta en cantidad, velocidad, filtros y fotos.
- **Donde Lüga ya se separa:** comparación de barrios, entorno, juicio de precio e independencia.
- **Donde pierde plata:** todavía gasta en jugar el juego de los portales. Extracciones pagas, adaptadores de fuentes nuevas, insistir con fuentes bloqueadas, filtros y capas del mapa que no paran de crecer. Y ahí pierde igual: tiene el 2 % de los avisos de Zonaprop en el escenario del benchmark.

## 3. Grilla ERRC (con pocos recursos)

| **Eliminar** (baja el costo) | **Aumentar** (sube el valor) |
| --- | --- |
| La carrera por el inventario: no más extracciones pagas, ni adaptadores de fuentes nuevas, ni insistir con fuentes bloqueadas. Libera los cerca de USD 2,50 que quedan de Apify y el mantenimiento de adaptadores. | **Juicio de precio:** de una posición a un veredicto explicado, que muestra en qué se basa (cuántos parecidos, qué rango) y que revisa el corredor. |
| La «lista completa» como lo que se paga (diapositiva 8). La lista completa es lo que los portales ya regalan. | **Independencia visible:** «Nadie paga para aparecer acá», y por qué importa. |
| «Enterate primero»: una promesa de velocidad que Lüga no puede cumplir. | **Esfuerzo ahorrado:** hasta 3 avisos por correo, cada uno con su motivo. «De cada 6, 5 no son para vos» pasa a ser el valor, no una disculpa. |
| El radar de prensa semanal dentro del producto: no sirve al trabajo de quien compra, y cuesta una tarea programada y mantenimiento. | |
| El SaaS para inmobiliarias de USD 39 por mes: no está construido y choca con la independencia. | |

| **Reducir** (baja el costo) | **Crear** (valor nuevo) |
| --- | --- |
| **Capas del mapa:** quedarse con las que usa el explorador de necesidades (subte, escuelas, salud, plazas, ruido, costo mensual). Dejar de sumar o mantener el resto (rampas, cines, clubes, gimnasios, garajes). | **Segunda opinión sobre un aviso que la persona ya encontró en un portal:** carga precio, m², ambientes y barrio, o el aviso si ya está en la base. Lüga responde dónde queda frente a los parecidos, si el barrio encaja con su presupuesto y qué información falta (expensas, antigüedad, ubicación aproximada). Se apoya en `comparables.py`, que ya existe. Acompaña a Zonaprop en lugar de pelearle. |
| **Filtros:** solo los esenciales (operación, presupuesto, m², ambientes). Sin carrera por igualar a los portales. | **Veredicto para reenviar:** un enlace con el aviso, su comparación y su barrio, pensado para mandar a la pareja o a los padres. Responde a la dimensión social, a quien tiene que justificar la elección, y lleva Lüga a quienes deciden en conjunto. |
| **Frecuencia de actualización:** cada 2 días alcanza. No pagar por más velocidad. | |

**Cuidado con los datos:** la segunda opinión pide datos que la persona carga a mano. No leer automáticamente el enlace de un portal sin una autorización que lo cubra, y no guardar lo que la persona carga más allá de la respuesta.

## 4. Por qué es innovación en valor y no solo diferenciación

- **Baja el costo:** sin gasto en extracción, mantenimiento de adaptadores, tarea del radar, capas extra ni producto B2B.
- **Sube el valor donde la persona lo siente:** en lo emocional (no pagar de más), en lo social (justificar la elección) y en lo funcional (menos avisos, cada uno con su motivo).
- **El factor nuevo juega con el hábito del portal, no contra él.** Usa dos de los seis caminos de la skill:
  - **Ofertas complementarias:** el momento antes de la visita y de la negociación.
  - **Cadena de compradores:** la pareja y los padres que deciden en conjunto.

**No clientes que podría convertir:**

- **A punto de serlo:** quien ya busca en Zonaprop y duda de un precio. La segunda opinión es para esa persona.
- **Que rechazan:** quien no contrata a una inmobiliaria porque representa al vendedor. La independencia responde a eso.
- **Inexplorados:** quien llega de fuera de CABA o se muda por primera vez y no conoce los barrios. La comparación de barrios es para esa persona.

**Precio estratégico:** el corredor va de gratis (portales) a la comisión de una inmobiliaria. La primera segunda opinión es gratis. El pase de USD 9 incluye opiniones ilimitadas y la alerta. Se prueba dentro del [experimento concierge](experimento-concierge.md), ofreciendo la segunda opinión en esos correos, sin un experimento nuevo.

## 5. Diagnóstico

- **Lüga hoy: 4/10.** La curva se separa, pero no elimina nada y sigue pagando para competir en cantidad.
- **Lüga con ERRC: 8/10 en el papel.** Curva propia, elimina y crea, rompe la relación entre valor y costo, y apunta a los tres niveles de no clientes.
- **La fila que falla: no hay evidencia de un salto de utilidad de 10 veces.** El [design sprint](sprint-confianza.md) (confianza) y el [concierge](experimento-concierge.md) (pago) son los que pueden mostrarlo.

Este movimiento es coherente con el [núcleo de estrategia](estrategia.md): competir en juicio, no en inventario. Le agrega una pieza concreta: la segunda opinión.
