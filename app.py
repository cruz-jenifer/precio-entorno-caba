import json
import os
from hashlib import sha256
from pathlib import Path

import streamlit as st

from precio_entorno import concentracion, entorno, mapa
from precio_entorno.bases import demo_rentals, operation_path
from precio_entorno.importing import BARRIOS, import_crimes, import_listings, usable_pin
from precio_entorno.inmobiliarias import CATALOGS
from precio_entorno.matching import compare_neighborhoods
from precio_entorno.store import Store

ROOT = Path(__file__).resolve().parent
fixtures = json.loads((ROOT / 'data/fixtures/demo.json').read_text(encoding='utf-8'))
demo_base = Path(os.environ.get('PRECIO_ENTORNO_DB', ROOT / 'data/local/demo.sqlite3'))
real_base = ROOT / 'data/local/real.sqlite3'
entorno_dir = ROOT / 'data/processed/entorno'


@st.cache_resource(show_spinner='Cargando capas del entorno…')
def load_layers(folder, stamp):
    """Capas de datos abiertos; `stamp` invalida la caché cuando se regeneran."""
    return entorno.load(folder)


@st.cache_data(show_spinner=False)
def file_digest(path, stamp):
    return sha256(Path(path).read_bytes()).hexdigest()


@st.cache_resource(show_spinner='Preparando los años del Mapa del Delito…')
def crime_index(signature):
    return concentracion.CrimeIndex([item[0] for item in signature])


def money(value, currency):
    return f"{currency} {value:,.0f}".replace(',', '.') if value is not None else '—'


st.set_page_config(page_title='Lüga', layout='centered')
st.title('Lüga')
goal = st.radio('¿Qué querés hacer?', ('Comprar', 'Alquilar'), horizontal=True)
operation = 'venta' if goal == 'Comprar' else 'alquiler'
mode = st.radio('Datos de trabajo', ('Demo ficticia', 'Datos reales'), horizontal=True)
demo = mode == 'Demo ficticia'
demo_path, real_path = operation_path(demo_base, operation), operation_path(real_base, operation)
if demo_path.resolve() == real_path.resolve():
    st.error('Las bases de la demo y de datos reales deben usar rutas distintas.')
    st.stop()
store = Store(demo_path if demo else real_path)
if demo:
    if operation == 'venta':
        store.seed(fixtures['initial'])
    else:
        store.ingest(demo_rentals(fixtures['alquiler']['initial']), source='demo-alquiler')
    st.caption('Los avisos y los delitos de la demo son ficticios. Las capas del mapa y las columnas de entorno '
               'son datos abiertos reales de Buenos Aires Data.')
else:
    st.caption('Datos reales · Catálogo autorizado y Mapa del Delito de CABA, cargados desde archivos locales.')
st.write('Compará barrios según tu presupuesto y guardá una búsqueda para ver nuevos avisos que encajen.'
         if operation == 'venta' else
         'Compará barrios según tu presupuesto mensual y guardá una búsqueda para ver nuevos alquileres que encajen.')

st.subheader('1. Qué estás buscando')
if operation == 'venta':
    currency = 'USD'
    c1, c2, c3 = st.columns(3)
    budget = c1.number_input('Presupuesto (USD)', min_value=1, value=110000, step=5000)
else:
    c0, c1, c2, c3 = st.columns(4)
    currency = c0.selectbox('Moneda', ('ARS', 'USD'), help='Los avisos se comparan en la moneda en que se publicaron, sin conversión.')
    budget = c1.number_input(f'Alquiler mensual máximo ({currency})', min_value=1,
                             value=800000 if currency == 'ARS' else 900, step=50000 if currency == 'ARS' else 50,
                             key=f'budget-{currency}')
min_area = c2.number_input('Superficie cubierta mínima (m²)', min_value=1, value=40)
rooms = c3.number_input('Ambientes', min_value=1, value=2)
stamp = (entorno_dir / 'resumen.json').stat().st_mtime if (entorno_dir / 'resumen.json').exists() else None
layers = load_layers(str(entorno_dir), stamp) if stamp else None
prefs = st.pills('¿Qué te importa del entorno?', mapa.PREFERENCES, selection_mode='multi',
                 default=['Subte', 'Plazas y parques'], key='prefs',
                 help='Suma columnas descriptivas a la comparación y enciende esas capas en el mapa. '
                      'No se combinan en un puntaje.') or []
level = 'primario'
if 'Escuelas' in prefs:
    level = st.segmented_control('Nivel educativo', mapa.LEVEL_NAMES, default='primario',
                                 format_func=str.capitalize, key='school-level') or 'primario'

st.subheader('2. Compará barrios y elegí uno')
listings = store.listings()
comparison = compare_neighborhoods(listings, budget, min_area, rooms, currency)
if not demo:
    in_currency = [item for item in listings if (item.get('currency') or 'USD') == currency]
    source = listings[0]['source'] if listings else 'sin cargar'
    word = 'precios publicados' if operation == 'venta' else 'alquileres publicados'
    st.caption(f'Catálogo {source} · {len(in_currency)} avisos aptos para comparar {word} en {currency} · '
               f'{sum(map(usable_pin, in_currency))} también tienen pin utilizable.')
    st.caption('La comparación general resume el barrio. La capa de registros permite elegir un inmueble '
               'y contar hechos en tres radios. Un pin utilizable tiene coordenadas plausibles '
               'y precisión de hasta 100 m declarada por la fuente.')
if operation == 'alquiler':
    st.caption('Precios de alquiler mensuales publicados, sin expensas. No se convierten pesos a dólares.')
if comparison and layers:
    for row in comparison:
        row.update(entorno.comparison_columns(layers['resumen'].get(row['Barrio']), prefs, level))
if comparison:
    st.dataframe(comparison, hide_index=True)
    if layers and prefs:
        st.caption('Columnas de entorno por barrio oficial · Datos abiertos de Buenos Aires Data. '
                   'Describen el barrio, no un aviso en particular.')
else:
    st.info('Importá un catálogo para comparar barrios.' if not listings
            else f'No hay avisos publicados en {currency} para comparar.')
zones = sorted(row['Barrio'] for row in comparison) if demo else sorted(set(BARRIOS.values()))
neighborhood = st.selectbox('Barrio para la alerta', zones, key=f'neighborhood-{mode}-{operation}')



def environment_map():
    if layers is None:
        st.info('Las capas del mapa todavía no se generaron. Ejecutá `python -m precio_entorno.entorno`.')
        return
    if neighborhood not in layers['resumen']:
        return
    st.markdown(f'**Entorno de {neighborhood}**')
    active = st.pills('Capas del mapa', mapa.LAYERS, selection_mode='multi', default=list(prefs),
                      key=f"layers-{'|'.join(prefs)}") or []
    controls = st.columns(3)
    noise_period, crime, crime_label, school = 'diurno', None, '', level
    analysis, focus, radius, persistent = None, None, 500, False
    if 'Escuelas' in active and 'Escuelas' not in prefs:
        school = controls[0].selectbox('Nivel educativo', mapa.LEVEL_NAMES, index=1, format_func=str.capitalize)
    if 'Ruido' in active:
        noise_period = controls[1].segmented_control(
            'Ruido', ('diurno', 'nocturno'), default='diurno', key='noise-period',
            format_func=lambda p: 'De día' if p == 'diurno' else 'De noche') or 'diurno'
    if 'Delitos registrados' in active:
        if demo:
            st.info('En la demo los delitos son ficticios y no se ubican en el mapa.')
        else:
            paths = concentracion.source_paths(ROOT / 'data/raw')
            if not paths:
                crime_file, _ = store.crime_periods()
                path = ROOT / 'data/raw' / crime_file['filename'] if crime_file else None
                if path and path.exists() and file_digest(str(path), path.stat().st_mtime) == crime_file['digest']:
                    paths = (path,)
            if not paths:
                st.info('Faltan CSV anuales oficiales en data/raw/ o el archivo que se importó, con su misma huella.')
            else:
                try:
                    index = crime_index(tuple((str(p), p.stat().st_mtime_ns, p.stat().st_size) for p in paths))
                    c1, c2, c3 = st.columns(3)
                    chosen = c1.selectbox('Vista de registros', ['Persistencia'] + index.years, key='crime-year')
                    kind = c2.selectbox('Tipo', ['todos', 'robo', 'hurto'], key='crime-kind',
                                        format_func=lambda k: {'todos': 'Robos y hurtos', 'robo': 'Robo · fuerza o violencia', 'hurto': 'Hurto · sin violencia'}[k])
                    band = c3.selectbox('Horario', ['todas', 'diurno', 'nocturno', 'sin_dato'], key='crime-band',
                                        format_func=lambda b: {'todas': 'Todos', 'diurno': 'Día · 06–19:59', 'nocturno': 'Noche · 20–05:59', 'sin_dato': 'Sin horario'}[b])
                    candidates = {i['id']: i for i in listings if i['neighborhood'] == neighborhood and usable_pin(i)}
                    selected = st.selectbox('Entorno de un inmueble', [''] + list(candidates),
                                            format_func=lambda i: f"{i} · {money(candidates[i]['price'], candidates[i]['currency'])}" if i else 'Vista general · celdas de 200 m')
                    radius = st.select_slider('Radio acumulativo (m)', options=list(concentracion.RADIOS), value=500)
                    persistent = chosen == 'Persistencia'
                    analysis = index.analyze(entorno.bbox_of(layers['barrios'], neighborhood),
                                             candidates.get(selected), radius, kind, band,
                                             None if persistent else chosen)
                    focus = analysis['inmueble']
                    crime = [dict(cell, hechos=len(cell['anios_altos']))
                             for cell in analysis['celdas'] if cell['persistente']] if persistent else [
                                 cell for cell in analysis['celdas'] if cell['hechos'] > 0]
                    crime_label = f"{', '.join(map(str, index.years)) if persistent else chosen} · {kind} · {band} · celda de 200 m"
                    if not crime:
                        st.info('Sin celdas persistentes con estos filtros; no implica ausencia de delitos.' if persistent
                                else 'Sin registros geolocalizados con estos filtros; no implica ausencia de delitos.')
                except (OSError, ValueError) as error:
                    st.error(f'No se pudo analizar el Mapa del Delito: {error}')
    deck, legend = mapa.build(layers, neighborhood, active, school, noise_period, crime, crime_label,
                              focus=focus, radius=radius, persistence=persistent)
    st.pydeck_chart(deck, height=520)
    if legend:
        st.markdown(mapa.legend_html(legend), unsafe_allow_html=True)
    for layer in active:
        if layer != 'Delitos registrados' or crime:
            st.caption(mapa.NOTES[layer])
    if analysis:
        st.markdown('**Registros y contexto**')
        st.write(concentracion.LIMITACIONES[0])
        if analysis['revision_2025']:
            st.warning(analysis['revision_2025'])
            st.markdown(f'[Ficha oficial de 2025]({concentracion.REVISION_URL})')
        st.caption(analysis['unidad'])
        if analysis['resumen_radios']:
            import pandas as pd
            summary = pd.DataFrame(analysis['resumen_radios'])
            selected_summary = summary[summary['radio_m'] == radius]
            if kind != 'todos':
                selected_summary = selected_summary[selected_summary['tipo'] == kind]
            chart = selected_summary.pivot(index='anio', columns='tipo', values='total' if band == 'todas' else band)
            chart.index = chart.index.astype(str)
            st.bar_chart(chart, stack=False, x_label='Año del hecho', y_label=f'Hechos registrados a {radius} m')
            st.caption(f'Gráfico: {kind}, horario {band}. Los años con meses faltantes son parciales, sin anualizar.')
            st.dataframe(summary.rename(columns={'anio': 'Año', 'radio_m': 'Radio (m)', 'tipo': 'Tipo',
                                                  'diurno': 'Día', 'nocturno': 'Noche', 'sin_dato': 'Sin horario',
                                                  'total': 'Total'}), hide_index=True)
            st.caption('Conteos acumulativos sin filtros de tipo ni horario. No sumar radios. '
                       f"Precisión informada del pin del aviso: {focus['precision_m']} m.")
        else:
            st.caption('Elegí un inmueble con pin preciso para comparar los tres radios. No se usa el centro del barrio.')
        with st.expander('Persistencia, cobertura y limitaciones'):
            st.write(analysis['persistencia']['definicion'])
            if not analysis['persistencia']['disponible']:
                st.info('Faltan dos años con registros observados en los 12 meses para evaluar persistencia.')
            st.dataframe(analysis['cobertura'], hide_index=True)
            for note in analysis['limitaciones'][1:]:
                st.write(note)
            st.json(analysis['calidad'])
            st.dataframe(analysis['fuentes'], hide_index=True)
    summary = layers['resumen'][neighborhood]
    with st.expander(f'Ficha de {neighborhood}'):
        facts = {'Comuna': summary['comuna'], 'Superficie del barrio (ha)': summary['area_ha']}
        facts.update(entorno.comparison_columns(summary, mapa.PREFERENCES, school))
        st.dataframe([{'Dato': k, 'Valor': '—' if v is None else str(v)} for k, v in facts.items()], hide_index=True)
        st.caption('Los porcentajes de ruido usan las celdas de 100 m relevadas por el Mapa de Ruido. '
                   'Los cortes de 70 dBA de día y 65 dBA de noche son descriptivos, no límites normativos.')
    with st.expander('Fuentes de las capas'):
        st.dataframe([{'Capa': f['titulo'], 'Período': f['periodo'], 'Archivo': f['archivo'], 'Enlace': f['url'],
                       'Licencia': f['licencia']} for f in layers['fuentes']['fuentes']],
                     hide_index=True, column_config={'Enlace': st.column_config.LinkColumn()})
        st.caption(f"Capas generadas el {layers['fuentes']['generado']}. "
                   'Unidad geográfica: barrio oficial de CABA.')


environment_map()

if demo:
    context = [dict(Tipo=r['kind'], Franja=r['time_band'], Hechos=r['count'], Período=r['period'])
               for r in fixtures['context'] if r['neighborhood'] == neighborhood]
    if context:
        with st.expander('Contexto del barrio · Datos ficticios'):
            st.dataframe(context, hide_index=True)
else:
    with st.expander('Delitos registrados por barrio · Mapa del Delito de CABA'):
        crime_file, periods = store.crime_periods()
        if crime_file:
            st.caption(f"Archivo {crime_file['filename']} · SHA-256 {crime_file['digest']}")
            period = st.selectbox('Mes del hecho', periods)
            context = store.crime_summary(neighborhood, period)
            if context:
                st.caption(f'{neighborhood} · {period} · Hechos registrados en las filas válidas del archivo.')
                st.dataframe([
                    {'Tipo': r['kind'], 'Franja': 'Sin dato' if r['hour'] is None else f"{r['hour']:02d}:00",
                     'Hechos': r['count']} for r in context
                ], hide_index=True)
            else:
                st.info(f'{neighborhood} · {period} · Sin cobertura observada en el archivo.')
        else:
            st.info('Sin cobertura. Todavía no se cargó un archivo del Mapa del Delito.')

if st.button('Guardar búsqueda', disabled=not neighborhood):
    if store.save_search(neighborhood, budget, min_area, rooms, currency):
        st.success('Búsqueda guardada. Las alertas se generan al incorporar avisos nuevos.')
    else:
        st.info('Esta búsqueda ya está guardada.')

searches = store.searches()
if searches:
    st.caption('Búsquedas guardadas')
    st.dataframe([{'ID': s['id'], 'Barrio': s['neighborhood'], 'Hasta': money(s['budget'], s.get('currency') or 'USD'),
                   'Desde (m²)': s['min_area'], 'Ambientes': s['rooms']} for s in searches], hide_index=True)


def show_report(label, report):
    st.info(f'{label} · Filas leídas {report.read} · Incorporadas {report.added} · '
            f'Duplicadas {report.duplicates} · Descartadas {report.discarded} · Alertas nuevas {report.alerts}')
    fields = sorted(report.missing.keys() | report.invalid.keys())
    if fields:
        st.dataframe([{'Campo': name, 'Faltantes': report.missing[name], 'Inválidos': report.invalid[name]}
                      for name in fields], hide_index=True)


if demo:
    st.subheader('3. Probá la actualización')
    example = 'Caballito con los filtros iniciales' + (' en ARS' if operation == 'alquiler' else '')
    st.write(f'Guardá una búsqueda antes de importar el lote nuevo. Para el ejemplo, elegí {example}.')
    if st.button('Importar lote nuevo de la demo', disabled=not searches):
        if operation == 'venta':
            added, matches = store.ingest(fixtures['new'])
        else:
            added, matches = store.ingest(demo_rentals(fixtures['alquiler']['new']), source='demo-alquiler')
        st.session_state[f'demo_report-{operation}'] = f'Avisos nuevos: {added}. Alertas nuevas: {matches}.'
        st.rerun()
    if f'demo_report-{operation}' in st.session_state:
        st.info(st.session_state[f'demo_report-{operation}'])
else:
    st.subheader('3. Importá datos locales')
    with st.form(f'listings-import-{operation}'):
        catalog = st.text_input('Nombre del catálogo autorizado',
                                value=listings[0]['source'] if listings else CATALOGS[operation])
        kind = 'en venta' if operation == 'venta' else 'en alquiler'
        listings_file = st.file_uploader(f'Avisos vigentes de departamentos {kind}', type=['csv', 'json'])
        authorized = st.checkbox('Confirmo que el archivo proviene del catálogo autorizado indicado.')
        if st.form_submit_button('Importar avisos'):
            if not listings_file or not authorized:
                st.error('Elegí el archivo y confirmá el acceso autorizado al catálogo.')
            else:
                try:
                    st.session_state[f'listings_report-{operation}'] = import_listings(
                        store, listings_file.getvalue(), listings_file.name, catalog, operation)
                except ValueError as error:
                    st.error(str(error))
                else:
                    st.rerun()
    if f'listings_report-{operation}' in st.session_state:
        show_report('Avisos', st.session_state[f'listings_report-{operation}'])

    with st.form(f'crime-import-{operation}'):
        crime_csv = st.file_uploader('CSV oficial del Mapa del Delito de CABA', type=['csv'])
        st.caption('La carga reemplaza el archivo de contexto anterior.')
        if st.form_submit_button('Cargar contexto'):
            if not crime_csv:
                st.error('Elegí el CSV oficial.')
            else:
                try:
                    st.session_state[f'crime_report-{operation}'] = import_crimes(
                        store, crime_csv.getvalue(), crime_csv.name)
                except ValueError as error:
                    st.error(str(error))
                else:
                    st.rerun()
    if f'crime_report-{operation}' in st.session_state:
        show_report('Mapa del Delito', st.session_state[f'crime_report-{operation}'])

alerts = store.alerts()
if alerts:
    st.caption(f'Alertas · {goal} · {mode}')
    rows = []
    for a in alerts:
        row = {'Búsqueda': a['search_id'], 'Aviso': a['id'], 'Barrio': a['neighborhood'],
               'Precio publicado': money(a['price'], a['currency']),
               'Superficie cubierta (m²)': a['covered_area'], 'Ambientes': a['rooms'],
               'Vigencia': {'baja': 'Ya no está publicado', 'reservado': 'Reservado',
                            'no_visto': 'No visto en el último barrido'}.get(a.get('status'), 'Publicado')}
        if operation == 'alquiler':
            row['Expensas'] = money(a.get('expenses'), 'ARS')
        if not demo:
            row['Enlace'] = a['url']
        rows.append(row)
    st.dataframe(rows, hide_index=True, column_config={'Enlace': st.column_config.LinkColumn()})
else:
    st.caption('Aún no hay alertas.')

if not demo and operation == 'venta':
    from precio_entorno.inferencia import DEFAULT_OUT, load as load_model, predict
    import pandas as pd

    st.subheader('Referencia de precio publicado')
    if (DEFAULT_OUT / 'evaluacion.json').exists():
        try:
            bundle = load_model(DEFAULT_OUT)
            evaluation = bundle['report']
            c1, c2, c3 = st.columns(3)
            c1.metric('MAE de prueba (USD/m²)', f"{evaluation['modelo_prueba']['mae']:,.0f}")
            c2.metric('MAE baseline (USD/m²)', f"{evaluation['baseline_prueba']['mae']:,.0f}")
            c3.metric('Prueba dentro de ±20 %', f"{evaluation['dentro_20_pct_prueba']:.1%}")
            st.caption(f"Modelo {bundle['version']} · {evaluation['prueba']} observaciones de prueba · "
                       f"Entrenado {evaluation['fecha_utc'][:10]}. Prueba histórica, sin validación temporal.")
            if 'prueba_solo_campos_importador' in evaluation:
                st.caption('Con los campos básicos del importador, sin enriquecimiento, el MAE de prueba es '
                           f"{evaluation['prueba_solo_campos_importador']['mae']:,.0f} USD/m².")
            candidates = [r for r in listings if r['neighborhood'] == neighborhood and r.get('currency') == 'USD']
            if candidates:
                frame = pd.DataFrame(candidates)
                frame['agency'] = frame['id'].str.split(':').str[0]
                prediction = predict(bundle, frame)
                st.dataframe(prediction, hide_index=True)
                st.download_button('Descargar referencias', prediction.to_csv(index=False),
                                   'referencias_publicacion.csv', 'text/csv')
            st.caption('Referencia de publicación de venta en USD, no tasación ni precio de cierre. '
                       'El modelo operativo fue reajustado con todo el corte histórico. '
                       'Las variables faltantes se indican por aviso; su error puede superar al de prueba. '
                       'Los delitos registrados se mantienen como contexto separado.')
        except (OSError, ValueError, KeyError) as error:
            st.error(f'No se pudo generar la referencia: {error}')
    else:
        st.info('Todavía no se generó el modelo de referencia de publicación.')
