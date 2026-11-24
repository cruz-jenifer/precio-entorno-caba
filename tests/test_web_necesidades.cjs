/* Pruebas del catálogo y las reglas del explorador de necesidades, sin navegador ni solicitudes externas. */
const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

function runtime(search = '', guardado = null) {
  const elements = new Map();
  const element = () => ({
    innerHTML: '', hidden: false, value: '', textContent: '', options: [], classList: { toggle() {} },
    querySelector: () => null, setAttribute() {}, add() {},
  });
  const context = vm.createContext({
    URLSearchParams, Intl, Set, Map, console, Option: class {},
    window: { matchMedia: () => ({ matches: false }), location: { search } },
    localStorage: { getItem: () => (guardado ? JSON.stringify(guardado) : null), setItem() {} },
    document: {
      querySelector: (id) => {
        if (!elements.has(id)) elements.set(id, element());
        return elements.get(id);
      },
      querySelectorAll: () => [],
    },
    ResizeObserver: class { observe() {} },
    maplibregl: {
      Map: class {
        constructor() { this.touchZoomRotate = { disableRotation() {} }; }
        addControl() {} on() {} getSource() { return null; }
      },
      NavigationControl: class {}, Popup: class { on() { return this; } remove() { return this; } },
    },
  });
  const source = fs.readFileSync(path.join(__dirname, '../web/app.js'), 'utf8');
  vm.runInContext(source.replace(/iniciar\(\);\s*$/, ''), context);
  return (code) => JSON.parse(JSON.stringify(vm.runInContext(code, context) ?? null));
}

const resolver = (run, necesidades, encendidas = [], apagadas = []) => run(`resolverNecesidades(
  new Set(${JSON.stringify(necesidades)}),
  { encendidas: new Set(${JSON.stringify(encendidas)}), apagadas: new Set(${JSON.stringify(apagadas)}) })`);

test('sin necesidades quedan solo las capas elegidas a mano', () => {
  const run = runtime();
  const r = resolver(run, [], ['verdes', 'subte']);
  assert.deepEqual(r.capas, ['subte', 'verdes']);          // orden del mapa, no el de la elección
  assert.deepEqual(r.columnas, []);
  assert.deepEqual(r.origen, { subte: ['manual'], verdes: ['manual'] });
  assert.deepEqual(resolver(run, []).capas, []);
});

test('una necesidad suma sus capas, columnas y advertencias, sin filtros', () => {
  const run = runtime();
  const r = resolver(run, ['familia']);
  assert.deepEqual(r.capas, ['verdes', 'escuelas', 'salud']);
  assert.deepEqual(r.cercania, ['verdes', 'escuelas', 'salud']);
  assert.ok(r.columnas.includes('escuela') && r.columnas.includes('balcon'));
  assert.ok(r.advertencias.some((a) => a.includes('vacante')));   // nota de la capa de escuelas
  assert.ok(!('filtros' in r));
});

test('varias necesidades se unen sin duplicados y guardan de dónde viene cada capa', () => {
  const run = runtime();
  const r = resolver(run, ['familia', 'teletrabajo', 'sin_auto'], ['subte']);
  assert.deepEqual(r.capas, ['subte', 'verdes', 'escuelas', 'salud', 'ruido', 'colectivos', 'bibliotecas', 'trenes']);
  assert.deepEqual(r.origen.subte, ['sin_auto', 'manual']);
  assert.equal(new Set(r.columnas).size, r.columnas.length);
  assert.equal(new Set(r.advertencias).size, r.advertencias.length);
});

test('la elección manual gana: una capa apagada no vuelve por una necesidad', () => {
  const run = runtime();
  const r = resolver(run, ['familia'], ['estacionamiento'], ['salud']);
  assert.deepEqual(r.capas, ['verdes', 'escuelas', 'estacionamiento']);
  assert.ok(!r.cercania.includes('estacionamiento'));   // sin distancia por aviso
});

test('el costo mensual no prende capas y una necesidad desconocida no hace nada', () => {
  const run = runtime();
  assert.deepEqual(resolver(run, ['costo_mensual']).capas, []);
  assert.deepEqual(resolver(run, ['costo_mensual']).columnas, ['precio', 'expensas', 'cocheras']);
  assert.deepEqual(resolver(run, ['inexistente']), resolver(run, []));
});

test('el explorador está encendido para todos; ?explorador=0 lo apaga', () => {
  assert.equal(runtime()('EXPLORADOR'), true);
  assert.equal(runtime('?explorador=1')('EXPLORADOR'), true);
  const run = runtime('', { prefs: [], necesidades: ['sin_escaleras'] });
  assert.deepEqual(run('[...estado.necesidades]'), ['sin_escaleras']);
  assert.equal(run('columnasExplorador()[0].titulo'), 'Acceso según el aviso');
});

test('con ?explorador=0 la app vuelve a la de antes: capas de «Lo que me importa» y nada recordado', () => {
  const run = runtime('?explorador=0', { prefs: ['subte'], necesidades: ['familia'], apagadas: ['subte'] });
  assert.equal(run('EXPLORADOR'), false);
  assert.deepEqual(run('[...capasIniciales()]'), ['subte']);
  assert.deepEqual(run('[...estado.necesidades]'), []);
  run("estado.seleccionado = 'Almagro'; estado.capas = capasIniciales(); alternarCapa('subte');");
  assert.deepEqual(run('[...estado.prefs]'), ['subte']);   // apagar un chip no cambia las preferencias
});

test('con el interruptor, apagar una capa sugerida dura al cambiar de barrio', () => {
  const run = runtime('?explorador=1', { prefs: ['verdes'], necesidades: ['sin_auto'] });
  assert.equal(run('EXPLORADOR'), true);
  assert.deepEqual(run('[...capasIniciales()]'), ['subte', 'verdes', 'colectivos', 'trenes']);
  run("estado.seleccionado = 'Almagro'; estado.capas = capasIniciales(); alternarCapa('subte');");
  assert.deepEqual(run('[...capasIniciales()]'), ['verdes', 'colectivos', 'trenes']);
  run("alternarCapa('subte');");                            // volver a prenderla la recupera
  assert.deepEqual(run('[...capasIniciales()]'), ['subte', 'verdes', 'colectivos', 'trenes']);
  assert.deepEqual(run('[...estado.apagadas]'), []);
});

test('con el interruptor, prender un chip lo suma a «Lo que me importa»; delitos no se recuerda', () => {
  const run = runtime('?explorador=1');
  run("estado.seleccionado = 'Almagro'; estado.capas = new Set(); alternarCapa('ruido'); alternarCapa('delitos');");
  assert.ok(run("estado.prefs.has('ruido')"));
  assert.ok(!run("estado.prefs.has('delitos')"));
  assert.ok(run("estado.capas.has('delitos')"));
});

test('las columnas siguen a las necesidades y a las capas prendidas', () => {
  const run = runtime('?explorador=1', { prefs: [], necesidades: ['familia', 'costo_mensual'], apagadas: ['salud'] });
  assert.deepEqual(run('columnasExplorador().map((c) => c.titulo)'),
    ['Escuela (primario)', 'Plaza', 'El texto menciona', 'Expensas']);   // salud apagada: sin CeSAC ni hospital
  run("estado.operacion = 'alquiler';");
  assert.equal(run('columnasExplorador().at(-1).titulo'), 'Por mes');
  assert.deepEqual(runtime('?explorador=0', { necesidades: ['familia'] })('columnasExplorador()'), []);   // apagado
});

test('los textos no confunden «no menciona» ni «sin ubicación» con «no tiene»', () => {
  const run = runtime('?explorador=1');
  const def = "COLUMNAS_DISTANCIA.subte";
  assert.equal(run(`celdaDistancia(${def}, { cercania: null })`), '—');
  assert.match(run(`celdaDistancia(${def}, { ubicacion: 'publicada', cercania: { subte: { m: 1250, estacion: 'X', linea: 'D' } } })`), /1,3 km · D/);
  assert.match(run(`celdaDistancia(${def}, { ubicacion: 'aproximada', cercania: { subte: { m: 80, estacion: 'X', linea: 'A' } } })`), /80 m.*aprox\./);
  assert.equal(run("celdaDistancia(COLUMNAS_DISTANCIA.ruido_diurno, { cercania: { ruido_diurno: { dba: null } } })"), 'Sin celda relevada');
  assert.match(run("celdaRasgos(['patio', 'balcon'], { rasgos: { patio: null, balcon: null } })"), /Sin texto/);
  assert.match(run("celdaRasgos(['patio', 'balcon'], { rasgos: { patio: 0, balcon: 0 } })"), /No los menciona/);
  assert.equal(run("celdaRasgos(['patio', 'balcon'], { rasgos: { patio: 1, balcon: 1 } })"), 'patio y balcón');
});

test('el costo por mes no suma monedas distintas ni inventa expensas', () => {
  const run = runtime('?explorador=1');
  assert.equal(run("porMes({ precio: 800000, moneda: 'ARS', expensas: 95000 })"), 'ARS 895.000');
  assert.equal(run("porMes({ precio: 900, moneda: 'USD', expensas: 95000 })"), 'USD 900 + ARS 95.000');
  assert.match(run("porMes({ precio: 800000, moneda: 'ARS', expensas: null })"), /expensas sin informar/);
});

test('«Me muevo sin auto» suma el subte con ascensor informado y el tren', () => {
  const run = runtime('?explorador=1', { prefs: [], necesidades: ['sin_auto'] });
  assert.deepEqual(run('columnasExplorador().map((c) => c.titulo)'), ['Subte', 'Subte con ascensor', 'Tren']);
  assert.match(run("NOTAS.subte"), /no indica si funcionan/);
});

test('«Voy a estudiar a una facultad» suma universidades, tren, subte y bibliotecas', () => {
  const run = runtime('', { prefs: [], necesidades: ['estudio'] });
  const r = run('explorador()');
  assert.deepEqual(r.capas, ['subte', 'bibliotecas', 'universidades', 'trenes']);
  assert.deepEqual(r.cercania, ['subte', 'bibliotecas', 'universidades', 'trenes']);
  assert.deepEqual(run('columnasExplorador().map((c) => c.titulo)'), ['Subte', 'Biblioteca', 'Universidad', 'Tren']);
  assert.ok(r.advertencias.some((a) => a.includes('oferta académica')));
  assert.ok(r.advertencias.some((a) => a.includes('2019')));
  const celda = (def, valor) => run(`celdaDistancia(COLUMNAS_DISTANCIA.${def}, { ubicacion: 'publicada', cercania: { ${def}: ${JSON.stringify(valor)} } })`);
  assert.match(celda('tren', { m: 400, estacion: 'Coghlan', linea: 'Mitre' }), /400 m · Mitre/);
  assert.match(celda('universidad', { m: 740, nombre: 'UBA', unidad: 'Facultad de Derecho' }), /740 m/);
  assert.equal(run("datoComparacion('trenes', { trenes: 2, trenes_lineas: ['Mitre', 'San Martín'] })"), '2 estaciones · Mitre, San Martín');
  assert.equal(run("datoComparacion('trenes', { trenes: 0, trenes_lineas: [] })"), 'Sin estaciones de tren');
  assert.equal(run("datoComparacion('universidades', { universidades: 19 })"), '19 sedes universitarias');
});

test('«Necesito evitar escaleras» suma acceso, subte con ascensor y salud, y pide preguntar', () => {
  const run = runtime('?explorador=1', { prefs: [], necesidades: ['sin_escaleras'] });
  const r = run('explorador()');
  assert.deepEqual(r.capas, ['subte', 'salud']);
  assert.deepEqual(run('columnasExplorador().map((c) => c.titulo)'),
    ['Acceso según el aviso', 'Subte con ascensor', 'CeSAC', 'Hospital']);
  assert.ok(r.advertencias.some((a) => a.includes('escalones entre la vereda y el ascensor')));
  assert.ok(r.advertencias.some((a) => a.includes('no significa que no tenga')));
});

test('el acceso distingue «dice que no», «no lo menciona» y «sin dato»', () => {
  const run = runtime('?explorador=1');
  const celda = (rasgos, piso = null) => run(`celdaAcceso(${JSON.stringify({ rasgos, piso })})`);
  assert.equal(celda({ ascensor: 1, sin_ascensor: 0, acceso_sin_escalones: 0 }), 'Ascensor');
  assert.equal(celda({ ascensor: 1, sin_ascensor: 0, acceso_sin_escalones: 1 }), 'Acceso sin escalones y ascensor');
  assert.equal(celda({ ascensor: 0, sin_ascensor: 1, acceso_sin_escalones: 0 }), 'Dice que no tiene ascensor');
  assert.equal(celda({ ascensor: 0, sin_ascensor: 1, acceso_sin_escalones: 0 }, 0), 'Planta baja; dice que no tiene ascensor');
  assert.equal(celda({ ascensor: null, sin_ascensor: null, acceso_sin_escalones: null }, 0), 'Planta baja');
  assert.match(celda({ ascensor: 0, sin_ascensor: 0, acceso_sin_escalones: 0 }), /No lo menciona/);
  assert.match(celda({ ascensor: null, sin_ascensor: null, acceso_sin_escalones: null }), /Sin dato/);
  assert.match(run('celdaAcceso({})'), /Sin dato/);
});

const HOSPITAL = { nombre: 'Hospital ficticio', lon: -58.43, lat: -34.62 };

test('«Tengo que ir seguido a un lugar» suma la distancia solo con un lugar elegido', () => {
  const sinLugar = runtime('?explorador=1', { prefs: [], necesidades: ['lugar_fijo'] });
  assert.deepEqual(sinLugar('columnasExplorador().map((c) => c.titulo)'), []);
  assert.ok(sinLugar('explorador()').advertencias.some((a) => a.includes('Lüga no lo recibe')));
  const run = runtime('?explorador=1', { prefs: [], necesidades: ['lugar_fijo', 'sin_escaleras'], lugarFijo: HOSPITAL });
  assert.deepEqual(run('columnasExplorador().map((c) => c.titulo)').slice(0, 2), ['A tu lugar fijo', 'Acceso según el aviso']);
  // Con el explorador apagado (?explorador=0), el lugar guardado no se usa.
  assert.equal(runtime('?explorador=0', { necesidades: ['lugar_fijo'], lugarFijo: HOSPITAL })('estado.lugarFijo'), null);
});

test('la distancia al lugar fijo es en línea recta y respeta la ubicación del aviso', () => {
  const run = runtime('?explorador=1', { prefs: [], necesidades: ['lugar_fijo'], lugarFijo: HOSPITAL });
  const norte = -34.62 + 1000 / 111320;   // 1 km al norte
  assert.equal(run(`Math.round(metrosEntre(-58.43, -34.62, -58.43, ${norte}))`), 1000);
  assert.equal(run(`celdaLugarFijo({ ubicacion: 'publicada', lon: -58.43, lat: ${norte} })`), '1 km');
  assert.match(run(`celdaLugarFijo({ ubicacion: 'aproximada', lon: -58.43, lat: ${norte} })`), /1 km.*aprox\./);
  assert.match(run('celdaLugarFijo({ ubicacion: null, lon: null, lat: null })'), /Sin ubicación/);
});

test('distancia de un punto a un barrio: 0 adentro, al borde afuera', () => {
  const run = runtime('?explorador=1');
  const d = 1000 / 111320;
  const cuadrado = JSON.stringify({ type: 'Polygon', coordinates: [[[-58.44, -34.63], [-58.42, -34.63], [-58.42, -34.61], [-58.44, -34.61], [-58.44, -34.63]]] });
  assert.equal(run(`metrosABarrio(-58.43, -34.62, ${cuadrado})`), 0);
  assert.equal(run(`Math.round(metrosABarrio(-58.43, ${-34.61 + d}, ${cuadrado}))`), 1000);
  const multi = JSON.stringify({ type: 'MultiPolygon', coordinates: [JSON.parse(cuadrado).coordinates] });
  assert.equal(run(`metrosABarrio(-58.43, -34.62, ${multi})`), 0);
  assert.equal(run('metrosABarrio(-58.43, -34.62, null)'), null);
});

test('el lugar fijo se valida, queda en el navegador y no viaja en los pedidos', () => {
  const run = runtime('?explorador=1', { prefs: [], necesidades: ['lugar_fijo'], lugarFijo: HOSPITAL });
  assert.equal(run("lugarValido({ nombre: 'Lejos', lon: -60, lat: -34.6 })"), null);
  assert.equal(run("lugarValido({ nombre: 'Sin coordenadas' })"), null);
  assert.equal(run(`lugarValido({ nombre: 'x'.repeat(300), lon: -58.43, lat: -34.62 }).nombre.length`), 120);
  const pedido = run('consulta().toString()');
  assert.ok(!pedido.includes('58.43') && !pedido.includes('34.62') && !pedido.includes('ficticio'));
});

test('«Necesito un lugar tranquilo» suma ruido de día y de noche, contrafrente y qué preguntar', () => {
  const run = runtime('?explorador=1', { prefs: [], necesidades: ['tranquilo'] });
  const r = run('explorador()');
  assert.deepEqual(r.capas, ['ruido']);
  assert.deepEqual(r.cercania, ['ruido']);
  assert.deepEqual(run('columnasExplorador().map((c) => c.titulo)'), ['Ruido de día', 'Ruido de noche', 'El texto menciona']);
  assert.ok(r.advertencias.some((a) => a.includes('doble vidrio')));
  assert.equal(run("celdaDistancia(COLUMNAS_DISTANCIA.ruido_nocturno, { cercania: { ruido_nocturno: { dba: 62 } } })"), '62 dBA');
  assert.equal(run("celdaDistancia(COLUMNAS_DISTANCIA.ruido_nocturno, { cercania: { ruido_nocturno: { dba: null } } })"), 'Sin celda relevada');
});

test('con la necesidad de silencio, cada barrio muestra la noche y se puede ordenar por ella', () => {
  const entorno = (dia, noche) => ({ subte_lineas: [], ruido: { diurno: { alto: dia }, nocturno: { alto: noche } } });
  const run = runtime('?explorador=1', { prefs: [], necesidades: ['tranquilo'] });
  assert.equal(run(`datoComparacion('ruido', ${JSON.stringify(entorno(0.5, 0.25))})`),
    '50 % de celdas con 70 dBA o más de día · 25 % con 65 dBA o más de noche');
  // Sin la necesidad, el texto de siempre.
  assert.equal(runtime('?explorador=1', { prefs: [] })(`datoComparacion('ruido', ${JSON.stringify(entorno(0.5, 0.25))})`),
    '50 % de celdas con 70 dBA o más de día');
  run(`estado.ordenBarrios = 'ruido'; estado.barrios = [
    { barrio: 'Ruidoso', coincidencias: 9, avisos: 9, mediana: 1, entorno: ${JSON.stringify(entorno(0.9, 0.8))} },
    { barrio: 'Sin dato', coincidencias: 9, avisos: 9, mediana: 1, entorno: null },
    { barrio: 'Tranquilo', coincidencias: 1, avisos: 1, mediana: 1, entorno: ${JSON.stringify(entorno(0.3, 0.1))} }];
    renderLista();`);
  const html = run("document.querySelector('#contenido').innerHTML");
  assert.ok(html.indexOf('Tranquilo') < html.indexOf('Ruidoso') && html.indexOf('Ruidoso') < html.indexOf('Sin dato'));
  assert.match(html, /Menos ruido de noche/);
});

test('resaltado de pines: fuerte si cumple todo lo elegido, tenue si no o sin dato, nada sin criterios', () => {
  const sin = runtime('', { prefs: [], necesidades: [] });
  assert.equal(sin('cumpleNecesidades({ rasgos: {} })'), null);
  const esc = runtime('', { prefs: [], necesidades: ['sin_escaleras'] });
  assert.equal(esc("cumpleNecesidades({ rasgos: { ascensor: 1, sin_ascensor: 0 } })"), true);
  assert.equal(esc("cumpleNecesidades({ rasgos: { ascensor: 0, sin_ascensor: 1 }, piso: 0 })"), true);   // planta baja
  assert.equal(esc("cumpleNecesidades({ rasgos: { ascensor: 0, sin_ascensor: 1 } })"), false);
  assert.equal(esc("cumpleNecesidades({ rasgos: { ascensor: null } })"), false);                         // sin dato: tenue
  const tranq = runtime('', { prefs: [], necesidades: ['tranquilo'] });
  assert.equal(tranq("cumpleNecesidades({ rasgos: {}, cercania: { ruido_nocturno: { dba: 60 } } })"), true);
  assert.equal(tranq("cumpleNecesidades({ rasgos: {}, cercania: { ruido_nocturno: { dba: 65 } } })"), false);
  assert.equal(tranq("cumpleNecesidades({ rasgos: { contrafrente: 1 }, cercania: { ruido_nocturno: { dba: 70 } } })"), true);
  const lugar = runtime('', { prefs: [], necesidades: ['lugar_fijo'], lugarFijo: HOSPITAL });
  const cerca = -34.62 + 1500 / 111320;
  const lejos = -34.62 + 2500 / 111320;
  assert.equal(lugar(`cumpleNecesidades({ rasgos: {}, ubicacion: 'publicada', lon: -58.43, lat: ${cerca} })`), true);
  assert.equal(lugar(`cumpleNecesidades({ rasgos: {}, ubicacion: 'publicada', lon: -58.43, lat: ${lejos} })`), false);
  assert.equal(lugar('cumpleNecesidades({ rasgos: {}, ubicacion: null, lon: null, lat: null })'), false);
  // Varias necesidades: tiene que cumplir todas.
  const dos = runtime('', { prefs: [], necesidades: ['sin_escaleras', 'tranquilo'] });
  assert.equal(dos("cumpleNecesidades({ rasgos: { ascensor: 1 }, cercania: { ruido_nocturno: { dba: 70 } } })"), false);
  assert.equal(dos('criteriosPines().length'), 2);
});

test('el mapa de barrios sigue al orden de la lista: más avisos, menos ruido de noche o cerca del lugar', () => {
  const entorno = (noche) => ({ ruido: { diurno: { alto: 0.5 }, nocturno: { alto: noche } } });
  const barrios = JSON.stringify([
    { barrio: 'A', coincidencias: 10, entorno: entorno(0.8) },
    { barrio: 'B', coincidencias: 5, entorno: entorno(0.2) },
    { barrio: 'C', coincidencias: 0, entorno: entorno(0.1) }]);
  const run = runtime('', { prefs: [], necesidades: ['tranquilo'] });
  run(`estado.barrios = ${barrios}; estado.ordenBarrios = 'avisos';`);
  assert.deepEqual(run('[...escalaBarrios().valores]'), [['A', 1], ['B', 0.5], ['C', 0]]);
  run("estado.ordenBarrios = 'ruido';");
  const e = run('({ orden: escalaBarrios().orden, v: [...escalaBarrios().valores] })');
  assert.equal(e.orden, 'ruido');
  assert.deepEqual(e.v, [['A', 0.001], ['B', 1], ['C', 0]]);   // C sin avisos que encajen: sin color
  // Sin la necesidad, el orden por ruido no vale y el mapa vuelve a contar avisos.
  const otro = runtime('', { prefs: [], necesidades: [] });
  otro(`estado.barrios = ${barrios}; estado.ordenBarrios = 'ruido';`);
  assert.equal(otro('ordenEfectivo()'), 'avisos');
  const cuadrado = { type: 'Polygon', coordinates: [[[-58.44, -34.63], [-58.42, -34.63], [-58.42, -34.61], [-58.44, -34.61], [-58.44, -34.63]]] };
  const conLugar = runtime('', { prefs: [], necesidades: ['lugar_fijo'], lugarFijo: HOSPITAL });
  conLugar(`estado.barrios = ${barrios}; estado.ordenBarrios = 'lugar';
    estado.formas = { features: [{ properties: { barrio: 'A' }, geometry: ${JSON.stringify(cuadrado)} }] };`);
  assert.deepEqual(conLugar('[...escalaBarrios().valores]'), [['A', 1], ['B', 0], ['C', 0]]);   // B sin forma: sin dato
});

test('«Me muevo en bici» prende ciclovías y Ecobici; «Trabajo desde casa» suma bibliotecas', () => {
  const run = runtime('?explorador=1', { prefs: [], necesidades: ['bicicleta', 'teletrabajo'] });
  const r = run('explorador()');
  assert.deepEqual(r.capas, ['ruido', 'ciclovias', 'ecobici', 'bibliotecas']);
  assert.deepEqual(r.cercania, ['ruido', 'ciclovias', 'ecobici', 'bibliotecas']);
  assert.deepEqual(run('columnasExplorador().map((c) => c.titulo)'),
    ['Ciclovía', 'Ecobici', 'Biblioteca', 'Ruido de día', 'El texto menciona']);
  assert.ok(r.advertencias.some((a) => a.includes('no garantiza un recorrido continuo')));
  assert.ok(r.advertencias.some((a) => a.includes('operativa')));
});

test('«Frente a parecidos» no se presenta como tasación y avisa cuando hay pocos', () => {
  const run = runtime();
  const celda = run(`celdaComparacion({ n: 15, posicion: 'debajo', precio_m2: 1622, mediana_m2: 1897, p25_m2: 1788,
    p75_m2: 2958, diferencia_pct: -14, criterios: ['mismo barrio y moneda'], sin_antiguedad: false }, 'USD')`);
  assert.match(celda, /Más bajo que la mayoría/);
  assert.match(celda, /−14 % vs\. mediana de 15 parecidos/);
  assert.match(celda, /USD 1\.622\/m²/);
  assert.match(run("celdaComparacion({ n: 3, posicion: null, motivo: 'Hay 3 avisos parecidos' }, 'USD')"), /Pocos parecidos/);
  assert.match(run('NOTA_COMPARACION'), /no es una tasación/);
  assert.equal(run("textoComparacion({ n: 9, posicion: 'dentro', diferencia_pct: 0 })"), 'En línea · 0 % vs. mediana de 9 parecidos');
  assert.match(run("textoComparacion({ n: 2, posicion: null })"), /Pocos avisos parecidos/);
});
