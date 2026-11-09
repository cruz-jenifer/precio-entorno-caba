import json
import os
from hashlib import sha256
from pathlib import Path

import streamlit as st

from precio_entorno import entorno, mapa
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


@st.cache_data(show_spinner='Ubicando hechos registrados…')
def crime_map(path, digest, period, kind, bbox):
    return entorno.crime_cells(path, period, kind, bbox)


def money(value, currency):
    return f"{currency} {value:,.0f}".replace(',', '.') if value is not None else '—'


st.set_page_config(page_title='Precio y Entorno CABA', layout='centered')
st.title('Precio y Entorno CABA')
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
    st.caption('El contexto se cruza por barrio. Un pin utilizable tiene coordenadas plausibles '
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
            crime_file, periods = store.crime_periods()
            path = ROOT / 'data/raw' / crime_file['filename'] if crime_file else None
            if not crime_file:
                st.info('Cargá el CSV del Mapa del Delito para ver esta capa.')
            elif not path.exists() or file_digest(str(path), path.stat().st_mtime) != crime_file['digest']:
                st.info(f"Para ubicar los hechos, guardá {crime_file['filename']} en data/raw/. "
                        'Tiene que ser el mismo archivo que se cargó.')
            else:
                c1, c2 = st.columns(2)
                period = c1.selectbox('Mes del hecho', periods, key='map-period')
                bbox = entorno.bbox_of(layers['barrios'], neighborhood)
                crime, kinds = crime_map(str(path), crime_file['digest'], period, None, bbox)
                kind = c2.selectbox('Tipo de delito', ['Todos'] + sorted(kinds), key='map-kind')
                if kind != 'Todos':
                    crime = crime_map(str(path), crime_file['digest'], period, kind, bbox)[0]
                crime_label = f"{period} · {'todos los tipos' if kind == 'Todos' else kind}"
                if not crime:
                    st.info('No hay hechos con coordenadas para ese mes y tipo en la zona.')
    deck, legend = mapa.build(layers, neighborhood, active, school, noise_period, crime, crime_label)
    st.pydeck_chart(deck, height=520)
    if legend:
        st.markdown(mapa.legend_html(legend), unsafe_allow_html=True)
    for layer in active:
        if layer != 'Delitos registrados' or crime:
            st.caption(mapa.NOTES[layer])
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
               'Superficie cubierta (m²)': a['covered_area'], 'Ambientes': a['rooms']}
        if operation == 'alquiler':
            row['Expensas'] = money(a.get('expenses'), 'ARS')
        if not demo:
            row['Enlace'] = a['url']
        rows.append(row)
    st.dataframe(rows, hide_index=True, column_config={'Enlace': st.column_config.LinkColumn()})
else:
    st.caption('Aún no hay alertas.')
