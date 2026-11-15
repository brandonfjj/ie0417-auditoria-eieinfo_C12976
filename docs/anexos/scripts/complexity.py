"""Complejidad ciclomática (McCabe) por función de EIEInfo, por análisis AST.

Uso: python3 -I complexity.py <ruta_repo> <salida.json>

Solo lee archivos; no importa ni ejecuta código del repo auditado.

Reglas de conteo (las mismas que usa radon, para que las cifras sean comparables):
  CC = 1
     + 1 por cada if / elif / expresión condicional (IfExp)
     + 1 por cada for / while (+1 si tiene else)
     + 1 por cada except (+1 si el try tiene else)
     + (n - 1) por cada operación booleana de n operandos (and / or)
     + 1 por cada generador de una comprensión, + 1 por cada if de la comprensión
     + 1 por cada case de un match
Las funciones anidadas se miden por separado y no suman a la función que las contiene.
Se excluyen pruebas (tests*.py, tests/), migraciones y static/.
"""
import ast
import json
import os
import re
import sys
from collections import defaultdict

REPO = sys.argv[1]
OUT = sys.argv[2]
SRV = os.path.join(REPO, 'src', 'server')
FUNC = (ast.FunctionDef, ast.AsyncFunctionDef)
TEST_RE = re.compile(r'(^|/)tests?(_[^/]*)?\.py$|/tests/')


def cc_of(func):
    """Complejidad de una función sin descender a funciones o clases anidadas."""
    total = 1
    stack = list(ast.iter_child_nodes(func))
    while stack:
        n = stack.pop()
        if isinstance(n, FUNC + (ast.ClassDef, ast.Lambda)):
            continue
        if isinstance(n, (ast.If, ast.IfExp)):
            total += 1
        elif isinstance(n, (ast.For, ast.AsyncFor, ast.While)):
            total += 1 + bool(n.orelse)
        elif isinstance(n, ast.Try):
            total += len(n.handlers) + bool(n.orelse)
        elif isinstance(n, ast.BoolOp):
            total += len(n.values) - 1
        elif isinstance(n, ast.comprehension):
            total += 1 + len(n.ifs)
        elif isinstance(n, ast.Match):
            total += len(n.cases)
        stack.extend(ast.iter_child_nodes(n))
    return total


def walk_funcs(node, prefix=''):
    """Genera (nombre calificado, nodo) de toda función, incluidas métodos y anidadas."""
    for child in ast.iter_child_nodes(node):
        if isinstance(child, FUNC):
            name = prefix + child.name
            yield name, child
            yield from walk_funcs(child, name + '.<local>.')
        elif isinstance(child, ast.ClassDef):
            yield from walk_funcs(child, prefix + child.name + '.')
        else:
            yield from walk_funcs(child, prefix)


funcs = []
per_file = {}
for root, dirs, files in os.walk(SRV):
    dirs[:] = [d for d in dirs if d not in ('migrations', '__pycache__', 'static', 'node_modules', 'templates')]
    for f in files:
        if not f.endswith('.py'):
            continue
        p = os.path.join(root, f)
        rel = os.path.relpath(p, REPO)
        if TEST_RE.search(os.path.relpath(p, SRV)):
            continue
        src = open(p, encoding='utf-8', errors='replace').read()
        try:
            tree = ast.parse(src)
        except SyntaxError:
            per_file[rel] = {'error': 'SyntaxError'}
            continue
        loc = src.count('\n')
        fl = []
        for name, node in walk_funcs(tree):
            cc = cc_of(node)
            length = node.end_lineno - node.lineno + 1
            fl.append({'file': rel, 'line': node.lineno, 'name': name, 'cc': cc, 'len': length})
        funcs += fl
        per_file[rel] = {
            'loc': loc, 'n_funcs': len(fl),
            'cc_sum': sum(x['cc'] for x in fl),
            'cc_max': max((x['cc'] for x in fl), default=0),
            'n_cc_gt10': sum(1 for x in fl if x['cc'] > 10),
            'n_cc_gt20': sum(1 for x in fl if x['cc'] > 20),
        }

per_app = defaultdict(lambda: {'n_funcs': 0, 'cc_sum': 0, 'cc_max': 0, 'n_cc_gt10': 0, 'n_cc_gt20': 0,
                               'n_len_gt100': 0, 'len_max': 0})
for x in funcs:
    app = x['file'].split('/')[2]
    a = per_app[app]
    a['n_funcs'] += 1
    a['cc_sum'] += x['cc']
    a['cc_max'] = max(a['cc_max'], x['cc'])
    a['n_cc_gt10'] += x['cc'] > 10
    a['n_cc_gt20'] += x['cc'] > 20
    a['n_len_gt100'] += x['len'] > 100
    a['len_max'] = max(a['len_max'], x['len'])
for a in per_app.values():
    a['cc_mean'] = round(a['cc_sum'] / a['n_funcs'], 2) if a['n_funcs'] else 0

funcs.sort(key=lambda x: (-x['cc'], x['file'], x['line']))
by_len = sorted(funcs, key=lambda x: (-x['len'], x['file'], x['line']))
out = {
    'resumen': {
        'n_funcs': len(funcs),
        'cc_gt10': sum(1 for x in funcs if x['cc'] > 10),
        'cc_gt20': sum(1 for x in funcs if x['cc'] > 20),
        'cc_gt50': sum(1 for x in funcs if x['cc'] > 50),
        'len_gt100': sum(1 for x in funcs if x['len'] > 100),
    },
    'por_app': dict(per_app),
    'por_archivo': per_file,
    'top_cc': funcs[:40],
    'top_len': by_len[:25],
}
json.dump(out, open(OUT, 'w'), indent=1, ensure_ascii=False)

print('RESUMEN', out['resumen'])
print('\nPOR APP (funcs | cc_media | cc_max | >10 | >20 | len>100 | len_max)')
for app, a in sorted(per_app.items(), key=lambda kv: -kv[1]['cc_sum']):
    print(f"{app:32} {a['n_funcs']:5} {a['cc_mean']:6} {a['cc_max']:4} {a['n_cc_gt10']:4} {a['n_cc_gt20']:4} {a['n_len_gt100']:4} {a['len_max']:5}")
print('\nTOP 25 CC')
for x in funcs[:25]:
    print(f"{x['cc']:4} {x['len']:5}  {x['file']}:{x['line']}  {x['name']}")
print('\nTOP 15 LONGITUD')
for x in by_len[:15]:
    print(f"{x['len']:5} {x['cc']:4}  {x['file']}:{x['line']}  {x['name']}")
print('\nTOP 15 ARCHIVOS POR CC ACUMULADA')
for rel, d in sorted(per_file.items(), key=lambda kv: -kv[1].get('cc_sum', 0))[:15]:
    print(f"{d['cc_sum']:5} {d['loc']:5} {d['n_funcs']:4} max={d['cc_max']:3} >10={d['n_cc_gt10']:3}  {rel}")
