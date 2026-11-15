"""Perfil estático de la suite de pruebas de EIEInfo (no la ejecuta).

Uso: python3 -I tests_audit.py <ruta_repo>

Solo lee archivos (AST). Por cada archivo de pruebas reporta: clases, métodos
`test*`, clases que declaran `fixtures = [...]`, uso de `self.client`, de
`mock`/`patch`, pruebas sin ninguna aserción, pruebas marcadas con skip y
aserciones por prueba. También cruza con la lista de apps que ejecuta el CI.
"""
import ast
import os
import re
import sys
from collections import Counter, defaultdict

REPO = sys.argv[1]
SRV = os.path.join(REPO, 'src', 'server')
TEST_RE = re.compile(r'(^|/)tests?(_[^/]*)?\.py$|/tests/')

drone = open(os.path.join(REPO, '.drone.yml'), encoding='utf-8').read()
m = re.search(r'^\s*- coverage run --source=(\S+) manage\.py test (.+)$', drone, re.M)
ci_source = m.group(1).split(',') if m else []
ci_apps = m.group(2).split() if m else []

rows = []
skips = []
fixtures_used = Counter()
for root, dirs, files in os.walk(SRV):
    dirs[:] = [d for d in dirs if d not in ('migrations', '__pycache__', 'static', 'node_modules', 'templates')]
    for f in files:
        p = os.path.join(root, f)
        rel = os.path.relpath(p, SRV)
        if not f.endswith('.py') or not TEST_RE.search(rel):
            continue
        src = open(p, encoding='utf-8', errors='replace').read()
        try:
            tree = ast.parse(src)
        except SyntaxError:
            continue
        r = Counter()
        r['loc'] = src.count('\n')
        bases = Counter()
        for c in tree.body:
            if not isinstance(c, ast.ClassDef):
                continue
            tests = [n for n in c.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
                     and n.name.startswith('test')]
            if not tests:
                continue
            r['clases'] += 1
            for b in c.bases:
                bases[ast.unparse(b).split('.')[-1]] += 1
            has_fix = False
            for n in c.body:
                if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'fixtures' for t in n.targets):
                    has_fix = True
                    if isinstance(n.value, (ast.List, ast.Tuple)):
                        for e in n.value.elts:
                            if isinstance(e, ast.Constant):
                                fixtures_used[(rel.split('/')[0], e.value)] += len(tests)
            cls_skip = any('skip' in ast.unparse(d) for d in c.decorator_list)
            for t in tests:
                r['tests'] += 1
                body = ast.unparse(t)
                n_assert = len(re.findall(r'\bself\.assert\w+\(|\bassert ', body)) + \
                    len(re.findall(r'\.assert_(called|not_called|any_call|has_calls)\w*\(', body))
                r['aserciones'] += n_assert
                r['sin_asercion'] += n_assert == 0
                r['con_fixture'] += has_fix
                r['usa_client'] += 'self.client' in body
                decs = ' '.join(ast.unparse(d) for d in t.decorator_list)
                r['usa_mock'] += bool(re.search(r'\bpatch\b|\bMock\b|MagicMock', decs + body))
                if cls_skip or 'skip' in decs or 'expectedFailure' in decs or 'skipTest(' in body:
                    r['skip'] += 1
                    reason = re.search(r"skip\w*\(\s*['\"]([^'\"]{0,90})", decs + body)
                    skips.append((rel, t.lineno, t.name, reason.group(1) if reason else ''))
        if r['tests']:
            rows.append((rel, r, dict(bases)))

print('CI ejecuta:', ' '.join(ci_apps))
print('CI mide cobertura de:', ' '.join(ci_source))
print('\nARCHIVO | LOC | clases | tests | con fixture | self.client | mock | sin aserción | skip | aserciones/test | en CI')
tot = Counter()
for rel, r, bases in sorted(rows, key=lambda x: -x[1]['tests']):
    app = rel.split('/')[0]
    tot.update(r)
    tot['en_ci'] += r['tests'] if app in ci_apps else 0
    print(f"{rel:45} {r['loc']:5} {r['clases']:3} {r['tests']:4} {r['con_fixture']:4} {r['usa_client']:4} "
          f"{r['usa_mock']:4} {r['sin_asercion']:3} {r['skip']:3} {r['aserciones'] / r['tests']:5.1f}  "
          f"{'sí' if app in ci_apps else 'NO'}  {bases}")
print('TOTAL', dict(tot))
print('\nFIXTURES DECLARADOS (app, archivo) -> nº de pruebas que dependen')
for (app, fx), n in sorted(fixtures_used.items(), key=lambda kv: -kv[1]):
    exists = any(fx in fs or fx + '.json' in fs for _, _, fs in os.walk(os.path.join(SRV, app)))
    gen = bool(re.search(rf'> {re.escape(app)}/fixtures/{re.escape(fx)}', drone))
    print(f'  {app:28} {fx:28} {n:4}  versionado={"sí" if exists else "no"}  generado_en_CI={"sí" if gen else "NO"}')
print('\nSKIPS')
for s in skips:
    print(f'  {s[0]}:{s[1]} {s[2]} — {s[3]}')
