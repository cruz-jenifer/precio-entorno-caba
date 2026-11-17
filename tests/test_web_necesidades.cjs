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
  assert.deepEqual(r.capas, ['subte', 'verdes', 'escuelas', 'salud', 'ruido']);
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

test('sin el interruptor la app sigue igual: capas de «Lo que me importa» y nada recordado', () => {
  const run = runtime('', { prefs: ['subte'], necesidades: ['familia'], apagadas: ['subte'] });
  assert.equal(run('EXPLORADOR'), false);
  assert.deepEqual(run('[...capasIniciales()]'), ['subte']);
  assert.deepEqual(run('[...estado.necesidades]'), []);
  run("estado.seleccionado = 'Almagro'; estado.capas = capasIniciales(); alternarCapa('subte');");
  assert.deepEqual(run('[...estado.prefs]'), ['subte']);   // apagar un chip no cambia las preferencias
});

test('con el interruptor, apagar una capa sugerida dura al cambiar de barrio', () => {
  const run = runtime('?explorador=1', { prefs: ['verdes'], necesidades: ['sin_auto'] });
  assert.equal(run('EXPLORADOR'), true);
  assert.deepEqual(run('[...capasIniciales()]'), ['subte', 'verdes']);
  run("estado.seleccionado = 'Almagro'; estado.capas = capasIniciales(); alternarCapa('subte');");
  assert.deepEqual(run('[...capasIniciales()]'), ['verdes']);
  run("alternarCapa('subte');");                            // volver a prenderla la recupera
  assert.deepEqual(run('[...capasIniciales()]'), ['subte', 'verdes']);
  assert.deepEqual(run('[...estado.apagadas]'), []);
});

test('con el interruptor, prender un chip lo suma a «Lo que me importa»; delitos no se recuerda', () => {
  const run = runtime('?explorador=1');
  run("estado.seleccionado = 'Almagro'; estado.capas = new Set(); alternarCapa('ruido'); alternarCapa('delitos');");
  assert.ok(run("estado.prefs.has('ruido')"));
  assert.ok(!run("estado.prefs.has('delitos')"));
  assert.ok(run("estado.capas.has('delitos')"));
});
