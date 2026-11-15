"""Detección de funciones duplicadas en EIEInfo por análisis AST.

Uso: python3 -I duplication.py <ruta_repo> [min_lineas]

Solo lee archivos; no importa ni ejecuta código del repo auditado.
Se excluyen pruebas, migraciones y static/. Tres niveles:

  1. Clones exactos: mismo AST (ignora espacios, comentarios y docstrings).
  2. Clones estructurales: mismo AST después de anonimizar identificadores,
     atributos y constantes (el clásico "copiar, pegar y cambiar nombres").
  3. Homónimas parecidas: funciones con el mismo nombre en archivos distintos
     cuyo texto normalizado coincide en al menos un 80 % (difflib).
"""
import ast
import difflib
import os
import re
import sys
from collections import defaultdict

REPO = sys.argv[1]
MIN = int(sys.argv[2]) if len(sys.argv) > 2 else 8
SRV = os.path.join(REPO, 'src', 'server')
FUNC = (ast.FunctionDef, ast.AsyncFunctionDef)
TEST_RE = re.compile(r'(^|/)tests?(_[^/]*)?\.py$|/tests/')


def strip_doc(node):
    body = node.body
    if body and isinstance(body[0], ast.Expr) and isinstance(getattr(body[0], 'value', None), ast.Constant) \
            and isinstance(body[0].value.value, str):
        body = body[1:]
    return body


class Anon(ast.NodeTransformer):
    def visit_Name(self, n):
        return ast.copy_location(ast.Name(id='_', ctx=n.ctx), n)

    def visit_Attribute(self, n):
        self.generic_visit(n)
        n.attr = '_'
        return n

    def visit_Constant(self, n):
        return ast.copy_location(ast.Constant(value=0), n)

    def visit_arg(self, n):
        n.arg = '_'
        n.annotation = None
        return n

    def visit_keyword(self, n):
        self.generic_visit(n)
        n.arg = '_' if n.arg else None
        return n


funcs = []
for root, dirs, files in os.walk(SRV):
    dirs[:] = [d for d in dirs if d not in ('migrations', '__pycache__', 'static', 'node_modules', 'templates')]
    for f in files:
        p = os.path.join(root, f)
        if not f.endswith('.py') or TEST_RE.search(os.path.relpath(p, SRV)):
            continue
        src = open(p, encoding='utf-8', errors='replace').read()
        try:
            tree = ast.parse(src)
        except SyntaxError:
            continue
        for n in ast.walk(tree):
            if not isinstance(n, FUNC):
                continue
            length = n.end_lineno - n.lineno + 1
            if length < MIN:
                continue
            body = strip_doc(n)
            if not body:
                continue
            mod = ast.Module(body=body, type_ignores=[])
            exact = ast.dump(mod)
            import copy
            anon = ast.dump(Anon().visit(copy.deepcopy(mod)))
            funcs.append({'file': os.path.relpath(p, SRV), 'line': n.lineno, 'name': n.name, 'len': length,
                          'exact': exact, 'anon': anon, 'text': ast.unparse(mod)})


def groups(key):
    g = defaultdict(list)
    for x in funcs:
        g[x[key]].append(x)
    return sorted((v for v in g.values() if len(v) > 1),
                  key=lambda v: -sum(x['len'] for x in v))


def show(title, gs, limit=30):
    n_f = sum(len(g) for g in gs)
    redundant = sum(sum(x['len'] for x in g) - max(x['len'] for x in g) for g in gs)
    print(f'\n== {title}: {len(gs)} grupos, {n_f} funciones, {redundant} líneas redundantes')
    for g in gs[:limit]:
        print(f"  [{len(g)} copias, {g[0]['len']} líneas c/u aprox.]")
        for x in g:
            print(f"     {x['file']}:{x['line']} {x['name']} ({x['len']})")


print(f'Funciones de producción con al menos {MIN} líneas: {len(funcs)}')
ex = groups('exact')
show('CLONES EXACTOS', ex)
exact_keys = {x['exact'] for g in ex for x in g}
st = [g for g in groups('anon') if len({x['exact'] for x in g}) > 1]
show('CLONES ESTRUCTURALES (identificadores y constantes anonimizados)', st, 40)

by_name = defaultdict(list)
for x in funcs:
    by_name[x['name']].append(x)
print('\n== HOMÓNIMAS PARECIDAS (>= 80 %, archivos distintos, no exactas)')
rows = []
for name, xs in by_name.items():
    for i, a in enumerate(xs):
        for b in xs[i + 1:]:
            if a['file'] == b['file'] or a['exact'] == b['exact']:
                continue
            r = difflib.SequenceMatcher(None, a['text'], b['text'], autojunk=False).ratio()
            if r >= 0.8:
                rows.append((r, a, b))
for r, a, b in sorted(rows, key=lambda t: -min(t[1]['len'], t[2]['len'])):
    print(f"  {r:.2f}  {a['file']}:{a['line']} ({a['len']})  ~  {b['file']}:{b['line']} ({b['len']})  {a['name']}")
print(f'  total pares: {len(rows)}')
