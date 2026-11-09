# Brainstorming y selección del rubro · Capstone

**Equipo:** [completar]. **Rubro elegido:** intermediación inmobiliaria de departamentos en venta en CABA. **Cliente objetivo:** una inmobiliaria que gestiona búsquedas para varios compradores.

## Ideas evaluadas

| Idea | Problema y usuario | Datos tentativos | Métrica de negocio | Decisión |
| --- | --- | --- | --- | --- |
| 1. Comparar barrios y alertar por avisos nuevos | Quien gestiona búsquedas inmobiliarias revisa avisos dispersos y puede enterarse tarde de una opción compatible. | Catálogo autorizado de avisos vigentes y Mapa del Delito de CABA como contexto. | Minutos ahorrados por búsqueda frente al método habitual. | **Elegida.** Tiene un usuario identificable, un recorrido demostrable y una métrica que se puede medir con una inmobiliaria. |
| 2. Detectar bajas de precio de un mismo aviso | Una inmobiliaria quiere saber cuándo un inmueble entra en el presupuesto de sus compradores. | Capturas periódicas autorizadas del catálogo, con ID estable, fecha y precio publicado. | Tiempo entre una baja observada y su revisión. | Postergada. Requiere acumular un historial comparable y distinguir cambios de precio de republicaciones. |
| 3. Monitorear alquileres por moneda y barrio | Quien busca alquilar necesita comparar oferta con presupuestos en pesos o en dólares. | Catálogo autorizado de alquileres, moneda, precio mensual, superficie y expensas publicadas. | Tiempo para reunir opciones compatibles. | Extensión. Tiene valor, pero suma reglas de moneda y expensas a la primera entrega. |
| 4. Medir qué preferencias concentran las búsquedas | Una inmobiliaria quiere saber qué combinaciones de barrios, presupuestos y ambientes conviene atender primero. | Búsquedas guardadas anonimizadas y catálogo autorizado para medir coincidencias. | Proporción de búsquedas activas con al menos una opción compatible. | Postergada. Requiere suficientes búsquedas reales. La actividad registrada representa a los usuarios de la herramienta. |
| 5. Estimar cuánto tarda en venderse un departamento | Una inmobiliaria quiere priorizar el seguimiento de propiedades con mayor probabilidad de concretar una operación. | Historial de operaciones cerradas y fechas de publicación, cedido por una inmobiliaria. | Tiempo hasta la venta. | Descartada para esta entrega. El catálogo de avisos vigentes no permite observar cierres. |

## Alcance de la idea elegida

- **Producto 1 · Analytics.** Limpiar y resumir avisos de venta en USD. Mostrar oferta, precios publicados por m² y coincidencias por barrio. Presentar hechos registrados como contexto, con período y unidad geográfica.
- **Producto 2 · Inference.** Estimar una referencia de precio publicado por m² para un aviso nuevo. Evaluar el error absoluto medio en USD/m² frente a una mediana de comparables y probar si agregar indicadores de delitos mejora la predicción.
- **Recorrido del prototipo.** Cargar preferencias, comparar barrios, guardar una búsqueda y recibir una alerta cuando entra un aviso compatible.
- **Validación.** Comparar los minutos que tarda una inmobiliaria en encontrar opciones relevantes con su método habitual y con el prototipo. Registrar también cuántas alertas considera útiles.

La comparación prioriza ideas con un usuario concreto, fuentes accesibles con autorización, valor medible y alcance viable para las dos entregas. Las cinco propuestas son una reconstrucción para completar la consigna. El equipo puede ajustar el listado según las ideas que haya discutido.
