/* Pruebas de la página de precios, sin navegador ni solicitudes externas. */
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

test('los precios se muestran en pesos con el dólar de referencia y el recomendado es Buscar', () => {
  const run = runtime();
  const html = run('renderPrecios()');
  assert.ok(html.includes('ARS 13.000') && html.includes('≈ USD 9'));
  assert.ok(html.includes('ARS 42.000') && html.includes('≈ USD 29'));
  assert.ok(html.includes('Gratis'));
  assert.ok(html.includes('ARS 1.450 por USD'));
  // El nivel más caro va primero (ancla) y el recomendado es Buscar.
  const orden = run('PRECIOS.niveles.map((n) => n.id)');
  assert.deepEqual(orden, ['acompanado', 'buscar', 'explorar']);
  assert.deepEqual(run('PRECIOS.niveles.filter((n) => n.recomendado).map((n) => n.id)'), ['buscar']);
});

test('la página responde las dudas y no promete una tasación', () => {
  const html = runtime()('renderPrecios()');
  for (const texto of ['No es una tasación', 'Nadie paga para aparecer', 'sin renovación automática',
    'Garantía Tres Avisos', 'Hoy no cobramos']) {
    assert.ok(html.includes(texto), texto);
  }
});

test('cada nivel tiene su botón y el pesos coincide con el dólar al tipo de cambio de referencia', () => {
  const run = runtime();
  const niveles = run('PRECIOS.niveles');
  const tc = run('PRECIOS.tipoCambio');
  const html = run('renderPrecios()');
  for (const n of niveles) {
    assert.ok(html.includes(`data-anotarme="${n.id}"`), n.id);
    if (n.ars) assert.ok(Math.abs(n.ars / tc - n.usd) < 0.5, `${n.id}: ${n.ars} ARS vs USD ${n.usd}`);
  }
});

test('el nivel anotado por defecto es el recomendado', () => {
  const run = runtime();
  assert.equal(run('nivelInteres().id'), 'buscar');
  assert.equal(run('(estado.interes = "acompanado", nivelInteres().id)'), 'acompanado');
});
