"""Vulnerabilidades conocidas en las dependencias declaradas de EIEInfo.

Uso:
  python3 -m venv /tmp/venv-audit && /tmp/venv-audit/bin/pip install pip-audit==2.10.1
  python3 -I deps_audit.py <ruta_repo> /tmp/venv-audit/bin/pip-audit <salida.json> > salida.txt

Lee los dos archivos de requisitos del repo auditado y clasifica cada línea:
versión fijada (`==`), sin fijar o instalada desde git. Con las fijadas arma un
archivo temporal (fuera del repo) y corre pip-audit con
`--no-deps --disable-pip -s osv`. En ese modo pip-audit solo consulta la base
OSV por nombre y versión: no resuelve dependencias, no instala paquetes ni
ejecuta código de EIEInfo.

Límites:
- Las dependencias transitivas no se auditan (habría que instalar el entorno).
- Lo instalado desde git solo se audita si la referencia es una etiqueta fija
  verificada a mano (VCS_ETIQUETAS); una rama móvil no es auditable.
- Lo que no está fijado se instala en su última versión al construir y no se
  audita.

Un mismo CVE aparece en OSV con varios identificadores (PYSEC, GHSA); los
avisos se agrupan por alias y se cuenta una vulnerabilidad por grupo. Para cada
una se reporta la primera versión corregida por encima de la declarada.
"""
import datetime
import json
import os
import re
import subprocess
import sys
import tempfile

from packaging.version import InvalidVersion, Version

REPO, PIP_AUDIT, OUT_JSON = sys.argv[1:4]

ARCHIVOS = [
    ('requirements.txt',
     'raíz: instalación manual, la de producción según README.md:41-46'),
    ('docker/django/requirements.txt',
     'Docker y CI: docker/django/Dockerfile:20-22'),
]

# Referencias git que son etiquetas fijas, con su equivalente publicado en PyPI.
# Verificado con: git ls-remote https://github.com/django-wiki/django-wiki 'refs/tags/releases/0.10.1'
VCS_ETIQUETAS = {
    'git+https://github.com/django-wiki/django-wiki.git@releases/0.10.1': ('wiki', '0.10.1'),
}

PIN_RE = re.compile(r'^([A-Za-z0-9][A-Za-z0-9._-]*)(\[[^\]]*\])?==([A-Za-z0-9.+!_-]+)$')
CRED_RE = re.compile(r'(://)[^/@\s]+@')


def norm(nombre):
    return re.sub(r'[-_.]+', '-', nombre).lower()


def ver(s):
    try:
        return Version(s)
    except InvalidVersion:
        return None


def leer(ruta_rel):
    fijadas, sin_fijar, vcs, duplicadas = {}, [], [], []
    with open(os.path.join(REPO, ruta_rel), encoding='utf-8') as fh:
        for n, linea in enumerate(fh, 1):
            if linea.lstrip().startswith('#'):
                continue
            req = re.sub(r'\s+#.*$', '', linea).strip()
            if not req:
                continue
            if req.startswith(('git+', '-e ', 'hg+', 'svn+', 'bzr+')):
                url = CRED_RE.sub(r'\1«ENMASCARADO»@', req)
                vcs.append({'linea': n, 'ref': url, 'pypi': VCS_ETIQUETAS.get(req)})
                continue
            m = PIN_RE.match(req)
            if not m:
                sin_fijar.append({'linea': n, 'req': req})
                continue
            nombre, version = m.group(1), m.group(3)
            k = norm(nombre)
            if k in fijadas:
                duplicadas.append({'linea': n, 'nombre': nombre, 'primera': fijadas[k]['linea']})
                continue
            fijadas[k] = {'linea': n, 'nombre': nombre, 'version': version}
    for v in vcs:
        if v['pypi']:
            nombre, version = v['pypi']
            fijadas.setdefault(norm(nombre), {'linea': v['linea'], 'nombre': nombre,
                                              'version': version, 'desde_git': True})
    return fijadas, sin_fijar, vcs, duplicadas


def pip_audit(fijadas):
    with tempfile.TemporaryDirectory() as td:
        req = os.path.join(td, 'req.txt')
        out = os.path.join(td, 'out.json')
        with open(req, 'w', encoding='utf-8') as fh:
            for d in fijadas.values():
                fh.write(f"{d['nombre']}=={d['version']}\n")
        p = subprocess.run([PIP_AUDIT, '-r', req, '--no-deps', '--disable-pip', '-s', 'osv',
                            '-f', 'json', '--progress-spinner', 'off', '-o', out],
                           capture_output=True, text=True)
        if p.returncode not in (0, 1):  # 1 = se encontraron vulnerabilidades
            sys.exit(f'pip-audit falló ({p.returncode}):\n{p.stderr}')
        with open(out, encoding='utf-8') as fh:
            return json.load(fh)


def agrupar(version_actual, vulns):
    """Une avisos que comparten id o alias; devuelve una entrada por vulnerabilidad."""
    padre = {}

    def raiz(x):
        padre.setdefault(x, x)
        while padre[x] != x:
            padre[x] = padre[padre[x]]
            x = padre[x]
        return x

    for v in vulns:
        ids = [v['id']] + v.get('aliases', [])
        for a in ids[1:]:
            padre[raiz(a)] = raiz(ids[0])
    grupos = {}
    for v in vulns:
        g = grupos.setdefault(raiz(v['id']), {'ids': set(), 'fixes': set(), 'desc': ''})
        g['ids'].update([v['id']] + v.get('aliases', []))
        g['fixes'].update(v.get('fix_versions', []))
        if not g['desc'] and v.get('description'):
            g['desc'] = v['description']
    actual = ver(version_actual)
    res = []
    for g in grupos.values():
        cves = sorted(i for i in g['ids'] if i.startswith('CVE-'))
        ident = cves[0] if cves else sorted(g['ids'])[0]
        mayores = sorted(f for f in (ver(x) for x in g['fixes']) if f and actual and f > actual)
        desc = ' '.join(g['desc'].split())
        res.append({'id': ident, 'ids': sorted(g['ids']),
                    'corrige': str(mayores[0]) if mayores else None,
                    'resumen': desc[:120] + ('…' if len(desc) > 120 else '')})
    res.sort(key=lambda r: (ver(r['corrige']) or Version('0'), r['id']) if r['corrige'] else (Version('999'), r['id']))
    return res


def main():
    commit = subprocess.run(['git', '-C', REPO, 'rev-parse', '--short=8', 'HEAD'],
                            capture_output=True, text=True).stdout.strip()
    version_pa = subprocess.run([PIP_AUDIT, '--version'], capture_output=True, text=True).stdout.strip()
    salida = {'commit': commit, 'fecha': datetime.date.today().isoformat(),
              'herramienta': version_pa, 'servicio': 'osv', 'archivos': {}}
    detalle = {}

    print('Vulnerabilidades conocidas en dependencias declaradas de EIEInfo')
    print(f'Commit: {commit} · Fecha: {salida["fecha"]} · {version_pa} · servicio OSV · --no-deps --disable-pip')
    print('Una vulnerabilidad = un grupo de avisos con id o alias en común. '
          '"Corrige" = primera versión corregida por encima de la declarada.\n')

    for ruta, papel in ARCHIVOS:
        fijadas, sin_fijar, vcs, duplicadas = leer(ruta)
        crudo = pip_audit(fijadas)
        salida['archivos'][ruta] = {'papel': papel, 'fijadas': list(fijadas.values()),
                                    'sin_fijar': sin_fijar, 'vcs': vcs,
                                    'duplicadas': duplicadas, 'pip_audit': crudo}
        print(f'== {ruta} ({papel})')
        print(f'Fijadas con ==: {len(fijadas)} · sin fijar: {len(sin_fijar)} · '
              f'desde git: {len(vcs)} · duplicadas: {len(duplicadas)}')
        for s in sin_fijar:
            print(f'  sin fijar   línea {s["linea"]}: {s["req"]}')
        for v in vcs:
            nota = (f'auditado como {v["pypi"][0]}=={v["pypi"][1]} (etiqueta fija)' if v['pypi']
                    else 'no auditable (rama o referencia móvil)')
            print(f'  desde git   línea {v["linea"]}: {v["ref"]} → {nota}')
        for d in duplicadas:
            print(f'  duplicada   línea {d["linea"]}: {d["nombre"]} (ya en línea {d["primera"]})')

        vulnerables = []
        for dep in crudo['dependencies']:
            if dep.get('skip_reason'):
                print(f'  omitido por pip-audit: {dep["name"]} ({dep["skip_reason"]})')
                continue
            if not dep.get('vulns'):
                continue
            grupos = agrupar(dep['version'], dep['vulns'])
            detalle[(dep['name'], dep['version'])] = grupos
            sin_fix = [g for g in grupos if not g['corrige']]
            todas = max((ver(g['corrige']) for g in grupos if g['corrige']), default=None)
            linea = fijadas[norm(dep['name'])]['linea']
            vulnerables.append((dep['name'], dep['version'], linea, len(grupos), todas, len(sin_fix)))
        total = sum(v[3] for v in vulnerables)
        print(f'Paquetes con vulnerabilidades conocidas: {len(vulnerables)} de {len(fijadas)} auditados · '
              f'vulnerabilidades: {total}')
        print(f'  {"paquete":16} {"versión":9} {"línea":>5} {"vulns":>5}  corrige todas')
        for nombre, version, linea, n, todas, sf in sorted(vulnerables, key=lambda x: -x[3]):
            extra = f' ({sf} sin corrección publicada)' if sf else ''
            print(f'  {nombre:16} {version:9} {linea:>5} {n:>5}  {todas or "—"}{extra}')
        print()

    print('== Detalle por paquete (unión de ambos archivos)')
    for (nombre, version), grupos in sorted(detalle.items(), key=lambda x: -len(x[1])):
        print(f'\n{nombre} {version}: {len(grupos)} vulnerabilidades')
        for g in grupos:
            print(f'  {g["id"]:20} corrige {g["corrige"] or "—":10} {g["resumen"]}')

    with open(OUT_JSON, 'w', encoding='utf-8') as fh:
        json.dump(salida, fh, ensure_ascii=False, indent=1)


main()
