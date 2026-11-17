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
const CAPAS_MAPA = [...PREFERENCIAS, { clave: 'estacionamiento', nombre: 'Estacionamiento' }];
const CAPAS = [...CAPAS_MAPA, { clave: 'delitos', nombre: 'Delitos registrados' }];
const SUBTE = { A: '#18CCCC', B: '#EB0909', C: '#233AA8', D: '#02A17A', E: '#AE3D97', H: '#FFD600' };
const COLOR = { verdes: '#5E7D4F', riesgo: '#1E88E5', escuela: '#1E2A32', cesac: '#00897B', hospital: '#795548',
  aviso: '#6A4FB3', estacionamiento: '#1671A3' };
const RUIDO = [[50, '#FFFFCC'], [55, '#FFEDA0'], [60, '#FED976'], [65, '#FEB24C'], [70, '#FD8D3C'], [75, '#F03B20'], [80, '#BD0026']];
const DELITOS = ['#D3DBE3', '#A9B8C8', '#7E93AB', '#55708E', '#2E4560'];
const ESTILO = 'https://basemaps.cartocdn.com/gl/positron-gl-style/style.json';
const NOTA_AVISOS = 'Punto que publica la fuente, sin precisión declarada: puede marcar el edificio o una referencia cercana. '
  + 'Hueco si cae a entre 150 y 500 m del barrio del aviso. Más lejos, no se dibuja. Un punto más grande reúne varios avisos.';
const NOTAS = {
  subte: 'Indican conectividad, no tiempos de viaje.',
  verdes: 'Plazas, parques, jardines y paseos. No incluye canteros ni plazoletas.',
  escuelas: 'Estar cerca no asegura una vacante. Consultá cada escuela.',
  salud: 'Estar cerca no asegura turnos.',
  ruido: 'Nivel exterior típico por celda de 100 m, medido sobre todo en calles. No describe el interior de un departamento.',
  riesgo: 'Áreas de prevención publicadas en 2020. Si una dirección cae dentro, conviene preguntarlo en la visita.',
  estacionamiento: 'Inventario oficial publicado en 2021, sin fecha de relevamiento informada. Confirmá que el garaje siga funcionando y consultá cupos y abonos mensuales.',
  delitos: 'Hechos registrados por celda de 200 m. Más circulación puede concentrar más eventos y existe subregistro. No equivalen a la probabilidad individual de victimización.',
};
/* Explorador de necesidades (docs/plan-explorador-necesidades.md). Apagado por defecto: se prueba con
   ?explorador=1. Cada necesidad sugiere capas y columnas; no filtra avisos ni arma puntajes. */
const EXPLORADOR = (() => {
  try { return new URLSearchParams(window.location?.search || '').get('explorador') === '1'; } catch { return false; }
})();
const NECESIDADES = [
  { clave: 'sin_auto', nombre: 'Me muevo sin auto', descripcion: 'Subte cercano y líneas de colectivo del barrio.',
    capas: ['subte'], columnas: ['subte'],
    advertencias: ['Las líneas de colectivo salen de recorridos publicados en 2019: confirmá el recorrido vigente.'] },
  { clave: 'familia', nombre: 'Escuelas y salud cerca', descripcion: 'Escuelas del nivel elegido, centros de salud y plazas.',
    capas: ['escuelas', 'salud', 'verdes'],
    columnas: ['escuela', 'cesac', 'hospital', 'plaza', 'ambientes', 'superficie', 'patio', 'balcon'], advertencias: [] },
  { clave: 'teletrabajo', nombre: 'Trabajo desde casa', descripcion: 'Ruido exterior de día, ambientes, luz y contrafrente.',
    capas: ['ruido'], columnas: ['ruido_diurno', 'ambientes', 'superficie', 'luminoso', 'contrafrente'], advertencias: [] },
  { clave: 'costo_mensual', nombre: 'Quiero ver el costo mensual', descripcion: 'Precio publicado, expensas y cocheras.',
    capas: [], columnas: ['precio', 'expensas', 'cocheras'],
    advertencias: ['Los importes se suman por moneda, sin convertir. Si el aviso no informa las expensas, se indica.'] },
];
// Capas con distancia por aviso en /api/barrios/{barrio}/avisos (precio_entorno/cercania.py).
const CAPAS_CERCANIA = ['subte', 'escuelas', 'salud', 'verdes', 'ruido'];

/* Combina las necesidades elegidas con las decisiones manuales. La elección manual gana: una capa apagada a mano
   no vuelve aunque una necesidad la sugiera. Devuelve capas en el orden del mapa, sin duplicados. */
function resolverNecesidades(seleccion, manual = { encendidas: new Set(), apagadas: new Set() }) {
  const elegidas = NECESIDADES.filter((n) => seleccion.has(n.clave));
  const origen = {};
  for (const n of elegidas) for (const c of n.capas) (origen[c] ||= []).push(n.clave);
  for (const c of manual.encendidas) (origen[c] ||= []).push('manual');
  const capas = CAPAS.map((c) => c.clave).filter((c) => origen[c] && !manual.apagadas.has(c));
  return {
    capas,
    columnas: [...new Set(elegidas.flatMap((n) => n.columnas))],
    cercania: capas.filter((c) => CAPAS_CERCANIA.includes(c)),
    advertencias: [...new Set([...capas.map((c) => NOTAS[c]), ...elegidas.flatMap((n) => n.advertencias)].filter(Boolean))],
    origen: Object.fromEntries(capas.map((c) => [c, origen[c]])),
  };
}

function explorador() {
  return resolverNecesidades(estado.necesidades, { encendidas: estado.prefs, apagadas: estado.apagadas });
}

const metrosTexto = (m) => (m < 1000 ? `${numero.format(m)} m` : `${decimal.format(m / 1000)} km`);
// Columnas de distancia de la tabla de avisos: la capa tiene que estar prendida para que la API la calcule.
const COLUMNAS_DISTANCIA = {
  subte: { capa: 'subte', titulo: () => 'Subte', valor: (c) => c.subte,
    texto: (v) => `<span title="Estación ${esc(v.estacion)}">${metrosTexto(v.m)} · ${esc(v.linea)}</span>` },
  escuela: { capa: 'escuelas', titulo: () => `Escuela (${estado.nivel})`, valor: (c) => c.escuela },
  cesac: { capa: 'salud', titulo: () => 'CeSAC', valor: (c) => c.cesac },
  hospital: { capa: 'salud', titulo: () => 'Hospital', valor: (c) => c.hospital },
  plaza: { capa: 'verdes', titulo: () => 'Plaza', valor: (c) => c.plaza },
  ruido_diurno: { capa: 'ruido', titulo: () => 'Ruido de día', valor: (c) => c.ruido_diurno,
    texto: (v) => (v.dba == null ? 'Sin celda relevada' : `${v.dba} dBA`) },
};
const RASGOS_TEXTO = { patio: 'patio', balcon: 'balcón', luminoso: 'luminoso', contrafrente: 'contrafrente' };

function celdaDistancia(def, aviso) {
  const v = aviso.cercania && def.valor(aviso.cercania);
  if (!v || (!('dba' in v) && v.m == null)) return '—';
  const texto = def.texto ? def.texto(v) : metrosTexto(v.m);
  return aviso.ubicacion === 'aproximada' ? `${texto} <span class="fuente">aprox.</span>` : texto;
}

function celdaRasgos(claves, aviso) {
  if (claves.every((k) => aviso.rasgos?.[k] == null)) return '<span class="fuente">Sin texto</span>';
  const menciona = claves.filter((k) => aviso.rasgos[k] === 1).map((k) => RASGOS_TEXTO[k]);
  return menciona.length ? esc(enumerar(menciona)) : '<span class="fuente">No los menciona</span>';
}

function porMes(aviso) {
  if (aviso.expensas == null) return `${dinero(aviso.precio, aviso.moneda)} <span class="fuente">+ expensas sin informar</span>`;
  if (aviso.moneda === 'ARS') return dinero(aviso.precio + aviso.expensas, 'ARS');
  return `${dinero(aviso.precio, aviso.moneda)} + ${dinero(aviso.expensas, 'ARS')}`;
}

// Columnas extra de la tabla según las necesidades: [{ titulo, celda(aviso) }].
function columnasExplorador() {
  if (!EXPLORADOR || !estado.necesidades.size) return [];
  const { columnas, capas } = explorador();
  const extra = Object.entries(COLUMNAS_DISTANCIA)
    .filter(([clave, def]) => columnas.includes(clave) && capas.includes(def.capa))
    .map(([, def]) => ({ titulo: def.titulo(), celda: (a) => celdaDistancia(def, a) }));
  const rasgos = Object.keys(RASGOS_TEXTO).filter((k) => columnas.includes(k));
  if (rasgos.length) extra.push({ titulo: 'El texto menciona', celda: (a) => celdaRasgos(rasgos, a) });
  if (columnas.includes('expensas')) {
    extra.push(estado.operacion === 'alquiler'
      ? { titulo: 'Por mes', celda: porMes }
      : { titulo: 'Expensas', celda: (a) => (a.expensas == null ? '<span class="fuente">No informadas</span>' : dinero(a.expensas, 'ARS')) });
  }
  return extra;
}

function renderSegunNecesidades(b) {
  if (!EXPLORADOR || !estado.necesidades.size) return '';
  const r = explorador();
  const nombres = NECESIDADES.filter((n) => estado.necesidades.has(n.clave)).map((n) => n.nombre);
  const nombreCapa = (c) => CAPAS.find((x) => x.clave === c)?.nombre || c;
  const origen = (c) => (r.origen[c].includes('manual') ? 'Elegida por vos'
    : `Sugerida por «${r.origen[c].map((k) => NECESIDADES.find((n) => n.clave === k).nombre).join('» y «')}»`);
  const filas = r.capas.filter((c) => c !== 'delitos').map((c) => `<dt>${esc(nombreCapa(c))}</dt><dd>${esc(origen(c))}</dd>`);
  const colectivos = estado.necesidades.has('sin_auto') && b.entorno?.colectivos?.length
    ? `<dt>Colectivos</dt><dd>${b.entorno.colectivos.length} líneas pasan por el barrio, según recorridos de 2019</dd>` : '';
  const conCercania = estado.avisos.filter((a) => a.cercania).length;
  const sinUbicacion = estado.avisos.filter((a) => !a.ubicacion).length;
  const distancias = r.cercania.length && estado.avisos.length && estado.cercaniaInfo
    ? `<p class="fuente">${conCercania} de ${estado.avisos.length} ${plural(estado.avisos.length, 'aviso tiene', 'avisos tienen')} distancias en la tabla.
        ${sinUbicacion ? `${sinUbicacion} sin ubicación publicada ${plural(sinUbicacion, 'queda', 'quedan')} sin distancia.` : ''}
        ${esc(estado.cercaniaInfo.metodo || '')}</p>` : '';
  return `<section class="segun" aria-labelledby="titulo-segun">
      <h2 id="titulo-segun">Según lo que elegiste</h2>
      <p class="fuente">${esc(enumerar(nombres))}. <button class="boton-texto" type="button" data-abrir-importa>Cambiar</button></p>
      ${filas.length || colectivos ? `<dl class="hechos">${filas.join('')}${colectivos}</dl>` : ''}
      ${distancias}
      ${r.advertencias.length ? `<ul class="segun-avisos">${r.advertencias.map((a) => `<li>${esc(a)}</li>`).join('')}</ul>` : ''}
    </section>`;
}

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

/* «Dónde comer»: datos de Google consultados a pedido. No se guardan ni se dibujan en el mapa. */
const TIPOS_LUGAR = [['restaurantes', 'Restaurantes'], ['cafes', 'Cafés'], ['bares', 'Bares']];
const MIN_RESENAS = 200;
const MIN_RESENAS_BAJO = 50;
const LUGARES_VISIBLES = 5;

function lugaresIniciales(tipo) {
  return { tipo, fase: 'inicial', datos: null, minResenas: MIN_RESENAS, todos: false, pedido: 0, mensaje: '' };
}

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
  necesidades: new Set(EXPLORADOR ? guardado.necesidades || [] : []),
  apagadas: new Set(EXPLORADOR ? guardado.apagadas || [] : []),
  nivel: guardado.nivel || 'primario',
  ruido: 'diurno',
  delitos: { anio: '', tipo: 'todos', franja: 'todas', radio: '500', inmueble: '' },
  pedidoDelitos: 0,
  info: null,
  barrios: [],
  formas: null,
  seleccionado: null,
  avisos: [],
  cercaniaInfo: null,
  capas: new Set(),
  capasDatos: {},
  delitosDatos: null,
  hover: null,
  leyendaCerrada: window.matchMedia('(max-width: 820px)').matches,
  leyendaAbierta: false,
  lugares: lugaresIniciales('restaurantes'),
  parecidos: { barrio: null, datos: null, error: '' },
};

function guardar() {
  const { modo, operacion, moneda, presupuesto, superficie, ambientes, nivel } = estado;
  try {
    localStorage.setItem('precio-entorno-filtros', JSON.stringify(
      { modo, operacion, moneda, presupuesto, superficie, ambientes, ambientesOMas: estado.ambientesOMas, nivel, prefs: [...estado.prefs],
        ...(EXPLORADOR ? { necesidades: [...estado.necesidades], apagadas: [...estado.apagadas] } : {}) }));
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
  const elegidas = EXPLORADOR ? new Set(explorador().capas) : estado.prefs;
  const partes = PREFERENCIAS.filter((p) => elegidas.has(p.clave)).map((p) => datos[p.clave]);
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
      ${prensaFila(b.barrio)}
    </button></li>`).join('');
  const compactos = sin.map((b) => `<li><button type="button" data-barrio="${esc(b.barrio)}">${esc(b.barrio)} · ${b.avisos}</button></li>`).join('');
  $('#contenido').innerHTML = `
    <h1 class="titulo-lista">${titulo}</h1>
    <p class="nota">${nota}</p>
    ${renderRadarLista()}
    ${con.length ? `<ul class="barrios">${filas}</ul>` : ''}
    ${sin.length ? `<details class="sin-coincidencias"${con.length ? '' : ' open'}>
      <summary>${sin.length} ${plural(sin.length, 'barrio', 'barrios')} sin avisos que encajen</summary>
      <ul class="lista-compacta">${compactos}</ul></details>` : ''}`;
}

/* Panel: ficha del barrio */

const lugaresOsm = (g) => g.restaurantes + g.cafes + g.bares;
const densidadOsm = (e) => (e.area_ha ? (lugaresOsm(e.gastronomia) / e.area_ha) * 100 : null);

function textoGastronomia(e) {
  const g = e.gastronomia;
  const valores = estado.barrios.map((b) => (b.entorno?.gastronomia ? densidadOsm(b.entorno) : null))
    .filter((v) => v != null).sort((a, b) => a - b);
  const medio = Math.floor(valores.length / 2);
  const mediana = valores.length ? (valores.length % 2 ? valores[medio] : (valores[medio - 1] + valores[medio]) / 2) : null;
  const densidad = densidadOsm(e);
  return `${numero.format(lugaresOsm(g))} registrados en OpenStreetMap: ${g.restaurantes} ${plural(g.restaurantes, 'restaurante', 'restaurantes')}, `
    + `${g.cafes} ${plural(g.cafes, 'café', 'cafés')} y ${g.bares} ${plural(g.bares, 'bar', 'bares')}`
    + (densidad == null ? '' : `. ${numero.format(Math.round(densidad))} cada 100 ha`)
    + (mediana == null ? '' : ` (barrio mediano: ${numero.format(Math.round(mediana))})`);
}

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
      ...(e.gastronomia ? [['Cafés, bares y restaurantes', textoGastronomia(e)]] : []),
      [`Escuelas de nivel ${estado.nivel}`, `${total}, de las que ${escuelas.Estatal || 0} son de gestión estatal`],
      ['Salud', `${e.cesac} CeSAC y ${e.hospitales} ${plural(e.hospitales, 'hospital', 'hospitales')}`],
      ['Ruido de día', dia == null ? 'Sin cobertura suficiente' : `70 dBA o más en el ${dia} % de las celdas relevadas`],
      ['Ruido de noche', noche == null ? 'Sin cobertura suficiente' : `65 dBA o más en el ${noche} % de las celdas relevadas`],
      ['Riesgo hídrico', `${porcentaje(e.riesgo_hidrico)} % de la superficie en área de prevención`],
    );
  }
  const alquiler = estado.operacion === 'alquiler';
  const visibles = estado.verTodos ? estado.avisos : estado.avisos.slice(0, 25);
  const extra = columnasExplorador();
  const filas = visibles.map((a) => `<tr>
      <td>${dinero(a.precio, a.moneda)}</td>
      <td>${a.superficie} m²</td>
      <td>${a.ambientes}</td>
      <td>${a.cocheras == null ? 'No informada' : a.cocheras === 0 ? 'Sin cochera' : a.cocheras}</td>
      ${alquiler ? `<td>${a.expensas == null ? '—' : dinero(a.expensas, 'ARS')}</td>` : ''}
      ${extra.map((c) => `<td>${c.celda(a)}</td>`).join('')}
      <td>${a.enlace ? `<a href="${esc(a.enlace)}" target="_blank" rel="noopener">Ver aviso</a>` : 'Ejemplo'}</td>
      <td>${a.pin_utilizable ? `<button class="boton-texto" type="button" data-inmueble="${esc(a.id)}">${estado.delitos.inmueble === a.id ? 'Entorno elegido' : 'Ver registros cerca'}</button>`
        : a.ubicacion ? `<button class="boton-texto" type="button" data-ubicar="${esc(a.id)}" title="Ver en el mapa">Ubicar</button>`
          : '<span class="fuente">Sin ubicación</span>'}</td>
    </tr>`).join('');
  const ubicados = estado.avisos.filter((a) => a.ubicacion).length;
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
        : `${estado.modo === 'real' ? `<div class="alerta-mail">
            <label class="campo campo-mail"><span class="campo-etiqueta">Mail</span>
              <input type="email" id="mail-alerta" autocomplete="email" inputmode="email" maxlength="254"
                placeholder="Opcional, para recibir avisos nuevos"></label>
            <p class="fuente">Si dejás tu mail, lo usamos solo para mandarte los avisos nuevos de esta búsqueda.
              Cada correo trae un enlace para darte de baja.</p>
          </div>` : ''}
          <button class="boton-primario" type="button" id="crear-alerta">Crear alerta para ${esc(b.barrio)}</button>`}
      <p class="estado" id="estado-alerta" role="status"></p>
      ${ficha.length ? `<h2>Entorno</h2>
        <dl class="hechos">${ficha.map(([k, v]) => `<dt>${esc(k)}</dt><dd>${esc(v)}</dd>`).join('')}</dl>
        <p class="fuente">Datos abiertos de Buenos Aires Data, por barrio oficial. Describen el barrio, no un departamento.
          ${e?.gastronomia ? `Cafés, bares y restaurantes: © colaboradores de OpenStreetMap${e.gastronomia.captura ? `, captura del ${fechaCorta(e.gastronomia.captura)}` : ''}. La cobertura depende de quién mapea cada zona.` : ''}
          <button class="boton-texto" type="button" data-fuentes>Ver fuentes</button></p>` : ''}
      ${renderSegunNecesidades(b)}
      ${renderParecidos(b.barrio)}
      ${renderLugares(b.barrio)}
      ${estado.modo === 'real' ? `<h2>Localizar estacionamientos</h2>
        <p class="fuente">Inventario oficial publicado en 2021, sin fecha de relevamiento informada. Confirmá funcionamiento, horarios, cupos y tarifas con el lugar.</p>
        <form id="buscar-estacionamientos">
          ${camposOrigen()}
          <button type="submit" class="boton-texto">Localizar estacionamientos</button>
        </form><div id="resultado-estacionamientos" role="status"></div>
        <h2>Cocheras en alquiler mensual</h2>
        <form id="buscar-cocheras">
          <label>Moneda <select name="moneda"><option>ARS</option><option>USD</option></select></label>
          <label>Hasta <input name="presupuesto" type="number" min="1" value="250000" required></label>
          ${camposOrigen()}
          <button type="submit" class="boton-texto">Buscar cocheras</button>
        </form><div id="resultado-cocheras" role="status"></div>
        <p class="fuente">Con «Mi ubicación actual», el navegador pide permiso al buscar. La ubicación se usa solo para esa consulta y no se guarda.</p>` : ''}
      ${b.coincidencias ? `<h2>Avisos que encajan</h2>
        ${extra.length ? `<p class="fuente">Deslizá la tabla hacia la derecha para ver ${enumerar(extra.map((c) => `«${c.titulo}»`))}.</p>` : ''}
        <table class="avisos">
          <thead><tr><th>Precio publicado</th><th>Cubierta</th><th>Amb.</th><th>Cocheras</th>${alquiler ? '<th>Expensas</th>' : ''}${extra.map((c) => `<th>${esc(c.titulo)}</th>`).join('')}<th><span hidden>Enlace</span></th><th>Mapa</th></tr></thead>
          <tbody>${filas}</tbody>
        </table>
        ${estado.avisos.length > visibles.length ? `<p class="fuente">Se muestran los ${visibles.length} más baratos de ${estado.avisos.length}. <button class="boton-texto" type="button" id="ver-todos">Ver todos</button></p>` : ''}
        <p class="fuente">${estado.modo === 'demo' ? 'Avisos ficticios de ejemplo.' : 'Precios de publicación del catálogo autorizado, no tasaciones ni precios de cierre.'}
          ${estado.modo === 'real' ? `${ubicados} de ${estado.avisos.length} ${plural(estado.avisos.length, 'aviso tiene', 'avisos tienen')} un punto en el mapa, publicado por la fuente sin precisión declarada.` : ''}</p>` : ''}
      ${renderAnalisisDelitos()}
      ${renderRadarFicha(b.barrio)}
    </article>`;
}

// Origen compartido por las búsquedas de estacionamientos y cocheras.
function camposOrigen() {
  return `<label>Buscar desde <select name="origen"><option value="barrio">Todo el barrio</option>
      <option value="actual">Mi ubicación actual</option>
      <option value="mapa">El centro del mapa</option>
      ${estado.avisos.filter((a) => a.ubicacion).map((a) => `<option value="${esc(a.id)}">Aviso ${esc(a.id)}</option>`).join('')}
    </select></label>
    <label>Radio para búsqueda cercana <select name="radio"><option value="300">300 m</option><option value="500" selected>500 m</option><option value="1000">1 km</option></select></label>`;
}

function enCaba(lat, lon) {
  return lat >= -34.73 && lat <= -34.52 && lon >= -58.54 && lon <= -58.32;
}

function ubicacionActual() {
  if (!navigator.geolocation || !window.isSecureContext) {
    return Promise.reject(new Error('Este navegador no permite consultar la ubicación en esta página. Elegí el centro del mapa.'));
  }
  return new Promise((resolve, reject) => navigator.geolocation.getCurrentPosition(
    (p) => resolve({ lat: p.coords.latitude, lon: p.coords.longitude, precision: Math.round(p.coords.accuracy) }),
    (error) => reject(new Error(error.code === 1 ? 'No se autorizó el acceso a la ubicación. Podés usar el centro del mapa.'
      : error.code === 3 ? 'La consulta de ubicación tardó demasiado. Intentá otra vez o usá el mapa.'
        : 'No se pudo obtener tu ubicación. Podés usar el centro del mapa.')),
    { enableHighAccuracy: true, timeout: 10000, maximumAge: 60000 }));
}

// Devuelve null para todo el barrio, o el punto de partida de una búsqueda cercana.
async function puntoDeBusqueda(origen, output) {
  if (origen === 'barrio') return null;
  let punto;
  if (origen === 'actual') {
    output.textContent = 'Esperando tu ubicación…';
    punto = await ubicacionActual();
    if (!enCaba(punto.lat, punto.lon)) {
      throw new Error('Tu ubicación está fuera del área de consulta de CABA. Mové el mapa hasta la zona que querés explorar y elegí el centro del mapa.');
    }
    marcarMiUbicacion(punto);
  } else if (origen === 'mapa') {
    const centro = mapa.getCenter();
    punto = { lat: centro.lat, lon: centro.lng };
  } else {
    const aviso = estado.avisos.find((a) => a.id === origen);
    punto = aviso && { lat: aviso.lat, lon: aviso.lon, aviso };
  }
  if (!punto) throw new Error('Elegí una ubicación disponible.');
  if (!enCaba(punto.lat, punto.lon)) {
    throw new Error('La ubicación está fuera del área de consulta de CABA. Mové el mapa hasta la zona que querés explorar.');
  }
  return punto;
}

function notaPrecision(punto, radio) {
  if (punto?.precision == null) return '';
  return `<p class="fuente">Precisión informada por el dispositivo: aproximadamente ${punto.precision} m.${
    punto.precision > radio ? ' Supera el radio elegido; usá el centro del mapa para precisar la búsqueda.' : ''}</p>`;
}

function costoMensual(vivienda, cochera) {
  const totales = {};
  const componentes = [
    [vivienda.precio, vivienda.moneda],
    [cochera.precio, cochera.moneda],
    [vivienda.expensas, 'ARS'],
    [cochera.expensas, cochera.moneda_expensas],
  ];
  for (const [importe, moneda] of componentes) {
    if (importe != null) totales[moneda] = (totales[moneda] || 0) + importe;
  }
  const pendientes = [];
  if (vivienda.expensas == null) pendientes.push('expensas de la vivienda');
  if (cochera.expensas == null) pendientes.push('expensas de la cochera');
  const total = Object.entries(totales).map(([moneda, importe]) => dinero(importe, moneda)).join(' + ');
  return `<p>Vivienda y cochera por mes · ${pendientes.length ? 'Subtotal conocido' : 'Alquileres y expensas'} ${total}.
    ${pendientes.length ? 'Falta informar ' + pendientes.join(' y ') + '.' : ''}</p>`;
}

function textoPrecioParecido(p, barrio) {
  if (!p.coincidencias) return 'Ningún aviso encaja con tu búsqueda';
  const base = `${p.coincidencias} ${plural(p.coincidencias, 'aviso encaja', 'avisos encajan')}, mediana ${dinero(p.mediana, estado.moneda)}`;
  if (p.diferencia_mediana == null) return base;
  if (p.diferencia_mediana === 0) return `${base}, igual que en ${barrio}`;
  return `${base}, ${dinero(Math.abs(p.diferencia_mediana), estado.moneda)} ${p.diferencia_mediana < 0 ? 'menos' : 'más'} que en ${barrio}`;
}

function renderParecidos(barrio) {
  const p = estado.parecidos;
  if (p.barrio !== barrio || (!p.datos && !p.error)) return '';
  if (p.error) return `<section class="parecidos"><h2>Barrios parecidos</h2><p class="fuente">${esc(p.error)}</p></section>`;
  if (!p.datos.length) return '';
  const elegidas = PREFERENCIAS.filter((x) => estado.prefs.has(x.clave)).map((x) => x.nombre.toLowerCase());
  const items = p.datos.map((x) => `<li class="parecido">
      <button type="button" class="parecido-boton" data-barrio="${esc(x.barrio)}">
        <span class="parecido-nombre">${esc(x.barrio)}</span>
        <span class="parecido-precio">${esc(textoPrecioParecido(x, barrio))}</span>
      </button>
      <ul class="parecido-motivos">
        ${x.parecido_en.map((m) => `<li><span class="motivo-marca" aria-hidden="true">=</span>${esc(m.texto)}</li>`).join('')}
        ${x.diferencias.map((m) => `<li class="motivo-difiere"><span class="motivo-marca" aria-hidden="true">≠</span>${esc(m.texto)}</li>`).join('')}
      </ul>
    </li>`).join('');
  return `<section class="parecidos" aria-labelledby="titulo-parecidos">
      <h2 id="titulo-parecidos">Barrios parecidos</h2>
      <p class="fuente">Por su entorno, no por su precio.${elegidas.length ? ` Pesa doble lo que marcaste: ${esc(enumerar(elegidas))}.` : ''}
        Primero, los que tienen avisos que encajan con tu búsqueda.</p>
      <ol class="lista-parecidos">${items}</ol>
    </section>`;
}

async function cargarParecidos() {
  const barrio = estado.seleccionado;
  if (!barrio) return;
  const params = consulta({ nivel: estado.nivel });
  estado.prefs.forEach((clave) => params.append('prefs', clave));
  try {
    const datos = await api(`/api/barrios/${encodeURIComponent(barrio)}/parecidos?${params}`);
    if (barrio !== estado.seleccionado) return;
    estado.parecidos = { barrio, datos: datos.parecidos, error: '' };
  } catch (error) {
    if (barrio !== estado.seleccionado) return;
    estado.parecidos = { barrio, datos: null, error: `No se pudieron calcular los barrios parecidos: ${error.message}` };
  }
  renderPanel();
}

function renderLugares(barrio) {
  if (estado.modo !== 'real' || !estado.info?.lugares) return '';
  const l = estado.lugares;
  const tipos = TIPOS_LUGAR.map(([clave, nombre]) => `<button type="button" class="chip-lugar" data-lugares-tipo="${clave}"
      aria-pressed="${l.tipo === clave}">${nombre}</button>`).join('');
  const nombreTipo = TIPOS_LUGAR.find(([clave]) => clave === l.tipo)[1].toLowerCase();
  let cuerpo;
  if (l.fase === 'inicial') {
    cuerpo = `<p class="fuente">Se consulta a Google solo cuando lo pedís.</p>
      <button class="boton-secundario" type="button" id="cargar-lugares">Ver los más valorados en Google</button>`;
  } else if (l.fase === 'cargando') {
    cuerpo = '<p class="fuente" role="status">Consultando a Google…</p>';
  } else if (l.fase === 'error') {
    cuerpo = `<p>${esc(l.mensaje)}</p>
      <p class="fuente">Mientras tanto, las capas del mapa siguen disponibles.</p>`;
  } else {
    const filtrados = l.datos.lugares.filter((x) => x.resenas >= l.minResenas);
    const visibles = l.todos ? filtrados : filtrados.slice(0, LUGARES_VISIBLES);
    const filas = visibles.map((x) => `<li class="lugar">
        <span class="lugar-nombre">${esc(x.nombre)}</span>
        <span class="lugar-datos">★ ${decimal.format(x.nota)}, ${numero.format(x.resenas)} ${plural(x.resenas, 'reseña', 'reseñas')}${x.precio ? `, ${esc(x.precio)}` : ''}</span>
        ${x.enlace ? `<a class="lugar-enlace" href="${esc(x.enlace)}" target="_blank" rel="noopener">Abrir en Maps</a>` : ''}
      </li>`).join('');
    cuerpo = filtrados.length
      ? `<ol class="lugares">${filas}</ol>
        ${filtrados.length > visibles.length ? `<button class="boton-texto" type="button" id="lugares-todos">Ver los ${filtrados.length} más valorados</button>` : ''}`
      : `<p>Google no devolvió ${nombreTipo} con al menos ${numero.format(l.minResenas)} reseñas en ${esc(barrio)}.</p>
        ${l.minResenas > MIN_RESENAS_BAJO ? `<button class="boton-texto" type="button" id="lugares-menos">Mostrar los que tienen al menos ${MIN_RESENAS_BAJO}</button>` : ''}`;
    cuerpo += `<p class="fuente">Los más valorados entre los ${l.datos.en_barrio} lugares de ${esc(barrio)} que devolvió Google,
      con al menos ${numero.format(l.minResenas)} reseñas. Calificaciones de usuarios de Google, no de Precio y Entorno.
      Se consultan al momento y no se guardan.</p>`;
  }
  return `<section class="lugares-google" aria-labelledby="titulo-lugares">
      <div class="lugares-encabezado"><h2 id="titulo-lugares">Dónde comer</h2><span class="atribucion-google">Google Maps</span></div>
      <div class="chips-lugar" role="group" aria-label="Tipo de lugar">${tipos}</div>
      ${cuerpo}
    </section>`;
}

async function cargarLugares() {
  const barrio = estado.seleccionado;
  if (!barrio) return;
  const l = estado.lugares;
  const pedido = l.pedido + 1;
  Object.assign(l, { fase: 'cargando', pedido, todos: false, minResenas: MIN_RESENAS });
  renderFicha();
  try {
    const datos = await api(`/api/barrios/${encodeURIComponent(barrio)}/lugares?${new URLSearchParams({ tipo: l.tipo, modo: estado.modo })}`);
    if (barrio !== estado.seleccionado || pedido !== estado.lugares.pedido) return;
    if (datos.disponible) Object.assign(l, { fase: 'listo', datos });
    else Object.assign(l, { fase: 'error', mensaje: datos.motivo === 'cupo' ? 'La consulta a Google no está disponible por este mes.' : datos.mensaje });
  } catch (error) {
    if (barrio !== estado.seleccionado || pedido !== estado.lugares.pedido) return;
    Object.assign(l, { fase: 'error', mensaje: `No se pudo consultar a Google: ${error.message}` });
  }
  renderFicha();
}

function renderAnalisisDelitos() {
  if (!estado.capas.has('delitos')) return '';
  const d = estado.delitosDatos;
  if (!d?.disponible) return `<section class="analisis-delitos" aria-live="polite"><h2>Registros y contexto</h2><p class="nota">${esc(d?.motivo || 'Cargando registros…')}</p></section>`;
  const filas = d.resumen_radios.map((r) => `<tr${r.radio_m === Number(estado.delitos.radio) ? ' class="radio-elegido"' : ''}>
    <th scope="row">${r.anio} · ${numero.format(r.radio_m)} m · ${r.tipo === 'robo' ? 'Robo' : 'Hurto'}</th>
    <td>${numero.format(r.diurno)}</td><td>${numero.format(r.nocturno)}</td><td>${numero.format(r.sin_dato)}</td><td>${numero.format(r.total)}</td></tr>`).join('');
  const series = d.resumen_radios.filter((r) => r.radio_m === Number(estado.delitos.radio)
    && (estado.delitos.tipo === 'todos' || r.tipo === estado.delitos.tipo));
  const valor = (r) => estado.delitos.franja === 'todas' ? r.total : r[estado.delitos.franja];
  const maximo = Math.max(1, ...series.map(valor));
  const barras = series.map((r) => `<div class="serie-registros"><span>${r.anio} · ${r.tipo === 'robo' ? 'Robo' : 'Hurto'}</span>
    <div class="barra-registros" aria-hidden="true"><i style="width:${valor(r) / maximo * 100}%"></i></div><strong>${numero.format(valor(r))}</strong></div>`).join('');
  return `<section class="analisis-delitos" aria-live="polite"><h2>Registros y contexto</h2>
    <p class="nota"><strong>Los registros no indican tu probabilidad de sufrir un delito.</strong> Más peatones y actividad pueden concentrar más eventos. Existe subregistro.</p>
    ${d.revision_2025 ? `<p class="revision-fuente">${esc(d.revision_2025)} <a href="${esc(d.revision_url)}" target="_blank" rel="noopener">Ficha oficial</a></p>` : ''}
    <p class="fuente">${esc(d.unidad)} Día: 06–19:59 h. Noche: 20–05:59 h. Sin horario se informa aparte.</p>
    ${d.inmueble ? `<h3>Alrededor del aviso ${esc(d.inmueble.id)}</h3><p class="fuente">Precisión informada del pin: ${d.inmueble.precision_m} m. Los círculos pueden cruzar límites de barrio.</p>
      <figure class="comparacion-registros"><figcaption>Hechos registrados a ${numero.format(Number(estado.delitos.radio))} m · ${esc(estado.delitos.tipo)} · horario ${esc(estado.delitos.franja)}</figcaption>${barras}</figure>
      <details><summary>Los tres radios · día y noche, por año y tipo</summary><div class="tabla-registros"><table class="avisos"><caption>Conteos acumulativos sin filtros de tipo ni franja; no sumar los radios.</caption>
      <thead><tr><th>Año · radio · tipo</th><th>Día</th><th>Noche</th><th>Sin hora</th><th>Total</th></tr></thead><tbody>${filas}</tbody></table></div></details>`
      : '<p class="nota">Elegí «Ver registros cerca» en un aviso con pin preciso para comparar radios de 250, 500 y 1.000 m. Esta vista general usa celdas, no totales por barrio.</p>'}
    <h3>Persistencia entre años</h3><p class="fuente">${esc(d.persistencia.definicion)}</p>
    ${!d.persistencia.disponible ? '<p class="nota">Faltan al menos dos años con los 12 meses observados para evaluar persistencia.</p>' : ''}
    <p class="fuente">Cobertura observada: ${d.cobertura.map((c) => `${c.anio}: ${c.meses_observados.length}/12 meses`).join(' · ')}. Los conteos de años parciales no se anualizan.</p>
    <details><summary>Fuente, calidad y límites</summary><ul class="nota">${d.limitaciones.map((s) => `<li>${esc(s)}</li>`).join('')}</ul>
      <p class="fuente">Robos y hurtos excluidos por falta de coordenadas válidas: ${numero.format(d.calidad.robos_hurtos_sin_pin || 0)}. Sin horario entre los geolocalizados: ${numero.format(d.calidad.robos_hurtos_sin_horario || 0)}. Estos valores corresponden al conjunto de fuentes.</p>
      ${d.fuentes.map((f) => `<p class="fuente">${esc(f.archivo)} · <a href="${esc(f.url)}" target="_blank" rel="noopener">Mapa del Delito CABA</a><br>SHA-256: <span class="huella-fuente">${esc(f.sha256)}</span></p>`).join('')}</details></section>`;
}

/* Radar de tendencias barriales: capa editorial, separada de avisos, delitos y datos de ejemplo. */

const ESTADO_FUENTE = { ok: 'Completa', parcial: 'Parcial', error: 'Falló', restringido: 'Acceso restringido', sin_ejecutar: 'Sin ejecutar' };
const fechaCorta = (iso) => (iso ? new Intl.DateTimeFormat('es-AR', { day: 'numeric', month: 'numeric', year: 'numeric',
  timeZone: 'America/Argentina/Buenos_Aires' }).format(new Date(iso.length === 10 ? `${iso}T12:00:00-03:00` : iso)) : '—');
const fechaHora = (iso) => (iso ? new Intl.DateTimeFormat('es-AR', { day: 'numeric', month: 'numeric', year: 'numeric',
  hour: '2-digit', minute: '2-digit', timeZone: 'America/Argentina/Buenos_Aires' }).format(new Date(iso)) : '—');
const fechaLarga = (iso) => new Intl.DateTimeFormat('es-AR', { day: 'numeric', month: 'long', year: 'numeric',
  timeZone: 'America/Argentina/Buenos_Aires' }).format(new Date(`${iso}T12:00:00-03:00`));

function periodoRadar(r) {
  return `del ${fechaLarga(r.periodo.desde)} al ${fechaLarga(r.periodo.hasta)}`;
}

function fuentesConProblemas(r) {
  return r.fuentes.filter((f) => !['ok', 'parcial'].includes(f.estado));
}

function avisoFuentes(r) {
  const malas = fuentesConProblemas(r);
  const parciales = r.fuentes.filter((f) => f.estado === 'parcial');
  const partes = [];
  if (malas.length) partes.push(`Sin datos de ${enumerar(malas.map((f) => f.medio))} para este período: la recolección ${plural(malas.length, 'falló', 'fallaron')} y eso no significa que no hubo notas.`);
  if (parciales.length) partes.push(`La recolección de ${enumerar(parciales.map((f) => f.medio))} fue parcial.`);
  return partes.length ? `<p class="nota radar-alerta">${esc(partes.join(' '))}</p>` : '';
}

function renderRadarLista() {
  const r = estado.radar;
  if (!r) return '';
  if (!r.disponible) {
    return `<p class="fuente radar-lista">Radar de tendencias barriales: ${esc(r.motivo || 'no está disponible.')}</p>`;
  }
  const filas = r.barrios.filter((b) => b.notas || b.aperturas).map((b) => `<tr>
      <th scope="row"><button class="boton-texto" type="button" data-barrio="${esc(b.barrio)}">${esc(b.barrio)}</button></th>
      <td>${b.notas ? `<button class="radar-numero" type="button" data-radar-barrio="${esc(b.barrio)}" data-radar-tipo="notas"
        aria-label="Ver las ${b.notas} ${plural(b.notas, 'nota', 'notas')} sobre ${esc(b.barrio)}">${b.notas}</button>` : '0'}</td>
      <td>${b.aperturas ? `<button class="radar-numero" type="button" data-radar-barrio="${esc(b.barrio)}" data-radar-tipo="aperturas"
        aria-label="Ver las aperturas reportadas en ${esc(b.barrio)}">${b.aperturas}</button>` : '0'}</td></tr>`).join('');
  const sinBarrio = r.sin_barrio.length;
  const problemas = fuentesConProblemas(r).length + r.fuentes.filter((f) => f.estado === 'parcial').length;
  return `<details class="radar radar-lista"${estado.radarAbierto ? ' open' : ''}>
    <summary><span class="radar-titulo" id="titulo-radar">Radar de tendencias barriales</span>
      <span class="radar-resumen">${r.totales.notas} ${plural(r.totales.notas, 'nota', 'notas')} de prensa ·
        ${r.totales.aperturas} ${plural(r.totales.aperturas, 'apertura reportada', 'aperturas reportadas')} ·
        ${fechaCorta(r.periodo.desde)} al ${fechaCorta(r.periodo.hasta)}${problemas ? ' · revisar fuentes' : ''}</span></summary>
    <p class="nota">Notas inmobiliarias publicadas ${periodoRadar(r)} en ${enumerar(r.fuentes.map((f) => f.medio))}.
      ${esc(r.aviso)} Es una capa editorial aparte: no usa los avisos, los delitos ni los datos de ejemplo.</p>
    <p class="fuente">Última actualización: ${fechaHora(r.actualizado)} ·
      <button class="boton-texto" type="button" data-radar-fuentes>Estado de las fuentes</button></p>
    <ul class="radar-fuentes">${r.fuentes.map((f) => `<li class="radar-estado radar-${esc(f.estado)}">
      ${esc(f.medio)}: ${esc(ESTADO_FUENTE[f.estado] || f.estado)}${['ok', 'parcial'].includes(f.estado) ? ` · ${f.notas} ${plural(f.notas, 'nota', 'notas')}` : ''}</li>`).join('')}</ul>
    ${avisoFuentes(r)}
    ${filas ? `<table class="tabla radar-tabla">
      <caption>Barrios con notas centradas en ellos, en orden alfabético. Tocá un número para ver las notas que lo respaldan.</caption>
      <thead><tr><th scope="col">Barrio</th><th scope="col">Notas publicadas</th><th scope="col">Aperturas reportadas</th></tr></thead>
      <tbody>${filas}</tbody></table>`
      : '<p class="nota">Ninguna nota del período se centró en un barrio porteño.</p>'}
    <p class="fuente">Las menciones al pasar y las comparaciones no suman. Una apertura cuenta solo si la nota informa local, dirección y una fecha de apertura dentro del período.
      ${sinBarrio ? `<button class="boton-texto" type="button" data-radar-sin-barrio>${sinBarrio} ${plural(sinBarrio, 'nota', 'notas')} sin barrio asignado</button>` : ''}</p>
  </details>`;
}

function prensaFila(barrio) {
  const fila = estado.radar?.disponible && estado.radar.barrios.find((x) => x.barrio === barrio);
  if (!fila || !(fila.notas || fila.aperturas)) return '';
  const partes = [`${fila.notas} ${plural(fila.notas, 'nota', 'notas')}`];
  if (fila.aperturas) partes.push(`${fila.aperturas} ${plural(fila.aperturas, 'apertura', 'aperturas')}`);
  return `<span class="fila-prensa">En la prensa: ${partes.join(' · ')}</span>`;
}

function renderNotaRadar(n) {
  const republicada = n.republicaciones?.length
    ? `<p class="fuente">También publicada en: ${n.republicaciones.map((x) => `<a href="${esc(x.url)}" target="_blank" rel="noopener">${esc(x.medio)}, ${fechaCorta(x.fecha_publicacion)}</a>`).join(' · ')}</p>` : '';
  return `<li class="radar-nota">
    <p class="radar-meta">${fechaCorta(n.fecha_publicacion)} · ${esc(n.medio)} · ${esc(n.tema_nombre)}</p>
    <a href="${esc(n.url)}" target="_blank" rel="noopener">${esc(n.titular)}</a>
    <p class="fuente">${esc(n.resumen)}${n.fecha_hecho ? ` Fecha del hecho: ${fechaCorta(n.fecha_hecho)}.` : ''}</p>
    ${republicada}</li>`;
}

function renderAperturaRadar(a) {
  return `<li class="radar-nota">
    <p class="radar-meta">Apertura el ${fechaCorta(a.fecha_apertura)}${a.barrio ? ` · ${esc(a.barrio)}` : ''}</p>
    <strong>${esc(a.local)}</strong>, ${esc(a.direccion)}
    ${a.fechas_informadas.length > 1 ? `<p class="fuente">Las notas informan fechas distintas: ${a.fechas_informadas.map(fechaCorta).join(', ')}.</p>` : ''}
    <p class="fuente">${plural(a.notas.length, 'Lo respalda', 'Lo respaldan')}: ${a.notas.map((n) => `<a href="${esc(n.url)}" target="_blank" rel="noopener">${esc(n.medio)}, ${fechaCorta(n.fecha_publicacion)}</a>`).join(' · ')}</p></li>`;
}

function coberturaAperturas(barrio) {
  return (estado.radar?.aperturas_sin_conteo || []).filter((a) => a.barrio === barrio);
}

function renderRadarFicha(barrio) {
  const r = estado.radar;
  if (!r?.disponible) return '';
  const d = r.detalle[barrio] || { notas: [], aperturas: [] };
  const fila = r.barrios.find((b) => b.barrio === barrio);
  const extra = coberturaAperturas(barrio);
  return `<section class="radar radar-ficha" aria-labelledby="titulo-prensa">
    <h2 id="titulo-prensa">En la prensa</h2>
    <p class="fuente">Radar de tendencias barriales, ${periodoRadar(r)}. Cobertura de los medios monitoreados, no demanda medida.</p>
    ${avisoFuentes(r)}
    <dl class="hechos"><dt>Notas publicadas</dt><dd>${d.notas.length}</dd><dt>Aperturas reportadas</dt><dd>${d.aperturas.length}</dd></dl>
    ${d.notas.length ? `<ul class="radar-notas">${d.notas.map(renderNotaRadar).join('')}</ul>`
      : '<p class="nota">Ninguna nota del período se centró en este barrio.</p>'}
    ${d.aperturas.length ? `<h3>Aperturas reportadas</h3><ul class="radar-notas">${d.aperturas.map(renderAperturaRadar).join('')}</ul>` : ''}
    ${extra.length ? `<h3>Cobertura de aperturas que no suma</h3><ul class="radar-notas">${extra.map((a) => `<li class="radar-nota">
      ${a.local ? `<strong>${esc(a.local)}</strong>` : 'Local sin nombre identificado'}: ${esc(a.motivo)}.
      <a href="${esc(a.nota.url)}" target="_blank" rel="noopener">${esc(a.nota.medio)}</a></li>`).join('')}</ul>` : ''}
    ${fila?.incidentales ? `<p class="fuente">Además, ${fila.incidentales} ${plural(fila.incidentales, 'nota lo nombra', 'notas lo nombran')} al pasar o como comparación. No suman.</p>` : ''}
  </section>`;
}

function abrirRadar(contenido) {
  $('#radar-contenido').innerHTML = contenido;
  $('#dialogo-radar').showModal();
}

function detalleRadar(barrio, tipo) {
  const r = estado.radar;
  const d = r.detalle[barrio] || { notas: [], aperturas: [] };
  if (tipo === 'aperturas') {
    abrirRadar(`<h3>Aperturas reportadas en ${esc(barrio)}</h3>
      <p class="nota">${periodoRadar(r)}. Cada apertura agrupa las notas que informan el mismo local y la misma dirección. No es un censo: solo incluye lo que publicaron los medios monitoreados.</p>
      <ul class="radar-notas">${d.aperturas.map(renderAperturaRadar).join('')}</ul>`);
    return;
  }
  abrirRadar(`<h3>Notas publicadas sobre ${esc(barrio)}</h3>
    <p class="nota">${periodoRadar(r)}. Notas centradas en el barrio: lo nombran en el titular, la bajada o un subtítulo, o varias veces sin usarlo como comparación.</p>
    <ul class="radar-notas">${d.notas.map(renderNotaRadar).join('')}</ul>`);
}

function detalleSinBarrio() {
  const r = estado.radar;
  abrirRadar(`<h3>Notas sin barrio asignado</h3>
    <p class="nota">${periodoRadar(r)}. Tratan sobre la Ciudad en general, otra ciudad o un tema sin un barrio puntual, o lo nombran de forma ambigua.</p>
    <ul class="radar-notas">${r.sin_barrio.map(renderNotaRadar).join('')}</ul>`);
}

function detalleFuentesRadar() {
  const r = estado.radar;
  abrirRadar(`<h3>Estado de las fuentes</h3>
    <p class="nota">Período ${periodoRadar(r)}. Cada medio se recolecta y se guarda por separado: si uno falla, se conservan sus datos anteriores y la falla se informa.</p>
    <table class="tabla"><thead><tr><th>Medio</th><th>Estado</th><th>Notas</th><th>Recolectado</th></tr></thead><tbody>
    ${r.fuentes.map((f) => `<tr><td><a href="${esc(f.seccion)}" target="_blank" rel="noopener">${esc(f.medio)}</a></td>
      <td>${esc(ESTADO_FUENTE[f.estado] || f.estado)}</td><td>${['ok', 'parcial'].includes(f.estado) ? f.notas : '—'}</td>
      <td>${fechaHora(f.recolectado_en)}</td></tr>`).join('')}</tbody></table>
    ${r.fuentes.map((f) => `<p class="fuente"><strong>${esc(f.medio)}.</strong> ${esc(f.metodo)}
      ${f.cobertura_desde ? ` Los listados llegaron hasta el ${fechaCorta(f.cobertura_desde)}.` : ''}
      ${f.motivo ? ` Observaciones: ${esc(f.motivo)}` : ''}
      ${f.ultimo_intento && f.ultimo_intento.fecha !== f.recolectado_en ? ` Último intento: ${fechaHora(f.ultimo_intento.fecha)}, ${esc(ESTADO_FUENTE[f.ultimo_intento.estado] || f.ultimo_intento.estado)}.` : ''}</p>`).join('')}
    <p class="fuente">Se guardan medio, titular, enlace, fechas, barrios, tema y un resumen propio. No se guarda el texto de las notas ni se leen notas de acceso restringido.</p>`);
}

async function cargarRadar() {
  try {
    estado.radar = await api('/api/radar');
  } catch (error) {
    estado.radar = { disponible: false, motivo: `No se pudo cargar el radar: ${error.message}` };
  }
}

function renderPanel() {
  if (estado.seleccionado) renderFicha();
  else renderLista();
  pintarAvisos();
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
// Centra el mapa en la ubicación del navegador; después se puede buscar desde «El centro del mapa».
// La posición queda en el navegador y no se envía al servidor hasta que se pide una búsqueda.
if (window.isSecureContext && navigator.geolocation) {
  mapa.addControl(new maplibregl.GeolocateControl({
    positionOptions: { enableHighAccuracy: true, timeout: 10000, maximumAge: 60000 },
    fitBoundsOptions: { maxZoom: 16 }, showAccuracyCircle: true, trackUserLocation: false,
  }), 'top-right');
}
let marcadorUbicacion = null;
function marcarMiUbicacion({ lat, lon, precision }) {
  if (!marcadorUbicacion) {
    const punto = document.createElement('div');
    punto.className = 'mi-ubicacion';
    marcadorUbicacion = new maplibregl.Marker({ element: punto });
  }
  marcadorUbicacion.setLngLat([lon, lat]).addTo(mapa);
  marcadorUbicacion.getElement().title = `Tu ubicación (precisión aproximada ${precision} m)`;
  mapa.flyTo({ center: [lon, lat], zoom: Math.max(mapa.getZoom(), 15) });
}
const mapaListo = new Promise((resolver) => mapa.on('load', resolver));
new ResizeObserver(() => mapa.resize()).observe(document.querySelector('.mapa'));
const popup = new maplibregl.Popup({ closeButton: false, closeOnClick: false, offset: 10, maxWidth: '18rem' });
// Lista de avisos de un punto, con enlaces. Se cierra a mano al tocar otro lugar del mapa.
const popupAviso = new maplibregl.Popup({ closeButton: true, closeOnClick: false, offset: 12, maxWidth: '20rem',
  className: 'popup-avisos' });
popupAviso.on('close', () => { estado.pinAbierto = null; });

async function prepararMapa() {
  const [formas] = await Promise.all([api('/api/mapa/barrios'), mapaListo]);
  estado.formas = formas;
  mapa.resize();
  if (!estado.seleccionado) encuadrar(null, true);
  const simbolo = mapa.getStyle().layers.find((capa) => capa.type === 'symbol')?.id;
  mapa.addSource('barrios', { type: 'geojson', data: formas, promoteId: 'barrio' });
  for (const id of ['delitos', 'radios', 'inmueble', ...CAPAS_MAPA.map((c) => c.clave), 'avisos']) {
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
  mapa.addLayer({ id: 'estacionamiento', type: 'circle', source: 'estacionamiento',
    // Toda la ciudad: puntos chicos con el mapa alejado para que se lean los 2.700 garajes.
    paint: { 'circle-radius': ['interpolate', ['linear'], ['zoom'], 11, 2.5, 14, 4.5, 16, 6],
      'circle-color': COLOR.estacionamiento,
      'circle-stroke-color': '#FFFFFF', 'circle-stroke-width': ['interpolate', ['linear'], ['zoom'], 11, 0.5, 14, 1.5] } });
  // Avisos que encajan: relleno si la ubicación publicada es coherente con el barrio, hueco si es aproximada.
  // Un punto con varios avisos (un mismo edificio) se dibuja más grande.
  mapa.addLayer({ id: 'avisos', type: 'circle', source: 'avisos',
    paint: {
      'circle-radius': ['interpolate', ['linear'], ['get', 'cantidad'], 1, 5, 5, 8, 20, 11],
      'circle-color': ['case', ['get', 'aproximada'], '#FFFFFF', COLOR.aviso],
      'circle-stroke-color': ['case', ['get', 'aproximada'], COLOR.aviso, '#FFFFFF'],
      'circle-stroke-width': ['case', ['get', 'aproximada'], 2, 1.4],
    } });
  mapa.addLayer({ id: 'radios', type: 'line', source: 'radios',
    paint: { 'line-color': '#6A4FB3', 'line-width': ['case', ['get', 'seleccionado'], 2.5, 1], 'line-dasharray': [3, 2] } });
  mapa.addLayer({ id: 'inmueble', type: 'circle', source: 'inmueble',
    paint: { 'circle-radius': 7, 'circle-color': '#6A4FB3', 'circle-stroke-color': '#FFFFFF', 'circle-stroke-width': 2 } });

  const puntos = ['subte', 'salud', 'escuelas', 'estacionamiento'];
  const conTexto = [...puntos, 'verdes', 'riesgo', 'ruido', 'delitos'];

  mapa.on('mousemove', (evento) => {
    const barrio = mapa.queryRenderedFeatures(evento.point, { layers: ['barrios-relleno'] })[0];
    marcarHover(barrio ? barrio.id : null, 'mapa');
    const pin = mapa.queryRenderedFeatures(evento.point, { layers: ['avisos'] })[0];
    if (pin) {
      mapa.getCanvas().style.cursor = 'pointer';
      if (estado.pinAbierto === pin.properties.clave) popup.remove();
      else popup.setLngLat(pin.geometry.coordinates).setHTML(esc(textoPin(pin.properties.clave))).addTo(mapa);
      return;
    }
    const elemento = mapa.queryRenderedFeatures(evento.point, { layers: conTexto })[0];
    const texto = elemento ? textoElemento(elemento) : (barrio && !estado.seleccionado ? textoBarrio(barrio.id) : null);
    mapa.getCanvas().style.cursor = barrio || elemento ? 'pointer' : '';
    if (texto) popup.setLngLat(evento.lngLat).setHTML(esc(texto)).addTo(mapa);
    else popup.remove();
  });
  mapa.on('mouseout', () => { popup.remove(); marcarHover(null, 'mapa'); });
  mapa.on('click', (evento) => {
    const pin = mapa.queryRenderedFeatures(evento.point, { layers: ['avisos'] })[0];
    if (pin) {
      abrirPin(pin.properties.clave);
      return;
    }
    popupAviso.remove();
    const elemento = mapa.queryRenderedFeatures(evento.point, { layers: conTexto })[0];
    if (elemento) {
      popup.setLngLat(evento.lngLat).setHTML(esc(textoElemento(elemento))).addTo(mapa);
      return;
    }
    const barrio = mapa.queryRenderedFeatures(evento.point, { layers: ['barrios-relleno'] })[0];
    if (barrio && barrio.id !== estado.seleccionado) seleccionar(barrio.id);
  });
  pintarAvisos();
}

/* Pines de los avisos */

function claveUbicacion(a) {
  return `${a.lat.toFixed(6)},${a.lon.toFixed(6)}`;
}

function gruposAvisos() {
  const grupos = new Map();
  for (const a of estado.avisos) {
    if (!a.ubicacion) continue;
    const clave = claveUbicacion(a);
    if (!grupos.has(clave)) grupos.set(clave, []);
    grupos.get(clave).push(a);
  }
  return grupos;
}

function pintarAvisos() {
  const fuente = mapa.getSource('avisos');
  if (!fuente) return;
  const grupos = estado.seleccionado ? gruposAvisos() : new Map();
  fuente.setData({ type: 'FeatureCollection', features: [...grupos].map(([clave, lista]) => ({
    type: 'Feature', geometry: { type: 'Point', coordinates: [lista[0].lon, lista[0].lat] },
    properties: { clave, cantidad: lista.length, aproximada: lista.every((a) => a.ubicacion === 'aproximada') },
  })) });
  if (estado.pinAbierto && !grupos.has(estado.pinAbierto)) popupAviso.remove();
}

function textoPin(clave) {
  const lista = gruposAvisos().get(clave) || [];
  if (lista.length === 1) {
    const a = lista[0];
    return `${dinero(a.precio, a.moneda)} · ${a.superficie} m² · ${a.ambientes} amb.${a.ubicacion === 'aproximada' ? ' Ubicación aproximada.' : ''}`;
  }
  const precios = lista.map((a) => a.precio);
  return `${lista.length} avisos en este punto, de ${dinero(Math.min(...precios), lista[0].moneda)} a ${dinero(Math.max(...precios), lista[0].moneda)}. Tocá para verlos.`;
}

function abrirPin(clave) {
  const lista = gruposAvisos().get(clave);
  if (!lista) return;
  popup.remove();
  estado.pinAbierto = clave;
  const filas = lista.map((a) => `<li><strong>${esc(dinero(a.precio, a.moneda))}</strong> · ${a.superficie} m² · ${a.ambientes} amb.
    ${a.enlace ? `<a href="${esc(a.enlace)}" target="_blank" rel="noopener">Ver aviso</a>` : ''}</li>`).join('');
  const nota = lista.every((a) => a.ubicacion === 'aproximada')
    ? 'Ubicación aproximada: el punto publicado cae a entre 150 y 500 m del barrio.'
    : 'Punto publicado por la fuente, sin precisión declarada.';
  popupAviso.setLngLat([lista[0].lon, lista[0].lat])
    .setHTML(`<p class="pin-titulo">${lista.length === 1 ? '1 aviso' : `${lista.length} avisos`} en este punto</p>
      <ul class="pin-lista">${filas}</ul><p class="pin-nota">${nota}</p>`)
    .addTo(mapa);
  estado.pinAbierto = clave;
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
    const detalle = JSON.parse(typeof p.por_anio === 'string' ? p.por_anio : JSON.stringify(p.por_anio));
    const altos = JSON.parse(typeof p.anios_altos === 'string' ? p.anios_altos : JSON.stringify(p.anios_altos));
    return `Celda de 200 m · ${Object.entries(detalle).map(([y, n]) => `${y}: ${n}`).join(' · ')} hechos. ${estado.delitos.tipo}; ${estado.delitos.franja}. Años de concentración alta: ${altos.join(', ') || 'ninguno'}. La celda puede cruzar el círculo; los conteos por radio usan cada registro.`;
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

function encuadrarPin(pin) {
  const dlat = 1100 / 111320;
  const dlon = dlat / Math.cos(pin.lat * Math.PI / 180);
  const alto = mapa.getContainer().clientHeight;
  const controles = document.querySelector('.mapa-arriba').getBoundingClientRect().height;
  mapa.fitBounds([[pin.lon - dlon, pin.lat - dlat], [pin.lon + dlon, pin.lat + dlat]], {
    padding: { top: Math.min(controles + 25, alto * 0.3), bottom: celular() ? alto * 0.44 : 50, left: 30, right: 45 },
    duration: reducido ? 0 : 500,
  });
}

/* Capas del barrio elegido */

function claveCapa(clave) {
  // Los garajes cubren toda la ciudad: se piden una vez, sin importar el barrio.
  return [clave === 'estacionamiento' ? 'CABA' : estado.seleccionado, clave, clave === 'escuelas' ? estado.nivel : '', clave === 'ruido' ? estado.ruido : ''].join('|');
}

async function actualizarCapas() {
  const barrio = estado.seleccionado;
  const fijas = CAPAS_MAPA.map((c) => c.clave);
  if (!barrio) {
    fijas.concat('delitos', 'radios', 'inmueble').forEach((id) => mapa.getSource(id)?.setData(VACIO));
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
    if (estado.capas.has('delitos') && !await cargarDelitos()) return;
  } catch (error) {
    mostrarAvisoMapa(`No se pudieron cargar las capas: ${error.message}`);
  }
  if (barrio !== estado.seleccionado) return;
  for (const c of fijas) mapa.getSource(c)?.setData(estado.capas.has(c) ? estado.capasDatos[claveCapa(c)] || VACIO : VACIO);
  const delitos = estado.capas.has('delitos') && estado.delitosDatos?.disponible ? estado.delitosDatos.celdas : VACIO;
  mapa.getSource('delitos')?.setData(delitos);
  const d = estado.capas.has('delitos') && estado.delitosDatos?.disponible ? estado.delitosDatos : null;
  mapa.getSource('radios')?.setData(d?.radios || VACIO);
  mapa.getSource('inmueble')?.setData(d?.inmueble ? { type: 'FeatureCollection', features: [{ type: 'Feature',
    geometry: { type: 'Point', coordinates: [d.inmueble.lon, d.inmueble.lat] }, properties: {} }] } : VACIO);
  renderControles();
  renderLeyenda();
  renderPanel();
}

async function cargarDelitos() {
  const secuencia = ++estado.pedidoDelitos;
  const pedido = new URLSearchParams({ barrio: estado.seleccionado, modo: estado.modo, operacion: estado.operacion });
  for (const clave of ['tipo', 'franja', 'radio', 'inmueble']) if (estado.delitos[clave]) pedido.set(clave, estado.delitos[clave]);
  if (estado.delitos.anio && estado.delitos.anio !== 'persistencia') pedido.set('anio', estado.delitos.anio);
  const datos = await api(`/api/delitos/concentracion?${pedido}`);
  if (secuencia !== estado.pedidoDelitos) return false;
  if (datos.disponible) {
    if (!estado.delitos.anio) estado.delitos.anio = datos.persistencia.disponible ? 'persistencia' : String(datos.anios.at(-1));
    const persistencia = estado.delitos.anio === 'persistencia';
    for (const f of datos.celdas.features) {
      const p = f.properties;
      p.hechos = persistencia ? p.anios_altos.length : (p.por_anio[estado.delitos.anio] || 0);
      p.paso = persistencia ? Math.min(4, p.hechos) : [5, 10, 20, 50].filter((n) => p.hechos >= n).length;
    }
    datos.celdas.features = datos.celdas.features.filter((f) => persistencia ? f.properties.persistente : f.properties.hechos > 0);
  }
  estado.delitosDatos = datos;
  return true;
}

function mostrarAvisoMapa(texto) {
  $('#mapa-pista').hidden = false;
  $('#mapa-pista').textContent = texto;
}

// Capas al elegir un barrio. Sin el explorador, las de «Lo que me importa», como siempre.
function capasIniciales() {
  return new Set(EXPLORADOR ? explorador().capas : estado.prefs);
}

/* Prende o apaga una capa desde los chips del mapa. Con el explorador, la decisión se recuerda: prender la suma a
   «Lo que me importa» y apagar una capa sugerida por una necesidad la deja apagada al cambiar de barrio. Delitos
   nunca se recuerda. */
function alternarCapa(clave) {
  const prender = !estado.capas.has(clave);
  if (prender) estado.capas.add(clave); else estado.capas.delete(clave);
  if (!EXPLORADOR || !CAPAS_MAPA.some((c) => c.clave === clave)) return;
  if (prender) {
    estado.prefs.add(clave);
    estado.apagadas.delete(clave);
  } else {
    estado.prefs.delete(clave);
    if (NECESIDADES.some((n) => estado.necesidades.has(n.clave) && n.capas.includes(clave))) estado.apagadas.add(clave);
  }
  guardar();
  sincronizarControles();
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
      partes.push(`<div class="control-flotante">
        <label>Vista <select data-control="anio">${[['persistencia', 'Persistencia entre años'], ...d.anios.map((y) => [String(y), String(y)])].map(([v, t]) => `<option value="${v}"${v === estado.delitos.anio ? ' selected' : ''}>${t}</option>`).join('')}</select></label>
        <label>Tipo <select data-control="tipo">${[['todos', 'Robos y hurtos'], ['robo', 'Robos · fuerza o violencia'], ['hurto', 'Hurtos · sin violencia']].map(([v, t]) => `<option value="${v}"${v === estado.delitos.tipo ? ' selected' : ''}>${t}</option>`).join('')}</select></label>
        <label>Horario <select data-control="franja">${[['todas', 'Todos los horarios'], ['diurno', 'Día · 06–19:59'], ['nocturno', 'Noche · 20–05:59'], ['sin_dato', 'Sin horario informado']].map(([v, t]) => `<option value="${v}"${v === estado.delitos.franja ? ' selected' : ''}>${t}</option>`).join('')}</select></label>
        ${d.inmueble ? `<label>Radio <select data-control="radio">${[250, 500, 1000].map((r) => `<option value="${r}"${String(r) === estado.delitos.radio ? ' selected' : ''}>${numero.format(r)} m</option>`).join('')}</select></label><button class="boton-texto" type="button" data-quitar-inmueble>Vista general</button>` : ''}
        <p class="fuente">${d.celdas.features.length ? `${d.celdas.features.length} celdas visibles` : estado.delitos.anio === 'persistencia' ? 'Sin celdas persistentes con estos filtros; no implica ausencia de delitos.' : 'Sin registros geolocalizados con estos filtros; no implica ausencia de delitos.'}</p>
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
  const conPunto = estado.avisos.filter((a) => a.ubicacion);
  if (conPunto.length) {
    const pin = (hueco, etiqueta) => `<li><span class="chip-muestra chip-pin${hueco ? ' chip-pin-hueco' : ''}"></span>${esc(etiqueta)}</li>`;
    bloques.push(`<h3>Avisos que encajan</h3><ul class="leyenda-items">${pin(false, 'Punto publicado')}${
      conPunto.some((a) => a.ubicacion === 'aproximada') ? pin(true, 'Aproximado') : ''}</ul>`);
    notas.push(`<li><strong>Avisos.</strong> ${esc(NOTA_AVISOS)}</li>`);
  }
  for (const c of CAPAS) {
    if (!estado.capas.has(c.clave)) continue;
    let items = [];
    if (c.clave === 'subte') {
      const lineas = [...new Set((estado.capasDatos[claveCapa('subte')]?.features || []).map((f) => f.properties.line))].sort();
      items = lineas.map((l) => muestra(SUBTE[l] || '#55626B', `Línea ${l}`));
    } else if (c.clave === 'verdes') items = [muestra(COLOR.verdes, 'Plaza o parque')];
    else if (c.clave === 'escuelas') items = [muestra(COLOR.escuela, `Escuela de nivel ${estado.nivel}`)];
    else if (c.clave === 'salud') items = [muestra(COLOR.cesac, 'CeSAC'), muestra(COLOR.hospital, 'Hospital')];
    else if (c.clave === 'estacionamiento') {
      const capa = estado.capasDatos[claveCapa(c.clave)];
      if (capa?.features.length) items = [muestra(COLOR.estacionamiento, `Garaje comercial · ${numero.format(capa.features.length)} en toda la ciudad`)];
      else if (capa) items = [esc(capa.disponible ? 'Sin garajes registrados.' : 'Inventario de garajes sin cargar.')];
    }
    else if (c.clave === 'riesgo') items = [muestra(COLOR.riesgo, 'Área de prevención')];
    else if (c.clave === 'ruido') {
      items = RUIDO.map(([v, color]) => muestra(color, v === 50 ? 'Menos de 55 dBA' : v === 80 ? '80 dBA o más' : `${v} a ${v + 5} dBA`));
    } else if (c.clave === 'delitos') {
      const d = estado.delitosDatos;
      if (!d?.disponible) continue;
      items = estado.delitos.anio === 'persistencia'
        ? [...new Set(d.celdas.features.map((f) => f.properties.hechos))].sort((a, b) => a - b).map((n) => muestra(DELITOS[Math.min(4, n)], `Concentración alta en ${n} años`))
        : ['1–4', '5–9', '10–19', '20–49', '50 o más'].map((r, i) => muestra(DELITOS[i], `${r} hechos / celda · ${estado.delitos.anio}`));
      if (d.inmueble) items.push(muestra('#6A4FB3', `Pin del aviso · círculos 250, 500 y 1.000 m`));
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
  $('#abrir-preferencias-texto').hidden = !estado.info.interpretar_preferencias;
}

async function cargarBarrios() {
  const datos = await api(`/api/barrios?${consulta()}`);
  estado.barrios = datos.barrios;
  pintarCoropletas();
}

async function cargarAvisos() {
  if (!estado.seleccionado) return;
  const barrio = estado.seleccionado;
  const pedido = consulta();
  if (EXPLORADOR && estado.necesidades.size) {
    const { cercania } = explorador();
    cercania.forEach((c) => pedido.append('capas', c));
    if (cercania.includes('escuelas')) pedido.set('nivel', estado.nivel);
  }
  const datos = await api(`/api/barrios/${encodeURIComponent(barrio)}/avisos?${pedido}`);
  if (barrio === estado.seleccionado) {
    estado.avisos = datos.avisos;
    estado.cercaniaInfo = datos.cercania || null;
  }
}

async function seleccionar(nombre) {
  if (estado.seleccionado && mapa.getSource('barrios')) {
    mapa.setFeatureState({ source: 'barrios', id: estado.seleccionado }, { sel: false });
  }
  estado.seleccionado = nombre;
  estado.verTodos = false;
  estado.avisos = [];
  estado.delitosDatos = null;
  estado.delitos.inmueble = '';
  estado.pedidoDelitos += 1;
  estado.lugares = { ...lugaresIniciales(estado.lugares.tipo), pedido: estado.lugares.pedido + 1 };
  popup.remove();
  popupAviso.remove();
  if (nombre && mapa.getSource('barrios')) mapa.setFeatureState({ source: 'barrios', id: nombre }, { sel: true });
  estado.capas = nombre ? capasIniciales() : new Set();
  pintarCoropletas();
  encuadrar(nombre);
  renderChips();
  renderPanel();
  $('#contenido').scrollTop = 0;
  if (celular()) plegarPanel(false);
  estado.parecidos = { barrio: null, datos: null, error: '' };
  cargarParecidos();
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
      cargarParecidos();
      if (!estado.avisos.some((a) => a.id === estado.delitos.inmueble)) estado.delitos.inmueble = '';
      if (estado.capas.has('delitos')) await actualizarCapas();
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
  const ambientes = $('#ambientes');
  const valor = String(estado.ambientes) + (estado.ambientesOMas ? '+' : '');
  if (![...ambientes.options].some((o) => o.value === valor)) {
    ambientes.add(new Option(estado.ambientes + ' ambientes' + (estado.ambientesOMas ? ' o más' : ''), valor));
  }
  ambientes.value = valor;
  $('#nivel').value = estado.nivel;
  $('#franja-demo').hidden = estado.modo !== 'demo';
  // Capas que alguna necesidad elegida sugiere, aunque estén apagadas a mano.
  const sugeridas = new Set(EXPLORADOR ? NECESIDADES.filter((n) => estado.necesidades.has(n.clave)).flatMap((n) => n.capas) : []);
  $('#preferencias').innerHTML = `<legend ${EXPLORADOR ? 'class="importa-titulo"' : 'hidden'}>${EXPLORADOR ? 'Capas del mapa' : 'Lo que me importa'}</legend>${PREFERENCIAS.map((p) => `
    <label><input type="checkbox" value="${p.clave}"${estado.prefs.has(p.clave) ? ' checked' : ''}>${esc(p.nombre)}${
      sugeridas.has(p.clave) && !estado.prefs.has(p.clave) ? `<small class="sugerida">${estado.apagadas.has(p.clave) ? 'sugerida, apagada' : 'sugerida'}</small>` : ''}</label>`).join('')}`;
  $('#nivel-campo').hidden = !estado.prefs.has('escuelas');
  renderResumenNecesidades();
  const elegidas = estado.prefs.size + estado.necesidades.size;
  $('#abrir-importa').textContent = elegidas ? `Lo que me importa: ${elegidas}` : 'Lo que me importa';
  $('#abrir-importa').classList.toggle('con-eleccion', elegidas > 0);
}

// Casillas de necesidades. Se dibujan al iniciar y al restablecer, no en cada cambio, para no perder el foco.
function renderNecesidades() {
  // Sin el interruptor no se toca nada; con una página vieja en caché tampoco hay casillas que dibujar.
  const contenedor = $('#necesidades');
  if (!EXPLORADOR || !contenedor) return;
  contenedor.hidden = false;
  $('#necesidades-pie').hidden = false;
  contenedor.innerHTML = `<legend class="importa-titulo">Lo que necesitás</legend>${NECESIDADES.map((n) => `
    <label class="necesidad"><input type="checkbox" value="${n.clave}"${estado.necesidades.has(n.clave) ? ' checked' : ''}>
      <span>${esc(n.nombre)}<small>${esc(n.descripcion)}</small></span></label>`).join('')}`;
}

function renderResumenNecesidades() {
  if (!EXPLORADOR || !$('#necesidades-resumen')) return;
  const r = explorador();
  const nombres = r.capas.map((c) => CAPAS.find((x) => x.clave === c)?.nombre || c);
  const columnas = columnasExplorador().map((c) => c.titulo);
  $('#necesidades-resumen').textContent = estado.necesidades.size
    ? `En el mapa: ${nombres.length ? enumerar(nombres) : 'ninguna capa'}.`
      + (columnas.length ? ` En la tabla de avisos: ${enumerar(columnas)}.` : '') + ' No se oculta ningún aviso.'
    : 'Elegí una o más para ver capas y datos relacionados. No filtran avisos ni arman puntajes.';
}

async function aplicarNecesidades() {
  guardar();
  sincronizarControles();
  if (!estado.seleccionado) { renderPanel(); return; }
  const delitos = estado.capas.has('delitos');
  estado.capas = capasIniciales();
  if (delitos) estado.capas.add('delitos');
  renderChips();
  actualizarCapas();
  try { await cargarAvisos(); } catch { /* La ficha sigue con los avisos anteriores. */ }
  renderPanel();
}

function enteroDe(texto) {
  const valor = parseInt(String(texto).replace(/\D/g, ''), 10);
  return Number.isFinite(valor) && valor > 0 ? valor : null;
}

async function cambiarContexto() {
  // Invalida antes de los awaits para no mostrar un resultado de la base anterior.
  estado.pedidoDelitos += 1;
  estado.delitosDatos = null;
  estado.delitos = { anio: '', tipo: 'todos', franja: 'todas', radio: '500', inmueble: '' };
  estado.avisos = [];
  for (const id of ['delitos', 'radios', 'inmueble']) mapa.getSource(id)?.setData(VACIO);
  renderPanel();
  sincronizarControles();
  guardar();
  try {
    await cargarEstado();
    await cargarBarrios();
    if (estado.seleccionado) {
      await cargarAvisos();
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

function conectarPreferencias() {
  const dialogo = $('#dialogo-preferencias');
  const interpretar = $('#interpretar-preferencias');
  const revisar = $('#revisar-preferencias');
  const salida = $('#estado-preferencias');
  let pedido;
  let capas = [];
  let requiereConfirmacion = false;
  const opciones = (items) => items.map(([id, label]) =>
    '<option value="' + esc(id) + '">' + esc(label) + '</option>').join('');

  function presentar(propuesta) {
    const valores = Object.fromEntries(propuesta.campos.map((c) => [c.clave, c.valor]));
    const barrios = [...new Set(propuesta.campos.filter((c) => c.clave === 'barrio').map((c) => c.valor))];
    capas = propuesta.campos.filter((c) => c.clave === 'capa').map((c) => c.valor);
    const barrio = barrios.length === 1 ? barrios[0] : barrios.length ? '' : estado.seleccionado || '';
    const campos = [
      ['operacion', 'Operación', valores.operacion ?? estado.operacion, [['venta', 'Comprar'], ['alquiler', 'Alquilar']]],
      ['moneda', 'Moneda', valores.moneda ?? estado.moneda, [['USD', 'USD'], ['ARS', 'ARS']]],
      ['presupuesto', 'Presupuesto máximo', valores.presupuesto ?? estado.presupuesto, 1000000000],
      ['superficie', 'Superficie cubierta mínima (m²)', valores.superficie ?? estado.superficie, 2000],
      ['ambientes', 'Ambientes', valores.ambientes ?? estado.ambientes, 20],
      ['ambientes_o_mas', 'Cantidad de ambientes', valores.ambientes_o_mas ?? String(estado.ambientesOMas),
        [['false', 'Exacta'], ['true', 'O más']]],
      ['barrio', 'Barrio', barrio, [['', 'Comparación general'], ...[...new Set([
        ...barrios, ...(barrio ? [barrio] : []), ...estado.barrios.map((b) => b.barrio)
      ])].sort((a, b) => a.localeCompare(b, 'es')).map((b) => [b, b])]],
    ];
    $('#campos-preferencias').innerHTML = campos.map(([clave, label, valor, tipo]) => {
      const origen = clave === 'barrio' && barrios.length > 1 ? 'Elegí un barrio o compará todos'
        : clave in valores ? 'De tu descripción' : 'Valor actual';
      const control = Array.isArray(tipo)
        ? '<select name="' + clave + '">' + opciones(tipo) + '</select>'
        : '<input type="number" name="' + clave + '" required min="1" step="1" max="' + tipo + '">';
      return '<label>' + label + control + '<small>' + origen + '</small></label>';
    }).join('');
    campos.forEach(([clave, , valor]) => { revisar.elements.namedItem(clave).value = valor; });
    const avisos = [
      ...propuesta.dudas.map((d) => 'Revisá «' + d.evidencia + '» (' + d.campo + ').'),
      ...propuesta.no_soportadas.map((c) => 'No se aplicará «' + c.evidencia + '»' +
        (c.obligatoria ? ' (requisito indicado).' : '.')),
      ...capas.map((c) => 'Capa del mapa: ' + PREFERENCIAS.find((p) => p.clave === c)?.nombre + '.'),
    ];
    requiereConfirmacion = propuesta.dudas.length > 0 || barrios.length > 1 ||
      propuesta.no_soportadas.some((c) => c.obligatoria);
    $('#avisos-preferencias').innerHTML = avisos.map((aviso) => '<li>' + esc(aviso) + '</li>').join('');
    $('#confirmar-preferencias').hidden = !requiereConfirmacion;
    $('#confirmacion-preferencias').checked = false;
    revisar.hidden = false;
  }

  $('#abrir-preferencias-texto').addEventListener('click', () => dialogo.showModal());
  $('#cancelar-preferencias').addEventListener('click', () => dialogo.close());
  dialogo.addEventListener('close', () => {
    pedido?.abort();
    pedido = null;
    interpretar.reset();
    interpretar.querySelector('button').disabled = false;
    revisar.hidden = true;
    $('#campos-preferencias').replaceChildren();
    $('#avisos-preferencias').replaceChildren();
    salida.textContent = '';
    capas = [];
  });
  interpretar.addEventListener('input', () => {
    pedido?.abort();
    pedido = null;
    interpretar.querySelector('button').disabled = false;
    revisar.hidden = true;
    salida.textContent = '';
  });
  interpretar.addEventListener('submit', async (e) => {
    e.preventDefault();
    if (pedido) return;
    const actual = new AbortController();
    pedido = actual;
    const boton = interpretar.querySelector('button');
    boton.disabled = true;
    revisar.hidden = true;
    salida.textContent = 'Interpretando…';
    try {
      const propuesta = await api('/api/preferencias/interpretar', {
        method: 'POST', signal: actual.signal, headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ texto: $('#texto-preferencias').value }),
      });
      if (pedido === actual) {
        presentar(propuesta);
        salida.textContent = '';
      }
    } catch (error) {
      if (pedido === actual) salida.textContent = error.message;
    } finally {
      if (pedido === actual) {
        pedido = null;
        boton.disabled = false;
      }
    }
  });
  revisar.addEventListener('submit', async (e) => {
    e.preventDefault();
    if (revisar.hidden) return;
    const f = new FormData(revisar);
    if (f.get('operacion') === 'venta' && f.get('moneda') !== 'USD') {
      salida.textContent = 'Para comprar, elegí USD.';
      return;
    }
    if (requiereConfirmacion && !$('#confirmacion-preferencias').checked) {
      salida.textContent = 'Confirmá que revisaste los avisos antes de aplicar.';
      return;
    }
    clearTimeout(espera);
    estado.operacion = f.get('operacion');
    estado.moneda = f.get('moneda');
    estado.presupuesto = Number(f.get('presupuesto'));
    estado.superficie = Number(f.get('superficie'));
    estado.ambientes = Number(f.get('ambientes'));
    estado.ambientesOMas = f.get('ambientes_o_mas') === 'true';
    capas.forEach((capa) => estado.prefs.add(capa));
    dialogo.close();
    await cambiarContexto();
    await seleccionar(f.get('barrio') || null);
  });
}

function conectarEventos() {
  conectarPreferencias();
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
    if (e.target.checked) estado.apagadas.delete(clave);
    else if (EXPLORADOR && NECESIDADES.some((n) => estado.necesidades.has(n.clave) && n.capas.includes(clave))) {
      estado.apagadas.add(clave);
    }
    if (estado.seleccionado) {
      if (e.target.checked) estado.capas.add(clave); else estado.capas.delete(clave);
      renderChips();
      actualizarCapas();
    }
    sincronizarControles();
    guardar();
    renderPanel();
    cargarParecidos();
  });
  $('#nivel').addEventListener('change', (e) => { cambiarNivel(e.target.value); });
  $('#necesidades')?.addEventListener('change', (e) => {
    const clave = e.target.value;
    if (e.target.checked) estado.necesidades.add(clave); else estado.necesidades.delete(clave);
    aplicarNecesidades();
  });
  $('#restablecer-necesidades')?.addEventListener('click', () => {
    estado.necesidades.clear();
    estado.apagadas.clear();
    estado.prefs = new Set(['subte', 'verdes']);
    renderNecesidades();
    aplicarNecesidades();
  });
  $('#contenido').addEventListener('click', (e) => {
    if (!e.target.closest('[data-abrir-importa]')) return;
    e.stopPropagation();
    $('#importa').hidden = false;
    $('#abrir-importa').setAttribute('aria-expanded', 'true');
    $('#necesidades input')?.focus();
  });

  let consultaEstacionamientos = 0;
  $('#contenido').addEventListener('submit', async (e) => {
    if (e.target.id !== 'buscar-estacionamientos') return;
    e.preventDefault();
    const output = $('#resultado-estacionamientos');
    const fields = new FormData(e.target);
    const params = new URLSearchParams({ barrio: estado.seleccionado, radio: fields.get('radio') });
    const request = ++consultaEstacionamientos;
    output.textContent = 'Buscando estacionamientos…';
    try {
      const point = await puntoDeBusqueda(fields.get('origen'), output);
      if (!output.isConnected || request !== consultaEstacionamientos) return;
      if (point) { params.set('lat', point.lat); params.set('lon', point.lon); }
      output.textContent = 'Buscando estacionamientos…';
      const data = await api('/api/estacionamientos?' + params);
      if (!output.isConnected || request !== consultaEstacionamientos) return;
      if (!data.disponible) { output.textContent = 'El inventario de estacionamientos todavía no está cargado.'; return; }
      output.innerHTML = `<p>${data.estacionamientos.length} estacionamientos en el inventario para esta búsqueda.</p>`
        + notaPrecision(point, Number(fields.get('radio')))
        + (data.estacionamientos.length ? '<ul>' + data.estacionamientos.map((r) => `<li>
          <strong>${esc(r.detalle)}</strong> · ${esc(r.barrio)}
          ${r.distancia_m == null ? '' : `· ${r.distancia_m} m en línea recta`}
          <button type="button" class="boton-texto" data-estacionamiento-lat="${r.lat}" data-estacionamiento-lon="${r.lon}" data-estacionamiento-texto="${esc(r.detalle)}">Ver en mapa</button>
          <a href="https://www.google.com/maps/dir/?api=1&amp;destination=${r.lat},${r.lon}" target="_blank" rel="noopener">Cómo llegar</a>
          </li>`).join('') + '</ul>' : '<p>La cobertura histórica puede ser incompleta.</p>')
        + `<p class="fuente">Fuente: <a href="${esc(data.fuente)}" target="_blank" rel="noopener">Buenos Aires Data</a>, ${esc(data.periodo)}. Las distancias no representan recorridos a pie.</p>`;
    } catch (error) {
      if (output.isConnected && request === consultaEstacionamientos) output.textContent = 'No se pudo completar la búsqueda. ' + error.message;
    }
  });
  let consultaCocheras = 0;
  $('#contenido').addEventListener('submit', async (e) => {
    if (e.target.id !== 'buscar-cocheras') return;
    e.preventDefault();
    const output = $('#resultado-cocheras');
    const fields = new FormData(e.target);
    const params = new URLSearchParams({ barrio: estado.seleccionado, radio: fields.get('radio'),
      moneda: fields.get('moneda'), presupuesto: fields.get('presupuesto') });
    const operacion = estado.operacion;
    const consulta = ++consultaCocheras;
    output.textContent = 'Buscando cocheras…';
    try {
      const punto = await puntoDeBusqueda(fields.get('origen'), output);
      if (!output.isConnected || consulta !== consultaCocheras) return;
      const aviso = punto?.aviso;
      if (punto) { params.set('lat', punto.lat); params.set('lon', punto.lon); }
      output.textContent = 'Buscando cocheras…';
      const data = await api('/api/cocheras?' + params);
      if (!output.isConnected || consulta !== consultaCocheras) return;
      if (!data.disponible) { output.textContent = 'El catálogo de cocheras está pendiente de incorporación.'; return; }
      output.innerHTML = data.avisos.length ? '<ul>' + data.avisos.map((r) =>
        `<li><a href="${esc(r.url)}" target="_blank" rel="noopener">${esc(r.direccion || r.barrio)}</a>
        · ${dinero(r.precio, r.moneda)} por mes
        · ${r.expensas == null ? 'Expensas no informadas' : `Expensas ${dinero(r.expensas, r.moneda_expensas)}`}
        ${r.distancia_m == null ? '' : `· aproximadamente ${r.distancia_m} m en línea recta`}
        · Captura ${esc(fechaCorta(r.capturado))}
        ${aviso && operacion === 'alquiler' ? costoMensual(aviso, r) : ''}</li>`).join('') + '</ul>'
        : 'Sin coincidencias en el catálogo para estos filtros.';
      output.innerHTML += notaPrecision(punto, Number(fields.get('radio')));
      if (punto) output.innerHTML += '<p class="fuente">Distancias aproximadas en línea recta desde el punto elegido hasta las ubicaciones publicadas.</p>';
    } catch (error) {
      if (output.isConnected && consulta === consultaCocheras) output.textContent = 'No se pudo consultar el catálogo. ' + error.message;
    }
  });

  $('#contenido').addEventListener('click', async (e) => {
    const estacionamiento = e.target.closest('[data-estacionamiento-lat]');
    if (estacionamiento) {
      const coords = [Number(estacionamiento.dataset.estacionamientoLon), Number(estacionamiento.dataset.estacionamientoLat)];
      mapa.flyTo({ center: coords, zoom: 17 });
      popupAviso.setLngLat(coords).setHTML(esc(estacionamiento.dataset.estacionamientoTexto) + '<p>Inventario sin fecha de relevamiento informada. Confirmá funcionamiento y cupos.</p>').addTo(mapa);
      if (celular()) plegarPanel(false);
      return;
    }
    const inmueble = e.target.closest('[data-inmueble]');
    if (inmueble) {
      estado.delitos.inmueble = inmueble.dataset.inmueble;
      estado.capas.add('delitos');
      estado.delitosDatos = null;
      renderChips(); renderPanel();
      await actualizarCapas();
      const pin = estado.delitosDatos?.inmueble;
      if (pin) { if (celular()) plegarPanel(false); encuadrarPin(pin); }
      return;
    }
    const ubicar = e.target.closest('[data-ubicar]');
    if (ubicar) {
      const aviso = estado.avisos.find((a) => a.id === ubicar.dataset.ubicar);
      if (aviso?.ubicacion) {
        if (celular()) plegarPanel(false);
        encuadrarPin(aviso);
        abrirPin(claveUbicacion(aviso));
      }
      return;
    }
    const tipoLugar = e.target.closest('[data-lugares-tipo]');
    if (tipoLugar) {
      if (tipoLugar.dataset.lugaresTipo !== estado.lugares.tipo) {
        estado.lugares.tipo = tipoLugar.dataset.lugaresTipo;
        if (estado.lugares.fase === 'inicial') renderFicha(); else cargarLugares();
      }
      return;
    }
    if (e.target.closest('#cargar-lugares')) { cargarLugares(); return; }
    if (e.target.closest('#lugares-todos')) { estado.lugares.todos = true; renderFicha(); return; }
    if (e.target.closest('#lugares-menos')) { estado.lugares.minResenas = MIN_RESENAS_BAJO; renderFicha(); return; }
    const numero = e.target.closest('[data-radar-barrio]');
    if (numero) { detalleRadar(numero.dataset.radarBarrio, numero.dataset.radarTipo); return; }
    if (e.target.closest('[data-radar-fuentes]')) { detalleFuentesRadar(); return; }
    if (e.target.closest('[data-radar-sin-barrio]')) { detalleSinBarrio(); return; }
    const fila = e.target.closest('[data-barrio]');
    if (fila) { seleccionar(fila.dataset.barrio); return; }
    if (e.target.closest('#volver')) { seleccionar(null); return; }
    if (e.target.closest('[data-fuentes]')) { abrirFuentes(); return; }
    if (e.target.closest('#crear-alerta')) crearAlerta(e.target.closest('#crear-alerta'));
    if (e.target.closest('#ver-todos')) { estado.verTodos = true; renderFicha(); }
  });
  $('#contenido').addEventListener('toggle', (e) => {
    if (e.target.matches('.radar-lista')) estado.radarAbierto = e.target.open;
  }, true);
  $('#contenido').addEventListener('mouseover', (e) => {
    const fila = e.target.closest('.fila');
    marcarHover(fila ? fila.dataset.barrio : null, 'lista');
  });
  $('#contenido').addEventListener('mouseleave', () => marcarHover(null, 'lista'));

  $('#capas').addEventListener('click', (e) => {
    const chip = e.target.closest('[data-capa]');
    if (!chip) return;
    const clave = chip.dataset.capa;
    alternarCapa(clave);
    chip.setAttribute('aria-pressed', estado.capas.has(clave));
    renderPanel();
    actualizarCapas();
  });
  $('#capa-controles').addEventListener('change', (e) => {
    const control = e.target.dataset.control;
    if (control === 'nivel') cambiarNivel(e.target.value);
    if (['anio', 'tipo', 'franja', 'radio'].includes(control)) { estado.delitos[control] = e.target.value; actualizarCapas(); }
  });
  $('#capa-controles').addEventListener('click', (e) => {
    if (e.target.closest('[data-quitar-inmueble]')) { estado.delitos.inmueble = ''; actualizarCapas(); encuadrar(estado.seleccionado); }
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
  if (estado.prefs.has('escuelas')) cargarParecidos();
  if (EXPLORADOR && estado.seleccionado && explorador().cercania.includes('escuelas')) {
    cargarAvisos().then(renderPanel).catch(() => {});
  }
}

async function crearAlerta(boton) {
  const salida = $('#estado-alerta');
  const campoMail = $('#mail-alerta');
  const email = campoMail ? campoMail.value.trim() : '';
  if (campoMail && email && !campoMail.checkValidity()) {
    salida.className = 'estado error';
    salida.textContent = 'Revisá el mail: no parece una dirección válida.';
    campoMail.focus();
    return;
  }
  boton.disabled = true;
  try {
    const { creada, correo } = await api(`/api/busquedas?${new URLSearchParams({ modo: estado.modo, operacion: estado.operacion })}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ barrio: estado.seleccionado, presupuesto: estado.presupuesto,
        superficie: estado.superficie, ambientes: estado.ambientes, moneda: estado.moneda,
        ambientes_o_mas: estado.ambientesOMas,
        ...(email ? { email, consentimiento: true } : {}) }),
    });
    const local = creada
      ? 'Alerta creada. Cuando entre un aviso nuevo que encaje, lo vas a ver en Mis alertas.'
      : 'Ya tenías una alerta con estos mismos filtros.';
    salida.className = correo && !correo.enviado ? 'estado error' : 'estado ok';
    salida.textContent = !correo ? local
      : correo.enviado ? `${local} También te vamos a escribir a ${email}.`
        : `${local} No se activó el aviso por correo: ${correo.motivo}`;
    if (correo && correo.enviado) campoMail.value = '';
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
        <td>${b.superficie} m²</td><td>${b.ambientes}${b.ambientes_o_mas ? ' o más' : ''}</td></tr>`).join('')}</tbody></table>
      <h3>Avisos nuevos que encajan</h3>
      ${alertas.length ? `<table class="tabla"><thead><tr><th>Barrio</th><th>Precio publicado</th><th>Cubierta</th><th>Amb.</th><th></th></tr></thead><tbody>
      ${alertas.map((a) => `<tr><td>${esc(a.barrio)}</td><td>${dinero(a.precio, a.moneda)}</td><td>${a.superficie} m²</td>
        <td>${a.ambientes}</td><td>${{ baja: 'Ya no está publicado', reservado: 'Reservado' }[a.estado]
          ?? (a.enlace ? `<a href="${esc(a.enlace)}" target="_blank" rel="noopener">Ver aviso</a>` : 'Ejemplo')}</td></tr>`).join('')}
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
  renderNecesidades();
  sincronizarControles();
  conectarEventos();
  renderChips();
  $('#contenido').innerHTML = '<p class="nota">Cargando barrios…</p>';
  try {
    await Promise.all([cargarEstado(), cargarBarrios(), cargarRadar()]);
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
