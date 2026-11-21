# Colab integral · Lüga

El cuaderno reúne el trabajo en 50 celdas, con teoría intercalada con resultados ejecutables. Usa el corte real autorizado de noviembre de 2026, cinco familias de modelos y referencias separadas. No necesita clonar el repositorio dentro de Colab ni configurar credenciales.

## Leer resultados en GitHub o Colab

El [notebook publicado](../notebooks/capstone_integral_colab.ipynb) conserva las salidas verificadas de las 21 celdas de código, nueve figuras y conclusiones estáticas de los modelos. Se puede abrir en [Google Colab](https://colab.research.google.com/github/montesquieu891/precio-entorno-caba/blob/main/notebooks/capstone_integral_colab.ipynb) y leer sin ejecutar. El Anexo A incluye los resultados históricos de la evaluación temporal del HGB operativo, separado del benchmark principal.

La vista pública omite tablas de avisos individuales, widgets y rutas locales. Conserva las métricas, los gráficos y los diagnósticos agregados. El paquete de datos y las copias privadas listadas abajo permanecen fuera de Git: esos enlaces relativos solo funcionan en el entorno local y sus archivos se comparten por separado con acceso autorizado.

## Archivos locales para reproducirlo

La [entrega completa en un solo ZIP](../data/processed/colab-capstone/Entrega_Colab_Precio_Entorno_CABA.zip), de aproximadamente 6,2 MB, reúne el notebook fuente, la copia entrenada, el paquete autónomo de entrada, las salidas con modelo y un `LEEME.md`. Extraerlo antes de subir los archivos a Colab.

1. **Notebook público con salidas:** [`notebooks/capstone_integral_colab.ipynb`](../notebooks/capstone_integral_colab.ipynb).
2. **Paquete de datos, código y evidencia auditada:** [`capstone_bundle.zip`](../data/processed/colab-capstone/capstone_bundle.zip), de aproximadamente 3,5 MB. Queda fuera de Git.
3. **Copia ejecutada en modo lectura:** [`capstone_integral_lectura.ipynb`](../data/processed/colab-capstone/capstone_integral_lectura.ipynb).
4. **Copia ejecutada con entrenamiento completo:** [`capstone_integral_entrenado.ipynb`](../data/processed/colab-capstone/capstone_integral_entrenado.ipynb).

Abrir [Google Colab](https://colab.research.google.com/), elegir **Archivo → Subir notebook** y seleccionar el `.ipynb`. Configurar un entorno CPU y ejecutar desde el principio. En la sección 1, subir `capstone_bundle.zip` cuando aparezca el selector. Se puede colocar antes en el panel de archivos o en la ruta opcional de Drive que indica el cuaderno.

El notebook con salidas está publicado en GitHub y se abre desde Colab. Los ZIP de insumos y las copias privadas son artefactos locales; no se creó una copia en una cuenta de Google. Los datos autorizados requieren conservar las condiciones de acceso al compartir el paquete.

## Dos recorridos

**Lectura sin ejecución:** abrir el notebook publicado y recorrer tablas, figuras, conclusiones y anexo. No requiere el ZIP.

**Reejecución en modo lectura:** elegir `REENTRENAR=False` antes de ejecutar. La copia pública conserva el valor usado en su ejecución original (`True`). Comprueba los hashes de la evidencia y recupera las predicciones externas auditadas. Recalcula calidad, gráficos, ANOVA, comparaciones e incertidumbre, e interpreta un fold. Después reajusta el modelo final para probar persistencia e inferencia. La celda del benchmark aclara que sus resultados son históricos, no un entrenamiento nuevo.

**Reproducción completa:** `REENTRENAR=True`. Repite el benchmark anidado: 500 ajustes de búsqueda/refit de las cinco familias en dos escenarios, más cinco ajustes del HGB de referencia. La interpretación y el reajuste final son operaciones adicionales. El tiempo depende del equipo; Colab no garantiza recursos ilimitados. No se utiliza GPU ni se llama a APIs pagas.

La copia con entrenamiento conserva `REENTRENAR=True` y todas sus salidas. Para una exposición ágil conviene el notebook fuente o la copia de lectura. En una sesión nueva ambos necesitan el ZIP para volver a ejecutar.

## Qué contiene

| Tramo | Pregunta y evidencia |
| --- | --- |
| Datos | Contrato, precio por m², procedencia, hashes, fuentes, faltantes y grupos de propiedades aproximados |
| EDA | Distribuciones, mapa de medianas barriales, cobertura de atributos y asociaciones lineales/monótonas |
| Contexto | Delitos registrados por barrio y año, separados del objetivo predictivo y del radar editorial |
| ANOVA | Hipótesis, clásico, Welch, diagnósticos, tamaño de efecto y 1.128 pares corregidos con Holm |
| Modelos | Ridge, KNN, Random Forest, HistGradientBoosting y MLP: formulación, pérdidas, hiperparámetros y escala logarítmica |
| Evaluación | Validación anidada por grupos, medianas global/comparables, referencia HGB histórica, MAE/RMSE/R²/MdAPE y bootstrap emparejado |
| Diagnóstico | Residuos, brecha de entrenamiento, errores por barrio/fuente, convergencia y sensibilidad a datos incompletos |
| Interpretación | Permutación y dependencia parcial sobre un fold externo, con límites de correlación y combinaciones físicas |
| Producto | Explorador por barrio, ambientes y presupuesto usando referencias externas OOF |
| Operación | Modelo reajustado con transformación completa, recarga consistente, contrato de lotes y rechazo de moneda incompatible |
| Negocio | Escenario editable de ahorro de tiempo, costos de operación y límites de las estimaciones |
| Cierre | Protocolo de captura futura, exportación privada de tablas/figuras/modelo y referencias |
| Anexo A | Validación temporal retrospectiva del HGB operativo: 1.763 avisos, MAE 528,7 frente a 581,0 USD/m² de comparables |

## Generación y reproducción local

Usar un Python con las dependencias del proyecto y las herramientas de notebooks disponibles (`nbformat`, `nbclient`, `ipykernel`, `ipywidgets`). Si faltan:

```powershell
python -m pip install nbformat nbclient ipykernel ipywidgets
```

Desde la raíz del proyecto:

```powershell
python scripts/preparar_colab_capstone.py
python notebooks/build_capstone_integral.py
python scripts/ejecutar_colab_capstone.py
python scripts/ejecutar_colab_capstone.py --reentrenar
python scripts/empaquetar_entrega_colab.py
python scripts/publicar_colab_resultados.py
python -m unittest discover -s tests -v
```

El generador `build_capstone_integral.py` crea un notebook sin salidas. Después de ejecutarlo, `publicar_colab_resultados.py` usa la copia entrenada completa para actualizar el notebook público, eliminar salidas individuales y añadir conclusiones estáticas. No publica en GitHub por sí mismo: requiere revisar, hacer commit y push del notebook. Este último paso evita reemplazar la entrega pública por celdas vacías.

El notebook fuente se genera con `build_capstone_integral.py`, que integra las explicaciones de `docs/memoria-matematica.md`. La edición mantenible se hace en el generador y la memoria y luego se regenera; no editar solo el JSON del notebook. El preparador verifica que código, bundle y predicciones coincidan con el manifiesto del benchmark antes de armar el paquete.

Cada ejecución local usa un kernel limpio y conserva su `.ipynb` con salidas en `data/processed/colab-capstone/`. El espacio de trabajo autónomo está en `data/processed/colab-capstone/workspace/`, y la salida descargable es `workspace/salidas_capstone.zip`. Las predicciones individuales, datos y modelo permanecen fuera de Git.

## Interpretación y límites

El modelo exportado por este notebook sigue la especificación del benchmark logarítmico; su salida vuelve a USD/m². El artefacto previo de Streamlit usa otra especificación y no se sustituye automáticamente. La sensibilidad a campos básicos del cuaderno usa un fold externo, y no debe confundirse con el ensayo 80/20 del prototipo.

El cuaderno identifica el mejor observado dentro de la captura. No acredita generalización temporal, causalidad del barrio, seguridad de un inmueble ni ahorro real del cliente. El ranking ordena revisión y mantiene la aclaración de precios publicados. El ANOVA no se usa para comparar los cinco modelos.

Las figuras no recortan los errores extremos del diagnóstico OOF. Las barras de medias barriales muestran desvíos descriptivos, no intervalos de confianza. Los intervalos de diferencias de MAE son condicionales a predicciones OOF fijas y no son intervalos individuales de precio.

## Verificación de la entrega

Se ejecutaron los dos modos en kernels locales limpios: **21 de 21 celdas de código**, sin errores y con **nueve figuras incrustadas** en cada copia. La ejecución completa tomó aproximadamente 358 segundos en el equipo disponible; no es una promesa de duración en Colab. MAE, RMSE y R² de todas las filas del benchmark coincidieron con la auditoría guardada, con tolerancia absoluta de 10⁻⁸.

Se comprobó el guardado/recarga del modelo, el rechazo de moneda incompatible, la validez del notebook y la integridad de los insumos. Se inspeccionaron los gráficos principales y se corrigió el espaciado de coordenadas del mapa. La suite del proyecto terminó con **258 pruebas aprobadas**. El acceso automatizado al navegador falló al iniciar, de modo que la validación fue local y no se creó una copia alojada en Google.

El anexo se incorpora desde `reports/validacion_temporal.json` y muestra su hash. Reentrenar el benchmark no vuelve a ejecutar esa evaluación operativa. Parte de sus capturas es anterior al ajuste final: evalúa capturas posteriores al catálogo de entrenamiento, sin acreditar una prueba prospectiva completa.
