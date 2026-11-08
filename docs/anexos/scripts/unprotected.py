"""Lista vistas (funciones con 1er arg request / CBV) sin decorador o mixin de auth.
Uso: python3 -I unprotected.py <src/server>"""
import ast, os, sys
SRV = sys.argv[1]
AUTH_WORDS = ('login', 'required', 'permission', 'staff', 'superuser', 'user_passes')
out = []
for root, dirs, files in os.walk(SRV):
    dirs[:] = [d for d in dirs if d not in ('migrations', 'tests', '__pycache__', 'static', 'templates')]
    for f in files:
        if not (f.endswith('.py') and ('views' in f or os.path.basename(root) == 'views')):
            continue
        p = os.path.join(root, f)
        src = open(p, encoding='utf-8', errors='replace').read()
        try:
            t = ast.parse(src)
        except SyntaxError:
            continue
        for n in t.body:
            if isinstance(n, ast.FunctionDef) and n.args.args and n.args.args[0].arg == 'request':
                decs = ast.unparse(n.decorator_list) if n.decorator_list else ''
                if any(w in decs.lower() for w in AUTH_WORDS):
                    continue
                body = ast.get_source_segment(src, n) or ''
                inner = any(k in body for k in ('is_authenticated', 'has_perm', 'groups.filter', 'PermissionDenied', 'redirect_to_login', 'puede_', 'es_'))
                out.append(('func', os.path.relpath(p, SRV), n.lineno, n.name, decs, inner))
            elif isinstance(n, ast.ClassDef):
                bases = [ast.unparse(b) for b in n.bases]
                if not any('View' in b or 'Mixin' in b for b in bases):
                    continue
                if any('Required' in b or 'Mixin' in b and 'Login' in b for b in bases):
                    continue
                decs = ast.unparse(n.decorator_list) if n.decorator_list else ''
                body = ast.get_source_segment(src, n) or ''
                if 'method_decorator' in body and any(w in body.lower() for w in ('login', 'required')):
                    continue
                inner = any(k in body for k in ('is_authenticated', 'has_perm', 'test_func', 'PermissionDenied'))
                out.append(('cbv', os.path.relpath(p, SRV), n.lineno, n.name, ','.join(bases), inner))
from collections import Counter
c = Counter(o[1].split('/')[0] for o in out)
print('POR_APP', dict(c))
for o in out:
    print(*o, sep=' | ')
