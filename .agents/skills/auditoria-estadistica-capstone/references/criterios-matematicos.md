# Criterios para la fundamentación

## Predicción

- Distinguir la pérdida usada para entrenar de la usada para elegir hiperparámetros y reportar desempeño. El cuadrado minimiza la media condicional y el valor absoluto una mediana condicional, bajo existencia e integrabilidad pertinentes; una clase restringida y la regularización aproximan esos funcionales.
- Si z = log(y), exp(E[z|x]) es una media geométrica condicional; no es E[y|x] en general. Bajo error normal homocedástico, la corrección exp(sigma²/2) necesita supuestos estimados solo en entrenamiento. No agregarla automáticamente a un modelo elegido por MAE.
- Precisar codificación y escala de la distancia de KNN, penalización y tratamiento del intercepto de Ridge, bootstrap/hojas/promedio de Random Forest, pérdida e incrementos de boosting, y activaciones/objetivo/optimizador/convergencia del MLP. Evitar presentar una fórmula genérica de descenso por gradiente como descripción exacta de cualquier biblioteca.
- Al describir regularización de una red, verificar si la biblioteca normaliza por toda la muestra, por lote o por suma de pesos. No sustituir el cálculo efectivo de minibatches por una función objetivo global supuesta sin aclararlo.
- Definir errores con un signo consistente, denominador de porcentajes y población de ponderación. MAE por aviso y MAE con igual peso por propiedad aproximada responden a preguntas distintas.
- Reportar tamaño y composición de cada segmento. El desvío entre folds no es un intervalo de confianza. Un bootstrap sobre errores OOF ya obtenidos es condicional a esos modelos y particiones, y no incluye toda la variabilidad de reentrenar y seleccionar.

## Inferencia

- En ANOVA de un factor usar y_ig = mu_g + epsilon_ig; independencia es una hipótesis del diseño, no un resultado de un test de normalidad. Welch admite varianzas distintas, no dependencia arbitraria.
- Distinguir significación, magnitud y causalidad. Eta cuadrado descriptivo mide proporción de sumas de cuadrados en la muestra; no es R² predictivo ni efecto causal de barrio.
- Normalidad agrupada de residuos heterocedásticos puede rechazarse aunque cada barrio fuera normal. Explicar qué diagnostica la prueba; no usarla como selector automático de metodología.
- Los intervalos puntuales de pares no son simultáneos. Aplicar Holm a la familia completa de contrastes predefinida y usar ese valor p para decisiones ajustadas. No interpretar falta de rechazo como equivalencia.
- Diferenciar sensibilidad de rangos, medias, medianas y transformaciones logarítmicas. Informar con fidelidad qué hipótesis corresponde a cada prueba.

## Alcance y criterios de aceptación

Documentar información futura, proxies de fuente, coordenadas repetidas y dependencia por edificio. La validación aleatoria agrupada dentro de una captura no prueba transferencia temporal o espacial. Formular la próxima prueba prospectiva antes de observarla, con criterios técnicos y de negocio separados.
