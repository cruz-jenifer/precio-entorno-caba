# ANOVA de precios publicados por barrio

Análisis exploratorio del 18/11/2026. Pregunta: **¿difiere la media del precio publicado en USD por m² cubierto entre los barrios del catálogo autorizado?** Este contraste complementa el EDA. No compara el desempeño de los cinco modelos ni prueba el aporte predictivo de delitos registrados.

## Diseño y datos

- Variable respuesta: precio publicado por m² cubierto, en USD/m²; sin logaritmo ni conversión de monedas.
- Factor: barrio oficial de CABA, con 48 niveles incluidos.
- H₀: todas las medias barriales son iguales. H₁: al menos una difiere.
- Nivel de significación fijado: α = 0,05.
- Datos: 3.806 avisos del corte histórico del catálogo autorizado de noviembre de 2026. Dataset y SHA-256 están en el reporte de resultados.
- Unidad de análisis: grupo de propiedad aproximada. Se toma una mediana de USD/m² por `grupo` para evitar dar más peso a posibles copias del mismo inmueble. Quedan **3.582 unidades**, distribuidas en 48 barrios.
- Cobertura mínima fijada: cinco grupos por barrio. No se excluyó ningún barrio por ese filtro. Se rechazan precios no positivos o no finitos, monedas diferentes de USD, grupos sin identificar o grupos asignados a distintos barrios.

La pertenencia a `grupo` proviene de la heurística existente del proyecto, que utiliza barrio, ambientes, superficie y precio redondeados para detectar posibles copias entre fuentes. No equivale a una identificación física validada; puede omitir duplicados o agrupar inmuebles distintos. La prueba se aplica a las medianas de grupo, por lo que sus medias barriales no coinciden necesariamente con las medias ponderadas por aviso del dashboard.

## Método y supuestos

Se eligió **ANOVA de Welch como contraste principal**, que permite distintas varianzas y tamaños de muestra. Se informa también el ANOVA clásico como referencia y su descomposición de sumas de cuadrados. Welch requiere independencia de unidades y normalidad aproximada dentro de los grupos, o suficiente robustez de la aproximación para estas muestras; no resuelve dependencia espacial ni colas extremas. [Documentación oficial de SciPy](https://docs.scipy.org/doc/scipy-1.16.0/reference/generated/scipy.stats.f_oneway.html).

Se calcularon Brown–Forsythe (Levene centrado en la mediana) para evaluar homogeneidad de varianzas y un diagnóstico global de normalidad sobre residuos centrados por barrio. Este diagnóstico agrupado puede reflejar también la heterogeneidad de varianzas y no reemplaza una inspección de cada distribución. Como sensibilidad se calculó Kruskal–Wallis; contrasta distribuciones/rangos, no la igualdad de medias ni necesariamente de medianas.

Tras el contraste global se calcularon pruebas t de Welch para los 1.128 pares posibles de barrios. Los valores p se corrigieron con **Holm sobre toda esa familia de comparaciones**, usando α = 0,05. Los intervalos de diferencia de medias guardados en el CSV son intervalos puntuales al 95 %, sin ajuste simultáneo: la decisión por par se basa en el p ajustado, no en esos intervalos.

## Resultados observados

| Prueba / medida | Resultado | Lectura |
| --- | --- | --- |
| **ANOVA de Welch** | F(47; 970,25) = **59,14**; p = **1,57 × 10⁻²⁴⁹** | Se rechaza igualdad global de medias, bajo los supuestos de la prueba |
| ANOVA clásico | F(47; 3.534) = 62,48; p < 0,001 | Conclusión global coincidente, con supuestos de varianza más restrictivos |
| Brown–Forsythe | W = 9,99; p = 5,51 × 10⁻⁶⁶ | Evidencia contra igualdad de varianzas; justifica priorizar Welch |
| Normalidad global de residuos | K² = 1.893,26; p < 0,001 | No se sostiene normalidad agrupada; cautela con la aproximación paramétrica |
| Kruskal–Wallis | H = 1.727,39; p < 0,001 | También encuentra diferencias en distribuciones/rangos |
| η² clásico, descriptivo | **0,454** | El 45,4 % de la variación observada entre unidades se ubica entre barrios en esta descomposición |
| Comparaciones por pares | **696 de 1.128** con p de Holm < 0,05 | No todos los pares muestran diferencias significativas |

η² es una medida descriptiva de esta muestra; no expresa un efecto causal del barrio, un porcentaje de precio causado por la ubicación ni el R² de un modelo validado fuera de muestra. Los valores p guardados como cero en algunas pruebas reflejan subdesbordamiento numérico, no probabilidades literalmente nulas.

**Ejemplo: Almagro frente a Caballito.** Almagro tiene 201 grupos, con media de 2.456,33 USD/m²; Caballito, 178 y media de 2.713,98. La diferencia Almagro − Caballito es −257,64 USD/m². El p sin ajuste es 0,00137, pero el p corregido de Holm es **0,4844**. A α = 0,05 no se rechaza la igualdad de medias de este par tras controlar las 1.128 comparaciones. Esto tampoco demuestra equivalencia entre ambos barrios.

## Interpretación y límites

Hay evidencia exploratoria de que las medias de publicación no son iguales entre todos los barrios del catálogo. Esto respalda presentar referencias y comparables por ubicación, pero **no demuestra por sí mismo que agregar barrio mejore la predicción**: esa afirmación requiere evaluar modelos con y sin esa variable sobre las mismas particiones.

Las diferencias pueden reflejar composición de inmuebles: superficie, edad, estado, amenities, fuente y segmento. Este ANOVA de un factor no controla esos atributos. No permite atribuir las diferencias a delitos, seguridad, servicios u otra característica causal del barrio. Los delitos registrados y el radar editorial no intervienen en el contraste.

La muestra no es probabilística y los grupos aproximados no garantizan independencia entre propiedades de un mismo edificio, desarrollador o microzona. Hay heterogeneidad de varianzas y no normalidad; Welch y la sensibilidad de rangos ayudan a evaluar la estabilidad del hallazgo, pero no eliminan esas limitaciones. Los p nominales son condicionales al diseño y sus supuestos. El resultado describe el corte observado y no acredita generalización temporal ni representatividad de todos los inmuebles de CABA.

## Reproducción y archivos

```powershell
python -m precio_entorno.anova_barrios
python -m unittest discover -s tests -v
```

Requiere SciPy ≥ 1.16, declarado en `requirements.txt`; la ejecución usó 1.16.3. No entrena modelos, captura avisos ni llama a servicios pagos.

El comando genera en `data/processed/anova-barrios/`:

- `resultados.json`: hipótesis, configuración, cobertura, estadísticos, valores p, supuestos y SHA-256 del dataset.
- `barrios.csv`: cantidad de unidades, media, mediana y desvío por barrio.
- `anova_clasico.csv`: sumas de cuadrados, grados de libertad y cuadrados medios.
- `pares_holm.csv`: diferencias de medias, intervalos puntuales y valores p sin ajuste y ajustados.

Se conservaron copias agregadas de la corrida en `reports/anova_barrios_resultados.json`, `reports/anova_barrios_barrios.csv`, `reports/anova_barrios_anova_clasico.csv` y `reports/anova_barrios_pares_holm.csv`. No incluyen contactos, IDs individuales ni texto de avisos. Las pruebas sintéticas verifican el resultado contra SciPy, la descomposición de cuadrados, el ajuste de Holm, el control de duplicados y la validación de entradas.
