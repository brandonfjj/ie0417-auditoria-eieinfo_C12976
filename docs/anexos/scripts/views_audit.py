"""Auditoría estática de vistas de EIEInfo: enrutamiento y protección.

Uso: python3 -I views_audit.py <ruta_repo>

Solo lee archivos; no importa ni ejecuta código del repo auditado.
Para cada vista (función de módulo cuyo primer argumento es `request`, o clase
basada en vistas) determina:

  - enrutada: su nombre (o el alias `x = decorador(Clase.as_view())`) aparece en
    algún `urls.py` o `urlpatterns/*.py` no comentado de la misma app;
  - protección: decoradores propios (`*_required`), envoltura a nivel de módulo,
    `LoginRequiredMixin`/`UserPassesTestMixin`, `method_decorator`, o comprobación
    explícita de sesión dentro del cuerpo (`request.session.get('…_id')`,
    `is_authenticated`, `_tiene_sesion`, `PermissionDenied`).

Es una heurística: la lista de "sin protección visible" requiere revisión manual
(hay vistas públicas por diseño). Las no enrutadas son candidatas a código muerto.
"""
import ast
import os
import re
import sys
from collections import Counter, defaultdict

REPO = sys.argv[1]
SRV = os.path.join(REPO, 'src', 'server')
AUTH_DEC = re.compile(r'required|permission|staff|superuser|user_passes', re.I)
AUTH_BODY = re.compile(r"session\.get\(\s*['\"]\w+_id['\"]|session\[['\"]\w+_id['\"]\]|is_authenticated|"
                       r"_tiene_sesion|PermissionDenied|has_perm|is_staff|is_superuser|_requiere_|_verificar_acceso|"
                       r"_puede_|obtener_usuario_sesion|_get_funcionario|_usuario_actual")
AUTH_BASE = re.compile(r'LoginRequired|UserPassesTest|PermissionRequired|Protegid|SesionPortal|Auth')


def is_view_file(rel):
    parts = rel.split('/')
    return parts[-1].endswith('.py') and (parts[-1].startswith('views') or 'views' in parts[:-1])


def is_url_file(rel):
    parts = rel.split('/')
    return parts[-1].endswith('.py') and (parts[-1].startswith('urls') or 'urlpatterns' in parts[:-1])


def strip_comments(src):
    return '\n'.join(l for l in src.splitlines() if not l.lstrip().startswith('#'))


apps = sorted(d for d in os.listdir(SRV) if os.path.isfile(os.path.join(SRV, d, '__init__.py')))
rows = []
for app in apps:
    url_text = ''
    view_files = []
    for root, dirs, files in os.walk(os.path.join(SRV, app)):
        dirs[:] = [d for d in dirs if d not in ('migrations', '__pycache__', 'static', 'templates', 'tests')]
        for f in files:
            p = os.path.join(root, f)
            rel = os.path.relpath(p, SRV)
            if is_url_file(rel):
                url_text += strip_comments(open(p, encoding='utf-8', errors='replace').read()) + '\n'
            elif is_view_file(rel):
                view_files.append(p)
    # el enrutador raíz también puede referenciar vistas
    url_text += strip_comments(open(os.path.join(SRV, 'eieinfo', 'urls.py'), encoding='utf-8').read())
    for p in view_files:
        src = open(p, encoding='utf-8', errors='replace').read()
        try:
            tree = ast.parse(src)
        except SyntaxError:
            continue
        rel = os.path.relpath(p, SRV)
        # alias a nivel de módulo: nombre = deco(Clase.as_view()) / nombre = Clase.as_view()
        alias = defaultdict(list)       # clase -> [(alias, protegido)]
        wrapped_funcs = {}              # función -> protegido por reasignación
        for n in tree.body:
            if isinstance(n, ast.Assign) and len(n.targets) == 1 and isinstance(n.targets[0], ast.Name):
                txt = ast.unparse(n.value)
                m = re.search(r'(\w+)\.as_view\(', txt)
                prot = bool(AUTH_DEC.search(txt.split('(')[0])) if '(' in txt else False
                if m:
                    alias[m.group(1)].append((n.targets[0].id, prot))
                elif isinstance(n.value, ast.Call) and n.value.args and isinstance(n.value.args[0], ast.Name):
                    wrapped_funcs[n.value.args[0].id] = prot
        for n in tree.body:
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if not (n.args.args and n.args.args[0].arg == 'request'):
                    continue
                decs = ' '.join(ast.unparse(d) for d in n.decorator_list)
                body = ast.get_source_segment(src, n) or ''
                prot = 'decorador' if AUTH_DEC.search(decs) else \
                    'envoltura' if wrapped_funcs.get(n.name) else \
                    'en-cuerpo' if AUTH_BODY.search(body) else ''
                routed = bool(re.search(rf'\b{re.escape(n.name)}\b', url_text))
                rows.append((app, rel, n.lineno, n.name, 'func', routed, prot, 'csrf_exempt' in decs))
            elif isinstance(n, ast.ClassDef):
                bases = [ast.unparse(b) for b in n.bases]
                if not any('View' in b for b in bases):
                    continue
                body = ast.get_source_segment(src, n) or ''
                names = [n.name] + [a for a, _ in alias.get(n.name, [])]
                routed = any(re.search(rf'\b{re.escape(x)}\b', url_text) for x in names)
                prot = 'envoltura' if any(pr for _, pr in alias.get(n.name, [])) else \
                    'mixin' if any(AUTH_BASE.search(b) for b in bases) else \
                    'method_decorator' if re.search(r'method_decorator\([^)]*required', body) else \
                    'en-cuerpo' if AUTH_BODY.search(body) else ''
                rows.append((app, rel, n.lineno, n.name, 'cbv:' + ','.join(bases), routed, prot,
                             'csrf_exempt' in body))

tot = Counter(r[0] for r in rows)
unrouted = Counter(r[0] for r in rows if not r[5])
noprot = Counter(r[0] for r in rows if r[5] and not r[6])
print('APP | vistas | no enrutadas | enrutadas sin protección visible')
for a in sorted(tot, key=lambda k: -tot[k]):
    print(f'{a:32} {tot[a]:4} {unrouted[a]:4} {noprot[a]:4}')
print('TOTAL', sum(tot.values()), sum(unrouted.values()), sum(noprot.values()))
print('PROTECCIÓN (enrutadas):', dict(Counter(r[6] or 'ninguna' for r in rows if r[5])))
print('\n== NO ENRUTADAS (candidatas a código muerto)')
for r in rows:
    if not r[5]:
        print(f'  {r[1]}:{r[2]} {r[3]} [{r[6] or "sin protección"}]')
print('\n== ENRUTADAS SIN PROTECCIÓN VISIBLE (revisar a mano)')
for r in rows:
    if r[5] and not r[6]:
        print(f'  {r[1]}:{r[2]} {r[3]} ({r[4][:40]}){" CSRF_EXEMPT" if r[7] else ""}')
print('\n== CSRF_EXEMPT')
for r in rows:
    if r[7]:
        print(f'  {r[1]}:{r[2]} {r[3]} routed={r[5]} prot={r[6] or "ninguna"}')
