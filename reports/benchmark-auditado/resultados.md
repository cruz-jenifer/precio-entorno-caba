# Benchmark auditado de cinco modelos

Resultados externos por aviso; pérdidas en USD/m² de publicación. Dos escenarios y tres referencias.

| model | scope | mae | rmse | r2 | mdape_pct | mae_fold_sd |
| --- | --- | --- | --- | --- | --- | --- |
| HGB fijo EDA | base | 448.258 | 680.016 | 0.677 | 12.862 | 13.738 |
| HistGradientBoosting | base | 451.041 | 674.992 | 0.681 | 13.291 | 10.719 |
| Random Forest | base | 460.504 | 699.165 | 0.658 | 13.479 | 13.023 |
| MLP | base | 505.355 | 741.042 | 0.616 | 15.296 | 11.648 |
| KNN | base | 515.139 | 784.307 | 0.570 | 15.163 | 12.005 |
| Ridge | base | 588.304 | 937.087 | 0.386 | 17.675 | 32.300 |
| HistGradientBoosting | edificio | 402.631 | 614.038 | 0.736 | 11.810 | 13.544 |
| Random Forest | edificio | 418.319 | 648.406 | 0.706 | 12.047 | 17.721 |
| MLP | edificio | 443.874 | 659.067 | 0.696 | 13.119 | 13.284 |
| KNN | edificio | 467.726 | 743.367 | 0.614 | 13.140 | 16.065 |
| Ridge | edificio | 524.545 | 827.884 | 0.521 | 15.521 | 23.900 |
| Mediana comparables | referencia | 585.584 | 921.099 | 0.407 | 17.129 | 20.830 |
| Mediana global | referencia | 811.797 | 1208.835 | -0.022 | 24.156 | 23.870 |

El desvío entre folds no es un intervalo de confianza. Los intervalos emparejados condicionales a errores OOF están en resumen.csv. Los ajustes y advertencias se conservan en ajustes.csv.

No mezclar estas métricas con la evaluación 80/20 del prototipo operativo: usan otra especificación.
