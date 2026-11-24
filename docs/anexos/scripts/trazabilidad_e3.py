#!/usr/bin/env python3
"""Verificación de coherencia interna de la Entrega 3 (auditoría EIEInfo, IE0417).

No lee ni ejecuta nada del repositorio auditado: solo compara documentos de este
repositorio entre sí.

Uso, desde la raíz del repositorio:

    python3 -I docs/anexos/scripts/trazabilidad_e3.py

Comprueba:
  1. §6.1 de la E3 tiene exactamente los 20 hallazgos H-01..H-20, sin repetir, y la
     severidad, el alcance y la prioridad de cada uno son los de la tabla §9.2 de la E2.
  2. Las intervenciones de cada hallazgo en §6.1 coinciden con la columna "Atiende"
     de §5.1.
  3. Las fases de cada hallazgo en §6.1 coinciden con la tabla §4.1.
  4. Todo hallazgo P1–P3 tiene al menos una intervención en §6.1.
  5. Los nombres de las intervenciones en §5.1 coinciden con los títulos de sus fichas
     (§5.2) y con las etiquetas de docs/diagramas/hoja-de-ruta.mmd.
  6. Cada bloque Mermaid del documento es idéntico a su fuente en docs/diagramas/ y
     ninguna fuente tiene líneas "%%" vacías (Mermaid 11 no las acepta).
  7. Las anclas internas (#...) y los enlaces relativos (../...) apuntan a algo que existe.

Sale con código 0 si todo pasa y 1 si encuentra algún problema.
"""
import os
import re
import sys

RAIZ = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
E3 = os.path.join(RAIZ, "docs", "entrega-3", "entrega-3.md")
E2 = os.path.join(RAIZ, "docs", "entrega-2", "entrega-2.md")
DIAGRAMAS = os.path.join(RAIZ, "docs", "diagramas")
# Orden de aparición de los bloques Mermaid en entrega-3.md.
BLOQUES = ["arquitectura-actual", "arquitectura-objetivo", "despliegue-objetivo", "hoja-de-ruta"]

problemas = []


def leer(ruta):
    with open(ruta, encoding="utf-8") as f:
        return f.read()


def seccion(texto, inicio, fin):
    i = texto.index(inicio)
    return texto[i:texto.index(fin, i)]


def normalizar(nombre):
    return re.sub(r"\s+", " ", nombre.replace("`", "").replace("<br/>", " ")).strip()


def ancla_github(titulo):
    t = titulo.strip().lower()
    t = re.sub(r"[^\w\- ]", "", t)
    return t.replace(" ", "-")


e3 = leer(E3)
e2 = leer(E2)

# 1. Hallazgos de §6.1 frente a la tabla §9.2 de la E2.
reg_e2 = {
    h: (sev, alc, pri.strip())
    for h, sev, alc, pri in re.findall(
        r"^\| (H-\d\d) \| [^|]+\| (\w+) \| (\w+) \| ([^|]+?) \|", seccion(e2, "### 9.2", "### 9.3"), re.M)
}
filas = re.findall(
    r"^\| (H-\d\d) [^|]*\| (\w+) \| (\w+) \| ([^|]+?) \| ([^|]+?) \| ([^|]+?) \| ([^|]+?) \|",
    seccion(e3, "### 6.1", "### 6.2"), re.M)
ids = [f[0] for f in filas]
esperados = [f"H-{n:02d}" for n in range(1, 21)]
if sorted(ids) != esperados or len(ids) != len(set(ids)):
    problemas.append(f"§6.1 debe tener H-01..H-20 sin repetir; tiene {ids}")
if len(reg_e2) != 20:
    problemas.append(f"Se esperaban 20 hallazgos en E2 §9.2; se leyeron {len(reg_e2)}")
for h, sev, alc, pri, *_ in filas:
    if h in reg_e2 and (sev, alc, pri.strip()) != reg_e2[h]:
        problemas.append(f"{h}: §6.1 dice {(sev, alc, pri.strip())}, E2 §9.2 dice {reg_e2[h]}")

matriz_int = {f[0]: set(re.findall(r"I-\d\d", f[4] + " " + f[5])) for f in filas}
matriz_fases = {f[0]: set(re.findall(r"F\d", f[6])) for f in filas}

# 2. Intervenciones: §5.1 ("Atiende") frente a §6.1.
t51 = seccion(e3, "### 5.1", "### 5.2")
nombres_51 = {}
atiende = {}
for iid, nombre, hs in re.findall(r"^\| (I-\d\d) \| ([^|]+?) \| ([^|]+?) \|", t51, re.M):
    nombres_51[iid] = normalizar(nombre)
    for h in re.findall(r"H-\d\d", hs):
        atiende.setdefault(h, set()).add(iid)
for h in sorted(set(atiende) | set(matriz_int)):
    if atiende.get(h, set()) != matriz_int.get(h, set()):
        problemas.append(f"{h}: §5.1 lo atienden {sorted(atiende.get(h, []))}, §6.1 dice {sorted(matriz_int.get(h, []))}")

# 3. Fases: §4.1 frente a §6.1.
fases_41 = {}
for fase, hs in re.findall(r"^\| \*\*(F\d)\*\*[^|]*\|[^|]+\|[^|]+\| ([^|]+) \|", seccion(e3, "### 4.1", "### 4.2"), re.M):
    for h in re.findall(r"H-\d\d", hs):
        fases_41.setdefault(h, set()).add(fase)
for h in sorted(set(fases_41) | set(matriz_fases)):
    if fases_41.get(h, set()) != matriz_fases.get(h, set()):
        problemas.append(f"{h}: §4.1 lo ubica en {sorted(fases_41.get(h, []))}, §6.1 en {sorted(matriz_fases.get(h, []))}")

# 4. Cobertura de P1–P3.
for h, (_, _, pri) in reg_e2.items():
    if re.search(r"P[123]", pri) and not matriz_int.get(h):
        problemas.append(f"{h} ({pri}) no tiene ninguna intervención en §6.1")

# 5. Nombres de intervenciones: §5.1, fichas y diagrama de la hoja de ruta.
fichas = {i: normalizar(n) for i, n in re.findall(r"^#### (I-\d\d) · (.+)$", e3, re.M)}
if set(fichas) != set(nombres_51):
    problemas.append(f"Fichas {sorted(fichas)} no coinciden con §5.1 {sorted(nombres_51)}")
for iid, nombre in nombres_51.items():
    if fichas.get(iid) != nombre:
        problemas.append(f"{iid}: §5.1 '{nombre}' frente a ficha '{fichas.get(iid)}'")
hoja = leer(os.path.join(DIAGRAMAS, "hoja-de-ruta.mmd"))
for iid, etiqueta in re.findall(r'^\s*\w+\["(I-\d\d) ([^"]+)"\]', hoja, re.M):  # solo nodos, no etiquetas de flechas
    etiqueta = normalizar(etiqueta)
    if etiqueta.startswith("etapa"):
        continue  # I-03 se rotula por etapas, no por nombre
    if iid in nombres_51 and etiqueta != nombres_51[iid]:
        problemas.append(f"hoja-de-ruta.mmd: {iid} '{etiqueta}' frente a §5.1 '{nombres_51[iid]}'")

# 6. Copias de los diagramas.
bloques = re.findall(r"```mermaid\n(.*?)```", e3, re.S)
if len(bloques) != len(BLOQUES):
    problemas.append(f"Se esperaban {len(BLOQUES)} bloques Mermaid; hay {len(bloques)}")
for nombre, bloque in zip(BLOQUES, bloques):
    fuente = leer(os.path.join(DIAGRAMAS, nombre + ".mmd"))
    if fuente != bloque:
        problemas.append(f"La copia de {nombre}.mmd en entrega-3.md no es idéntica a la fuente")
    if re.search(r"^%%\s*$", fuente, re.M):
        problemas.append(f"{nombre}.mmd tiene líneas '%%' vacías")

# 7. Anclas y enlaces relativos.
anclas = {ancla_github(t) for t in re.findall(r"^#{1,6} (.+)$", e3, re.M)}
for a in re.findall(r"\]\(#([^)]+)\)", e3):
    if a not in anclas:
        problemas.append(f"Ancla rota: #{a}")
for r in re.findall(r"\]\((\.\./[^)#]+)\)", e3):
    if not os.path.exists(os.path.normpath(os.path.join(os.path.dirname(E3), r))):
        problemas.append(f"Enlace roto: {r}")

print(f"Hallazgos en §6.1: {len(filas)} · intervenciones en §5.1: {len(nombres_51)} · "
      f"bloques Mermaid: {len(bloques)}")
if problemas:
    print(f"{len(problemas)} problema(s):")
    for p in problemas:
        print("  -", p)
    sys.exit(1)
print("OK: matriz, prioridades, fases, nombres, diagramas y enlaces son coherentes.")
