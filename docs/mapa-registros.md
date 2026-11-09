# Mapa de registros alrededor del inmueble

La unidad principal del análisis es el entorno del pin publicado de cada inmueble. Los totales por barrio quedan como una descripción histórica en el EDA; no se usan para clasificar barrios por seguridad ni para ordenar avisos.

## Recorrido en la interfaz

1. En **Datos reales**, elegir un barrio y un aviso con **Ver registros cerca**. La acción activa la capa de delitos y centra el mapa en el aviso.
2. Elegir **250, 500 o 1.000 m**, **robos o hurtos**, y **día, noche o sin horario**. El mapa dibuja los tres círculos y destaca el radio seleccionado.
3. Alternar un año o **Persistencia entre años**. La ficha compara los conteos anuales del radio y los filtros elegidos. La tabla desplegable mantiene los conteos completos de los tres radios, por año, tipo y horario, con ese alcance explícito.
4. **Vista general** vuelve a las celdas cercanas al barrio. No representa un total administrativo del barrio: incluye el entorno de sus límites.

Streamlit usa el mismo motor y ofrece los mismos radios, categorías, franjas y persistencia. El contexto mensual importado sigue disponible en un desplegable aparte para auditar el archivo cargado.

## Fuentes y trazabilidad

Se leen los CSV anuales oficiales locales `data/raw/delitos_20[0-9][0-9].csv`. Actualmente están disponibles los archivos de 2024 y 2025. No se descargan datos ni se ejecutan actores de Apify. Cada archivo aparece con nombre, enlace al catálogo y SHA-256. La caché se renueva si cambia el conjunto de archivos, su tamaño o su fecha de modificación.

Si no existen CSV anuales, se usa exclusivamente el archivo de contexto importado, verificando que su SHA-256 coincida con el guardado en la base. No se mezclan fixtures con los registros reales. La demo no cruza sus avisos ficticios con las fuentes reales.

La [ficha oficial del recurso de 2025](https://data.buenosaires.gob.ar/ar/dataset/6976d312-54e9-4398-b721-1504aedcce89/resource/66c0f0f6-e682-403d-abbe-47227d1966fe), consultada el 9 de noviembre de 2026, advierte una revisión del **informe ejecutivo** por errores detectados. La advertencia no identifica cada error ni establece que todos los registros del CSV sean inválidos. Se muestra junto al análisis y las comparaciones se presentan como descriptivas y sujetas a revisión.

## Conteos y calidad

- Cada ID se cuenta una vez **por año**, incluso si aparece en más de un archivo. Se suman los valores enteros no negativos de `cantidad`.
- Se requiere fecha válida, ID, barrio oficial, tipo y cantidad. Se conservan los hechos con hora desconocida. Para ubicar robos y hurtos se requieren coordenadas válidas dentro del rectángulo de CABA utilizado por el proyecto. Este control es aproximado y no certifica la precisión de la ubicación.
- Se separan `Robo` y `Hurto`; se excluyen siniestros viales y los demás tipos. Se incluyen los subtipos automotor. **Robo** incluye fuerza o violencia según la categoría de la fuente: no es posible aislar todos los robos violentos contra personas con esa categoría sola. No se usa `uso_arma` como sustituto de violencia.
- **Día:** 06:00 a 19:59. **Noche:** 20:00 a 05:59. Las horas faltantes, fraccionarias o fuera de 0–23 van a **Sin horario**. Las franjas duran 14 y 10 horas; los conteos no son tasas por hora ni por peatón.
- Se informa cuántos robos y hurtos se excluyen por coordenadas y cuántos hechos geolocalizados no tienen horario. Son indicadores del conjunto de archivos, no del radio elegido.

## Radios y celdas

Solo se habilita el cruce de un aviso si tiene coordenadas y precisión informada de **hasta 100 m**, como exige `usable_pin`. Una ubicación sin precisión informada no se reemplaza por el centro del barrio. Tener una precisión declarada no garantiza que el pin sea exacto.

Los conteos de los radios usan distancia geodésica sobre una esfera de radio medio terrestre, desde el pin del aviso a cada registro. Son radios acumulativos: 250 m está contenido en 500 m y este en 1.000 m; **no se suman**. Se incluyen hechos de barrios vecinos. En el borde de CABA solo se dispone de la porción cubierta por los registros de la Ciudad. No se calculan recorridos caminables.

La superficie coloreada utiliza una **grilla fija aproximada de 200 m**, con el mismo origen en todos los años. El mapa incluye las celdas que pueden tocar el círculo; una celda contiene todos sus registros, incluso los que quedan fuera del radio. Por eso su suma puede diferir del conteo exacto del radio. La ficha y el tooltip explican esta diferencia. La grilla evita publicar puntos individuales como si fueran direcciones exactas.

La escala anual es fija: **1–4, 5–9, 10–19, 20–49 y 50 o más hechos por celda**, con el período y filtros visibles. Cambiar de año no recalcula quintiles locales para el color. Una celda sin color puede no tener registros, carecer de geolocalización o no cumplir los filtros; no significa ausencia de delitos.

## Persistencia exploratoria

Para cada año, categoría y franja se cuentan hechos en todas las celdas con registros de CABA. El umbral alto es el mayor entre **5 hechos** y el **percentil 80 por rango más cercano** de los conteos positivos de ese año. Una celda es persistente si alcanza ese umbral en **al menos dos años con los 12 meses observados** en el conjunto de registros válidos de la ciudad. El benchmark no se recalcula al elegir otro inmueble o barrio.

Se usa el año de la fecha del hecho; no el de captura del aviso. Los años parciales se muestran como parciales, sin anualizar y excluidos de la regla de persistencia. Observar registros en los 12 meses **no certifica integridad** del archivo. Tampoco un cero observado prueba que no hubo delitos.

El mínimo de cinco hechos evita que una celda con un único evento sea marcada como concentración alta. El criterio es exploratorio, depende del tamaño de celda, del umbral y de la precisión espacial. No es un test de significancia ni un detector de tendencias causales. Con solo 2024 y 2025, la persistencia describe repetición en esos dos años; se fortalecerá la lectura al incorporar nuevas ediciones oficiales comparables.

## Interpretación

**La cantidad de delitos registrados no equivale a la probabilidad individual de victimización.** Los lugares con más peatones, comercios, estaciones y actividad pueden concentrar más eventos. Sin una medida de circulación y tiempo de exposición no hay denominador para estimar ese riesgo. Dividir por población residente o por superficie tampoco resuelve por sí solo las diferencias de circulación.

Existe subregistro y diferencias de denuncia y registro entre lugares y años. Los pines compartidos o de referencia introducen incertidumbre espacial, especialmente en 250 m. Una caída entre archivos puede reflejar cambios de registro o procesamiento; no se atribuye automáticamente a una mejora real. Se mantiene el desfase entre los años publicados y la fecha del aviso. No se produce un puntaje de seguridad ni una predicción de victimización.

## Verificación

```powershell
python -m unittest discover -s tests -v
node --check web/app.js
node --test tests/test_web_delitos.cjs
```

`tests/test_concentracion.py` verifica radios, límites horarios, cantidades, deduplicación, geometría, años parciales, filtros y persistencia. `tests/test_api.py` verifica la separación de la demo, la precisión del pin, las fuentes, el refresco de caché y las validaciones del endpoint `GET /api/delitos/concentracion`. La prueba de JavaScript verifica filtros, escala anual, descarte de picos aislados y respuestas asíncronas atrasadas sin navegador ni red.
