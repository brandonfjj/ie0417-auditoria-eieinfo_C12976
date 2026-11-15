"""Inventario del modelo de dominio de EIEInfo por análisis AST.

Uso: python3 -I domain.py <ruta_repo> <salida.json>

Solo lee archivos; no importa ni ejecuta código del repo auditado.
Por cada clase de `models.py` (o paquete `models/`) cuya herencia llega a
`models.Model` o `PolymorphicModel` registra: app, archivo:línea, bases,
si es abstracta, `db_table`, número de campos, número de métodos y propiedades,
y cada relación (ForeignKey / OneToOneField / ManyToManyField) con su destino,
`on_delete`, `related_name` y `through`.
"""
import ast
import json
import os
import sys
from collections import Counter, defaultdict

REPO = sys.argv[1]
OUT = sys.argv[2]
SRV = os.path.join(REPO, 'src', 'server')
REL = ('ForeignKey', 'OneToOneField', 'ManyToManyField')


def name_of(n):
    if isinstance(n, ast.Name):
        return n.id
    if isinstance(n, ast.Attribute):
        return n.attr
    return ''


def model_files(app):
    base = os.path.join(SRV, app)
    out = []
    for f in sorted(os.listdir(base)):
        p = os.path.join(base, f)
        if f == 'models.py':
            out.append(p)
        elif f == 'models' and os.path.isdir(p):
            out += [os.path.join(r, x) for r, _, fs in os.walk(p) for x in fs if x.endswith('.py')]
    return out


apps = sorted(d for d in os.listdir(SRV)
              if os.path.isfile(os.path.join(SRV, d, '__init__.py')))
classes = {}          # (app, nombre) -> info
by_name = defaultdict(list)
for app in apps:
    for p in model_files(app):
        src = open(p, encoding='utf-8', errors='replace').read()
        try:
            tree = ast.parse(src)
        except SyntaxError:
            continue
        for n in tree.body:
            if not isinstance(n, ast.ClassDef):
                continue
            info = {'app': app, 'name': n.name, 'file': os.path.relpath(p, REPO), 'line': n.lineno,
                    'end': n.end_lineno, 'bases': [name_of(b) for b in n.bases], 'abstract': False,
                    'db_table': None, 'n_fields': 0, 'n_methods': 0, 'n_properties': 0, 'rels': []}
            for b in n.body:
                if isinstance(b, ast.ClassDef) and b.name == 'Meta':
                    for m in b.body:
                        if isinstance(m, ast.Assign) and isinstance(m.targets[0], ast.Name):
                            k = m.targets[0].id
                            if k == 'abstract' and isinstance(m.value, ast.Constant):
                                info['abstract'] = bool(m.value.value)
                            if k == 'db_table' and isinstance(m.value, ast.Constant):
                                info['db_table'] = m.value.value
                elif isinstance(b, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    decs = [name_of(d) for d in b.decorator_list]
                    if 'property' in decs or 'cached_property' in decs:
                        info['n_properties'] += 1
                    else:
                        info['n_methods'] += 1
                elif isinstance(b, ast.Assign) and isinstance(b.value, ast.Call):
                    fn = name_of(b.value.func)
                    if fn.endswith('Field') or fn in REL:
                        info['n_fields'] += 1
                    if fn in REL and b.value.args:
                        a0 = b.value.args[0]
                        raw = a0.value if isinstance(a0, ast.Constant) else name_of(a0)
                        kw = {k.arg: k.value for k in b.value.keywords if k.arg}
                        info['rels'].append({
                            'field': b.targets[0].id if isinstance(b.targets[0], ast.Name) else '?',
                            'kind': fn, 'raw': raw, 'line': b.lineno,
                            'on_delete': name_of(kw['on_delete']) if 'on_delete' in kw else None,
                            'related_name': kw['related_name'].value
                            if isinstance(kw.get('related_name'), ast.Constant) else None,
                            'null': bool(getattr(kw.get('null'), 'value', False)),
                            'through': (kw['through'].value if isinstance(kw.get('through'), ast.Constant)
                                        else name_of(kw['through'])) if 'through' in kw else None,
                        })
            classes[(app, n.name)] = info
            by_name[n.name].append(app)

# cuáles son modelos: herencia que llega a Model / PolymorphicModel
is_model = set()
for key, c in classes.items():
    if any(b in ('Model', 'PolymorphicModel') for b in c['bases']):
        is_model.add(key)
changed = True
while changed:
    changed = False
    for key, c in classes.items():
        if key in is_model:
            continue
        for b in c['bases']:
            if any((a, b) in is_model for a in by_name.get(b, [])):
                is_model.add(key)
                changed = True
                break


def resolve(app, raw):
    """Devuelve (app_destino, modelo_destino) de un destino de relación."""
    if not isinstance(raw, str) or not raw:
        return (None, str(raw))
    if raw == 'self':
        return (app, 'self')
    if '.' in raw:
        a, m = raw.split('.', 1)
        return (a, m)
    if (app, raw) in classes:
        return (app, raw)
    cands = [a for a in by_name.get(raw, []) if (a, raw) in is_model]
    if len(cands) == 1:
        return (cands[0], raw)
    if cands:
        return ('|'.join(cands), raw)       # ambiguo: mismo nombre en varias apps
    return ('externo', raw)                 # p. ej. django.contrib.auth.User


models = []
cross = []
for key in sorted(is_model):
    c = classes[key]
    c['poly'] = 'PolymorphicModel' in c['bases']
    c['parents'] = []
    for b in c['bases']:
        for a in by_name.get(b, []):
            if (a, b) in is_model:
                c['parents'].append(f'{a}.{b}')
    for r in c['rels']:
        ta, tm = resolve(c['app'], r['raw'])
        r['to_app'], r['to_model'] = ta, tm
        if ta not in (c['app'], None):
            cross.append((c['app'], c['name'], r['field'], r['kind'], ta, tm, r['on_delete'],
                          f"{c['file']}:{r['line']}"))
    models.append(c)

dups = {n: sorted(set(a for a in apps_ if (a, n) in is_model))
        for n, apps_ in by_name.items()}
dups = {n: a for n, a in dups.items() if len(a) > 1}
kinds = Counter(r['kind'] for c in models for r in c['rels'])
ondel = Counter(r['on_delete'] for c in models for r in c['rels'] if r['kind'] != 'ManyToManyField')
incoming = Counter(f'{t[4]}.{t[5]}' for t in cross)

json.dump({'models': models, 'cross_app': cross, 'nombres_duplicados': dups,
           'relaciones_por_tipo': kinds, 'on_delete': ondel,
           'destinos_entre_apps': incoming.most_common()},
          open(OUT, 'w'), indent=1, ensure_ascii=False)

print('MODELOS', len(models), '| abstractos', sum(c['abstract'] for c in models),
      '| polimórficos (base directa)', sum(c['poly'] for c in models))
print('RELACIONES', dict(kinds), '| on_delete', dict(ondel))
print('RELACIONES ENTRE APPS', len(cross))
print('NOMBRES DE MODELO REPETIDOS', dups)
print('\nMODELOS (app.Modelo | archivo:línea | bases | campos | métodos | propiedades | tabla)')
for c in models:
    flags = ('A' if c['abstract'] else '') + ('P' if c['poly'] else '')
    print(f"{c['app']}.{c['name']} | {c['file'].replace('src/server/', '')}:{c['line']}-{c['end']} | "
          f"{','.join(c['bases'])} {flags} | {c['n_fields']} | {c['n_methods']} | {c['n_properties']} | {c['db_table']}")
print('\nDESTINOS MÁS REFERENCIADOS DESDE OTRAS APPS')
for k, v in incoming.most_common(15):
    print(f'{v:3} {k}')
print('\nRELACIONES ENTRE APPS (origen.campo -> destino | tipo | on_delete | evidencia)')
for t in sorted(cross):
    print(f"{t[0]}.{t[1]}.{t[2]} -> {t[4]}.{t[5]} | {t[3]} | {t[6]} | {t[7].replace('src/server/', '')}")
