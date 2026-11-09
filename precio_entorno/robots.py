"""Lectura de robots.txt con comodines, según la especificación RFC 9309 que usa Google.

`urllib.robotparser` compara prefijos literales y no entiende `*` ni `$`. Con reglas como
`Disallow: /*?pagina-` dejaría pasar páginas prohibidas. Este lector:
- elige el grupo cuyo User-agent coincide con el producto del cliente y, si no hay, el de `*`;
- interpreta `*` como cualquier secuencia y `$` final como fin de la URL;
- aplica la regla más larga que coincide y, ante un empate, la de Allow.
"""

import re
from urllib.parse import unquote, urlsplit


def _pattern(path):
    anchored = path.endswith('$')
    body = path[:-1] if anchored else path
    regex = '.*'.join(re.escape(part) for part in body.split('*'))
    return re.compile(regex + ('$' if anchored else ''))


class Robots:
    def __init__(self, text='', user_agent='*'):
        self.product = user_agent.split('/')[0].strip().lower()
        self.groups = self._parse(text)
        self.rules = self._select()

    @staticmethod
    def _parse(text):
        groups, agents, rules, last = [], [], [], None
        for raw in text.splitlines():
            line = raw.split('#', 1)[0].strip()
            if ':' not in line:
                continue
            field, value = (part.strip() for part in line.split(':', 1))
            field = field.lower()
            if field == 'user-agent':
                if last == 'rule':
                    groups.append((agents, rules))
                    agents, rules = [], []
                agents.append(value.lower())
                last = 'agent'
            elif field in ('allow', 'disallow') and agents:
                if value:
                    rules.append((field == 'allow', value, _pattern(value)))
                last = 'rule'
        if agents:
            groups.append((agents, rules))
        return groups

    def _select(self):
        specific = [rules for agents, rules in self.groups
                    if any(a != '*' and a in self.product for a in agents)]
        if specific:
            return [rule for rules in specific for rule in rules]
        return [rule for agents, rules in self.groups if '*' in agents for rule in rules]

    def allowed(self, url):
        parts = urlsplit(url)
        target = unquote(parts.path or '/') + (f'?{unquote(parts.query)}' if parts.query else '')
        best = None
        for allow, raw, pattern in self.rules:
            if pattern.match(target):
                rank = (len(raw), allow)
                if best is None or rank > best[0]:
                    best = (rank, allow)
        return True if best is None else best[1]


def disallow_all():
    return Robots('User-agent: *\nDisallow: /')
