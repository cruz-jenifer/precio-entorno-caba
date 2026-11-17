# Catálogo de cocheras mensuales

## Localizar estacionamientos

La capa **Estacionamiento** del mapa muestra todos los garajes del inventario en la ciudad, no solo los del barrio elegido, con puntos más chicos cuando el mapa está alejado. La leyenda indica el total.

En modo real, la ficha de cada barrio incluye «Localizar estacionamientos». Permite consultar todo el barrio oficial, un radio alrededor de un aviso con ubicación o el centro actual del mapa. Los radios disponibles son 300, 500 y 1000 metros; la búsqueda cercana incluye barrios vecinos y ordena por distancia en línea recta. «Ver en mapa» centra y abre el punto; «Cómo llegar» abre Google Maps con ese destino.

La API `/api/estacionamientos?barrio=Caballito` consulta el barrio. Con `lat`, `lon` y `radio` consulta cercanía. Distingue una capa sin cargar de una búsqueda sin coincidencias. Fuente: inventario oficial de garajes comerciales de Buenos Aires Data, publicado el 10 de mayo de 2021. El portal no informa la fecha del relevamiento; los campos del archivo llevan el sufijo `_16`, que sugiere un relevamiento de 2016 sin confirmar. No informa funcionamiento actual, cupos, horarios ni tarifas; estos datos requieren confirmación con el establecimiento.

«Mi ubicación actual» solicita la ubicación al navegador solo al enviar la búsqueda, tanto en estacionamientos como en cocheras. Requiere permiso y un contexto seguro (HTTPS o localhost). Marca el punto en el mapa, informa la precisión estimada del dispositivo y advierte cuando supera el radio elegido. Ante permiso denegado, tiempo agotado o ubicación fuera de CABA, permite continuar con el centro del mapa. El botón de ubicación del mapa lo centra en la posición del navegador sin consultar al servidor; después se puede buscar desde «El centro del mapa». Las coordenadas se envían a la API solo para resolver la consulta; no se agregan al catálogo ni a las preferencias guardadas.

La recopilación de candidatos de Century 21 y Migliorisi se ejecuta con `python scripts/recolectar_cocheras.py`. Reutiliza el cliente autorizado, consulta robots.txt y aplica las pausas existentes. Recorre hasta 30 páginas por fuente y guarda candidatos y registro en una carpeta fechada de `data/raw`. El registro indica el alcance recorrido y los errores. La incorporación al catálogo mensual requiere verificar la periodicidad.

Importar una exportación JSON de una fuente autorizada con `python -m precio_entorno.cocheras archivo.json`.
Cada ejecución reemplaza el corte completo después de validarlo. Los archivos reales se guardan en `data/local`, excluido de Git.

Cada fila requiere `id`, `fuente`, `barrio`, `precio`, `moneda`, `periodicidad`, `url` y `capturado`.
La periodicidad debe ser `mensual`, la moneda ARS o USD y la captura una fecha ISO.
Los campos opcionales son `direccion`, `lat` y `lon`. Las coordenadas deben estar juntas y dentro de CABA.
El importador conserva únicamente esos campos y deduplica por fuente e ID. Dos filas contradictorias provocan un error antes de reemplazar el catálogo.

La API permite consultar `/api/cocheras?barrio=Caballito&moneda=ARS&presupuesto=250000`.
Devuelve los avisos ordenados por precio mensual publicado y el indicador `disponible`, que informa si se cargó el catálogo.

La ficha del barrio en modo real permite filtrar por moneda y presupuesto y buscar en todo el barrio o en un radio de 300, 500 o 1.000 metros desde la ubicación actual, el centro del mapa o un aviso con ubicación. La consulta por radio incluye cocheras de barrios vecinos y muestra distancias aproximadas en línea recta. Las ubicaciones publicadas condicionan esa aproximación.

El catálogo admite `expensas` y `moneda_expensas` (ARS o USD). Un cero explícito se conserva y un importe desconocido se muestra como «Expensas no informadas».

Al seleccionar una vivienda en alquiler, cada resultado muestra la suma mensual de ambos alquileres y sus expensas conocidas, agrupada por moneda. Si faltan expensas, se etiqueta como subtotal conocido y se indican los conceptos pendientes. La comparación utiliza los importes publicados del corte consultado.

## Comprobación de periodicidad

Ejecutar `python -m precio_entorno.verificar_cocheras data/raw/cocheras-FECHA/candidatos.json`.
El verificador consulta las fichas de Century 21 y exige que el importe y la moneda coincidan con una expresión mensual explícita del contenido visible. Descarta scripts y estilos. Los importes contradictorios o sin periodicidad explícita quedan pendientes. Se detiene ante errores de consulta; el registro permite comparar candidatos y revisados.

Produce `mensuales-verificados.json` y `revision-mensual.json` junto a los candidatos. No reemplaza el catálogo activo: antes de importar este corte deben revisarse la cobertura y las expensas, que esta comprobación no extrae. Tampoco confirma disponibilidad por contacto con el anunciante. No guarda las descripciones ni datos de contacto.

Al 17 de noviembre de 2026, la consulta produjo cuatro candidatos activos de Century 21 y permitió verificar un alquiler mensual en Almagro. El corte local conserva sus expensas verificadas por separado. Caballito sigue sin avisos mensuales verificados en este corte; esto no implica ausencia de oferta. El recorrido de Migliorisi no aportó candidatos y RE/MAX respondió 403. Los garajes del mapa provienen de un inventario oficial sin fecha de relevamiento informada y no acreditan cupos ni alquileres vigentes.
