"""Análisis exploratorio de los CSV oficiales del Mapa del Delito de CABA.

Aplica las mismas reglas de validez que el importador de la app: barrio de CABA,
fecha, ID, tipo y cantidad entera. La franja faltante se conserva como «Sin dato».
Un mismo ID se cuenta una vez por año. Los conteos son hechos registrados, no un
puntaje de seguridad.
"""

import argparse
import json
from hashlib import sha256
from pathlib import Path

import pandas as pd

from precio_entorno.importing import BARRIOS, key

ROOT = Path(__file__).resolve().parents[1]
COLUMNS = ('id-mapa', 'fecha', 'franja', 'tipo', 'subtipo', 'uso_arma', 'uso_moto',
           'barrio', 'comuna', 'latitud', 'longitud', 'cantidad')
# Mismo rectángulo aproximado de CABA que usa el importador de avisos.
LAT, LON = (-34.73, -34.52), (-58.54, -58.32)
VIAL = 'Vialidad'
NIGHT = set(range(20, 24)) | set(range(0, 6))
FOCUS = ('Caballito', 'Almagro', 'Villa Crespo', 'Flores')
MONTHS = 'ene feb mar abr may jun jul ago sep oct nov dic'.split()


def blank(series):
    return series.str.strip().str.casefold().isin(['', 'null'])


def load(path):
    """Devuelve las filas válidas de un archivo y su reporte de calidad."""
    content = Path(path).read_bytes()
    raw = pd.read_csv(path, dtype=str, keep_default_na=False, encoding='utf-8-sig')
    raw.columns = [c.strip().lower() for c in raw.columns]
    missing_cols = [c for c in COLUMNS if c not in raw.columns]
    if missing_cols:
        raise ValueError(f'Faltan columnas del Mapa del Delito: {", ".join(missing_cols)}')

    df = pd.DataFrame({
        'id': raw['id-mapa'].str.strip().mask(blank(raw['id-mapa'])),
        'fecha': pd.to_datetime(raw['fecha'].str.strip(), format='%Y-%m-%d', errors='coerce'),
        'barrio': raw['barrio'].map(lambda x: BARRIOS.get(key(x))),
        'tipo': raw['tipo'].str.strip().mask(blank(raw['tipo'])),
        'subtipo': raw['subtipo'].str.strip().mask(blank(raw['subtipo'])),
        'franja': pd.to_numeric(raw['franja'], errors='coerce'),
        'cantidad': pd.to_numeric(raw['cantidad'], errors='coerce'),
        'uso_arma': raw['uso_arma'].str.strip().str.upper().eq('SI'),
        'uso_moto': raw['uso_moto'].str.strip().str.upper().eq('SI'),
        'comuna': pd.to_numeric(raw['comuna'], errors='coerce'),
        'latitud': pd.to_numeric(raw['latitud'], errors='coerce'),
        'longitud': pd.to_numeric(raw['longitud'], errors='coerce'),
    })
    df.loc[~df['franja'].between(0, 23) | (df['franja'] % 1 != 0), 'franja'] = pd.NA
    whole = (df['cantidad'] >= 0) & (df['cantidad'] % 1 == 0)
    faltantes = {c: int(blank(raw[c]).sum()) for c in COLUMNS}
    invalid_barrio = int((df['barrio'].isna() & ~blank(raw['barrio'])).sum())

    valid = (df['id'].notna() & df['fecha'].notna() & df['barrio'].notna()
             & df['tipo'].notna() & whole)
    df['anio'] = df['fecha'].dt.year
    duplicated = valid & df.duplicated(['anio', 'id'], keep='first')
    rows = df[valid & ~duplicated].copy()
    rows['anio'] = rows['anio'].astype(int)
    rows['franja'] = rows['franja'].astype('Int64')
    rows['cantidad'] = rows['cantidad'].astype(int)
    rows['mes'] = rows['fecha'].dt.strftime('%Y-%m')
    rows['categoria'] = rows['tipo'].where(rows['tipo'] != VIAL, 'Siniestros viales')
    rows['delito'] = rows['tipo'] != VIAL
    rows['pin_en_caba'] = rows['latitud'].between(*LAT) & rows['longitud'].between(*LON)

    by_type = pd.DataFrame({'leidas': df.groupby('tipo').size(),
                            'descartadas': df[~valid].groupby('tipo').size()}).fillna(0).astype(int)
    by_type['pct_descartadas'] = (by_type['descartadas'] / by_type['leidas'] * 100).round(1)
    pins = rows.loc[rows['pin_en_caba'], ['latitud', 'longitud']].round(6)
    per_point = pins.value_counts()
    calidad = {
        'archivo': Path(path).name,
        'sha256': sha256(content).hexdigest(),
        'filas_leidas': len(raw),
        'filas_validas': len(rows),
        'descartadas': int((~valid).sum()),
        'duplicadas': int(duplicated.sum()),
        'barrio_no_reconocido': invalid_barrio,
        'faltantes_por_columna': faltantes,
        'descartes_por_tipo': by_type.to_dict(orient='index'),
        'periodo': [rows['fecha'].min().date().isoformat(), rows['fecha'].max().date().isoformat()],
        'meses': int(rows['mes'].nunique()),
        'barrios': int(rows['barrio'].nunique()),
        'comunas': int(rows['comuna'].nunique()),
        'tipos': sorted(rows['tipo'].unique()),
        'hechos_registrados': int(rows['cantidad'].sum()),
        'cantidad_distinta_de_1': int((rows['cantidad'] != 1).sum()),
        'franja_sin_dato': int(rows['franja'].isna().sum()),
        'con_coordenadas': int(rows[['latitud', 'longitud']].notna().all(axis=1).sum()),
        'pin_en_caba': int(rows['pin_en_caba'].sum()),
        'puntos_distintos': int(len(per_point)),
        'hechos_en_puntos_con_10_o_mas': int(per_point[per_point >= 10].sum()),
    }
    return rows, calidad


def load_many(paths):
    """Une varios archivos anuales. Un ID repetido en el mismo año se cuenta una vez."""
    loaded = [load(path) for path in paths]
    rows = pd.concat([r for r, _ in loaded], ignore_index=True)
    repeated = rows.duplicated(['anio', 'id'], keep='first')
    calidades = [c for _, c in loaded]
    return rows[~repeated].reset_index(drop=True), calidades, int(repeated.sum())


def pivot(rows, index, columns='categoria'):
    table = rows.pivot_table(index=index, columns=columns, values='cantidad',
                             aggfunc='sum', fill_value=0, dropna=False)
    table.columns.name = None
    return table


def comuna_by_barrio(rows):
    return rows.groupby('barrio')['comuna'].agg(lambda c: c.mode().iat[0]).astype(int)


def tables(rows):
    franja = rows.assign(franja=rows['franja'].map(
        lambda h: 'Sin dato' if pd.isna(h) else f'{int(h):02d}'))
    return {
        'anio_categoria': pivot(rows, 'anio'),
        'mes_categoria': pivot(rows, 'mes'),
        'franja_categoria': pivot(franja, 'franja'),
        'subtipo': rows.groupby(['anio', 'tipo', 'subtipo'])['cantidad'].sum().rename('hechos')
                       .reset_index().sort_values(['anio', 'hechos'], ascending=[True, False]),
        'barrio_anio': barrio_anio(rows),
        'barrio_mes': barrio_mes(rows),
    }


def barrio_anio(rows):
    """Una fila por barrio y año, con conteos por tipo y proporciones de delitos."""
    table = pivot(rows, ['barrio', 'anio'])
    table['total_delitos'] = table.drop(columns='Siniestros viales', errors='ignore').sum(axis=1)
    delitos = rows[rows['delito']]
    for name, mask in (('pct_con_arma', delitos['uso_arma']), ('pct_con_moto', delitos['uso_moto']),
                       ('pct_nocturnos', delitos['franja'].isin(NIGHT))):
        marked = delitos[mask].groupby(['barrio', 'anio'])['cantidad'].sum()
        table[name] = (marked.reindex(table.index, fill_value=0) / table['total_delitos'] * 100).round(1)
    table.insert(0, 'comuna', table.index.get_level_values('barrio').map(comuna_by_barrio(rows)))
    return table


def barrio_mes(rows):
    """Dataset candidato: una fila por barrio y mes con cobertura en el archivo.

    Un barrio y mes sin filas válidas no aparece: no se completa con ceros. Dentro
    de una fila con cobertura, un tipo sin hechos vale cero registrado.
    """
    def count(mask):
        return rows[mask].groupby(['barrio', 'mes'])['cantidad'].sum()

    delito = rows['delito']
    out = pd.DataFrame({
        'filas_validas': rows.groupby(['barrio', 'mes']).size(),
        'robos': count(rows['tipo'] == 'Robo'),
        'hurtos': count(rows['tipo'] == 'Hurto'),
        'automotor': count(rows['subtipo'].isin(['Robo automotor', 'Hurto automotor'])),
        'lesiones_dolosas': count(rows['tipo'] == 'Lesiones'),
        'amenazas': count(rows['tipo'] == 'Amenazas'),
        'homicidios_dolosos': count(rows['tipo'] == 'Homicidios'),
        'delitos_con_arma': count(delito & rows['uso_arma']),
        'delitos_con_moto': count(delito & rows['uso_moto']),
        'delitos_nocturnos': count(delito & rows['franja'].isin(NIGHT)),
        'total_delitos': count(delito),
        'siniestros_viales': count(~delito),
    }).fillna(0).astype(int)
    out.insert(0, 'comuna', out.index.get_level_values('barrio').map(comuna_by_barrio(rows)))
    return out.reset_index()


def figures(t, out):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.ticker import FuncFormatter

    out.mkdir(parents=True, exist_ok=True)
    ink, muted, grid, surface = '#0b0b0b', '#52514e', '#e4e3df', '#fcfcfb'
    series = {'Robo': '#2a78d6', 'Hurto': '#eb6834', 'Otros delitos': '#1baf7a'}
    thousands = FuncFormatter(lambda v, _: f'{v:,.0f}'.replace(',', '.'))
    plt.rcParams.update({
        'figure.facecolor': surface, 'axes.facecolor': surface, 'axes.edgecolor': grid,
        'axes.labelcolor': muted, 'xtick.color': muted, 'ytick.color': muted,
        'text.color': ink, 'font.size': 10, 'axes.titlesize': 12, 'axes.titleweight': 'bold',
        'axes.titlelocation': 'left', 'axes.spines.top': False, 'axes.spines.right': False,
        'axes.grid': True, 'axes.grid.axis': 'y', 'grid.color': grid, 'grid.linewidth': 0.8,
        'axes.axisbelow': True, 'legend.frameon': False,
    })
    years = sorted(t['anio_categoria'].index)
    span = f'{years[0]}–{years[-1]}' if len(years) > 1 else str(years[0])

    def three(table):
        other = [c for c in table.columns if c not in ('Robo', 'Hurto', 'Siniestros viales')]
        return pd.DataFrame({'Robo': table['Robo'], 'Hurto': table['Hurto'],
                             'Otros delitos': table[other].sum(axis=1)})

    def header(ax, title, subtitle, pad=22):
        ax.set_title(title, pad=pad)
        ax.annotate(subtitle, (0, 1), xycoords='axes fraction', xytext=(0, 6),
                    textcoords='offset points', color=muted, fontsize=9, va='bottom')

    def lines(data, labels, title, subtitle, xlabel, name, width=8):
        fig, ax = plt.subplots(figsize=(width, 4.2), dpi=150)
        x = range(len(data))
        for col, color in series.items():
            ax.plot(x, data[col], color=color, linewidth=2, marker='o', markersize=4,
                    markeredgecolor=surface, markeredgewidth=1.5, label=col)
        # Etiquetas al final de cada línea, separadas si los valores quedan cerca.
        gap = data[list(series)].to_numpy().max() * 0.05
        placed = []
        for value, col in sorted((data[col].iat[-1], col) for col in series):
            y = max(value, placed[-1] + gap) if placed else value
            placed.append(y)
            ax.annotate(col, (len(data) - 1, y), xytext=(8, 0),
                        textcoords='offset points', va='center', color=ink, fontsize=9)
        ax.set_xticks(list(x), labels)
        ax.set_ylim(bottom=0)
        ax.set_xlim(-0.4, len(data) - 0.2)
        ax.set_xlabel(xlabel)
        ax.set_ylabel('Hechos registrados')
        ax.yaxis.set_major_formatter(thousands)
        header(ax, title, subtitle)
        ax.legend(loc='upper left', bbox_to_anchor=(0, -0.14), ncol=3)
        fig.tight_layout()
        fig.savefig(out / name)
        plt.close(fig)
        return ax

    monthly = three(t['mes_categoria'])
    labels = [MONTHS[int(m[5:]) - 1] + (f'\n{m[:4]}' if m[5:] == '01' else '') for m in monthly.index]
    lines(monthly, labels, f'Hechos registrados por mes · CABA {span}',
          'Otros delitos: lesiones dolosas, amenazas y homicidios. Excluye siniestros viales.',
          'Mes del hecho', 'delitos-por-mes.png', width=10)

    hourly = three(t['franja_categoria'].drop(index='Sin dato', errors='ignore'))
    lines(hourly, [h if int(h) % 3 == 0 else '' for h in hourly.index],
          f'Hechos registrados por franja horaria · CABA {span}',
          'Suma de los años. Hora de inicio de la franja. Excluye siniestros viales y franjas sin dato.',
          'Franja horaria', 'delitos-por-franja.png')

    # Barrios: un punto por año unido por una línea, ordenado por el último año.
    totals = t['barrio_anio']['total_delitos'].unstack('anio').reindex(columns=years, fill_value=0)
    totals = totals.sort_values(years[-1])
    fig, ax = plt.subplots(figsize=(8, 10.5), dpi=150)
    y = range(len(totals))
    colors = ['#2a78d6', '#eb6834']
    if len(years) > 1:
        ax.hlines(y, totals.min(axis=1), totals.max(axis=1), color=grid, linewidth=2, zorder=1)
    for year, color in zip(years[-2:], colors[-len(years[-2:]):]):
        ax.scatter(totals[year], y, s=36, color=color, edgecolor=surface, linewidth=1.5,
                   zorder=2, label=str(year))
    ax.set_yticks(list(y), totals.index)
    ax.grid(axis='y', visible=False)
    ax.grid(axis='x', visible=True)
    ax.tick_params(axis='y', length=0, labelsize=8.5)
    for label in ax.get_yticklabels():
        if label.get_text() in FOCUS:
            label.set_fontweight('bold')
            label.set_color(ink)
    ax.xaxis.set_major_formatter(thousands)
    ax.set_xlim(left=0)
    ax.margins(y=0.01)
    ax.set_xlabel('Delitos registrados por año (excluye siniestros viales)')
    header(ax, f'Delitos registrados por barrio · CABA {span}',
           'Conteos sin normalizar por población, superficie ni circulación.\n'
           'En negrita, los barrios del piloto y su posible ampliación.', pad=44)
    ax.legend(loc='lower right', ncol=len(years[-2:]))
    fig.tight_layout()
    fig.savefig(out / 'delitos-por-barrio.png')
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('inputs', type=Path, nargs='*',
                        help='CSV anuales. Por defecto, data/raw/delitos_20*.csv')
    parser.add_argument('--out-dir', type=Path, default=ROOT / 'data/processed/delitos')
    parser.add_argument('--fig-dir', type=Path, default=ROOT / 'docs/img/eda-delitos')
    parser.add_argument('--no-figures', action='store_true')
    args = parser.parse_args()
    inputs = args.inputs or sorted((ROOT / 'data/raw').glob('delitos_20*.csv'))
    try:
        if not inputs:
            raise ValueError('No hay CSV del Mapa del Delito en data/raw.')
        rows, calidades, repeated = load_many(inputs)
    except (OSError, ValueError) as error:
        parser.exit(1, f'Error: {error}\n')
    t = tables(rows)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    for name, table in t.items():
        table.to_csv(args.out_dir / f'{name}.csv', encoding='utf-8', index=table.index.name is not None
                     or isinstance(table.index, pd.MultiIndex))
    report = {'archivos': calidades, 'repetidos_entre_archivos': repeated,
              'filas_validas_total': len(rows)}
    (args.out_dir / 'calidad.json').write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    if not args.no_figures:
        figures(t, args.fig_dir)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    print(f'Tablas en {args.out_dir}')


if __name__ == '__main__':
    main()
