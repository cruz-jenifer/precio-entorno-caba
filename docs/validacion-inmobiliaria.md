# Validación con una inmobiliaria · Protocolo

Este protocolo cubre el eje "Valor para el usuario" y el entregable de validación de la consigna. Mide si la app ayuda a quien gestiona búsquedas de compradores a encontrar opciones compatibles más rápido y si sus alertas resultan útiles, antes de proyectar costos o retorno.

## 1. Preguntas

1. ¿Cuánto tarda una persona del equipo en encontrar opciones compatibles con la app, comparado con su método habitual?
2. ¿Qué proporción de las alertas resulta útil?
3. ¿Cuánto cuesta mantener el seguimiento, en tiempo y dinero?
4. ¿La inmobiliaria pagaría por la herramienta, y en qué condiciones?

## 2. Participantes y duración

- **Participantes:** una inmobiliaria con búsquedas activas de compradores en CABA, y una o dos personas que gestionen esas búsquedas.
- **Búsquedas:** entre 5 y 10 búsquedas reales de departamentos en venta, cargadas sin datos personales del comprador (solo presupuesto, ambientes, superficie y barrios de interés).
- **Duración:** dos semanas, con una captura del catálogo al inicio y luego cada dos o tres días.

## 3. Preparación

1. Confirmar por escrito el permiso de la inmobiliaria y el uso de los datos: solo agregados y sin datos de clientes.
2. Correr la captura (`python -m precio_entorno.inmobiliarias --autorizacion-confirmada`) e importar `avisos.json` en **Datos reales**.
3. Cargar en la app cada búsqueda del participante y anotar su ID en la planilla.
4. Copiar la planilla [registro-validacion.csv](plantillas/registro-validacion.csv) para registrar las tareas y las alertas.

## 4. Tareas

**Tarea A · Encontrar opciones.** Para cada búsqueda, la persona encuentra los avisos compatibles de dos maneras, en orden alternado entre búsquedas para no favorecer a ninguna:
- **Método habitual:** portales, CRM o planillas propias.
- **App:** comparación de barrios y lista de coincidencias.

Se registra el tiempo hasta tener la lista, la cantidad de opciones encontradas y cuántas considera relevantes.

**Tarea B · Revisar alertas.** Después de cada captura nueva se importan los avisos y se revisan las alertas. Para cada una, la persona marca:
- `util`: la enviaría al comprador;
- `no_util`: coincide con los filtros pero no sirve, e indica el motivo;
- `ya_conocida`: ya la tenía por otra vía.

**Tarea C · Costo operativo.** Se registra:
- el tiempo de cada captura y de cada importación;
- el tiempo dedicado a revisar las alertas;
- cualquier incidente: un sitio caído, un bloqueo o un dato erróneo.

## 5. Métricas

| Métrica | Cálculo | Fuente |
| --- | --- | --- |
| Tiempo ahorrado por búsqueda | Mediana de (método habitual − app), en minutos | Tarea A |
| Cobertura | Opciones relevantes de la app / opciones relevantes del método habitual | Tarea A |
| Precisión de alertas | Alertas `util` / alertas revisadas | Tarea B |
| Novedad | Alertas `util` no `ya_conocida` / alertas `util` | Tarea B |
| Costo operativo semanal | Minutos de captura, importación y revisión por semana, y USD de servicios (hoy 0) | Tarea C |

Con 5 a 10 búsquedas, los resultados son orientativos. Se reportan con su cantidad de casos y sin extrapolar a todo el mercado.

## 6. Entrevista final (20 minutos)

1. ¿En qué momento de su trabajo usaría la app? ¿Qué reemplazaría?
2. ¿Qué alertas no le sirvieron y por qué? ¿Qué filtro faltó?
3. ¿El contexto de delitos registrados le resultó útil, indiferente o contraproducente con los compradores?
4. ¿Confía en los precios y en los barrios que muestra la app? ¿Qué error vio?
5. Disposición a pagar, por usuario y por mes:
   - ¿A qué precio le parecería tan barata que dudaría de la calidad?
   - ¿A qué precio le parecería una buena compra?
   - ¿A qué precio le parecería cara, pero la pagaría igual?
   - ¿A qué precio no la pagaría?
6. ¿Qué necesitaría para usarla todos los días? Por ejemplo, correo, integración con su CRM o más fuentes.

## 7. Retorno estimado

Solo después de medir, el beneficio mensual puede estimarse así:

> beneficio = búsquedas activas por mes × minutos ahorrados por búsqueda × costo por minuto del personal − costo operativo mensual

Las cifras se reportan como un escenario con sus supuestos, no como una proyección de ingresos.

## 8. Cuidado de los datos

- No se cargan nombres, teléfonos ni correos de compradores ni de propietarios.
- La planilla usa identificadores de búsqueda, no datos personales.
- Los avisos capturados se usan solo para la prueba y el informe, y se eliminan al terminar si la inmobiliaria lo pide.
- En el informe aparecen solo resultados agregados y, si lo prefiere, sin el nombre de la inmobiliaria.
