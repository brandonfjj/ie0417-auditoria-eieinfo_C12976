"""Búsqueda de secretos en TODO el historial git de EIEInfo, con salida enmascarada.

Uso: python3 -I secrets_history.py <ruta_repo> [--all]

Solo ejecuta `git log` / `git show` de lectura. NUNCA imprime el valor de un
secreto: por cada hallazgo muestra tipo, archivo, nombre de la clave, commit y
fecha en que apareció por primera vez, número de valores distintos, forma del
valor (longitud y clases de caracteres) y si el mismo valor sigue en HEAD.

Los valores se comparan mediante un HMAC con clave aleatoria por ejecución, de
modo que ni siquiera un resumen estable del secreto sale del proceso.
"""
import hashlib
import hmac
import os
import re
import subprocess
import sys
from collections import defaultdict

REPO = sys.argv[1]
ALL = '--all' in sys.argv
KEY = os.urandom(32)
EXCLUDE = [':!src/server/eieinfo/static', ':!*.min.js', ':!*.min.css', ':!*.map', ':!*.svg',
           ':!*.png', ':!*.jpg', ':!*.pdf', ':!*.ipynb', ':!*.lock']


def tag(v):
    return hmac.new(KEY, v.encode('utf-8', 'replace'), hashlib.sha256).hexdigest()


def shape(v):
    cls = []
    if re.search(r'[a-z]', v): cls.append('a-z')
    if re.search(r'[A-Z]', v): cls.append('A-Z')
    if re.search(r'\d', v): cls.append('0-9')
    if re.search(r'[^A-Za-z0-9]', v): cls.append('símb.')
    return f"{len(v)} car. [{' '.join(cls)}]"


PLACEHOLDER = re.compile(
    r'^(x+|\*+|\.+|change.?me|password|passwd|secret|example|ejemplo|test(ing)?|todo|none|null|true|false|'
    r'your[-_ ].*|tu[-_ ].*|<.*>|\{.*\}|\$\{?.*|%\(.*|admin|root|info|eieinfo|user|usuario|contraseña|'
    r'clave|key|token|dummy|fake|default|imgur-.*|.*-here|aqui.*)$', re.I)

KV = re.compile(
    r"""(?ix)
    \b([\w.-]*(?:passw(?:or)?d|passwd|pwd|contrase[ñn]a|secret|token|api[_-]?key|apikey|client[_-]?id|
        client[_-]?secret|access[_-]?key|private[_-]?key|auth[_-]?key|credential)[\w.-]*)
    \s*(?:=|:|=>)\s*
    (?:(['"])([^'"\n]{4,200})\2|([^\s'"\#,;(){}\[\]]{6,200}))
    """)
SPECIFIC = [
    ('Token de bot de Telegram', re.compile(r'\b(\d{8,10}:[A-Za-z0-9_-]{35})\b')),
    ('Llave privada (PEM)', re.compile(r'(-----BEGIN [A-Z ]*PRIVATE KEY-----)')),
    ('API key de Google', re.compile(r'\b(AIza[0-9A-Za-z_-]{35})\b')),
    ('Token de Facebook', re.compile(r'\b(EAA[A-Za-z0-9]{30,})\b')),
    ('Llave de acceso AWS', re.compile(r'\b(AKIA[0-9A-Z]{16})\b')),
    ('Token de GitLab/GitHub', re.compile(r'\b(glpat-[A-Za-z0-9_-]{20,}|gh[pousr]_[A-Za-z0-9]{36,})\b')),
    ('URL con credenciales', re.compile(r'[a-z][a-z0-9+.-]*://[^/\s:@]+:([^@\s/]{3,})@')),
    ('Contraseña en línea de comando', re.compile(r'(?:--password[= ]|\s-p)([^\s\'"]{3,})')),
    ('Hash de contraseña Django', re.compile(r'(pbkdf2_sha256\$\d+\$[^\s\'",)]{20,})')),
    ('Cuenta de servicio de Google', re.compile(r'("private_key_id"|"client_email")\s*:')),
]
CODE_EXT = ('.py', '.js', '.html', '.ts', '.cjs')
NOT_LITERAL = re.compile(r'^(os\.|settings\.|request\.|self\.|forms\.|models\.|env\(|getenv|config\(|None|True|False|'
                         r'\w+\(|\w+\.\w+|\w+\[|[a-z_]+$)')
SENSITIVE_NAME = re.compile(
    r'(^|/)(\.env[\w.-]*|.*secret[\w.-]*|.*credential[\w.-]*|id_[rd]sa[\w.-]*|.*\.(pem|key|p12|pfx|jks|keystore|'
    r'crt|cer|sql|sqlite3?|db|dump|bak|csv|xlsx?|kdbx)|\.git-credentials|\.netrc|\.htpasswd|.*password[\w.-]*)$', re.I)


def git(*a):
    return subprocess.run(['git', '-C', REPO, *a], capture_output=True, text=True, errors='replace').stdout


rev = ['--all'] if ALL else ['HEAD']
print('Alcance:', 'todas las ramas y etiquetas (--all)' if ALL else 'historial de HEAD',
      '|', git('rev-list', '--count', *rev).strip(), 'commits')

# ---- 1. líneas agregadas en cualquier commit
finds = defaultdict(lambda: {'first': None, 'last': None, 'vals': {}, 'n': 0})
log = subprocess.Popen(['git', '-C', REPO, 'log', *rev, '--no-color', '-p', '-U0', '--no-ext-diff', '--no-renames',
                        '--reverse', '--date=short', '--format=\x01%h|%ad', '--', '.', *EXCLUDE],
                       stdout=subprocess.PIPE, text=True, errors='replace')
commit = date = path = None
for line in log.stdout:
    if line.startswith('\x01'):
        commit, date = line[1:].strip().split('|')
        continue
    if line.startswith('+++ b/'):
        path = line[6:].rstrip('\n')
        continue
    if not line.startswith('+') or line.startswith('+++') or path is None:
        continue
    if '/static/' in path or 'node_modules/' in path:
        continue                             # librerías de terceros vendorizadas: solo ruido
    text = line[1:]
    hits = []
    for name, rx in SPECIFIC:
        for m in rx.finditer(text):
            hits.append((name, name, m.group(1)))
    # En volcados SQL y líneas enormes no se buscan pares clave=valor: el "nombre de
    # clave" podría ser un fragmento de datos (p. ej. una sesión codificada).
    kv_iter = () if (path.endswith('.sql') or len(line) > 2000) else KV.finditer(text)
    for m in kv_iter:
        k = m.group(1)
        if len(k) > 45 or not re.match(r'^[A-Za-z_ñÑ][\w.ñÑ-]*$', k):
            continue
        v = m.group(3) if m.group(3) is not None else m.group(4)
        quoted = m.group(3) is not None
        if path.endswith(CODE_EXT) and not quoted:
            continue                         # en código solo cuentan literales entre comillas
        if not quoted and NOT_LITERAL.match(v):
            continue
        if re.search(r'(^|[_.-])(field|form|input|label|help|verbose|name|url|template|view|error|msg|message|'
                     r'reset|change|validators?|hashers?|widget|required|requirements?|length|min|max)', k, re.I):
            continue
        if ' ' in v.strip() and quoted and len(v.split()) > 2:
            continue                         # frases, no secretos
        hits.append(('Asignación clave=valor', k, v))
    for kind, k, v in hits:
        f = finds[(kind, path, k)]
        f['n'] += 1
        f['first'] = f['first'] or (commit, date)
        f['last'] = (commit, date)
        f['vals'].setdefault(tag(v), v)
log.wait()

head_cache = {}


def in_head(path, v):
    if path not in head_cache:
        r = subprocess.run(['git', '-C', REPO, 'show', f'HEAD:{path}'], capture_output=True, text=True, errors='replace')
        head_cache[path] = r.stdout if r.returncode == 0 else None
    c = head_cache[path]
    return 'archivo borrado' if c is None else ('sí' if v in c else 'no')


print('\n== 1. SECRETOS EN LÍNEAS AGREGADAS (valor enmascarado)')
print('tipo | archivo | clave | primer commit (fecha) | último commit | apariciones | valores distintos | '
      'forma | ¿placeholder? | ¿sigue en HEAD?')
rows = []
for (kind, path, k), f in finds.items():
    vals = list(f['vals'].values())
    real = [v for v in vals if not PLACEHOLDER.match(v.strip())]
    longest = max(vals, key=len)
    heads = sorted({in_head(path, v) for v in vals})
    rows.append((0 if real else 1, kind, path, k, f, len(vals), shape(longest),
                 'no' if real else 'sí', '/'.join(heads)))
for r in sorted(rows, key=lambda r: (r[0], r[1], r[2], r[3])):
    _, kind, path, k, f, nv, shp, ph, heads = r
    print(f"{kind} | {path} | {k[:40]} | {f['first'][0]} ({f['first'][1]}) | {f['last'][0]} ({f['last'][1]}) | "
          f"{f['n']} | {nv} | {shp} | {ph} | {heads}")
print(f'total: {len(rows)} (no placeholder: {sum(1 for r in rows if r[0] == 0)})')

# ---- 2. archivos con nombre sensible que existieron alguna vez
print('\n== 2. ARCHIVOS CON NOMBRE SENSIBLE EN EL HISTORIAL')
print('archivo | agregado en (fecha) | ¿existe en HEAD? | borrado en (fecha)')
added = {}
out = git('log', *rev, '--diff-filter=A', '--name-only', '--no-renames', '--reverse', '--date=short',
          '--format=\x01%h|%ad')
for line in out.splitlines():
    if line.startswith('\x01'):
        commit, date = line[1:].split('|')
    elif line.strip() and SENSITIVE_NAME.search(line) and '/static/' not in line:
        added.setdefault(line.strip(), (commit, date))
deleted = {}
out = git('log', *rev, '--diff-filter=D', '--name-only', '--no-renames', '--date=short', '--format=\x01%h|%ad')
for line in out.splitlines():
    if line.startswith('\x01'):
        commit, date = line[1:].split('|')
    elif line.strip() in added:
        deleted.setdefault(line.strip(), (commit, date))
head_files = set(git('ls-files').splitlines())
for p, (c, d) in sorted(added.items()):
    dl = deleted.get(p)
    print(f"{p} | {c} ({d}) | {'sí' if p in head_files else 'NO'} | {f'{dl[0]} ({dl[1]})' if dl and p not in head_files else '—'}")
print('total:', len(added))
