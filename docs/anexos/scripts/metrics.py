"""Métricas por app de EIEInfo. Uso: python3 -I metrics.py <ruta_repo> <salida.json>
Solo lee archivos (AST + git log); no ejecuta código del repo auditado."""
import ast, json, os, re, subprocess, sys
from collections import defaultdict

REPO = sys.argv[1]
OUT = sys.argv[2]
SRV = os.path.join(REPO, 'src', 'server')
SINCE = '2025-11-08'

def git(*a):
    return subprocess.run(['git', '-C', REPO, *a], capture_output=True, text=True).stdout

def lines(p):
    try:
        with open(p, encoding='utf-8', errors='replace') as f:
            return f.read().count('\n')
    except Exception:
        return 0

apps = sorted(d for d in os.listdir(SRV)
              if os.path.isdir(os.path.join(SRV, d)) and not d.startswith('.')
              and (os.path.exists(os.path.join(SRV, d, '__init__.py'))))
settings_txt = open(os.path.join(SRV, 'eieinfo', 'settings.py'), encoding='utf-8').read()
inst_block = settings_txt.split('INSTALLED_APPS', 1)[1].split(']', 1)[0]
installed_lines = [l.strip() for l in inst_block.splitlines() if l.strip() and not l.strip().startswith('#')]

def is_installed(app):
    return any(re.match(rf"['\"]{app}(\.apps\.|['\"])", l) for l in installed_lines)

def pyfiles(app):
    for root, dirs, files in os.walk(os.path.join(SRV, app)):
        dirs[:] = [d for d in dirs if d not in ('migrations', '__pycache__', 'node_modules', 'static')]
        for f in files:
            if f.endswith('.py'):
                yield os.path.join(root, f)

def group_files(app, stem):
    """stem.py, stem_*.py, stem/ package."""
    base = os.path.join(SRV, app)
    out = []
    for f in os.listdir(base):
        p = os.path.join(base, f)
        if f == f'{stem}.py' or (f.startswith(f'{stem}_') and f.endswith('.py')):
            out.append(p)
        elif f == stem and os.path.isdir(p):
            out += [os.path.join(r, x) for r, _, fs in os.walk(p) for x in fs if x.endswith('.py')]
    return out

def parse(p):
    try:
        return ast.parse(open(p, encoding='utf-8', errors='replace').read(), p)
    except SyntaxError:
        return None

# --- recolección de modelos para resolver herencia entre apps
model_names = {}
def base_name(b):
    if isinstance(b, ast.Name): return b.id
    if isinstance(b, ast.Attribute): return b.attr
    return ''

res = {}
all_py = []
for app in apps:
    m_files = group_files(app, 'models')
    classes = []
    for p in m_files:
        t = parse(p)
        if not t: continue
        for n in t.body:
            if isinstance(n, ast.ClassDef):
                classes.append((n.name, [base_name(b) for b in n.bases]))
    res[app] = {'_classes': classes, 'models_files': m_files}

known = set()
changed = True
for app in apps:
    for name, bases in res[app]['_classes']:
        if any('Model' in b for b in bases):
            known.add(name)
while changed:
    changed = False
    for app in apps:
        for name, bases in res[app]['_classes']:
            if name not in known and any(b in known for b in bases):
                known.add(name); changed = True
for app in apps:
    for name, _ in res[app]['_classes']:
        if name in known:
            model_names.setdefault(name, app)

URL_CALLS = {'path', 're_path', 'url'}
deps = defaultdict(lambda: defaultdict(set))   # app -> dep -> {motivos}
fk_deps = defaultdict(lambda: defaultdict(int))
todo = defaultdict(lambda: defaultdict(int))
commented = defaultdict(int)

for app in apps:
    r = res[app]
    r['installed'] = is_installed(app)
    r['n_models'] = sum(1 for n, _ in r['_classes'] if n in known)
    r['loc_models'] = sum(lines(p) for p in r['models_files'])
    r['loc_views'] = sum(lines(p) for p in group_files(app, 'views'))
    r['loc_forms'] = sum(lines(p) for p in group_files(app, 'forms'))
    # urls
    n_urls = 0
    for p in group_files(app, 'urls'):
        t = parse(p)
        if t:
            n_urls += sum(1 for n in ast.walk(t) if isinstance(n, ast.Call)
                          and isinstance(n.func, ast.Name) and n.func.id in URL_CALLS)
    r['n_urls'] = n_urls
    tdir = os.path.join(SRV, app, 'templates')
    tfiles = [os.path.join(rr, f) for rr, _, fs in os.walk(tdir) for f in fs] if os.path.isdir(tdir) else []
    r['n_templates'] = len(tfiles)
    r['loc_templates'] = sum(lines(p) for p in tfiles if p.endswith(('.html', '.tex', '.txt')))
    # tests
    n_tests = 0; test_files = []
    for p in pyfiles(app):
        rel = os.path.relpath(p, SRV)
        if re.search(r'(^|/)tests?(_[^/]*)?\.py$|/tests/', rel):
            t = parse(p)
            if t:
                k = sum(1 for n in ast.walk(t) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name.startswith('test'))
                if k: test_files.append(rel)
                n_tests += k
    r['n_tests'] = n_tests; r['test_files'] = test_files
    mdir = os.path.join(SRV, app, 'migrations')
    r['n_migrations'] = len([f for f in os.listdir(mdir) if f.endswith('.py') and f != '__init__.py']) if os.path.isdir(mdir) else 0
    r['has_migrations_dir'] = os.path.isdir(mdir)
    rel = os.path.join('src', 'server', app)
    r['last_commit'] = git('log', '-1', '--format=%ad', '--date=short', '--', rel).strip()
    r['commits_12m'] = len(git('log', f'--since={SINCE}', '--format=%h', '--', rel).split())
    r['commits_total'] = len(git('log', '--format=%h', '--', rel).split())
    loc_py = 0
    for p in pyfiles(app):
        n = lines(p); loc_py += n
        all_py.append((n, os.path.relpath(p, REPO)))
        src = open(p, encoding='utf-8', errors='replace').read()
        for tag in ('TODO', 'FIXME', 'HACK', 'XXX'):
            todo[app][tag] += len(re.findall(rf'#.*\b{tag}\b', src))
        commented[app] += sum(1 for l in src.splitlines()
                              if re.match(r'\s*#\s*(def |class |return |if |for |from |import |\w+\s*=\s*\S|\w+\(.*\)\s*$)', l))
        t = parse(p)
        if not t: continue
        if re.search(r'(^|/)tests?(_[^/]*)?\.py$|/tests/', os.path.relpath(p, SRV)):
            continue  # las dependencias se miden solo sobre código de producción
        for n in ast.walk(t):
            mod = None
            if isinstance(n, ast.ImportFrom) and n.module and n.level == 0:
                mod = n.module.split('.')[0]
            elif isinstance(n, ast.Import):
                for a in n.names:
                    m0 = a.name.split('.')[0]
                    if m0 in apps and m0 != app:
                        deps[app][m0].add('import')
            if mod and mod in apps and mod != app:
                deps[app][mod].add('import')
            if isinstance(n, ast.Call) and base_name(n.func) in ('ForeignKey', 'OneToOneField', 'ManyToManyField'):
                if n.args:
                    a0 = n.args[0]
                    target = None
                    if isinstance(a0, ast.Constant) and isinstance(a0.value, str):
                        s = a0.value
                        target = s.split('.')[0] if '.' in s else model_names.get(s)
                    else:
                        target = model_names.get(base_name(a0))
                    if target and target in apps and target != app:
                        deps[app][target].add('FK')
                        fk_deps[app][target] += 1
    r['loc_py'] = loc_py
    r['size_total'] = loc_py + r['loc_templates']
    del r['_classes']; r['models_files'] = [os.path.relpath(p, REPO) for p in r['models_files']]

all_py.sort(reverse=True)
top20 = [x for x in all_py if '/migrations/' not in x[1]][:20]
out = {'apps': res, 'installed_lines': installed_lines,
       'deps': {a: {d: sorted(v) for d, v in ds.items()} for a, ds in deps.items()},
       'fk': {a: dict(v) for a, v in fk_deps.items()},
       'todo': {a: dict(v) for a, v in todo.items()},
       'commented': dict(commented), 'top20': top20}
json.dump(out, open(OUT, 'w'), indent=1, ensure_ascii=False)
print('ok', len(apps), 'apps')
