# Alcance del capstone

La app ayuda a decidir dónde buscar un departamento en venta y avisa cuando aparece una opción que coincide. La comparación de barrios se basa en el número de avisos que encajan con los filtros. Los hechos delictivos registrados se presentan en un bloque separado, con período y franja. El prototipo no estima un puntaje de seguridad.

## Requisitos de entrega

1. **Datos.** Un catálogo autorizado de avisos vigentes y el Mapa del Delito de CABA. Cada dataset analítico debe quedar entre 700 y 2.000 registros, con unas diez variables interpretables, cobertura geográfica documentada y pocos faltantes.
2. **EDA.** Describir oferta y precios publicados por barrio, y hechos registrados por tipo, zona y horario. Mostrar cobertura, faltantes y ventanas temporales.
3. **Modelo.** Comparar una referencia de precio por m² basada en comparables con modelos equivalentes con y sin indicadores de delitos. Usar el mismo conjunto de prueba y reportar el error absoluto medio en USD/m². Una mejora predictiva no identifica un efecto causal.
4. **Producto.** Guardar filtros, elegir barrio e identificar una coincidencia nueva una sola vez por búsqueda. La demo muestra alertas en la app. El despliegue posterior puede agregar actualizaciones programadas y correo.
5. **Negocio.** Probar con una inmobiliaria que gestione búsquedas de varios compradores. Medir tiempo ahorrado, costo operativo y disposición a pagar antes de proyectar ROI.

## Secuencia de trabajo

1. Aprobar el recorrido con los datos ficticios.
2. Confirmar la fuente inmobiliaria autorizada. Hacer un piloto de 50 avisos en Caballito y Almagro con un tope de USD 5 en una sola cuenta, dentro del presupuesto de USD 25. Las demás cuentas de Apify, con hasta USD 5 cada una, quedan para ampliar la extracción.
3. Medir registros útiles, duplicados y precisión de ubicación. Ampliar solo después de verificar cobertura y costo por aviso usable. Incorporar Villa Crespo y Flores si hace falta.
4. Preparar los datasets finales y el cruce. Evaluar el modelo y documentar sus resultados.
5. Validar el producto con una inmobiliaria y agregar Make cuando haya una fuente actualizable.
