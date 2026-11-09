'use strict';

/* Precio y Entorno CABA: interfaz web. Habla con la API local de precio_entorno.api. */

const PREFERENCIAS = [
  { clave: 'subte', nombre: 'Subte' },
  { clave: 'verdes', nombre: 'Plazas y parques' },
  { clave: 'escuelas', nombre: 'Escuelas' },
  { clave: 'salud', nombre: 'Salud' },
  { clave: 'ruido', nombre: 'Ruido' },
  { clave: 'riesgo', nombre: 'Riesgo hídrico' },
];
const CAPAS = [...PREFERENCIAS, { clave: 'delitos', nombre: 'Delitos registrados' }];
const SUBTE = { A: '#18CCCC', B: '#EB0909', C: '#233AA8', D: '#02A17A', E: '#AE3D97', H: '#FFD600' };
const COLOR = { verdes: '#5E7D4F', riesgo: '#1E88E5', escuela: '#1E2A32', cesac: '#00897B', hospital: '#795548' };
const RUIDO = [[50, '#FFFFCC'], [55, '#FFEDA0'], [60, '#FED976'], [65, '#FEB24C'], [70, '#FD8D3C'], [75, '#F03B20'], [80, '#BD0026']];
const DELITOS = ['#D3DBE3', '#A9B8C8', '#7E93AB', '#55708E', '#2E4560'];
const ESTILO = 'https://basemaps.cartocdn.com/gl/positron-gl-style/style.json';
const NOTAS = {
  subte: 'Indican conectividad, no tiempos de viaje.',
  verdes: 'Plazas, parques, jardines y paseos. No incluye canteros ni plazoletas.',
  escuelas: 'Estar cerca no asegura una vacante. Consultá cada escuela.',
  salud: 'Estar cerca no asegura turnos.',
  ruido: 'Nivel exterior típico por celda de 100 m, medido sobre todo en calles. No describe el interior de un departamento.',
  riesgo: 'Áreas de prevención publicadas en 2020. Si una dirección cae dentro, conviene preguntarlo en la visita.',
  delitos: 'Hechos registrados por celda de 200 m. También reflejan diferencias de exposición y de denuncia. No son un puntaje de seguridad.',
};
const PRESUPUESTO = { 'venta-USD': 110000, 'alquiler-ARS': 800000, 'alquiler-USD': 900 };
const VACIO = { type: 'FeatureCollection', features: [] };
const reducido = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
const celular = () => window.matchMedia('(max-width: 820px)').matches;

const numero = new Intl.NumberFormat('es-AR');
const decimal = new Intl.NumberFormat('es-AR', { maximumFractionDigits: 1 });
const dinero = (valor, moneda) => (valor == null ? '—' : `${moneda} ${numero.format(valor)}`);
const plural = (n, uno, varios) => (n === 1 ? uno : varios);
const enumerar = (items) => (items.length < 2 ? items.join('') : `${items.slice(0, -1).join(', ')} y ${items.at(-1)}`);
const porcentaje = (v) => (v == null ? null : Math.round(v * 100));
const mes = (periodo) => {
  const [anio, numeroMes] = periodo.split('-').map(Number);
  return new Intl.DateTimeFormat('es-AR', { month: 'long', year: 'numeric' }).format(new Date(anio, numeroMes - 1, 1));
};
const esc = (texto) => String(texto ?? '').replace(/[&<>"']/g, (c) => (
  { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const $ = (selector) => document.querySelector(selector);

function leerGuardado() {
  try { return JSON.parse(localStorage.getItem('precio-entorno-filtros')) || {}; } catch { return {}; }
}

const guardado = leerGuardado();
const estado = {
  modo: guardado.modo || 'real',
  operacion: guardado.operacion || 'venta',
  moneda: guardado.moneda || 'USD',
  presupuesto: guardado.presupuesto || 110000,
  superficie: guardado.superficie || 40,
  ambientes: guardado.ambientes || 2,
  ambientesOMas: Boolean(guardado.ambientesOMas),
  verTodos: false,
  prefs: new Set(guardado.prefs || ['subte', 'verdes']),
  nivel: guardado.nivel || 'primario',
  ruido: 'diurno',
  delitos: { periodo: null, tipo: '' },
  info: null,
  barrios: [],
  formas: null,
  seleccionado: null,
  avisos: [],
  capas: new Set(),
  capasDatos: {},
  delitosDatos: null,
  hover: null,
  leyendaCerrada: window.matchMedia('(max-width: 820px)').matches,
  leyendaAbierta: false,
};

function guardar() {
  const { modo, operacion, moneda, presupuesto, superficie, ambientes, nivel } = estado;
  try {
    localStorage.setItem('precio-entorno-filtros', JSON.stringify(
      { modo, operacion, moneda, presupuesto, superficie, ambientes, ambientesOMas: estado.ambientesOMas, nivel, prefs: [...estado.prefs] }));
  } catch { /* Sin almacenamiento local: los filtros vuelven a los valores iniciales. */ }
}

function consulta(extra = {}) {
  const { modo, operacion, presupuesto, superficie, ambientes, moneda } = estado;
  return new URLSearchParams({ modo, operacion, presupuesto, superficie, ambientes, moneda,
    ambientes_o_mas: estado.ambientesOMas, ...extra });
}

async function api(ruta, opciones) {
  const respuesta = await fetch(ruta, opciones);
  if (!respuesta.ok) {
    let detalle = `Error ${respuesta.status}`;
    try { const cuerpo = await respuesta.json(); detalle = cuerpo.detail?.[0]?.msg || cuerpo.detail || detalle; } catch { /* sin cuerpo */ }
    throw new Error(detalle);
  }
  return respuesta.json();
}

/* Textos del entorno */

function datosEntorno(e) {
  if (!e) return {};
  const escuelas = e.escuelas[estado.nivel] || {};
  const totalEscuelas = (escuelas.Estatal || 0) + (escuelas.Privada || 0);
  const ruidoDia = porcentaje(e.ruido.diurno.alto);
  return {
    subte: e.subte_lineas.length ? `Subte ${enumerar(e.subte_lineas)}` : 'Sin estaciones de subte',
    verdes: e.verdes_cantidad
      ? `${e.verdes_cantidad} ${plural(e.verdes_cantidad, 'plaza o parque', 'plazas y parques')}, ${decimal.format(e.verdes_ha)} ha`
      : 'Sin plazas ni parques en el inventario',
    escuelas: `${totalEscuelas} ${plural(totalEscuelas, 'escuela', 'escuelas')} de nivel ${estado.nivel}`,
    salud: `${e.cesac} CeSAC y ${e.hospitales} ${plural(e.hospitales, 'hospital', 'hospitales')}`,
    ruido: ruidoDia == null ? 'Ruido sin cobertura suficiente'
      : `Ruido de día de 70 dBA o más en el ${ruidoDia} % de las celdas`,
    riesgo: `${porcentaje(e.riesgo_hidrico)} % en área de riesgo hídrico`,
  };
}

function lineaEntorno(e) {
  const datos = datosEntorno(e);
  const partes = PREFERENCIAS.filter((p) => estado.prefs.has(p.clave)).map((p) => datos[p.clave]);
  return partes.length ? `${partes.join('. ')}.` : '';
}

/* Panel: lista de barrios */

function renderLista() {
  const con = estado.barrios.filter((b) => b.coincidencias > 0);
  const sin = estado.barrios.filter((b) => !b.coincidencias);
  const total = estado.barrios.reduce((s, b) => s + b.avisos, 0);
  const encajan = con.reduce((s, b) => s + b.coincidencias, 0);
  const titulo = con.length
    ? `${con.length} ${plural(con.length, 'barrio tiene', 'barrios tienen')} avisos que encajan`
    : 'Ningún aviso encaja con estos filtros';
  const nota = con.length
    ? `${numero.format(encajan)} de ${numero.format(total)} avisos en ${estado.moneda} encajan con tu búsqueda. Precios publicados, no tasaciones. Elegí un barrio para ver su entorno en el mapa.`
    : 'Probá subir el presupuesto, bajar la superficie mínima o cambiar los ambientes. Igual podés elegir un barrio para ver su entorno.';
  const filas = con.map((b) => `
    <li><button class="fila" type="button" data-barrio="${esc(b.barrio)}">
      <span class="fila-nombre">${esc(b.barrio)}</span>
      <span class="fila-cuenta">${b.coincidencias} de ${b.avisos} ${plural(b.avisos, 'aviso', 'avisos')}</span>
      <span class="fila-mediana">Mediana ${dinero(b.mediana, estado.moneda)}</span>
      <span></span>
      ${b.entorno ? `<span class="fila-entorno">${esc(lineaEntorno(b.entorno))}</span>` : ''}
    </button></li>`).join('');
  const compactos = sin.map((b) => `<li><button type="button" data-barrio="${esc(b.barrio)}">${esc(b.barrio)} · ${b.avisos}</button></li>`).join('');
  $('#contenido').innerHTML = `
    <h1 class="titulo-lista">${titulo}</h1>
    <p class="nota">${nota}</p>
    ${con.length ? `<ul class="barrios">${filas}</ul>` : ''}
    ${sin.length ? `<details class="sin-coincidencias"${con.length ? '' : ' open'}>
      <summary>${sin.length} ${plural(sin.length, 'barrio', 'barrios')} sin avisos que encajen</summary>
      <ul class="lista-compacta">${compactos}</ul></details>` : ''}`;
}

/* Panel: ficha del barrio */

function renderFicha() {
  const b = estado.barrios.find((x) => x.barrio === estado.seleccionado);
  if (!b) return;
  const e = b.entorno;
  const ficha = [];
  if (e) {
    const escuelas = e.escuelas[estado.nivel] || {};
    const total = (escuelas.Estatal || 0) + (escuelas.Privada || 0);
    const dia = porcentaje(e.ruido.diurno.alto);
    const noche = porcentaje(e.ruido.nocturno.alto);
    ficha.push(
      ['Subte', e.subte_lineas.length
        ? `${plural(e.subte_lineas.length, 'Línea', 'Líneas')} ${enumerar(e.subte_lineas)}, ${e.subte_estaciones} ${plural(e.subte_estaciones, 'estación', 'estaciones')}`
        : 'Sin estaciones de subte'],
      ['Plazas y parques', e.verdes_cantidad
        ? `${e.verdes_cantidad} ${plural(e.verdes_cantidad, 'plaza o parque', 'plazas y parques')}, ${decimal.format(e.verdes_ha)} ha`
        : 'Ninguno en el inventario'],
      [`Escuelas de nivel ${estado.nivel}`, `${total}, de las que ${escuelas.Estatal || 0} son de gestión estatal`],
      ['Salud', `${e.cesac} CeSAC y ${e.hospitales} ${plural(e.hospitales, 'hospital', 'hospitales')}`],
      ['Ruido de día', dia == null ? 'Sin cobertura suficiente' : `70 dBA o más en el ${dia} % de las celdas relevadas`],
      ['Ruido de noche', noche == null ? 'Sin cobertura suficiente' : `65 dBA o más en el ${noche} % de las celdas relevadas`],
      ['Riesgo hídrico', `${porcentaje(e.riesgo_hidrico)} % de la superficie en área de prevención`],
    );
  }
  const alquiler = estado.operacion === 'alquiler';
  const visibles = estado.verTodos ? estado.avisos : estado.avisos.slice(0, 25);
  const filas = visibles.map((a) => `<tr>
      <td>${dinero(a.precio, a.moneda)}</td>
      <td>${a.superficie} m²</td>
      <td>${a.ambientes}</td>
      ${alquiler ? `<td>${a.expensas == null ? '—' : dinero(a.expensas, 'ARS')}</td>` : ''}
      <td>${a.enlace ? `<a href="${esc(a.enlace)}" target="_blank" rel="noopener">Ver aviso</a>` : 'Ejemplo'}</td>
    </tr>`).join('');
  const resumen = b.coincidencias
    ? `${b.coincidencias} de ${b.avisos} ${plural(b.avisos, 'aviso', 'avisos')} en ${estado.moneda} ${plural(b.coincidencias, 'encaja', 'encajan')} con tu búsqueda. Mediana ${dinero(b.mediana, estado.moneda)}.`
    : 'Ningún aviso encaja con tu búsqueda por ahora. Podés crear la alerta igual.';
  $('#contenido').innerHTML = `
    <article class="ficha">
      <button class="boton-texto volver" type="button" id="volver">Todos los barrios</button>
      <h1 class="titulo-barrio">${esc(b.barrio)}</h1>
      ${e ? `<p class="ficha-sub">Comuna ${e.comuna}, ${numero.format(Math.round(e.area_ha))} ha</p>` : ''}
      <p class="ficha-resumen">${resumen}</p>
      ${estado.ambientesOMas
        ? '<p class="nota">Para crear una alerta, elegí una cantidad exacta de ambientes.</p>'
        : `<button class="boton-primario" type="button" id="crear-alerta">Crear alerta para ${esc(b.barrio)}</button>`}
      <p class="estado" id="estado-alerta" role="status"></p>
      ${ficha.length ? `<h2>Entorno</h2>
        <dl class="hechos">${ficha.map(([k, v]) => `<dt>${esc(k)}</dt><dd>${esc(v)}</dd>`).join('')}</dl>
        <p class="fuente">Datos abiertos de Buenos Aires Data, por barrio oficial. Describen el barrio, no un departamento.
          <button class="boton-texto" type="button" data-fuentes>Ver fuentes</button></p>` : ''}
      ${b.coincidencias ? `<h2>Avisos que encajan</h2>
        <table class="avisos">
          <thead><tr><th>Precio publicado</th><th>Cubierta</th><th>Amb.</th>${alquiler ? '<th>Expensas</th>' : ''}<th><span hidden>Enlace</span></th></tr></thead>
          <tbody>${filas}</tbody>
        </table>
        ${estado.avisos.length > visibles.length ? `<p class="fuente">Se muestran los ${visibles.length} más baratos de ${estado.avisos.length}. <button class="boton-texto" type="button" id="ver-todos">Ver todos</button></p>` : ''}
        <p class="fuente">${estado.modo === 'demo' ? 'Avisos ficticios de ejemplo.' : 'Precios de publicación del catálogo autorizado, no tasaciones ni precios de cierre.'}</p>` : ''}
    </article>`;
}

function renderPanel() {
  if (estado.seleccionado) renderFicha();
  else renderLista();
}

/* Mapa */

const mapa = new maplibregl.Map({
  container: 'mapa',
  style: ESTILO,
  center: [-58.445, -34.615],
  zoom: 11.2,
  minZoom: 10,
  maxZoom: 17.5,
  dragRotate: false,
  pitchWithRotate: false,
  attributionControl: { compact: true },
});
mapa.touchZoomRotate.disableRotation();
mapa.addControl(new maplibregl.NavigationControl({ showCompass: false }), 'top-right');
const mapaListo = new Promise((resolver) => mapa.on('load', resolver));
new ResizeObserver(() => mapa.resize()).observe(document.querySelector('.mapa'));
const popup = new maplibregl.Popup({ closeButton: false, closeOnClick: false, offset: 10, maxWidth: '18rem' });

async function prepararMapa() {
  const [formas] = await Promise.all([api('/api/mapa/barrios'), mapaListo]);
  estado.formas = formas;
  mapa.resize();
  if (!estado.seleccionado) encuadrar(null, true);
  const simbolo = mapa.getStyle().layers.find((capa) => capa.type === 'symbol')?.id;
  mapa.addSource('barrios', { type: 'geojson', data: formas, promoteId: 'barrio' });
  for (const id of ['ruido', 'delitos', 'riesgo', 'verdes', 'subte', 'escuelas', 'salud']) {
    mapa.addSource(id, { type: 'geojson', data: VACIO });
  }
  const sel = ['boolean', ['feature-state', 'sel'], false];
  const hover = ['boolean', ['feature-state', 'hover'], false];
  mapa.addLayer({
    id: 'barrios-relleno', type: 'fill', source: 'barrios',
    paint: {
      'fill-color': ['interpolate', ['linear'], ['coalesce', ['feature-state', 'r'], 0],
        0, '#F3F4F1', 0.001, '#D3DAD5', 1, '#33434E'],
      'fill-opacity': 0.72,
    },
  }, simbolo);
  const escalaRuido = ['step', ['get', 'tipico'], RUIDO[0][1], ...RUIDO.slice(1).flat()];
  mapa.addLayer({ id: 'ruido', type: 'fill', source: 'ruido',
    paint: { 'fill-color': escalaRuido, 'fill-opacity': ['case', ['<', ['get', 'tipico'], 55], 0.3, 0.55] } }, simbolo);
  mapa.addLayer({ id: 'delitos', type: 'fill', source: 'delitos',
    paint: { 'fill-color': ['step', ['get', 'paso'], DELITOS[0], 1, DELITOS[1], 2, DELITOS[2], 3, DELITOS[3], 4, DELITOS[4]],
      'fill-opacity': ['interpolate', ['linear'], ['get', 'paso'], 0, 0.5, 4, 0.82] } }, simbolo);
  mapa.addLayer({ id: 'riesgo', type: 'fill', source: 'riesgo',
    paint: { 'fill-color': COLOR.riesgo, 'fill-opacity': 0.26 } }, simbolo);
  mapa.addLayer({ id: 'riesgo-borde', type: 'line', source: 'riesgo',
    paint: { 'line-color': COLOR.riesgo, 'line-width': 1 } }, simbolo);
  mapa.addLayer({ id: 'verdes', type: 'fill', source: 'verdes',
    paint: { 'fill-color': COLOR.verdes, 'fill-opacity': 0.5 } }, simbolo);
  mapa.addLayer({ id: 'verdes-borde', type: 'line', source: 'verdes',
    paint: { 'line-color': COLOR.verdes, 'line-width': 0.8 } }, simbolo);
  mapa.addLayer({ id: 'barrios-borde', type: 'line', source: 'barrios',
    paint: {
      'line-color': ['case', sel, '#6A4FB3', '#1E2A32'],
      'line-width': ['case', sel, 3.2, hover, 2.2, 0.7],
      'line-opacity': ['case', sel, 1, hover, 0.9, 0.45],
    } });
  mapa.addLayer({ id: 'escuelas', type: 'circle', source: 'escuelas',
    paint: { 'circle-radius': 4.5, 'circle-color': COLOR.escuela, 'circle-stroke-color': '#FFFFFF', 'circle-stroke-width': 1.2 } });
  mapa.addLayer({ id: 'salud', type: 'circle', source: 'salud',
    paint: { 'circle-radius': ['match', ['get', 'kind'], 'hospital', 7.5, 5.5],
      'circle-color': ['match', ['get', 'kind'], 'hospital', COLOR.hospital, COLOR.cesac],
      'circle-stroke-color': '#FFFFFF', 'circle-stroke-width': 1.5 } });
  mapa.addLayer({ id: 'subte', type: 'circle', source: 'subte',
    paint: { 'circle-radius': 6.5, 'circle-color': ['match', ['get', 'line'], ...Object.entries(SUBTE).flat(), '#55626B'],
      'circle-stroke-color': '#FFFFFF', 'circle-stroke-width': 2 } });

  const puntos = ['subte', 'salud', 'escuelas'];
  const conTexto = [...puntos, 'verdes', 'riesgo', 'ruido', 'delitos'];

  mapa.on('mousemove', (evento) => {
    const barrio = mapa.queryRenderedFeatures(evento.point, { layers: ['barrios-relleno'] })[0];
    marcarHover(barrio ? barrio.id : null, 'mapa');
    const elemento = mapa.queryRenderedFeatures(evento.point, { layers: conTexto })[0];
    const texto = elemento ? textoElemento(elemento) : (barrio && !estado.seleccionado ? textoBarrio(barrio.id) : null);
    mapa.getCanvas().style.cursor = barrio || elemento ? 'pointer' : '';
    if (texto) popup.setLngLat(evento.lngLat).setHTML(esc(texto)).addTo(mapa);
    else popup.remove();
  });
  mapa.on('mouseout', () => { popup.remove(); marcarHover(null, 'mapa'); });
  mapa.on('click', (evento) => {
    const elemento = mapa.queryRenderedFeatures(evento.point, { layers: conTexto })[0];
    if (elemento) {
      popup.setLngLat(evento.lngLat).setHTML(esc(textoElemento(elemento))).addTo(mapa);
      return;
    }
    const barrio = mapa.queryRenderedFeatures(evento.point, { layers: ['barrios-relleno'] })[0];
    if (barrio && barrio.id !== estado.seleccionado) seleccionar(barrio.id);
  });
}

function textoBarrio(nombre) {
  const b = estado.barrios.find((x) => x.barrio === nombre);
  if (!b) return nombre;
  return `${nombre}: ${b.coincidencias} ${plural(b.coincidencias, 'aviso encaja', 'avisos encajan')}`;
}

function textoElemento(f) {
  const p = f.properties;
  if (f.layer.id === 'ruido') {
    return `Nivel exterior típico de ${p.tipico} a ${p.tipico + 5} dBA. El máximo en la celda es de ${p.maximo} a ${p.maximo + 5} dBA.`;
  }
  if (f.layer.id === 'delitos') {
    const tipo = estado.delitos.tipo ? ` de ${estado.delitos.tipo.toLowerCase()}` : '';
    return `${p.hechos} ${plural(p.hechos, 'hecho registrado', 'hechos registrados')}${tipo} en ${mes(estado.delitosDatos.periodo)}.`;
  }
  return `${String(p.tooltip || p.name || '').split(' · ').join('. ')}.`.replace(/\.\.$/, '.');
}

function marcarHover(nombre, origen) {
  if (estado.hover === nombre) return;
  if (estado.hover && mapa.getSource('barrios')) mapa.setFeatureState({ source: 'barrios', id: estado.hover }, { hover: false });
  estado.hover = nombre;
  if (nombre && mapa.getSource('barrios')) mapa.setFeatureState({ source: 'barrios', id: nombre }, { hover: true });
  if (origen === 'mapa') {
    document.querySelectorAll('.fila.resaltada').forEach((fila) => fila.classList.remove('resaltada'));
    if (nombre) document.querySelector(`.fila[data-barrio="${CSS.escape(nombre)}"]`)?.classList.add('resaltada');
  }
}

function pintarCoropletas() {
  if (!mapa.getSource('barrios')) return;
  const maximo = Math.max(1, ...estado.barrios.map((b) => b.coincidencias));
  for (const b of estado.barrios) {
    mapa.setFeatureState({ source: 'barrios', id: b.barrio }, { r: b.coincidencias ? b.coincidencias / maximo : 0 });
  }
  mapa.setPaintProperty('barrios-relleno', 'fill-opacity',
    estado.seleccionado ? ['case', ['boolean', ['feature-state', 'sel'], false], 0, 0.3] : 0.72);
}

function limites(nombre) {
  const feature = estado.formas.features.find((f) => f.properties.barrio === nombre);
  const puntos = feature.geometry.coordinates.flatMap((poligono) => poligono[0]);
  const lons = puntos.map((p) => p[0]);
  const lats = puntos.map((p) => p[1]);
  return [[Math.min(...lons), Math.min(...lats)], [Math.max(...lons), Math.max(...lats)]];
}

function limitesCiudad() {
  const puntos = estado.formas.features.flatMap((f) => f.geometry.coordinates.flatMap((poligono) => poligono[0]));
  const lons = puntos.map((p) => p[0]);
  const lats = puntos.map((p) => p[1]);
  return [[Math.min(...lons), Math.min(...lats)], [Math.max(...lons), Math.max(...lats)]];
}

function encuadrar(nombre, inmediato = false) {
  if (!estado.formas) return;
  const alto = mapa.getContainer().clientHeight;
  const abajo = celular() ? Math.round(alto * 0.44) : 60;
  const arriba = celular() ? 110 : 70;
  const duracion = reducido || inmediato ? 0 : 900;
  const relleno = { top: nombre ? arriba + 60 : arriba, bottom: abajo, left: 40, right: 60 };
  mapa.fitBounds(nombre ? limites(nombre) : limitesCiudad(), { padding: relleno, duration: duracion });
}

/* Capas del barrio elegido */

function claveCapa(clave) {
  return [estado.seleccionado, clave, clave === 'escuelas' ? estado.nivel : '', clave === 'ruido' ? estado.ruido : ''].join('|');
}

async function actualizarCapas() {
  const barrio = estado.seleccionado;
  const fijas = ['subte', 'verdes', 'escuelas', 'salud', 'ruido', 'riesgo'];
  if (!barrio) {
    fijas.concat('delitos').forEach((id) => mapa.getSource(id)?.setData(VACIO));
    renderControles();
    renderLeyenda();
    return;
  }
  const faltan = fijas.filter((c) => estado.capas.has(c) && !estado.capasDatos[claveCapa(c)]);
  try {
    if (faltan.length) {
      const pedido = new URLSearchParams({ barrio, nivel: estado.nivel, ruido: estado.ruido });
      faltan.forEach((c) => pedido.append('capas', c));
      const respuesta = await api(`/api/mapa/capas?${pedido}`);
      if (barrio !== estado.seleccionado) return;
      faltan.forEach((c) => { estado.capasDatos[claveCapa(c)] = respuesta[c]; });
    }
    if (estado.capas.has('delitos')) await cargarDelitos();
  } catch (error) {
    mostrarAvisoMapa(`No se pudieron cargar las capas: ${error.message}`);
  }
  if (barrio !== estado.seleccionado) return;
  for (const c of fijas) mapa.getSource(c)?.setData(estado.capas.has(c) ? estado.capasDatos[claveCapa(c)] || VACIO : VACIO);
  const delitos = estado.capas.has('delitos') && estado.delitosDatos?.disponible ? estado.delitosDatos.celdas : VACIO;
  mapa.getSource('delitos')?.setData(delitos);
  renderControles();
  renderLeyenda();
}

async function cargarDelitos() {
  const pedido = new URLSearchParams({ barrio: estado.seleccionado, modo: estado.modo, operacion: estado.operacion });
  if (estado.delitos.periodo) pedido.set('periodo', estado.delitos.periodo);
  if (estado.delitos.tipo) pedido.set('tipo', estado.delitos.tipo);
  const datos = await api(`/api/delitos?${pedido}`);
  if (datos.disponible) {
    datos.cortes = cortesQuintiles(datos.celdas.features.map((f) => f.properties.hechos));
    for (const f of datos.celdas.features) f.properties.paso = pasoDelito(f.properties.hechos, datos.cortes);
    estado.delitos.periodo = datos.periodo;
  }
  estado.delitosDatos = datos;
}

function mostrarAvisoMapa(texto) {
  $('#mapa-pista').hidden = false;
  $('#mapa-pista').textContent = texto;
}

function renderChips() {
  const contenedor = $('#capas');
  contenedor.hidden = !estado.seleccionado;
  $('#mapa-pista').hidden = Boolean(estado.seleccionado);
  if (!estado.seleccionado) {
    $('#mapa-pista').textContent = 'Elegí un barrio para ver subte, plazas, ruido y más en el mapa.';
    return;
  }
  contenedor.innerHTML = CAPAS.map((c) => `<button class="chip" type="button" data-capa="${c.clave}"
    aria-pressed="${estado.capas.has(c.clave)}">${esc(c.nombre)}</button>`).join('');
}

function renderControles() {
  const partes = [];
  if (estado.seleccionado && estado.capas.has('escuelas')) {
    partes.push(`<label class="control-flotante">Escuelas de nivel
      <select data-control="nivel">${['inicial', 'primario', 'secundario'].map((n) =>
        `<option value="${n}"${n === estado.nivel ? ' selected' : ''}>${n}</option>`).join('')}</select></label>`);
  }
  if (estado.seleccionado && estado.capas.has('ruido')) {
    partes.push(`<div class="control-flotante">Ruido
      <div class="segmentado segmentado-chico" role="radiogroup" aria-label="Momento del día">
        <button type="button" role="radio" data-ruido="diurno" aria-checked="${estado.ruido === 'diurno'}">De día</button>
        <button type="button" role="radio" data-ruido="nocturno" aria-checked="${estado.ruido === 'nocturno'}">De noche</button>
      </div></div>`);
  }
  if (estado.seleccionado && estado.capas.has('delitos') && estado.delitosDatos) {
    const d = estado.delitosDatos;
    if (d.disponible) {
      const tipos = Object.keys(d.tipos).sort();
      partes.push(`<div class="control-flotante">
        <label>Mes <select data-control="periodo">${d.periodos.map((p) =>
          `<option value="${p}"${p === d.periodo ? ' selected' : ''}>${esc(mes(p))}</option>`).join('')}</select></label>
        <label>Tipo <select data-control="tipo"><option value="">Todos</option>${tipos.map((t) =>
          `<option value="${esc(t)}"${t === estado.delitos.tipo ? ' selected' : ''}>${esc(t)}</option>`).join('')}</select></label>
      </div>`);
    } else {
      partes.push(`<p class="control-flotante">${esc(d.motivo)}</p>`);
    }
  }
  $('#capa-controles').innerHTML = partes.join('');
}

function muestra(color, etiqueta) {
  return `<li><span class="chip-muestra" style="background:${color}"></span>${esc(etiqueta)}</li>`;
}

/* Cortes por quintiles de las celdas a la vista, para que cada tono reúna una parte parecida. */
function cortesQuintiles(valores) {
  const orden = [...valores].sort((a, b) => a - b);
  const cortes = [0.2, 0.4, 0.6, 0.8].map((q) => orden[Math.min(orden.length - 1, Math.floor(q * orden.length))]);
  return [...new Set(cortes)].filter((c) => c < orden.at(-1));
}

function pasoDelito(hechos, cortes) {
  const paso = cortes.filter((c) => hechos > c).length;
  return cortes.length >= 4 ? paso : Math.round((paso * 4) / Math.max(1, cortes.length));
}

function rangosDelitos(maximo, cortes) {
  const grupos = new Map();
  for (let n = 1; n <= maximo; n += 1) {
    const paso = pasoDelito(n, cortes);
    if (!grupos.has(paso)) grupos.set(paso, []);
    grupos.get(paso).push(n);
  }
  return [...grupos].map(([paso, ns]) => [DELITOS[paso],
    ns.length === 1 ? `${ns[0]} ${plural(ns[0], 'hecho', 'hechos')}` : `${ns[0]} a ${ns.at(-1)} hechos`]);
}

function renderLeyenda() {
  const leyenda = $('#leyenda');
  if (!estado.seleccionado) {
    const maximo = Math.max(0, ...estado.barrios.map((b) => b.coincidencias));
    leyenda.innerHTML = maximo ? `<h3>Avisos que encajan por barrio</h3>
      <div class="gradiente" style="background:linear-gradient(90deg,#D3DAD5,#33434E)"></div>
      <div class="gradiente-extremos"><span>1</span><span>${maximo}</span></div>` : '';
    return;
  }
  const bloques = [];
  const notas = [];
  for (const c of CAPAS) {
    if (!estado.capas.has(c.clave)) continue;
    let items = [];
    if (c.clave === 'subte') {
      const lineas = [...new Set((estado.capasDatos[claveCapa('subte')]?.features || []).map((f) => f.properties.line))].sort();
      items = lineas.map((l) => muestra(SUBTE[l] || '#55626B', `Línea ${l}`));
    } else if (c.clave === 'verdes') items = [muestra(COLOR.verdes, 'Plaza o parque')];
    else if (c.clave === 'escuelas') items = [muestra(COLOR.escuela, `Escuela de nivel ${estado.nivel}`)];
    else if (c.clave === 'salud') items = [muestra(COLOR.cesac, 'CeSAC'), muestra(COLOR.hospital, 'Hospital')];
    else if (c.clave === 'riesgo') items = [muestra(COLOR.riesgo, 'Área de prevención')];
    else if (c.clave === 'ruido') {
      items = RUIDO.map(([v, color]) => muestra(color, v === 50 ? 'Menos de 55 dBA' : v === 80 ? '80 dBA o más' : `${v} a ${v + 5} dBA`));
    } else if (c.clave === 'delitos') {
      const d = estado.delitosDatos;
      if (!d?.disponible) continue;
      items = d.maximo ? rangosDelitos(d.maximo, d.cortes).map(([color, texto]) => muestra(color, texto)) : [];
    }
    const titulo = c.clave === 'ruido' ? `Ruido ${estado.ruido === 'diurno' ? 'de día' : 'de noche'}` : c.nombre;
    bloques.push(`<h3>${esc(titulo)}</h3>${items.length ? `<ul class="leyenda-items">${items.join('')}</ul>` : ''}`);
    notas.push(`<li><strong>${esc(titulo)}.</strong> ${esc(NOTAS[c.clave])}</li>`);
  }
  leyenda.innerHTML = bloques.length
    ? `<details class="leyenda-caja"${estado.leyendaCerrada ? '' : ' open'}><summary>Leyenda</summary>
      ${bloques.join('')}<details class="leyenda-mas"${estado.leyendaAbierta ? ' open' : ''}><summary>Cómo leer el mapa</summary>
      <ul class="leyenda-notas">${notas.join('')}</ul>
      <button class="boton-texto" type="button" data-fuentes>Ver fuentes</button></details></details>`
    : '';
  leyenda.querySelector('.leyenda-mas')?.addEventListener('toggle', (e) => { estado.leyendaAbierta = e.target.open; });
  leyenda.querySelector('.leyenda-caja')?.addEventListener('toggle', (e) => {
    if (e.target.classList.contains('leyenda-caja')) estado.leyendaCerrada = !e.target.open;
  });
}

/* Carga de datos */

async function cargarEstado() {
  estado.info = await api(`/api/estado?${new URLSearchParams({ modo: estado.modo, operacion: estado.operacion })}`);
}

async function cargarBarrios() {
  const datos = await api(`/api/barrios?${consulta()}`);
  estado.barrios = datos.barrios;
  pintarCoropletas();
}

async function cargarAvisos() {
  if (!estado.seleccionado) return;
  const barrio = estado.seleccionado;
  const datos = await api(`/api/barrios/${encodeURIComponent(barrio)}/avisos?${consulta()}`);
  if (barrio === estado.seleccionado) estado.avisos = datos.avisos;
}

async function seleccionar(nombre) {
  if (estado.seleccionado && mapa.getSource('barrios')) {
    mapa.setFeatureState({ source: 'barrios', id: estado.seleccionado }, { sel: false });
  }
  estado.seleccionado = nombre;
  estado.verTodos = false;
  estado.avisos = [];
  estado.delitosDatos = null;
  popup.remove();
  if (nombre && mapa.getSource('barrios')) mapa.setFeatureState({ source: 'barrios', id: nombre }, { sel: true });
  estado.capas = new Set(nombre ? estado.prefs : []);
  pintarCoropletas();
  encuadrar(nombre);
  renderChips();
  renderPanel();
  $('#contenido').scrollTop = 0;
  if (celular()) plegarPanel(false);
  try {
    await cargarAvisos();
    if (nombre === estado.seleccionado) renderPanel();
  } catch (error) {
    $('#contenido').insertAdjacentHTML('beforeend', `<p class="vacio">No se pudieron cargar los avisos: ${esc(error.message)}</p>`);
  }
  await actualizarCapas();
}

let espera;
function recargar() {
  clearTimeout(espera);
  espera = setTimeout(async () => {
    guardar();
    try {
      await cargarBarrios();
      await cargarAvisos();
      renderPanel();
      renderLeyenda();
    } catch (error) {
      $('#contenido').innerHTML = `<p class="vacio">No se pudieron cargar los barrios: ${esc(error.message)}.
        Revisá que la API esté corriendo con <code>python -m precio_entorno.api</code>.</p>`;
    }
  }, 280);
}

/* Barra de filtros */

function sincronizarControles() {
  document.querySelectorAll('[data-operacion]').forEach((b) => b.setAttribute('aria-checked', b.dataset.operacion === estado.operacion));
  document.querySelectorAll('[data-modo]').forEach((b) => b.setAttribute('aria-checked', b.dataset.modo === estado.modo));
  const alquiler = estado.operacion === 'alquiler';
  $('#moneda').hidden = !alquiler;
  $('#moneda-fija').hidden = alquiler;
  $('#moneda').value = estado.moneda;
  $('#etiqueta-presupuesto').textContent = alquiler ? 'Hasta por mes' : 'Hasta';
  $('#presupuesto').value = numero.format(estado.presupuesto);
  $('#superficie').value = estado.superficie;
  $('#ambientes').value = `${estado.ambientes}${estado.ambientesOMas ? '+' : ''}`;
  $('#nivel').value = estado.nivel;
  $('#franja-demo').hidden = estado.modo !== 'demo';
  $('#preferencias').innerHTML = `<legend hidden>Lo que me importa</legend>${PREFERENCIAS.map((p) => `
    <label><input type="checkbox" value="${p.clave}"${estado.prefs.has(p.clave) ? ' checked' : ''}>${esc(p.nombre)}</label>`).join('')}`;
  $('#nivel-campo').hidden = !estado.prefs.has('escuelas');
  const elegidas = estado.prefs.size;
  $('#abrir-importa').textContent = elegidas ? `Lo que me importa: ${elegidas}` : 'Lo que me importa';
  $('#abrir-importa').classList.toggle('con-eleccion', elegidas > 0);
}

function enteroDe(texto) {
  const valor = parseInt(String(texto).replace(/\D/g, ''), 10);
  return Number.isFinite(valor) && valor > 0 ? valor : null;
}

async function cambiarContexto() {
  sincronizarControles();
  guardar();
  try {
    await cargarEstado();
    await cargarBarrios();
    if (estado.seleccionado) {
      await cargarAvisos();
      estado.delitosDatos = null;
      estado.delitos = { periodo: null, tipo: '' };
      await actualizarCapas();
    }
    renderPanel();
    renderLeyenda();
  } catch (error) {
    $('#contenido').innerHTML = `<p class="vacio">No se pudieron cargar los datos: ${esc(error.message)}</p>`;
  }
}

function plegarPanel(expandir) {
  const panel = $('#panel');
  panel.classList.toggle('expandido', expandir);
  $('#panel-asa').setAttribute('aria-expanded', expandir);
  $('#panel-asa').textContent = expandir ? 'Ver mapa' : 'Ver lista';
}

function conectarEventos() {
  document.querySelectorAll('[data-operacion]').forEach((boton) => boton.addEventListener('click', () => {
    if (estado.operacion === boton.dataset.operacion) return;
    estado.operacion = boton.dataset.operacion;
    estado.moneda = estado.operacion === 'venta' ? 'USD' : 'ARS';
    estado.presupuesto = PRESUPUESTO[`${estado.operacion}-${estado.moneda}`];
    cambiarContexto();
  }));
  document.querySelectorAll('[data-modo]').forEach((boton) => boton.addEventListener('click', () => {
    if (estado.modo === boton.dataset.modo) return;
    estado.modo = boton.dataset.modo;
    cambiarContexto();
  }));
  $('#moneda').addEventListener('change', (e) => {
    estado.moneda = e.target.value;
    estado.presupuesto = PRESUPUESTO[`alquiler-${estado.moneda}`];
    sincronizarControles();
    recargar();
  });
  $('#presupuesto').addEventListener('input', (e) => {
    const valor = enteroDe(e.target.value);
    if (valor) { estado.presupuesto = valor; recargar(); }
  });
  $('#presupuesto').addEventListener('blur', (e) => { e.target.value = numero.format(estado.presupuesto); });
  $('#superficie').addEventListener('input', (e) => {
    const valor = enteroDe(e.target.value);
    if (valor) { estado.superficie = valor; recargar(); }
  });
  $('#superficie').addEventListener('blur', (e) => { e.target.value = estado.superficie; });
  $('#ambientes').addEventListener('change', (e) => {
    estado.ambientes = parseInt(e.target.value, 10);
    estado.ambientesOMas = e.target.value.endsWith('+');
    recargar();
  });
  $('#filtros').addEventListener('submit', (e) => e.preventDefault());

  const importa = $('#importa');
  const abrirImporta = $('#abrir-importa');
  abrirImporta.addEventListener('click', () => {
    importa.hidden = !importa.hidden;
    abrirImporta.setAttribute('aria-expanded', !importa.hidden);
  });
  document.addEventListener('click', (e) => {
    if (!importa.hidden && !e.target.closest('.importa')) {
      importa.hidden = true;
      abrirImporta.setAttribute('aria-expanded', 'false');
    }
  });
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && !importa.hidden) {
      importa.hidden = true;
      abrirImporta.setAttribute('aria-expanded', 'false');
      abrirImporta.focus();
    }
  });
  $('#preferencias').addEventListener('change', (e) => {
    const clave = e.target.value;
    if (e.target.checked) estado.prefs.add(clave); else estado.prefs.delete(clave);
    if (estado.seleccionado) {
      if (e.target.checked) estado.capas.add(clave); else estado.capas.delete(clave);
      renderChips();
      actualizarCapas();
    }
    sincronizarControles();
    guardar();
    renderPanel();
  });
  $('#nivel').addEventListener('change', (e) => { cambiarNivel(e.target.value); });

  $('#contenido').addEventListener('click', async (e) => {
    const fila = e.target.closest('[data-barrio]');
    if (fila) { seleccionar(fila.dataset.barrio); return; }
    if (e.target.closest('#volver')) { seleccionar(null); return; }
    if (e.target.closest('[data-fuentes]')) { abrirFuentes(); return; }
    if (e.target.closest('#crear-alerta')) crearAlerta(e.target.closest('#crear-alerta'));
    if (e.target.closest('#ver-todos')) { estado.verTodos = true; renderFicha(); }
  });
  $('#contenido').addEventListener('mouseover', (e) => {
    const fila = e.target.closest('.fila');
    marcarHover(fila ? fila.dataset.barrio : null, 'lista');
  });
  $('#contenido').addEventListener('mouseleave', () => marcarHover(null, 'lista'));

  $('#capas').addEventListener('click', (e) => {
    const chip = e.target.closest('[data-capa]');
    if (!chip) return;
    const clave = chip.dataset.capa;
    if (estado.capas.has(clave)) estado.capas.delete(clave); else estado.capas.add(clave);
    chip.setAttribute('aria-pressed', estado.capas.has(clave));
    actualizarCapas();
  });
  $('#capa-controles').addEventListener('change', (e) => {
    const control = e.target.dataset.control;
    if (control === 'nivel') cambiarNivel(e.target.value);
    if (control === 'periodo') { estado.delitos.periodo = e.target.value; actualizarCapas(); }
    if (control === 'tipo') { estado.delitos.tipo = e.target.value; actualizarCapas(); }
  });
  $('#capa-controles').addEventListener('click', (e) => {
    const boton = e.target.closest('[data-ruido]');
    if (boton && boton.dataset.ruido !== estado.ruido) { estado.ruido = boton.dataset.ruido; actualizarCapas(); }
  });
  $('#leyenda').addEventListener('click', (e) => { if (e.target.closest('[data-fuentes]')) abrirFuentes(); });

  $('#abrir-alertas').addEventListener('click', abrirAlertas);
  document.querySelectorAll('[data-cerrar]').forEach((b) => b.addEventListener('click', () => b.closest('dialog').close()));
  $('#panel-asa').addEventListener('click', () => plegarPanel(!$('#panel').classList.contains('expandido')));
}

function cambiarNivel(nivel) {
  estado.nivel = nivel;
  guardar();
  sincronizarControles();
  renderPanel();
  actualizarCapas();
}

async function crearAlerta(boton) {
  const salida = $('#estado-alerta');
  boton.disabled = true;
  try {
    const { creada } = await api(`/api/busquedas?${new URLSearchParams({ modo: estado.modo, operacion: estado.operacion })}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ barrio: estado.seleccionado, presupuesto: estado.presupuesto,
        superficie: estado.superficie, ambientes: estado.ambientes, moneda: estado.moneda }),
    });
    salida.className = 'estado ok';
    salida.textContent = creada
      ? 'Alerta creada. Cuando entre un aviso nuevo que encaje, lo vas a ver en Mis alertas.'
      : 'Ya tenías una alerta con estos mismos filtros.';
  } catch (error) {
    salida.className = 'estado error';
    salida.textContent = `No se creó la alerta: ${error.message}`;
  } finally {
    boton.disabled = false;
  }
}

async function abrirAlertas() {
  const dialogo = $('#dialogo-alertas');
  const contenido = $('#alertas-contenido');
  contenido.innerHTML = '<p class="nota">Cargando…</p>';
  dialogo.showModal();
  try {
    const { busquedas, alertas } = await api(`/api/busquedas?${new URLSearchParams({ modo: estado.modo, operacion: estado.operacion })}`);
    const contexto = `${estado.operacion === 'venta' ? 'Compra' : 'Alquiler'} con ${estado.modo === 'demo' ? 'datos de ejemplo' : 'datos reales'}.`;
    if (!busquedas.length) {
      contenido.innerHTML = `<p class="nota">${contexto} Todavía no creaste alertas. Elegí un barrio y tocá Crear alerta.</p>`;
      return;
    }
    contenido.innerHTML = `<p class="nota">${contexto}</p>
      <h3>Alertas creadas</h3>
      <table class="tabla"><thead><tr><th>Barrio</th><th>Hasta</th><th>Desde</th><th>Ambientes</th></tr></thead><tbody>
      ${busquedas.map((b) => `<tr><td>${esc(b.barrio)}</td><td>${dinero(b.presupuesto, b.moneda)}</td>
        <td>${b.superficie} m²</td><td>${b.ambientes}</td></tr>`).join('')}</tbody></table>
      <h3>Avisos nuevos que encajan</h3>
      ${alertas.length ? `<table class="tabla"><thead><tr><th>Barrio</th><th>Precio publicado</th><th>Cubierta</th><th>Amb.</th><th></th></tr></thead><tbody>
      ${alertas.map((a) => `<tr><td>${esc(a.barrio)}</td><td>${dinero(a.precio, a.moneda)}</td><td>${a.superficie} m²</td>
        <td>${a.ambientes}</td><td>${a.enlace ? `<a href="${esc(a.enlace)}" target="_blank" rel="noopener">Ver aviso</a>` : 'Ejemplo'}</td></tr>`).join('')}
      </tbody></table>` : '<p class="nota">Todavía no entró ningún aviso nuevo que encaje. Los avisos que ya estaban cuando creaste la alerta no cuentan.</p>'}`;
  } catch (error) {
    contenido.innerHTML = `<p class="vacio">No se pudieron cargar las alertas: ${esc(error.message)}</p>`;
  }
}

async function abrirFuentes() {
  const dialogo = $('#dialogo-fuentes');
  const contenido = $('#fuentes-contenido');
  contenido.innerHTML = '<p class="nota">Cargando…</p>';
  dialogo.showModal();
  try {
    const { generado, fuentes } = await api('/api/fuentes');
    const catalogo = estado.info?.catalogo;
    contenido.innerHTML = `
      <p class="nota">Las capas se prepararon el ${esc(generado)} con datos abiertos de Buenos Aires Data, bajo licencia CC-BY 2.5 AR. La unidad geográfica es el barrio oficial.</p>
      <table class="tabla"><thead><tr><th>Capa</th><th>Período</th><th>Archivo</th></tr></thead><tbody>
      ${fuentes.map((f) => `<tr><td>${esc(f.titulo)}</td><td>${esc(f.periodo)}</td>
        <td>${f.url ? `<a href="${esc(f.url)}" target="_blank" rel="noopener">${esc(f.archivo)}</a>` : esc(f.archivo)}</td></tr>`).join('')}
      </tbody></table>
      <h3>Avisos y delitos</h3>
      <p class="nota">${estado.modo === 'demo' ? 'En la demo, los avisos y los delitos son ficticios.'
        : `Avisos del catálogo autorizado ${esc(catalogo || 'sin cargar')}, con precios de publicación. Delitos del Mapa del Delito de CABA${estado.info?.delitos ? `, archivo ${esc(estado.info.delitos.archivo)}` : ''}.`}</p>`;
  } catch (error) {
    contenido.innerHTML = `<p class="vacio">No se pudieron cargar las fuentes: ${esc(error.message)}</p>`;
  }
}

async function iniciar() {
  sincronizarControles();
  conectarEventos();
  renderChips();
  $('#contenido').innerHTML = '<p class="nota">Cargando barrios…</p>';
  try {
    await Promise.all([cargarEstado(), cargarBarrios()]);
    renderPanel();
  } catch (error) {
    $('#contenido').innerHTML = `<p class="vacio">No se pudieron cargar los barrios: ${esc(error.message)}.
      Revisá que la API esté corriendo con <code>python -m precio_entorno.api</code>.</p>`;
  }
  try {
    await prepararMapa();
    // Si la persona eligió un barrio mientras el mapa cargaba, se aplica ahora.
    if (estado.seleccionado) {
      mapa.setFeatureState({ source: 'barrios', id: estado.seleccionado }, { sel: true });
      encuadrar(estado.seleccionado, true);
    }
    pintarCoropletas();
    await actualizarCapas();
  } catch (error) {
    mostrarAvisoMapa(`El mapa no se pudo preparar: ${error.message}`);
  }
}

iniciar();
