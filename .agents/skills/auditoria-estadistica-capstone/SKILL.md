---
name: auditoria-estadistica-capstone
description: Audita y fundamenta matemáticamente un capstone de estadística o ML, contrastando datos, ecuaciones, código y resultados reproducibles. Usar para revisión metodológica, comparación de modelos e informes técnicos; no para cambios ordinarios de interfaz.
---

# Auditoría estadística del capstone

Producir una explicación defendible de lo que el experimento realmente estima. Verificar la implementación antes de redactar conclusiones; no certificar modelos como perfectos ni confundir pruebas de software con validez inferencial.

## Aplicación

1. Leer las instrucciones del proyecto y localizar sus fuentes, pipelines y evidencias ejecutadas. Inventariar protocolos distintos por dataset, objetivo, transformación, variables, partición y criterio de selección. Elegir con justificación la comparación principal; mantener resultados históricos identificados, sin combinar métricas de protocolos incompatibles.
2. Definir población objetivo, unidad de observación, unidad de partición, respuesta con unidades e información disponible en el momento de predicción. Revisar duplicados, muestreo, tiempo, denominadores compartidos, composición de fuentes y dependencia espacial. Diferenciar descripción, predicción y causalidad.
3. Verificar que imputación, codificación, escalado y selección se aprendan dentro de entrenamiento. Separar ajuste de hiperparámetros de evaluación externa y documentar el sesgo de seleccionar familia con esos resultados. Usar baselines calculados solo con entrenamiento y comparaciones emparejadas sobre las mismas observaciones.
4. Conectar cada modelo real con su formulación, pérdida, regularización y parámetros efectivos. Si se transforma el objetivo, derivar la transformación inversa y qué funcional estima; no asumir que exponenciar una predicción logarítmica produce la media de precios. Comprobar convergencia cuando corresponda y registrar advertencias en la evidencia.
5. Para ANOVA u otros contrastes, definir hipótesis, unidad experimental, supuestos, estadístico, grados de libertad, incertidumbre y alcance. Controlar multiplicidad en comparaciones por pares; no tratar folds dependientes como réplicas independientes ni aplicar ANOVA ordinario a errores emparejados de modelos.
6. Corregir defectos comprobados dentro del alcance autorizado. Reejecutar solamente los experimentos afectados y conservar procedencia, configuración, predicciones externas y resultados agregados. Mantener datos individuales y credenciales en los lugares permitidos por el proyecto.
7. Redactar el informe siguiendo pregunta → formulación → implementación → resultado → interpretación → limitación. Definir cada símbolo y unidad, explicar las ecuaciones en prosa y citar fuentes académicas primarias o documentación oficial realmente consultadas. Separar resultados medidos, supuestos y validaciones futuras.

Consultar [criterios matemáticos](references/criterios-matematicos.md) al formular o revisar modelos, inferencia y métricas. Adaptar profundidad al trabajo; no añadir pruebas estadísticas sin una pregunta definida.

## Evidencia de cierre

Entregar la matriz de experimentos, hallazgos con severidad y acción, memoria matemática, resultados reproducibles y comando de reproducción. Indicar qué quedó corregido, qué cambia los resultados y qué requiere datos futuros o validación del cliente. Ejecutar las pruebas exigidas por el proyecto. Si no hay un fallo nuevo, evitar repetir entrenamientos ya verificados.
