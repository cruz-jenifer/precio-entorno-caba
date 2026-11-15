"""Rasgos del aviso leídos de su título y su descripción, sin guardar el texto.

La descripción es del anunciante y suele traer sus teléfonos o correos: se lee en
memoria, se convierte en indicadores y se descarta. Cada indicador vale 1 si el aviso
lo menciona, 0 si hay texto pero no lo menciona (o lo niega: «sin balcón», «no apto
crédito») y queda sin dato si no hay texto. Un 0 no prueba que la unidad no lo tenga.
"""

import html
import re
import unicodedata

# Columna de la base → (nombre en castellano, patrones sobre texto sin tildes ni mayúsculas).
TRAITS = {
    'new_build': ('a_estrenar', (r'\b(a|para) estrenar\b', r'\bnunca habitad[oa]\b')),
    'needs_renovation': ('a_reciclar', (r'\b(a|para) (reciclar|refaccionar|remodelar|renovar)\b',
                                         r'\b(necesita|requiere) (refacciones|reciclaje|arreglos)\b')),
    'mortgage_eligible': ('apto_credito', (r'\bapt[oa]s?\s+(a\s+|para\s+)?(credito|hipotec\w*)\b',
                                           r'\bacepta\s+credito\b')),
    'balcony': ('balcon', (r'\bbalcon(es)?\b',)),
    'terrace': ('terraza', (r'\bterrazas?\b',)),
    'patio': ('patio', (r'\bpatio(s)?\b(?!\s+de\s+(luz|aire))',)),
    'amenities': ('amenities', (r'\bamenities\b', r'\b(pileta|piscina|gimnasio|gym|solarium)\b',
                                r'\bs\.?u\.?m\.?(?=[\s,.;)]|$)', r'\bsalon de usos multiples\b')),
    'bright': ('luminoso', (r'\bluminos[oa]s?\b', r'\b(muy buena|mucha|excelente) (luz|luminosidad)\b')),
    'rear_facing': ('contrafrente', (r'\bcontra\s*-?\s*frente\b', r'\bc/\s?frente\b')),
}
DESCRIPTION_FIELDS = tuple(TRAITS)
SPANISH_NAMES = {spanish: column for column, (spanish, _) in TRAITS.items()}
# Una mención precedida por estas palabras (con hasta una palabra en medio) no cuenta.
NEGATION = re.compile(r'\b(sin|no|ni|poco|nada|tampoco)\s+(\w+\s+)?$')
CON_O_SIN = re.compile(r'\bcon o sin\s+(\w+\s+)?$')   # «con o sin terraza»: la ofrece.
COMPILED = {column: [re.compile(p) for p in patterns] for column, (_, patterns) in TRAITS.items()}


def normalize(text):
    """Minúsculas, sin tildes, sin etiquetas HTML y con espacios simples."""
    text = html.unescape(re.sub(r'<[^>]+>', ' ', str(text or '')))
    text = unicodedata.normalize('NFKD', text.casefold())
    text = ''.join(ch for ch in text if not unicodedata.combining(ch))
    return re.sub(r'\s+', ' ', text).strip()


def mentions(text, patterns):
    for pattern in patterns:
        for match in pattern.finditer(text):
            before = text[max(0, match.start() - 30):match.start()]
            if not NEGATION.search(before) or CON_O_SIN.search(before):
                return True
    return False


def traits(*texts):
    """{columna: 1, 0 o None} a partir de los textos del aviso (título, descripción)."""
    text = normalize(' . '.join(str(t) for t in texts if t))
    if not text:
        return {column: None for column in DESCRIPTION_FIELDS}
    return {column: int(mentions(text, COMPILED[column])) for column in DESCRIPTION_FIELDS}
