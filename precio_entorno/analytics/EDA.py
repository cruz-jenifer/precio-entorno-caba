"""EDA: tablas del dashboard a partir del CSV limpio del ETL.

Resumen, barrios, ambientes, fuentes, distribución de USD/m² y correlaciones. Solo los avisos en
USD entran en USD/m². Los delitos registrados se muestran por barrio, como contexto, con su período.
"""

from datetime import datetime, timezone

import numpy as np
import pandas as pd

SMALL_SAMPLE = 10


def rooms_label(n):
    return '5 o más' if n >= 5 else str(int(n))


def eda(clean, etl_report=None):
    """Tablas del dashboard a partir del CSV limpio. Solo los avisos en USD entran en USD/m²."""
    usd = clean[clean['precio_m2_usd'].notna()].copy()
    for flag in ('tiene_pin', 'superficie_total_imputada', 'expensas_informadas'):
        usd[flag] = usd[flag].astype(str).str.lower().eq('true')
    period = usd['periodo_delitos'].dropna().iloc[0] if usd['periodo_delitos'].notna().any() else ''
    median = lambda s: round(float(s.median()), 1) if s.notna().any() else None

    resumen = pd.DataFrame([{
        'fecha_corrida': (etl_report or {}).get('fecha_corrida') or datetime.now(timezone.utc).strftime(
            '%Y-%m-%d %H:%M UTC'),
        'filas_leidas': (etl_report or {}).get('filas_leidas'),
        'filas_descartadas': (etl_report or {}).get('filas_descartadas'),
        'avisos': len(usd),
        'barrios': int(usd['barrio'].nunique()),
        'fuentes': int(usd['fuente'].nunique()),
        'mediana_usd_m2': median(usd['precio_m2_usd']),
        'mediana_precio_usd': median(usd['precio']),
        'mediana_superficie_m2': median(usd['superficie_cubierta_m2']),
        'posibles_duplicados': int(usd['posible_duplicado'].astype(str).str.lower().eq('true').sum()),
        'periodo_delitos': period,
        'nota': 'Precios de publicación, no tasaciones. Delitos registrados por barrio, como contexto.',
    }])

    g = usd.groupby('barrio')
    barrios = pd.DataFrame({
        'comuna': g['comuna'].first(),
        'avisos': g.size(),
        'mediana_usd_m2': g['precio_m2_usd'].median().round(0),
        'p25_usd_m2': g['precio_m2_usd'].quantile(0.25).round(0),
        'p75_usd_m2': g['precio_m2_usd'].quantile(0.75).round(0),
        'mediana_precio_usd': g['precio'].median().round(0),
        'mediana_superficie_m2': g['superficie_cubierta_m2'].median().round(0),
        'pct_con_pin': (g['tiene_pin'].mean() * 100).round(1),
        'latitud': g['latitud'].median().round(5),   # Igual con o sin las imputadas: son la mediana del barrio.
        'longitud': g['longitud'].median().round(5),
        'delitos_registrados': g['delitos_barrio'].first(),
        'robos_hurtos': g['robos_hurtos_barrio'].first(),
        'pct_con_arma': g['pct_con_arma_barrio'].first(),
    }).reset_index()
    # Looker Studio reconoce "lat,lon" como campo geográfico para el mapa de burbujas.
    barrios['ubicacion'] = np.where(barrios['latitud'].notna(),
                                    barrios['latitud'].astype(str) + ',' + barrios['longitud'].astype(str), '')
    barrios['muestra_chica'] = np.where(barrios['avisos'] < SMALL_SAMPLE, 'si', 'no')
    barrios['periodo_delitos'] = period
    barrios['unidad_delitos'] = 'barrio'
    barrios = barrios.sort_values('mediana_usd_m2', ascending=False)

    usd['ambientes_grupo'] = usd['ambientes'].map(rooms_label)
    g = usd.groupby('ambientes_grupo')
    ambientes = pd.DataFrame({
        'avisos': g.size(),
        'mediana_usd_m2': g['precio_m2_usd'].median().round(0),
        'mediana_precio_usd': g['precio'].median().round(0),
        'mediana_superficie_m2': g['superficie_cubierta_m2'].median().round(0),
    }).reset_index().rename(columns={'ambientes_grupo': 'ambientes'})

    g = usd.groupby('fuente')
    fuentes = pd.DataFrame({
        'avisos': g.size(),
        'pct_avisos': (g.size() / len(usd) * 100).round(1),
        'mediana_usd_m2': g['precio_m2_usd'].median().round(0),
        'pct_con_pin': (g['tiene_pin'].mean() * 100).round(1),
        # Cobertura de lo que publicó cada fuente, no de lo imputado.
        'pct_con_expensas': (g['expensas_informadas'].mean() * 100).round(1),
        'pct_con_superficie_total': ((1 - g['superficie_total_imputada'].mean()) * 100).round(1),
    }).reset_index().sort_values('avisos', ascending=False)

    edges = list(range(0, 6000, 500)) + [np.inf]
    bins = pd.cut(usd['precio_m2_usd'], edges, right=False)
    counts = bins.value_counts().sort_index()
    distribucion = pd.DataFrame({
        'rango_usd_m2': [f'{int(i.left):,}+'.replace(',', '.') if np.isinf(i.right)
                         else f'{int(i.left):,}–{int(i.right) - 1:,}'.replace(',', '.') for i in counts.index],
        'desde_usd_m2': [int(i.left) for i in counts.index],
        'avisos': counts.to_numpy(),
    })
    distribucion['pct'] = (distribucion['avisos'] / len(usd) * 100).round(1)
    distribucion = distribucion[distribucion['avisos'] > 0]

    variables = {'superficie_cubierta_m2': 'Superficie cubierta (m²)', 'ambientes': 'Ambientes',
                 'delitos_barrio': 'Delitos registrados en el barrio', 'robos_hurtos_barrio': 'Robos y hurtos en el barrio',
                 'latitud': 'Latitud (norte-sur)', 'longitud': 'Longitud (este-oeste)'}
    corr = []
    for col, label in variables.items():
        # Las coordenadas imputadas caen en el centro del barrio: solo se correlacionan los pines publicados.
        rows = usd[usd['tiene_pin']] if col in ('latitud', 'longitud') else usd
        pair = rows[[col, 'precio_m2_usd']].astype(float)
        defined = len(pair) > 2 and (pair.std() > 0).all()
        # Spearman = Pearson sobre rangos; así el Actor no necesita scipy.
        corr.append({'variable': label, 'columna': col, 'n': len(pair),
                     'pearson': round(float(pair[col].corr(pair['precio_m2_usd'])), 3) if defined else None,
                     'spearman': round(float(pair.rank()[col].corr(pair.rank()['precio_m2_usd'])), 3) if defined else None,
                     'unidad': 'aviso', 'nota': 'Asociación, no causalidad'})
    correlaciones = pd.DataFrame(corr)
    return {'resumen': resumen, 'barrios': barrios, 'ambientes': ambientes, 'fuentes': fuentes,
            'distribucion': distribucion, 'correlaciones': correlaciones}
