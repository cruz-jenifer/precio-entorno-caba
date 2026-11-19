"""ANOVA exploratorio de precios publicados por m² entre barrios de CABA."""

import argparse
import hashlib
import json
from itertools import combinations
from pathlib import Path

import numpy as np
import pandas as pd
import scipy
from scipy import stats

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATASET = ROOT / 'data/processed/ampliado/modelo-pines-aproximados-poi-control/dataset_modelo.csv'


def holm(pvalues):
    """Ajuste step-down de Holm para toda la familia de comparaciones."""
    p = np.asarray(pvalues, dtype=float)
    order = np.argsort(p)
    adjusted = np.empty_like(p)
    adjusted[order] = np.minimum(1, np.maximum.accumulate(p[order] * np.arange(len(p), 0, -1)))
    return adjusted


def analyze(df, min_groups=5, alpha=.05):
    required = {'grupo', 'neighborhood', 'precio_m2'}
    if not required.issubset(df) or df.empty:
        raise ValueError('Se requieren grupo, neighborhood y precio_m2 en una entrada no vacía.')
    if min_groups < 2 or not 0 < alpha < 1:
        raise ValueError('min_groups debe ser >= 2 y alpha debe estar entre 0 y 1.')
    data = df.copy()
    data['precio_m2'] = pd.to_numeric(data['precio_m2'], errors='coerce')
    if data[list(required)].isna().any().any() or not (
            np.isfinite(data['precio_m2']) & data['precio_m2'].gt(0)).all():
        raise ValueError('Se requieren grupos y barrios informados y precios finitos positivos.')
    if 'currency' in data and not data['currency'].eq('USD').all():
        raise ValueError('No se pueden mezclar monedas; se requieren precios en USD.')
    if data.groupby('grupo')['neighborhood'].nunique().gt(1).any():
        raise ValueError('Un grupo no puede pertenecer a distintos barrios.')
    # Cada propiedad aproximada pesa una vez, sin elegir según su precio.
    units = data.groupby(['grupo', 'neighborhood'], as_index=False)['precio_m2'].median()
    summary = units.groupby('neighborhood')['precio_m2'].agg(
        n='size', media='mean', mediana='median', desvio='std').reset_index()
    summary['incluido'] = summary['n'] >= min_groups
    included = summary.loc[summary['incluido'], 'neighborhood'].tolist()
    if len(included) < 2:
        raise ValueError('Se necesitan al menos dos barrios con suficientes grupos.')
    blocks = [units.loc[units['neighborhood'].eq(b), 'precio_m2'].to_numpy() for b in included]
    if any(np.var(x, ddof=1) <= 0 for x in blocks):
        raise ValueError('Welch requiere varianza positiva en cada barrio incluido.')
    n = np.array([len(x) for x in blocks])
    means = np.array([x.mean() for x in blocks])
    variances = np.array([x.var(ddof=1) for x in blocks])
    k, total = len(blocks), int(n.sum())
    grand_mean = np.average(means, weights=n)
    between = float(np.sum(n * (means - grand_mean) ** 2))
    within = float(sum(np.sum((x - x.mean()) ** 2) for x in blocks))
    classic = stats.f_oneway(*blocks)
    welch = stats.f_oneway(*blocks, equal_var=False)
    w = n / variances
    term = np.sum((1 - w / w.sum()) ** 2 / (n - 1))
    levene = stats.levene(*blocks, center='median')
    kruskal = stats.kruskal(*blocks)
    residuals = np.concatenate([x - x.mean() for x in blocks])
    normality = stats.normaltest(residuals) if total >= 8 else None
    comparisons = []
    for i, j in combinations(range(k), 2):
        result = stats.ttest_ind(blocks[i], blocks[j], equal_var=False)
        se = np.sqrt(variances[i] / n[i] + variances[j] / n[j])
        df_pair = (variances[i] / n[i] + variances[j] / n[j]) ** 2 / (
            (variances[i] / n[i]) ** 2 / (n[i] - 1) + (variances[j] / n[j]) ** 2 / (n[j] - 1))
        delta = means[i] - means[j]
        margin = stats.t.ppf(1 - alpha / 2, df_pair) * se
        comparisons.append({'barrio_a': included[i], 'barrio_b': included[j],
                            'n_a': int(n[i]), 'n_b': int(n[j]), 'diferencia_medias_usd_m2': delta,
                            'ic_puntual_inferior': delta - margin, 'ic_puntual_superior': delta + margin,
                            't_welch': float(result.statistic), 'p_sin_ajustar': float(result.pvalue)})
    pairs = pd.DataFrame(comparisons)
    pairs['p_holm'] = holm(pairs['p_sin_ajustar'])
    pairs['rechaza_h0_holm'] = pairs['p_holm'] < alpha
    table = pd.DataFrame([
        {'fuente': 'entre_barrios', 'suma_cuadrados': between, 'gl': k - 1, 'cuadrado_medio': between / (k - 1)},
        {'fuente': 'dentro_barrios', 'suma_cuadrados': within, 'gl': total - k, 'cuadrado_medio': within / (total - k)},
        {'fuente': 'total', 'suma_cuadrados': between + within, 'gl': total - 1, 'cuadrado_medio': None},
    ])
    report = {
        'hipotesis_nula': 'Las medias de precio publicado en USD/m² cubierto son iguales en todos los barrios incluidos.',
        'alpha': alpha, 'filas_entrada': len(df), 'grupos_antes_filtro': len(units),
        'unidades_analizadas': total, 'barrios_incluidos': k, 'minimo_grupos_por_barrio': min_groups,
        'barrios_excluidos': summary.loc[~summary['incluido'], 'neighborhood'].tolist(),
        'welch': {'F': float(welch.statistic), 'gl1': k - 1,
                  'gl2': float((k ** 2 - 1) / (3 * term)), 'p': float(welch.pvalue),
                  'rechaza_h0': bool(welch.pvalue < alpha)},
        'clasico': {'F': float(classic.statistic), 'gl1': k - 1, 'gl2': total - k,
                    'p': float(classic.pvalue), 'eta_cuadrado_descriptivo': between / (between + within)},
        'brown_forsythe': {'W': float(levene.statistic), 'p': float(levene.pvalue)},
        'normalidad_residuos': {'K2': float(normality.statistic), 'p': float(normality.pvalue)} if normality else None,
        'kruskal_sensibilidad': {'H': float(kruskal.statistic), 'p': float(kruskal.pvalue)},
        'pares': len(pairs), 'pares_significativos_holm': int(pairs['rechaza_h0_holm'].sum()),
        'scipy': scipy.__version__,
        'notas': ['Análisis exploratorio de una muestra no probabilística de avisos; no implica causalidad.',
                  'Una mediana por grupo aproximado; no garantiza independencia espacial o entre edificios.',
                  'Los intervalos por par son puntuales, no simultáneos; las decisiones usan p de Holm.',
                  'Kruskal contrasta distribuciones/rangos, no igualdad de medias ni necesariamente de medianas.',
                  'Un p guardado como 0 corresponde a subdesbordamiento numérico; no a probabilidad literalmente nula.'],
    }
    return report, summary, table, pairs


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dataset', type=Path, default=DEFAULT_DATASET)
    parser.add_argument('--salida', type=Path, default=ROOT / 'data/processed/anova-barrios')
    parser.add_argument('--min-grupos', type=int, default=5)
    args = parser.parse_args()
    try:
        report, summary, table, pairs = analyze(pd.read_csv(args.dataset), args.min_grupos)
        report['dataset'] = args.dataset.name
        report['dataset_sha256'] = hashlib.sha256(args.dataset.read_bytes()).hexdigest()
        args.salida.mkdir(parents=True, exist_ok=True)
        (args.salida / 'resultados.json').write_text(
            json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False), encoding='utf-8')
        for name, frame in [('barrios', summary), ('anova_clasico', table), ('pares_holm', pairs)]:
            frame.to_csv(args.salida / f'{name}.csv', index=False)
        print(json.dumps(report, ensure_ascii=False, indent=2))
    except (OSError, ValueError) as error:
        parser.exit(1, f'Error: {error}\n')


if __name__ == '__main__':
    main()
