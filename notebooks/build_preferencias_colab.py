"""Genera el notebook autónomo del piloto con el contrato y las reglas del repo."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from precio_entorno.importing import BARRIOS

OUT = ROOT / 'notebooks/preferencias_qwen_colab.ipynb'


def markdown(source):
    return {'cell_type': 'markdown', 'metadata': {}, 'source': source.strip().splitlines(keepends=True)}


def code(source):
    return {'cell_type': 'code', 'metadata': {}, 'source': source.strip().splitlines(keepends=True),
            'execution_count': None, 'outputs': []}


def main():
    package = ROOT / 'precio_entorno'
    preferences = (package / 'preferencias.py').read_text(encoding='utf-8')
    contract = preferences.split('class Interprete:', 1)[0]
    contract = contract.replace('from .importing import BARRIOS', 'BARRIOS = ' + repr(BARRIOS))
    evaluator = (package / 'evaluar_preferencias.py').read_text(encoding='utf-8')
    score = evaluator[evaluator.index('def evaluar('):evaluator.index('\ndef main(')]
    cases = json.loads((ROOT / 'data/fixtures/preferencias_sinteticas.json').read_text(encoding='utf-8'))['casos']
    cells = [
        markdown('''
# Precio + Entorno CABA · Piloto Qwen3 4B

Compará Qwen3 4B con las reglas usando exclusivamente las 120 consultas sintéticas incluidas. En Colab, seleccioná **Entorno de ejecución → Cambiar tipo de entorno de ejecución → GPU** y ejecutá las celdas en orden. El modelo es público y se descarga sin clave. La GPU del plan gratuito depende de la disponibilidad.

El conjunto de desarrollo tiene 40 casos y sirve para ajustar el enfoque. Reservá los 80 de prueba para medir el resultado final. Los tiempos corresponden a la GPU que Colab asigne.
'''),
        code('%pip -q install transformers==4.57.6 accelerate==1.12.0 "pydantic>=2,<3" httpx'),
        markdown('## Contrato, reglas y evaluación del proyecto'),
        code(contract + '\n' + score),
        code('CASOS = ' + repr(cases) + '''
SPLIT = 'prueba'  # Usá 'desarrollo' para ajustar el enfoque.
casos = [c for c in CASOS if c['split'] == SPLIT]
base = evaluar(casos, reglas)
print('Reglas:', base)
'''),
        markdown('''
## Cargar el modelo

La primera ejecución descarga los pesos de Hugging Face. El código usa FP16 en GPU y desactiva el modo de razonamiento. Se registra la revisión exacta para identificar cada corrida.
'''),
        code('''
import torch
from huggingface_hub import model_info
from transformers import AutoModelForCausalLM, AutoTokenizer

if not torch.cuda.is_available():
    raise RuntimeError('Seleccioná un entorno con GPU y volvé a ejecutar el notebook.')

MODELO = 'Qwen/Qwen3-4B'
REVISION = model_info(MODELO, token=False).sha
tokenizer = AutoTokenizer.from_pretrained(MODELO, revision=REVISION, token=False)
model = AutoModelForCausalLM.from_pretrained(
    MODELO, revision=REVISION, dtype=torch.float16, device_map={'': 0}, token=False
).eval()
print(MODELO, REVISION, torch.cuda.get_device_name(0))
'''),
        markdown('''
## Ejecutar por tandas

Se solicita JSON y se valida contra el contrato del proyecto. Una salida inválida se contabiliza como error sin recurrir a las reglas. Cada tanda guarda resultados y tiempos por ID sin copiar las frases ni las respuestas completas. El archivo vive en la sesión de Colab. Descargalo antes de cerrar y volvé a subirlo para reanudar una corrida con la misma configuración.
'''),
        code('''
import hashlib
from IPython.display import FileLink, display

TANDA = 10
MAX_TOKENS = 512
PROMPT = INSTRUCCIONES + '\\nDevolvé exclusivamente un objeto JSON, sin Markdown, con este esquema:\\n' + json.dumps(
    Propuesta.model_json_schema(), ensure_ascii=False
)
identidad = json.dumps([MODELO, REVISION, SPLIT, MAX_TOKENS, PROMPT, casos], sort_keys=True)
huella = hashlib.sha256(identidad.encode()).hexdigest()[:16]
archivo = Path(f'preferencias-{SPLIT}-{huella}.json')
vacio = {'campos': [], 'dudas': [], 'no_soportadas': []}
resultados = json.loads(archivo.read_text()) if archivo.exists() else {}


def interpretar(texto):
    texto = depurar(texto)
    mensajes = [{'role': 'system', 'content': PROMPT}, {'role': 'user', 'content': texto}]
    rendered = tokenizer.apply_chat_template(mensajes, tokenize=False, add_generation_prompt=True,
                                             enable_thinking=False)
    entradas = tokenizer(rendered, return_tensors='pt', add_special_tokens=False).to(model.device)
    with torch.inference_mode():
        generado = model.generate(**entradas, do_sample=False, max_new_tokens=MAX_TOKENS)
    nuevo = generado[0, entradas.input_ids.shape[1]:]
    contenido = tokenizer.decode(nuevo, skip_special_tokens=True).strip()
    return validar(Propuesta.model_validate_json(contenido), texto)


pendientes = [c for c in casos if c['id'] not in resultados]
for offset in range(0, len(pendientes), TANDA):
    for caso in pendientes[offset:offset + TANDA]:
        inicio = time.perf_counter()
        try:
            resultado = interpretar(caso['texto']).model_dump()
            for items in resultado.values():
                for item in items:
                    item['evidencia'] = ''
            error = None
        except ValueError as exc:
            resultado = vacio
            error = type(exc).__name__
        resultados[caso['id']] = {'propuesta': resultado, 'error': error,
                                  'segundos': time.perf_counter() - inicio}
    temporal = archivo.with_suffix('.tmp')
    temporal.write_text(json.dumps(resultados, ensure_ascii=False), encoding='utf-8')
    temporal.replace(archivo)
    print(f'{len(resultados)}/{len(casos)} casos')
display(FileLink(str(archivo)))
'''),
        code('''
from math import ceil

ids = {c['texto']: c['id'] for c in casos}
assert set(resultados) == set(ids.values()), 'Completá todas las tandas.'
medicion = evaluar(casos, lambda texto: Propuesta.model_validate(resultados[ids[texto]]['propuesta']))
tiempos = sorted(r['segundos'] for r in resultados.values())
medicion['latencia_p95_segundos'] = tiempos[ceil(0.95 * len(tiempos)) - 1]
medicion['respuestas_invalidas'] = sum(r['error'] is not None for r in resultados.values())
pasa = (medicion['exactitud'] >= 0.95 and medicion['deteccion_dudas'] >= 0.95
        and medicion['cambios_silenciosos'] == 0 and medicion['exactitud'] > base['exactitud']
        and medicion['deteccion_dudas'] > base['deteccion_dudas'])
print(json.dumps({'modelo': MODELO, 'revision': REVISION, 'split': SPLIT, 'reglas': base,
                  'qwen': medicion, 'supera_criterios_de_calidad': pasa}, indent=2, ensure_ascii=False))
'''),
    ]
    notebook = {'cells': cells, 'metadata': {'accelerator': 'GPU', 'colab': {},
                'kernelspec': {'name': 'python3', 'display_name': 'Python 3'}},
                'nbformat': 4, 'nbformat_minor': 4}
    OUT.write_text(json.dumps(notebook, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
