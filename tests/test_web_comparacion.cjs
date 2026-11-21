const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');

function runtime() {
  const context = vm.createContext({
    Intl, URLSearchParams, Set, Map, console,
    window: { matchMedia: () => ({ matches: false }), location: { search: '' } },
    localStorage: { getItem: () => null },
    document: { querySelector: () => null, querySelectorAll: () => [] },
  });
  const source = fs.readFileSync(path.join(__dirname, '../web/app.js'), 'utf8');
  vm.runInContext(source.replace(/iniciar\(\);\s*$/, ''), context);
  return (code) => JSON.parse(JSON.stringify(vm.runInContext(code, context)));
}

test('la comparación distingue cero, dato faltante y cobertura insuficiente', () => {
  const run = runtime();
  assert.equal(run("datoComparacion('verdes', null)"), 'Sin datos de entorno');
  assert.equal(run("datoComparacion('verdes', {verdes_cantidad:0, verdes_ha:0})"), '0 espacios · 0 ha');
  assert.equal(run("datoComparacion('verdes', {verdes_cantidad:0})"), 'Sin dato');
  assert.equal(run("datoComparacion('ruido', {ruido:{diurno:{alto:0}}})"), '0 % de celdas con 70 dBA o más de día');
  assert.equal(run("datoComparacion('ruido', {ruido:{diurno:{alto:null}}})"), 'Sin cobertura suficiente');
});

test('las filas siguen las preferencias y el nivel escolar elegidos', () => {
  const run = runtime();
  assert.deepEqual(run("(estado.prefs = new Set(['ruido','escuelas']), preferenciasComparacion().map(p=>p.clave))"), ['escuelas', 'ruido']);
  assert.equal(run("(estado.nivel='secundario', datoComparacion('escuelas',{escuelas:{primario:{Estatal:20},secundario:{Privada:3}}}))"), '3 de nivel secundario');
  assert.deepEqual(run("(estado.prefs.clear(), preferenciasComparacion())"), []);
});

test('sin coincidencias no se inventa mediana y la demo mantiene su identificación', () => {
  const run = runtime();
  const html = run(`estado.modo='demo'; estado.comparando=new Set(['Almagro','Caballito']);
    estado.prefs=new Set(['subte']); estado.barrios=[
      {barrio:'Almagro',coincidencias:0,avisos:3,mediana:null},
      {barrio:'Caballito',coincidencias:1,avisos:2,mediana:100000}]; renderComparacion()`);
  assert.ok(html.includes('Sin avisos que encajen'));
  assert.ok(html.includes('USD 100.000'));
  assert.ok(html.includes('Avisos ficticios de ejemplo'));
  assert.ok(html.includes('Sin datos de entorno'));
  assert.ok(!html.includes('USD 0'));
  assert.ok(!html.includes('Plazas y parques'));
});
