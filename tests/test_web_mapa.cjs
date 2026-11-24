const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');

function runtime() {
  const elements = new Map();
  const context = vm.createContext({
    Intl, URLSearchParams, Set, Map, console,
    window: { matchMedia: () => ({ matches: false }), location: { search: '' } },
    localStorage: { getItem: () => null },
    document: { querySelector: (id) => {
      if (!elements.has(id)) elements.set(id, { innerHTML: '', querySelector: () => null });
      return elements.get(id);
    } },
  });
  vm.runInContext(fs.readFileSync(path.join(__dirname, '../web/app.js'), 'utf8').replace(/iniciar\(\);\s*$/, ''), context);
  return { run: (code) => vm.runInContext(code, context), html: () => elements.get('#leyenda').innerHTML };
}

test('la leyenda general identifica conteos, ausencia de coincidencias y el alcance por barrio', () => {
  const { run, html } = runtime();
  run("estado.barrios=[{coincidencias:7},{coincidencias:0}];renderLeyenda()");
  assert.ok(html().includes('7 avisos'));
  assert.ok(html().includes('Sin avisos que encajen'));
  assert.ok(html().includes('no un mejor barrio'));
  assert.ok(html().includes('barrio oficial'));
});

test('todas las capas se pueden descubrir sin activar primero las adicionales', () => {
  const { run } = runtime();
  const claves = run('filaCapas().map(c=>c.clave)');
  assert.equal(claves.length, 18);
  assert.equal(new Set(claves).size, 18);
  for (const clave of ['subte','ruido','escuelas','delitos','colectivos','rampas','universidades','trenes']) assert.ok(claves.includes(clave));
});

test('la leyenda distingue una capa pendiente, no disponible y sin elementos', () => {
  const { run, html } = runtime();
  run("estado.seleccionado='Almagro';estado.capas=new Set(['verdes']);renderLeyenda()");
  assert.ok(html().includes('Datos pendientes de carga'));
  run("estado.capasDatos[claveCapa('verdes')]={disponible:false,features:[]};renderLeyenda()");
  assert.ok(html().includes('sin datos disponibles'));
  run("estado.capasDatos[claveCapa('verdes')]={disponible:true,features:[]};renderLeyenda()");
  assert.ok(html().includes('Sin elementos registrados'));
  assert.ok(!html().includes('Plaza o parque'));
});

test('el ruido nocturno muestra el umbral de noche y conserva la advertencia de alcance', () => {
  const { run, html } = runtime();
  run("estado.seleccionado='Almagro';estado.capas=new Set(['ruido']);estado.ruido='nocturno';estado.capasDatos[claveCapa('ruido')]={features:[{}]};renderLeyenda()");
  assert.ok(html().includes('Ruido de noche'));
  assert.ok(html().includes('65 dBA o más'));
  assert.ok(html().includes('No describe el interior de un departamento'));
});

test('la leyenda de delitos mantiene los años, la unidad geográfica y su límite de interpretación', () => {
  const { run, html } = runtime();
  run("estado.seleccionado='Almagro';estado.capas=new Set(['delitos']);estado.delitos.anio='persistencia';estado.delitosDatos={disponible:true,anios:[2024,2025],celdas:{features:[]}};renderLeyenda()");
  assert.ok(html().includes('Años 2024, 2025'));
  assert.ok(html().includes('celda de 200 m'));
  assert.ok(html().includes('probabilidad individual de victimización'));
});
