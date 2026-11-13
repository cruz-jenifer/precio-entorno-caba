/* Pruebas de estado y respuestas asíncronas, sin navegador ni solicitudes externas. */
const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

function runtime() {
  const elements = new Map();
  const context = vm.createContext({
    URLSearchParams, Intl, Set, Map, console,
    window: { matchMedia: () => ({ matches: false }) },
    localStorage: { getItem: () => null },
    document: { querySelector: (id) => {
      if (!elements.has(id)) elements.set(id, { innerHTML: '', hidden: false, querySelector: () => null });
      return elements.get(id);
    } },
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
  return { run: (code) => vm.runInContext(code, context), elements };
}

function payload() {
  return {
    disponible: true, anios: [2024, 2025], persistencia: { disponible: true, definicion: 'Regla' },
    celdas: { type: 'FeatureCollection', features: [
      { properties: { por_anio: { 2024: 8, 2025: 5 }, anios_altos: [2024, 2025], persistente: true } },
      { properties: { por_anio: { 2024: 70, 2025: 0 }, anios_altos: [2024], persistente: false } },
    ] },
    inmueble: { id: '<pin>', precision_m: 50 }, unidad: 'Hechos registrados',
    resumen_radios: [
      { anio: 2024, radio_m: 500, tipo: 'robo', diurno: 3, nocturno: 5, sin_dato: 0, total: 8 },
      { anio: 2025, radio_m: 500, tipo: 'robo', diurno: 1, nocturno: 4, sin_dato: 0, total: 5 },
    ],
    cobertura: [{ anio: 2024, meses_observados: [1] }], limitaciones: ['Límite'], fuentes: [], calidad: {},
  };
}

test('la persistencia excluye un pico aislado y la vista anual usa una escala fija', async () => {
  const { run } = runtime();
  run(`estado.seleccionado = 'Caballito'; api = async () => (${JSON.stringify(payload())});`);
  assert.equal(await run('cargarDelitos()'), true);
  assert.equal(run('estado.delitos.anio'), 'persistencia');
  assert.equal(run('estado.delitosDatos.celdas.features.length'), 1);
  assert.equal(run('estado.delitosDatos.celdas.features[0].properties.paso'), 2);
  run("estado.delitos.anio = '2024';");
  await run('cargarDelitos()');
  assert.equal(run('estado.delitosDatos.celdas.features.length'), 2);
  assert.equal(run('estado.delitosDatos.celdas.features[1].properties.paso'), 4);
  run("estado.delitos.anio = '2025';");
  await run('cargarDelitos()');
  assert.equal(run('estado.delitosDatos.celdas.features.length'), 1);
  assert.equal(run('estado.delitosDatos.celdas.features[0].properties.hechos'), 5);
});

test('una respuesta atrasada no reemplaza el tipo y horario más recientes', async () => {
  const { run } = runtime();
  run("const pendientes = []; api = () => new Promise((resolve) => pendientes.push(resolve));");
  const old = run('cargarDelitos()');
  run("estado.delitos.tipo = 'hurto'; estado.delitos.franja = 'nocturno';");
  const recent = run('cargarDelitos()');
  run(`pendientes[1](${JSON.stringify(payload())});`);
  assert.equal(await recent, true);
  run("pendientes[0]({ disponible: false, motivo: 'Respuesta anterior' });");
  assert.equal(await old, false);
  assert.equal(run('estado.delitosDatos.disponible'), true);
});

test('el gráfico respeta la franja y la ficha distingue el alcance de la tabla completa', async () => {
  const { run } = runtime();
  run(`api = async () => (${JSON.stringify(payload())}); estado.capas.add('delitos'); estado.delitos.tipo = 'robo'; estado.delitos.franja = 'nocturno';`);
  await run('cargarDelitos()');
  const html = run('renderAnalisisDelitos()');
  assert.match(html, /horario nocturno/);
  assert.match(html, /<strong>5<\/strong>/);
  assert.match(html, /<strong>4<\/strong>/);
  assert.match(html, /sin filtros de tipo ni franja/);
  assert.match(html, /&lt;pin&gt;/);
});

test('la demo informa indisponibilidad sin pintar celdas reales', async () => {
  const { run } = runtime();
  run("estado.modo = 'demo'; estado.capas.add('delitos'); api = async () => ({disponible: false, motivo: 'Los avisos ficticios no se cruzan con delitos reales.'});");
  await run('cargarDelitos()');
  assert.match(run('renderAnalisisDelitos()'), /ficticios/);
  assert.equal(run('estado.delitosDatos.disponible'), false);
});
