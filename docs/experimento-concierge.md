# Experimento concierge: ¿alguien paga por que sigan su búsqueda?

**Fecha:** 20 de noviembre de 2026. Experimento diseñado con la skill `lean-startup`, a partir de [jtbd.md](jtbd.md) y del [pricing de búsqueda personal](pricing-busqueda-personal.md). Todavía no se hizo.

## 1. La lista de funciones deseadas

No hay una lista escrita en un solo lugar. Esta reúne lo que los documentos planean y todavía no está construido:

1. Pase pago de 30 días (USD 9 o 15), con una vista previa gratis de 3 coincidencias ([pricing](pricing-busqueda-personal.md)).
2. Alertas por WhatsApp.
3. «Mi vida desde acá»: tiempos a pie o en bicicleta a hasta 3 lugares habituales ([plan](plan-mi-vida-desde-aca.md)).
4. Explorador de necesidades, etapas B y C: bicicleta, bibliotecas, condiciones del intérprete de texto ([plan](plan-explorador-necesidades.md)).
5. Intérprete de preferencias con IA, «Describí tu búsqueda» (oculto, pendiente de una API paga; ver [preferencias-ia.md](preferencias-ia.md)).
6. Detección de bajas de precio.
7. Verificación de que los avisos siguen vigentes.
8. Orden de avisos por preferencias, con el motivo de cada uno.
9. Respuesta «Me sirve» desde el correo.
10. Informes de demanda y pedidos derivados para inmobiliarias (línea B2B).
11. Normalización de direcciones con USIG.
12. Comparación lado a lado de dos avisos.
13. Más fuentes (Mob, Clarín, Argenprop, Mercado Libre).

## 2. La suposición más riesgosa

> **Quienes se mudan dentro de CABA van a pagar para que les sigan la búsqueda y les digan qué avisos vale la pena consultar, aunque la alerta de Zonaprop sea gratis.**

Es la más riesgosa porque, si falla, el negocio cae, y no hay ninguna evidencia a favor:

- **Si falla, cae casi toda la lista.** Los ítems 1, 2, 7, 8 y 9 solo tienen sentido si existe un pase pago. Los ítems 3, 4, 5 y 12 suman atracción, pero ninguno responde por qué pagar si el portal es gratis.
- **Es la más incierta.** En la escala de validación de la skill, la evidencia está en el nivel 1: «creemos que la quieren». Buscar en los portales es gratis. Lüga tiene el 2 % de los avisos de Zonaprop en el escenario del benchmark, y su única ventaja es el juicio sobre cada aviso ([jtbd.md, §5.2](jtbd.md#52-la-contratación-que-hay-que-vencer)).
- **Primero el valor.** El [design sprint](sprint-confianza.md) prueba si la gente confía en ese juicio, con 5 personas en una sesión de prueba. Solo un comportamiento real con plata real dice si ese juicio vale un pago.

El ítem 10 (B2B) es la opción de pivote si esta suposición falla.

## 3. El MVP más chico: concierge

**Por qué concierge:**

- **No una prueba de humo:** un botón «pagá USD 9» sin producto detrás solo mide clics. Y el pricing ya decidió que la persona tiene que ver el valor antes de pagar.
- **No un Mago de Oz:** prueba si hace falta automatizar, y ese no es el riesgo.
- **Concierge:** una persona hace el trabajo a mano, sin esconderlo, y cobra plata real. Prueba valor y pago juntos, sin código.

**Cómo funciona:**

- Un formulario con la búsqueda: operación, presupuesto, ambientes, barrios, y lo imprescindible separado de lo deseable.
- Dos veces por semana, una persona del equipo busca **a mano** en todas las fuentes, Zonaprop incluida, como cualquier usuario. Manda un correo con hasta 3 avisos, cada uno con una línea de motivo y la comparación de Lüga frente a los parecidos cuando hay 8 o más. Si no alcanzan, el correo lo dice.
- El primer correo es gratis. El segundo llega con la oferta: «Seguimos tu búsqueda 30 días por USD 9». El enlace de pago lo crea el equipo, por ejemplo con Mercado Pago. Una garantía de devolución si no llega ningún aviso útil baja la ansiedad de pagar.
- **No se construye:** pagos dentro de la app, WhatsApp, automatización ni fuentes nuevas.

## 4. Ficha del experimento (Construir-Medir-Aprender)

| | |
| --- | --- |
| **Hipótesis** | Al menos el 25 % de quienes buscan vivienda en CABA y reciben un correo gratis, elegido a mano, con al menos un aviso que cumple sus requisitos imprescindibles, paga USD 9 por 30 días de seguimiento. |
| **Tipo de suposición** | Valor y monetización juntos |
| **MVP** | Concierge: formulario, correo elegido a mano y enlace de pago |
| **Quiénes** | 20 personas elegibles: se mudaron hace poco o están buscando ahora en CABA, y su primer correo tuvo al menos un aviso que cumplía sus requisitos imprescindibles. Se reclutan con la [guía de entrevistas](guia-entrevistas.md#11-cómo-conseguirlas) y las publicaciones en comunidades. |
| **La métrica accionable** | **% de personas elegibles que pagan**, sobre las que recibieron el correo gratis. No altas, no aperturas. |
| **Umbral de éxito** | **5 o más de 20 pagan (≥ 25 %) dentro de los 7 días de la oferta.** Es el mismo umbral del [pricing](pricing-busqueda-personal.md#prueba-para-decidir). |
| **Criterio de pivote (fijado antes de empezar)** | **5 o más:** seguir y probar USD 15 con un grupo comparable. **3 o 4:** una iteración más sobre el mensaje, el canal o el precio, y después decidir. **0 a 2:** pivotar. Opciones: cambiar de segmento a inmobiliarias, o cambiar quién paga (gratis para quien busca, y la inmobiliaria paga por recibir búsquedas que la persona elige compartir). |
| **Se mira, pero no decide** | Avisos consultados desde el correo (el uso repetido), los motivos de quienes no pagan y las horas de trabajo manual por persona. |
| **Tiempo y costo** | Unas 3 semanas: 1 o 2 para reclutar y 1 para medir. Cero código y cero Apify. El costo es el tiempo de búsqueda manual, que también es un dato para el precio. |

**Orden:** hacerlo antes de construir cualquier ítem de la lista. Puede correr en paralelo con el [design sprint](sprint-confianza.md), que mejora el formato del correo.

**Cuidado con los datos:** el formulario pide mail y búsqueda. Guardar esos datos fuera del repositorio, informar para qué se usan y borrarlos al terminar si la persona lo pide.

## 5. Diagnóstico: 5/10 en el papel

Las cinco filas del diagnóstico de la skill tienen respuesta: suposición más riesgosa, prueba, métrica, versión más chica y criterio de pivote. Cada una suma 1 punto. Sumarían 2 con evidencia de nivel 3 o más, y todavía no hay ninguna. El próximo paso es correrlo: un pago real lleva la primera fila al nivel 4 («pagaron»).
