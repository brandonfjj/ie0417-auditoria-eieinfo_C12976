# Levantamiento técnico — Entrega 2 (anexo)

**Proyecto:** Auditoría de diseño de software — EIEInfo (IE0417, UCR)
**Repositorio auditado:** `https://git.ucr.ac.cr/eieinfo/EIEInfo.git`, rama `master`, commit `0b3c575c` (2026-11-04)
**Fecha del levantamiento:** 2026-11-13 (§7.4 rehecha el 2026-11-14 con `pip-audit`)
**Alcance:** materia prima con evidencia para el documento principal de la Entrega 2 (enunciado §7). Es acumulativo: parte de [`levantamiento-e1.md`](levantamiento-e1.md) y de [`../entrega-1/entrega-1.md`](../entrega-1/entrega-1.md) y no repite lo que ya está ahí; cuando un dato de la Entrega 1 se usa, se cita como "E1 §n".

## Convenciones

- Las rutas son relativas a la raíz del repo auditado (`~/repos/EIEInfo`). Dentro de `src/server/` se abrevia a `<app>/archivo.py:N` cuando no hay ambigüedad.
- **Secretos y datos personales:** nunca se transcriben. Se cita `archivo:línea` o commit, el tipo y la forma (`«ENMASCARADO»`, longitud o patrón).
- **"No determinable"** marca lo que el repositorio no permite afirmar.
- El análisis es **estático**: no se ejecutó EIEInfo, ni su suite de pruebas, ni Docker. `git -C ~/repos/EIEInfo status --porcelain` devuelve vacío antes y después del levantamiento.
- La única herramienta externa es `pip-audit` 2.10.1, instalada con autorización del estudiante (2026-11-14) en un entorno virtual fuera de ambos repositorios. Solo consulta la base OSV por nombre y versión de paquete (§7.4). El resto de las mediciones salen de scripts propios que solo leen archivos (AST y `git log`), guardados en [`scripts/`](scripts/):

| Script | Qué mide | Salida cruda |
|---|---|---|
| `metrics.py` (E1) | Tamaño, modelos, pruebas, actividad y dependencias por app | `scripts/metricas-eieinfo-0b3c575c.json` |
| `complexity.py` | Complejidad ciclomática (McCabe) y longitud por función; mismas reglas de conteo que `radon` | `scripts/complejidad-eieinfo-0b3c575c.json` |
| `domain.py` | Modelos, campos, relaciones y herencia de todos los `models.py` | `scripts/dominio-eieinfo-0b3c575c.json` |
| `duplication.py` | Clones exactos y estructurales entre funciones de producción (mínimo 8 líneas) | `scripts/duplicacion-eieinfo-0b3c575c.txt` |
| `tests_audit.py` | Perfil estático de la suite: pruebas, *fixtures*, `mock`, aserciones, `skip`, apps que corre el CI | `scripts/pruebas-eieinfo-0b3c575c.txt` |
| `views_audit.py` | Vistas, enrutamiento y protección visible; borrados sin comprobar el método HTTP | `scripts/vistas-eieinfo-0b3c575c.txt` |
| `secrets_history.py` | Secretos en todo el historial (`--all`), con valores enmascarados | `scripts/secretos-historial-eieinfo-0b3c575c.txt` |
| `deps_audit.py` | Vulnerabilidades conocidas en las dependencias declaradas (envuelve `pip-audit`) | `scripts/dependencias-eieinfo-0b3c575c.txt` y `.json` |

```bash
S=docs/anexos/scripts; R=~/repos/EIEInfo; H=0b3c575c
python3 -I $S/complexity.py $R $S/complejidad-eieinfo-$H.json
python3 -I $S/domain.py     $R $S/dominio-eieinfo-$H.json
python3 -I $S/duplication.py   $R > $S/duplicacion-eieinfo-$H.txt
python3 -I $S/tests_audit.py   $R > $S/pruebas-eieinfo-$H.txt
python3 -I $S/views_audit.py   $R > $S/vistas-eieinfo-$H.txt
python3 -I $S/secrets_history.py $R --all > $S/secretos-historial-eieinfo-$H.txt
python3 -m venv /tmp/venv-audit && /tmp/venv-audit/bin/pip install pip-audit==2.10.1
python3 -I $S/deps_audit.py $R /tmp/venv-audit/bin/pip-audit $S/dependencias-eieinfo-$H.json > $S/dependencias-eieinfo-$H.txt
```

---

## 1. Selección de módulos

### 1.1 Criterios y métricas

Se usan cuatro criterios, todos medibles desde el repositorio:

- **Tamaño:** LOC de producción (Python sin `tests*.py`, migraciones ni `static/`), LOC de vistas y número de rutas.
- **Acoplamiento:** fan-in y fan-out entre apps por `import` y por relaciones de modelo (E1 §4.1).
- **Actividad:** commits en los últimos 12 meses (`git log --since=2025-11-08 -- src/server/<app>`), autores distintos y antigüedad.
- **Criticidad:** qué proceso de la Escuela se detiene si el módulo falla y qué datos maneja.

A eso se suma la **complejidad ciclomática (CC)**, medida en esta entrega con `complexity.py`. En todo `src/server` hay 1408 funciones de producción; 48 tienen CC > 10 y 11 tienen CC > 20.

| Módulo | LOC prod. | LOC vistas | Rutas | Modelos | Fan-in | Fan-out | Commits 12 m (total) | Autores 12 m (total) | Primer commit | Funciones CC > 10 (CC máx.) | Pruebas `test*` |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `profesores` | 7653 | 5190 | 150 | 2 | 10 | **12** | **60** (909) | 7 (24) | 2016-02-28 | **14** (33) | 210 |
| `administrativos` | 6156 | 2428 | 93 | 17 | **16** | 9 | 38 (463) | 7 (24) | 2017-01-10 | 3 (25) | 84 |
| `estudiantes` | 4111 | 1483 | 43 | 17 | 10 | 9 | 24 (502) | 6 (18) | 2016-02-22 | 0 (9) | 36 |
| `firma_digital` | 4024 | 2918 | 29 | 8 | 0 | 2 | 47 (64) | 2 (2) | 2025-09-14 | 11 (28) | 456 |
| `trabajo_final_de_graduacion` | 2679 | 1352 | 27 | 8 | 2 | 5 | 13 (48) | 2 (4) | 2025-03-13 | 5 (29) | 74 |
| `trabajos_finales` | 2795 | 113 | 3 | 6 | 2 | 6 | 3 (90) | 1 (11) | 2017-04-27 | 0 (9) | 5 |
| `eieinfo` (configuración y servicios comunes) | 1130 | 0 | 24 | 0 | 13 | 0 | 33 (318) | 5 (21) | 2016-02-16 | 1 (**39**) | 6 |
| `webpage` (no propuesto; referencia) | 1074 | 403 | 30 | 8 | 12 | 8 | 24 (247) | 4 (20) | 2017-01-13 | 0 (10) | 91 |

Fuentes: `scripts/metricas-eieinfo-0b3c575c.json` (tamaño, modelos, pruebas, dependencias), `scripts/complejidad-eieinfo-0b3c575c.json` (CC), y por app:

```bash
git log --format=%h -- src/server/<app> | wc -l                          # commits totales
git log --since=2025-11-08 --format=%an -- src/server/<app> | sort -u | wc -l   # autores 12 m
git log --format=%ad --date=short --reverse -- src/server/<app> | head -1       # primer commit
```

Los archivos de producción con más commits en 12 meses (`git log --since=2025-11-08 --name-only --format= -- 'src/server/*.py' | sort | uniq -c | sort -rn`) son `firma_digital/views.py` (41), `profesores/views/consejo_asesor.py` (14), `firma_digital/models.py` (14), `eieinfo/settings.py` (13) y `trabajo_final_de_graduacion/views.py` (12). Los cinco pertenecen a módulos propuestos.

### 1.2 Propuesta: seis módulos o áreas

| # | Módulo o área | Por qué (métrica que lo justifica) | Qué pregunta de diseño responde |
|---|---|---|---|
| 1 | **`profesores`** | Es el mayor en todo: 7653 LOC de producción, 150 rutas, fan-out 12, 60 commits en 12 meses y 14 de las 48 funciones con CC > 10. Solo define 2 modelos. | ¿Qué responsabilidades absorbió el módulo "dios" y por dónde se puede partir? |
| 2 | **`administrativos`** | Fan-in 16: 12 apps tienen relaciones de modelo hacia él (30 `ForeignKey`/`OneToOne`/`ManyToMany` entrantes, `scripts/dominio-eieinfo-0b3c575c.json`). A la vez importa 9 apps de dominio. 93 rutas en 10 archivos de `urlpatterns/`. | ¿Por qué el núcleo de datos depende de sus clientes y qué costo tiene cambiar `Funcionario` o `Ciclo`? |
| 3 | **`estudiantes`** | 17 modelos y el `models.py` más grande del sistema (1347 LOC), con datos personales y académicos; solo 36 pruebas para 4111 LOC (la peor razón entre los módulos grandes). | ¿Cuánta lógica vive en los modelos y qué tan seguro es cambiarla sin pruebas? |
| 4 | **`firma_digital`** | Es el punto caliente del último año: `views.py` tiene 2918 LOC en un solo archivo, 41 commits en 12 meses y la mayor CC acumulada del sistema (492, con 11 funciones > 10). Fan-in 0 y 456 pruebas. Solo 2 autores. | ¿El código nuevo es mejor diseño o solo está mejor probado? Sirve de contraste con los módulos legados. |
| 5 | **Área de trabajos finales:** `trabajo_final_de_graduacion` + `trabajos_finales` + `profesores/views/trabajos_finales.py` | Dos subsistemas para el mismo dominio (E1 H-10): el antiguo concentra 1056 LOC en formularios y 113 en vistas, con 5 pruebas; el nuevo tiene la tercera función más compleja del sistema (CC 29, 196 líneas). Las rutas del TFG antiguo están comentadas en `profesores/urls.py:36` y `estudiantes/urls.py:32-33`, pero sus archivos siguen en el repo. | ¿Cómo conviven el subsistema viejo y el nuevo, qué quedó muerto y qué sigue vivo? |
| 6 | **Configuración y servicios comunes (`eieinfo`)** | Lo importan 13 apps. `settings.py` es el cuarto archivo más modificado (13 commits en 12 meses) y `eieinfo/email_service.py:16` (`enviar_email`) es **la función más compleja de todo el sistema** (CC 39). Concentra H-01, H-07 y H-08 de la Entrega 1. | ¿Qué tan frágil es el punto por donde pasan la configuración, el correo y las integraciones? |

**Descartados y por qué:**

- `webpage`: su papel doble (sitio público y librería de utilidades, fan-in 12) es relevante, pero es pequeño (1074 LOC, CC máx. 10) y se cubre como dependencia de los seis anteriores y en la sección 5.
- `cursos`: fan-in 7 y lógica en formularios (813 LOC), pero poca actividad (14 commits) y solo 5 rutas. Se cubre en el dominio (sección 4).
- `postulaciones`: tiene la CC media más alta por función (7,17 en 24 funciones), pero es una app hoja de 629 LOC de vistas. Su riesgo principal es de seguridad (código de acceso) y va en la sección 7.

**Alternativas si se quiere reducir a 4 o 5:** (a) quitar `eieinfo` del análisis modular, porque la sección 7 ya cubre configuración y secretos; (b) fusionar `estudiantes` con `administrativos` como "núcleo de datos". No se recomienda quitar `profesores`, `administrativos` ni el área de trabajos finales, porque son los que sostienen H-06, H-09 y H-10.

### 1.3 Decisión

El estudiante eligió (2026-11-13) cambiar `eieinfo` por `webpage`. Los seis módulos de la sección 3 son:

1. `profesores`
2. `administrativos`
3. `estudiantes`
4. `firma_digital`
5. Área de trabajos finales (`trabajo_final_de_graduacion` + `trabajos_finales` + `profesores/views/trabajos_finales.py`)
6. `webpage`

`eieinfo` (configuración, correo e integraciones) no se audita como módulo, pero se cubre en las secciones 2.8, 5 y 7.

---

## 2. Evaluación por atributos de calidad (enunciado 7.1)

Escala usada en el resumen: **Buena** (fortalezas dominan), **Aceptable** (equilibrio), **Débil** (debilidades dominan), **Crítica** (el atributo está comprometido en todo el sistema).

| Atributo | Valoración | Módulos que mejor lo ilustran (problema) | Módulos de contraste (fortaleza) |
|---|---|---|---|
| Mantenibilidad | Débil | `profesores`, área de trabajos finales | `solicitud_documentos_externo`, `eieinfo/email_service.py` |
| Modificabilidad | Débil | `administrativos` (modelos), `eieinfo` (configuración) | `firma_digital` (fan-in 0) |
| Cohesión | Débil | `profesores`, `administrativos`, `webpage` | `postulaciones`, `firma_digital` |
| Acoplamiento | Crítica | `administrativos` ↔ `profesores` ↔ `estudiantes` ↔ `cursos` | `firma_digital`, `solicitud_documentos_externo` |
| Testabilidad | Débil | `profesores`, `estudiantes`, `webpage` (dependen de un volcado) | `firma_digital`, `solicitud_documentos_externo` |
| Seguridad básica | Crítica | `eieinfo` (secretos), `*/misc.py` (autorización), plantillas | `firma_digital` (control de acceso a PDF), nginx |
| Consistencia arquitectónica | Débil | `trabajos_finales`, `cursos`, `profesores` frente a `firma_digital` | — |
| Observabilidad operativa | Débil | `eieinfo/settings.py`, `eieinfo/misc.py` | `eieinfo/email_service.py` |

### 2.1 Mantenibilidad

**Fortalezas**

- La complejidad no está repartida por todo el código: de 1408 funciones de producción, solo 48 (3,4 %) tienen CC > 10, 11 tienen CC > 20 y ninguna pasa de 50; la CC media es 2,97 (`scripts/complejidad-eieinfo-0b3c575c.json`). El problema es de concentración, no de degradación general.
- Las apps grandes y antiguas ya están partidas por subárea: `profesores/views/` (13 módulos) con su espejo `profesores/urlpatterns/`, igual que `administrativos` (10 archivos de rutas) y `estudiantes` (9).
- El 44 % de las funciones de producción tiene docstring (618 de 1408; AST), y hay 9 README por app (E1 §8.3).
- Existe un servicio central de correo nuevo, `eieinfo/email_service.py:16` (`enviar_email`), con validación de entradas y registro de errores (`:119-129`), al que ya delegan `Funcionario.EnviarEmail` (`administrativos/models.py:443-452`) y `EnviarEmailTemplate` (`eieinfo/misc.py:123-136`).

**Debilidades**

- **Duplicación estructural alta.** `scripts/duplication.py` encuentra 65 grupos de clones estructurales (160 funciones, 1661 líneas redundantes) y 86 pares de funciones homónimas con ≥ 80 % de texto igual en archivos distintos. El caso más grave: `resumen_ciclo` (158 líneas, CC 25) existe dos veces y difiere en **una sola línea** (`diff` de `administrativos/views/consejo_asesor.py:129-286` contra `profesores/views/consejo_asesor.py:289-446`: solo cambia `CrearContextoAdministrativo` por `CrearContextoProfesor`). Lo mismo pasa con `consolidacion_aulas` (65 líneas), `nombramientos_interinos` (42), `nombramientos_continuidad` (35), `grupos`, `proyectos` y `descargar_reporte_ciclo`: 10 funciones homónimas entre los dos `consejo_asesor.py`.
- **Código comentado masivo.** En el área de trabajos finales hay 1999 líneas desactivadas con el prefijo `##`: `trabajos_finales/models.py` (596 de 1313), `trabajos_finales/forms.py` (489 de 1056), `profesores/views/trabajos_finales.py` (466 de 978), `estudiantes/views/trabajos_finales.py` (202 de 414), más `reports.py`, `views.py`, `misc.py`, `admin.py` y los dos `urlpatterns/tfg.py` completos (comando: `git grep -cE "^\s*##" -- '*.py'`). Proviene del commit `f5a94cab` ("…sin verificación flake8", 2025-02-15).
- **Archivos monolíticos en el código nuevo.** `firma_digital/views.py` tiene 2918 líneas, 90 funciones o métodos y la mayor CC acumulada del sistema (492); `trabajo_final_de_graduacion/views.py`, 1352 líneas.
- **Funciones largas:** 18 funciones superan las 100 líneas; las mayores son `_emparejar_firmado` (199 líneas, `firma_digital/views.py:2371`), `enviar_revision_propuesta_tfg` (196, `trabajo_final_de_graduacion/views.py:432`) y `editar_grupo` (167, `profesores/views/consejo_asesor.py:98`).
- **Código defectuoso que sobrevive porque nadie lo ejecuta ni lo prueba:** `Profesor.ActualizarGruposUsuario` recorre `Comision.objects.all()` pero usa `comision.comision.nombre` y `comision.otros_nombramientos`, que son atributos de `ComisionCiclo` (`profesores/models.py:160-200`, líneas 183-189; solo lo llama `scripts/owncloud.py:36`); `PracticaProfesional.GetEncargados` llama `.funcionarios` sobre un `QuerySet` (`estudiantes/models.py:1016-1019`, desde el commit `8609b97b` de 2020-10-06) y lo invocan las notificaciones del flujo de práctica profesional (`estudiantes/forms.py:555,560`; `profesores/views/practica_profesional.py:71`), sin ninguna prueba que lo cubra; `Comision.ComisionCicloActual` tiene código inalcanzable después del `return` (`administrativos/models.py:1048-1053`).

**Módulos que lo ilustran:** `profesores` y `administrativos` (duplicación del Consejo Asesor), área de trabajos finales (código comentado), `firma_digital` (archivo monolítico).

### 2.2 Modificabilidad

**Fortalezas**

- Agregar un módulo **hoja** es barato y el historial lo demuestra: `postulaciones` (2025-08), `firma_digital` (2025-09) y `solicitud_documentos_externo` (2026-03) entraron con fan-in 0–2 (E1 §4.1) y solo tocan `INSTALLED_APPS` y `eieinfo/urls.py`.
- Los parámetros de negocio de la firma digital están en un modelo de configuración editable (`firma_digital/models.py:11-109`, `ConfiguracionFirmaDigital`), no en constantes.

**Debilidades**

- **Los conceptos centrales no tienen un punto único de cambio.**
  - `Ciclo.ObtenerCicloActual()` se invoca 94 veces en 28 archivos de producción y está implementado como `Ciclo.objects.filter(actual=True)[0]` (`administrativos/models.py:252-255`): si no hay ciclo marcado como actual lanza `IndexError` en casi todas las vistas. La unicidad del ciclo actual solo la mantiene un bucle en `SetCicloActual` (`:240-250`), sin restricción en la base.
  - Los **roles y comisiones se identifican por texto libre**. El código vivo busca 16 literales de rol distintos y 3 de comisión en 16 archivos (`Roles.objects.get(nombre="Proyecto Eléctrico")`, `'Recepción' in roles`, `roles[0] == 'Encargado de programas'`…). `Roles.nombre` es un `CharField` sin `unique` ni `choices` (`administrativos/models.py:919-942`). En los datos semilla (`docker/db/init.sql`, tabla `roles_admin`) **10 de los 16 nombres que el código busca no existen**, y hay dos variantes del mismo rol en el código: `"Práctica Profesional"` (`profesores/misc.py:130`) y `"Practica Profesional"` (`estudiantes/models.py:1017`).
- **El esquema de datos no se puede evolucionar de forma controlada** (H-03): sin migraciones versionadas, cada cambio de modelo exige además editar a mano los volcados `docker/db/init.sql` y `docker/django/testing.sql`, porque el CI no ejecuta `migrate` (`.drone.yml:102`) y construye sus fixtures a partir de esos volcados (§6).
- **Cambiar la configuración implica tocar dos archivos divergentes** (`src/server/eieinfo/settings.py` y `docker/django/settings.py`, E1 §2.2) y no hay variables de entorno.
- **Cambiar una regla de autorización implica tocar N decoradores** (§2.6 y §5.3): la regla "tiene Jefatura" está escrita 8 veces en `profesores/misc.py` y `administrativos/misc.py`.

**Módulos que lo ilustran:** `administrativos` (modelos `Ciclo`, `Roles`, `Comision`), `eieinfo` (configuración), `profesores/misc.py`.

### 2.3 Cohesión

**Fortalezas**

- Las apps recientes tienen una sola razón para existir: `postulaciones` (contratación docente), `solicitud_documentos_externo` (trámite de documentos), `firma_digital` (flujo de firma). Sus modelos solo los usa la propia app (fan-in 0–2).
- Dentro de `profesores`, la división `views/<subárea>.py` + `urlpatterns/<subárea>.py` sí agrupa por tema.

**Debilidades**

- **`profesores` es un portal, no un módulo de dominio.** Define 2 modelos (`Profesor`, `DelegacionDirector`) pero 136 vistas (`scripts/views_audit.py`) sobre dominios ajenos: planificación de ciclo y nombramientos (`views/consejo_asesor.py`, 2117 líneas y 54 rutas), proyecto eléctrico (`views/trabajos_finales.py`), asistencias, práctica profesional, noticias, laboratorios, proyectos y publicaciones.
- **`administrativos` cumple dos papeles incompatibles:** es el núcleo de datos (17 modelos) y a la vez el portal del personal administrativo (87 vistas). Sus `models.py` solo dependen de otras apps por dos relaciones declaradas como cadena (`:968` y `:1109`); las otras 8 dependencias salientes vienen de sus vistas, formularios y utilidades (`views/*.py`, `forms.py`, `duplicar_ciclo.py`, `nombramientos_auto.py`, `reportes.py`).
- **`webpage` es sitio público y librería de utilidades** (E1 §4.3): `CrearContexto` se llama 53 veces desde otras apps.
- **Los modelos mezclan persistencia con efectos externos:** envío de correo (`Funcionario.EnviarEmail`, `CambioContraseñaFuncionario.EnviarEmailRecuperacion` en `administrativos/models.py:1164`), generación de PDF con LaTeX (`estudiantes/models.py:1001-1012`, `cursos/models.py:422`), publicación en Facebook (`anuncios/models.py:233`, duplicada en `eventos/models.py:239`), numeración de oficios por conteo de filas, con un `save()` dentro del método que invoca la propia plantilla LaTeX (`estudiantes/models.py:989-999`, `CartaPracticaProfesional.tex:24`) y generación de vCard (`profesores/models.py`, `GetVCardInfo`).
- **Los nombres de app no describen su contenido:** `trabajos_finales` hoy solo contiene Proyecto Eléctrico (las clases de TFG están comentadas, `trabajos_finales/models.py:674-1264`), mientras que las apps `proyecto_electrico`, `asistencias` y `practica_profesional` existen como carpetas vacías de código de producción (E1 §3.3).

**Módulos que lo ilustran:** `profesores`, `administrativos`, `webpage`, `trabajos_finales`.

### 2.4 Acoplamiento

**Fortalezas**

- Hay apps con dependencia en un solo sentido: `firma_digital` (fan-out 2, fan-in 0), `solicitud_documentos_externo` (2/0), `conferencias` (4/0), `postulaciones` (2/2).
- Las relaciones de modelo entre apps casi siempre apuntan hacia el núcleo: de 81 relaciones entre apps, 14 llegan a `profesores.Profesor`, 10 a `administrativos.Funcionario`, 9 a `estudiantes.Estudiante` y 7 a `administrativos.Ciclo` (`scripts/dominio-eieinfo-0b3c575c.json`). A nivel de **datos** la dirección es razonable; el desorden está en el **código**.

**Debilidades**

- 90 dependencias y 28 pares bidireccionales entre 19 apps (E1 §4.1). El ciclo `administrativos` ↔ `profesores` ↔ `cursos` ↔ `estudiantes` hace que ninguna de las cuatro pueda importarse, probarse ni desplegarse sin las otras tres.
- **Acoplamiento por código copiado:** las 10 vistas duplicadas del Consejo Asesor (§2.1) obligan a cambiar siempre dos archivos en dos apps.
- **Acoplamiento a un decorador y a un "contexto" globales por portal:** `CrearContextoProfesor` se llama 140 veces, `CrearContextoAdministrativo` 68, `CrearContexto` (de `webpage`) 53 y `CrearContextoEstudiante` 48. `CrearContextoProfesor` (`profesores/misc.py:25-140`, CC 23) hace al menos 12 consultas por petición e importa modelos de 5 apps, incluida `trabajo_final_de_graduacion` (`:16`). Cualquier vista de profesor paga ese costo y queda acoplada a esas 5 apps.
- **Acoplamiento a los datos:** el código depende de nombres concretos de filas (`Comision.objects.get(nombre='Docencia')` en `profesores/misc.py:294` y `:338` lanza `DoesNotExist` si la fila se renombra).
- **Acoplamiento de las pruebas entre apps:** las 26 pruebas de `postulaciones` cargan el fixture `profesores`, generado para otra app (`scripts/pruebas-eieinfo-0b3c575c.txt`).
- **Integridad referencial delegada a la base sin política explícita:** de 141 `ForeignKey`/`OneToOneField`, 80 usan `on_delete=DO_NOTHING` (57 %), 36 `CASCADE` y 17 `SET_NULL` (`scripts/domain.py`). Borrar un `Funcionario`, un `Ciclo` o un `Estudiante` depende de lo que haga MariaDB, no de una decisión de diseño.

**Módulos que lo ilustran:** `administrativos`, `profesores`, `cursos`, `estudiantes` (el ciclo central); `firma_digital` como contraste.

### 2.5 Testabilidad

**Fortalezas**

- Hay una suite real: 1166 funciones `test*`, de las que 1136 pertenecen a apps que el CI ejecuta (`.drone.yml:275`), con 2,6 aserciones por prueba en promedio y solo 2 pruebas sin ninguna aserción (`scripts/tests_audit.py`).
- El código reciente construye sus propios datos y aísla lo externo: `firma_digital/tests.py` (456 pruebas, 0 con fixture, 156 con `mock`) y `solicitud_documentos_externo/tests.py` (79 pruebas, 0 con fixture, 33 con `mock`).

**Debilidades**

- **El 39 % de las pruebas (454) depende de fixtures que no están en el repositorio** y que el CI genera con `dumpdata` de una base cargada desde un volcado SQL (`.drone.yml:228-258`; `fixtures` está en `.gitignore:43`). En las apps antiguas la dependencia es casi total: `profesores` 186 de 210, `webpage` 78 de 91, `administrativos` 75 de 84, `estudiantes` 36 de 36.
- **13 de los 14 `skip` existen porque el fixture no trae los datos necesarios** (por ejemplo `webpage/tests.py:383-471`: "No hay anuncios en el fixture", "No hay eventos en el fixture"…).
- **La lógica vive donde es difícil aislarla:** vistas de 150–200 líneas que mezclan permisos, consultas, reglas y correo (§2.1), modelos con efectos externos (§2.3) y decoradores que consultan la base. No hay capa de servicios (`git ls-files | grep -E "/(services|selectors)"` → vacío). Solo `firma_digital` (30 usos) y `postulaciones` (2) usan `transaction.atomic`; no hay `ATOMIC_REQUESTS`.
- **Los decoradores de autorización no tienen pruebas dirigidas** y contienen defectos de lógica (§2.6).
- No existe `conftest.py`, fábrica de datos (`factory_boy`, `model_bakery`) ni configuración de cobertura (E1 §6).

**Módulos que lo ilustran:** `profesores`, `estudiantes` y `webpage` (dependencia del volcado); `firma_digital` y `solicitud_documentos_externo` (contraste).

### 2.6 Seguridad básica

**Fortalezas**

- Contraseñas con PBKDF2 y sal (`administrativos/models.py:487-504`); tokens de recuperación con `uuid4` (122 bits) y expiración de un día (`administrativos/models.py:1157-1162`, `estudiantes/models.py:315-320`).
- De 401 vistas enrutadas, 324 tienen protección visible (228 por decorador, 63 por envoltura de CBV, 24 por *mixin*, 9 dentro del cuerpo) y las 77 restantes son, casi todas, páginas públicas por diseño (`scripts/vistas-eieinfo-0b3c575c.txt`; revisión manual en §7).
- CSRF activo por defecto: solo 4 `csrf_exempt` en todo el sistema. Sin SQL crudo, `eval`, `exec` ni `pickle` (`git grep` → 0); el único subproceso es `pdflatex` con lista de argumentos (`eieinfo/misc.py:161-165`).
- nginx de producción con TLS 1.2/1.3, HSTS y bloqueo de `/media/tfg/` (E1 §1.4); descarga de PDF de firma y de archivos de TFG con control de acceso en la vista (E1 §5.3).
- Sanitización explícita en un punto: `alumni/forms.py:139-140` limpia las ofertas de empleo con `bleach`.

**Debilidades**

- **Secretos en el historial, no solo en el árbol actual** (detalle en §7.1): una contraseña SSH del servidor de producción estuvo en `.drone.yml` (commit `4dea1744`, 2026-08-12, retirada al día siguiente pero permanente en el historial de `master`); la contraseña SMTP de `settings.py:345` es **la misma desde 2016-02-25**; la `SECRET_KEY` original de Django está en el commit `e36b1478`.
- **Defectos de lógica en la autorización** (lectura directa de `profesores/misc.py` y `administrativos/misc.py`):
  - `comisiones_login_required` (`profesores/misc.py:374-412`): la rama `elif roles:` contiene la expresión suelta `(roles[0] == 'Encargado de programas')` (`:396`), que no decide nada, y a continuación concede el acceso. **Cualquier profesor con cualquier rol asignado entra** a las vistas de comisiones (`profesores/views/comisiones.py:49`, `:163`, `:165`).
  - `profesor_or_comision_docencia_or_consejo_asesor_login_required` (`:326-371`): evalúa `roles[0]` cuando `roles` puede ser `None` (`ObtenerRolesFuncionario` devuelve `None` sin roles, `administrativos/misc.py:50-56`) y termina con `elif request.session.get('prof_id')` (`:354`), que siempre es verdadero. O falla con error 500 o equivale a `profesor_login_required`.
  - `comision_docencia_or_consejo_asesor_login_required` (`:282-324`, 15 usos en `atributos/views.py` y otros): `'Encargado de programas' in roles` con `roles = None` lanza `TypeError`. Un profesor sin roles recibe un error 500 en lugar de "acceso denegado". El mismo patrón está en `:186-189` y en `administrativos/misc.py:107`.
  - Permisos cacheados en sesión (`admn_inventario`, `admn_recepcion`, `admn_asuntos_estudiantiles`; `administrativos/misc.py:102-111`, `:173-182`, `:212-221`): revocar el rol no surte efecto hasta que la sesión expire (6 horas, `settings.py:229-236`).
- **Salida HTML sin escapar:** 119 bloques `{% autoescape off %}` en 101 plantillas (`git grep -c "autoescape off" -- '*/templates/*'`), sobre campos que escriben estudiantes, profesores y egresados (`avance.observaciones`, `concurso.justificacion`, `usuario.biografia`, `profesor.biografia`…). Solo un campo se sanea al guardar (`alumni/forms.py:139`).
- **Plantillas LaTeX con datos del usuario sin escape de LaTeX:** `estudiantes/templates/estudiantes/latex/CartaPracticaProfesional.tex:27-29,50` inserta `nombre_empleador`, `puesto_empleador`, `nombre_institucion` y `extra_carta`; no existe ningún filtro de escape para LaTeX (`git grep -nE "tex_escape|latex_escape"` → vacío) y `pdflatex` se invoca sin restricciones adicionales (`eieinfo/misc.py:161-165`).
- Redirección abierta tras el login, oráculo de credenciales en `/funcionarios/login` y código de postulación de 32 bits sin límite de intentos (E1 §5.3; se confirman en §7).
- Política de contraseñas mínima: 6 caracteres declarados, con un error de comparación que en realidad exige 7 (`administrativos/misc.py:19` y `:241`).

**Módulos que lo ilustran:** `eieinfo` (secretos y configuración), `profesores/misc.py` y `administrativos/misc.py` (autorización), plantillas de `profesores`, `estudiantes` y `webpage` (`autoescape off`); `firma_digital` como contraste.

### 2.7 Consistencia arquitectónica

**Fortalezas**

- Todo el sistema sigue el patrón MVT de Django con plantillas del servidor; no hay una segunda arquitectura conviviendo (ni API REST paralela ni SPA).
- Un patrón propio se repite de forma reconocible en las apps antiguas: `misc.py` con `CrearContexto*` y `*_login_required`, `views/` + `urlpatterns/` por subárea.

**Debilidades**

- **Tres generaciones de código con convenciones distintas:**

| Aspecto | Generación 2016–2018 (`profesores`, `administrativos`, `estudiantes`, `cursos`) | Generación 2025–2026 (`firma_digital`, `trabajo_final_de_graduacion`, `postulaciones`) |
|---|---|---|
| Vistas | Funciones + CBV envueltas a nivel de módulo (`x = deco(V.as_view())`, 63 casos) | CBV con *mixins* propios (`firma_digital`, 24) o funciones con decoradores importados de `profesores.misc` (TFG) |
| Estructura | `views/` y `urlpatterns/` por subárea | Un solo `views.py` (2918 y 1352 líneas) |
| Nombres | `CamelCase` para funciones y métodos (`ObtenerCicloActual`, `SetPassword`), como exige `README.md:26-29` | `snake_case` (`enviar_email`, `_emparejar_firmado`) |
| Usuario | Modelo propio por portal + sesión `*_id` | `firma_digital` referencia `django.contrib.auth.User` en 5 relaciones (`firma_digital/models.py:138,234,242,304,344`) |
| Tablas | `db_table` explícito en español (`funcionarios`, `ciclos_admin`) | Nombre por defecto de Django o con sufijo de versión (`…_tfg_v6`, `concurso_tfg_v6`) |
| Transacciones | Ninguna | `transaction.atomic` (30 usos en `firma_digital`) |
| Pruebas | Fixture global | Datos creados en `setUp` + `mock` |

  En producción hay 320 funciones en `CamelCase` y 958 en `snake_case` (AST, sin pruebas ni métodos especiales).
- **Dónde va la lógica de negocio no es una decisión del sistema:** está en vistas (`profesores`, TFG), en formularios (`cursos/forms.py`, `trabajos_finales/forms.py`), en modelos (`estudiantes/models.py`, 72 funciones) o en módulos sueltos (`administrativos/duplicar_ciclo.py`, `nombramientos_auto.py`, `reportes.py`).
- **La identidad del usuario se resuelve de formas distintas:** sesión `prof_id` más consulta por petición (decoradores), permiso cacheado en sesión (`administrativos`), `django.contrib.auth` (`conferencias`, wiki) y un `User` espejo que `Funcionario.SetPassword` mantiene en paralelo con la misma contraseña (`administrativos/models.py:487-504`, `:521-553`).
- **Idiomas mezclados** en identificadores, incluso con `ñ` (`contraseña`, `año`) junto a `password` (E1 §8.2).

**Módulos que lo ilustran:** `firma_digital` frente a `profesores` (dos estilos completos); `trabajos_finales` y `cursos` (lógica en formularios).

### 2.8 Observabilidad operativa

**Fortalezas**

- Hay configuración de `LOGGING` con cuatro *loggers* y archivos separados (`settings.py:239-309`), y un *logger* de aplicación (`eieinfo`) declarado en 28 archivos.
- `email_service.enviar_email` registra cada fallo con destinatarios y asunto (`eieinfo/email_service.py:126-128`).
- El CI notifica por Telegram y por correo (`.drone.yml:305-343`).

**Debilidades**

- **Pocas trazas y mal niveladas.** En unas 40 000 líneas de producción hay 67 llamadas de registro (`git grep -hoE "(logger|debug)\.(debug|info|warning|error|exception)\("`): 21 `error`, 8 `exception`, 3 `warning` y 35 `debug`. El *logger* `eieinfo` está configurado en nivel `ERROR` (`settings.py:293-297`), así que los `warning` y los `logger.debug` se descartan en producción.
- **Errores silenciados:** 51 `except:` sin tipo en producción (`administrativos` 14, `profesores` 12, `estudiantes` 9), muchos con `pass` (por ejemplo `profesores/misc.py:69-70`, `:116-117`, `:126-127`, `:137-138`).
- **Sin alertas:** `ADMINS` vacío, por lo que los tres `mail_admins` configurados no envían nada (E1 H-12).
- **Archivos de registro sin rotación y con ruta fija:** `logging.FileHandler` hacia `/var/info/logs/*.log` (`settings.py:258-275`); el *logger* `django` escribe en nivel `DEBUG` (`:288-292`). `conf/` no incluye configuración de `logrotate` (solo `eieinfo.service`, `eieinfo.socket` y el sitio de nginx). `GenerarLaTeX` escribe además en `/var/info/logs/latex.log` y `latex.tex` con ruta fija (`eieinfo/misc.py:187-193`).
- **Sin endpoint de salud, métricas ni identificador de petición** (`git grep -nE "health|status_check" -- '*/urls.py'` → vacío). gunicorn en producción solo registra errores (E1 §1.4).
- **Las tareas programadas no dejan constancia:** no se puede determinar desde el repo si `crontab add` se ejecutó en Faraday, y el contenedor no levanta cron (E1 §5.4).
- **Trabajo pesado dentro de la petición:** dos ejecuciones de `pdflatex` sin tiempo límite (`eieinfo/misc.py:160-167`) y envío SMTP síncrono, con solo 3 *workers* (`eieinfo.service`).

**Módulos que lo ilustran:** `eieinfo` (`settings.py`, `misc.py`); `email_service.py` como contraste.

---

## 3. Auditoría modular (enunciado 7.2)

Perfil por archivo usado en esta sección (LOC, líneas vivas, vistas, CC, apps importadas): script AST sobre cada módulo, con los datos de `scripts/complejidad-eieinfo-0b3c575c.json` y `scripts/vistas-eieinfo-0b3c575c.txt`. "Líneas vivas" = líneas no vacías que no empiezan con `#`.

### 3.1 `profesores`

**Responsabilidad principal (según su nombre):** gestionar al personal docente: perfil, categoría, carga y portal del profesor.

**Responsabilidades reales observadas**

| Responsabilidad real | Evidencia | Dominio al que pertenece |
|---|---|---|
| Planificación académica del ciclo: grupos, horarios, aulas, cátedras, ciclos lectivos, presupuestos, nombramientos, jefaturas, comisiones | `profesores/views/consejo_asesor.py` (2117 líneas, 55 vistas, 54 rutas en `urlpatterns/consejo_asesor.py`): `editar_grupo:98`, `crear_horario_grupo:488`, `aulas_disponibles:589`, `consolidacion_aulas:1443`, `crear_ciclo:1223`, `generar_nombramientos:1243`, `jefaturas:1160`, `crear_comision:1317` | `cursos` + `administrativos` (los modelos están allá) |
| Alta y edición de profesores, proyectos y laboratorios | `CrearProfesor:2026`, `EditarProyecto:2053`, `EditarLaboratorio:2081` (mismo archivo) | `profesores`, `proyectos`, `laboratorios` |
| Aprobación de asistencias de estudiantes | `gestionar_solicitudes_asistencias:1596`, `cambiar_estado_asistencia:1806`; `views/asistencias.py` (377 líneas, importa 9 nombres de `estudiantes`) | `estudiantes` (modelos `Asistencia*`) |
| Flujo completo de Proyecto Eléctrico del lado docente | `views/trabajos_finales.py` (428 líneas vivas, 13 vistas, 20 nombres importados de `trabajos_finales`); 12 rutas en `urlpatterns/proyecto_electrico.py` | `trabajos_finales` |
| Revisión de práctica profesional | `views/practica_profesional.py` (119 líneas) | `estudiantes` (`PracticaProfesional`) |
| Comisiones: programas de curso, proyectos, ofertas de empleo | `views/comisiones.py` (10 vistas; importa `alumni`, `cursos`, `proyectos`) | `cursos`, `alumni` |
| Noticias y eventos del profesor | `views/noticias.py` (9 vistas sobre `anuncios` y `eventos`) | `anuncios`, `eventos` |
| Delegación de la dirección | `profesores/models.py:221-293` (`DelegacionDirector`), `views/home.py:309-437` | Gobierno de la Escuela |
| **Autorización de casi todo el sistema docente** | `profesores/misc.py:143-543`: 11 decoradores que usan `atributos/views.py`, `trabajo_final_de_graduacion/views.py`, `postulaciones/views.py:9` y la propia app; `firma_digital` importa de ahí el contexto y una constante | Transversal |
| Tarea programada de recordatorio de asistencias | `profesores/cron.py:13` | `estudiantes` |

De sus 2 modelos, solo `Profesor` (`profesores/models.py:48-218`) es propiamente del dominio "profesores". Las 136 vistas se reparten en 13 archivos; solo `views/publico.py`, `views/home.py` y parte de `views/cursos.py` tratan del profesor como tal.

**Dependencias relevantes**

- *Salientes (12 apps):* `administrativos` (relaciones de modelo; 26 nombres importados solo en `consejo_asesor.py`), `cursos`, `estudiantes`, `trabajos_finales`, `trabajo_final_de_graduacion` (desde `misc.py:16` y `views/home.py`), `proyectos`, `laboratorios`, `alumni`, `anuncios`, `eventos`, `postulaciones`, `webpage`.
- *Entrantes (10 apps):* 14 relaciones de modelo hacia `Profesor` desde 5 apps (`trabajo_final_de_graduacion` 5, `proyectos` 3, `cursos` 2, `laboratorios` 2, `trabajos_finales` 2). Además `profesores.misc` (decoradores y `CrearContextoProfesor`) lo importan `atributos`, `firma_digital` (`firma_digital/misc.py:10`, incluida la constante privada `_PUESTOS_FIRMA`), `trabajo_final_de_graduacion/views.py:9` y `administrativos/views/reservaciones.py:16`.

**Fortalezas**

- Organización interna por subárea (`views/` y `urlpatterns/` en paralelo), que da una costura natural para extraer.
- La parte más delicada de la planificación (choques de horario y aulas) sí tiene pruebas dedicadas: `ChoqueHorarioModalTest`, `EditarGrupoCambioProfesorTest`, `AulasDisponiblesTest`, `ConsolidacionAulasTest` (`profesores/tests.py:1583-2185`), y la delegación de director tiene 2 clases (`:2438-3077`).
- La delegación de dirección está modelada con auditoría (quién modificó y desactivó, y cuándo; `profesores/models.py:250-275`).

**Debilidades**

- **Baja cohesión** (tabla anterior) y el archivo más complejo del código heredado: `views/consejo_asesor.py` tiene 7 funciones con CC > 10, entre ellas `editar_grupo` (CC 33, 167 líneas), la segunda más compleja del sistema.
- **Duplicación con `administrativos`:** 10 vistas del Consejo Asesor copiadas (§2.1) y las 4 vistas de delegación (`views/home.py:309-437` frente a `administrativos/views/delegacion_director.py:15-150`, similitud 0,86–0,97).
- **Decoradores con defectos de lógica** (§2.6): `comisiones_login_required` (`misc.py:393-397`) y `profesor_or_comision_docencia_or_consejo_asesor_login_required` (`:350-355`). Solo 2 menciones a decoradores en `profesores/tests.py`.
- **`CrearContextoProfesor` es un cuello de botella de diseño:** 140 llamadas, CC 23, 5 bloques `except:` que silencian errores (`misc.py:69`, `:90`, `:116`, `:126`, `:137`), consulta `ObtenerRolesFuncionario` dos veces (`:65` y `:89`) y asigna `context['roles']` solo dentro del `except` (`:92`).
- **Operaciones destructivas por GET:** 7 vistas de este módulo borran sin comprobar el método HTTP (`eliminar_grupo:1420`, `eliminar_nombramiento:268`, `eliminar_horario:575`, `views/cursos.py:235`, `views/noticias.py:48`, `views/publicaciones.py:34`, `views/comisiones.py:240`); `eliminar_nombramiento` además redirige a `request.GET['next']` sin validar (`:277-278`) y se enlaza con `<a href>` (`templates/profesores/consejo_asesor/editar_nombramiento.html:25`). En todo el sistema son 15.
- **Código muerto o roto:** `gestionar_solicitudes_asistentes_12312` (`consejo_asesor.py:1744`, sin ruta y sin cuerpo útil), `info_horario` (`:1070`, sin ruta en `profesores`), `CrearLectorView`/`crear_lector` (`views/trabajos_finales.py:872,972`, cuya ruta está en el `urlpatterns/tfg.py` comentado), `views/inventario.py` (0 líneas), `urlpatterns/tfg.py` (56 líneas comentadas), 466 líneas `##` en `views/trabajos_finales.py`, y `Profesor.ActualizarGruposUsuario` (`models.py:160-200`), que falla en cuanto el profesor pertenece a una comisión.
- **`sugerencias` no tiene decorador** (`views/home.py:240`): un visitante anónimo puede guardar una `Sugerencia` por POST y después la vista falla con `Profesor.DoesNotExist` al construir el contexto.
- **`webservice_profesor`** (`views/home.py:55-64`) devuelve cédula y correo de cualquier profesor por `pk` a cualquier otro profesor autenticado.
- **Tres definiciones de "director":** `Profesor.Director` (titular o subdirector con delegación vigente, `models.py:113-124`), `es_director` del contexto (titular o subdirector, sin delegación; `misc.py:19-22,50`) y `firma_digital.views.es_director` (`firma_digital/views.py:71-85`, igual que la anterior). El subdirector puede firmar documentos sin delegación, pero no entrar a las vistas protegidas con `director_login_required`.

**Riesgos de cambio**

- Cambiar un decorador de `misc.py` afecta a 5 apps a la vez y no hay pruebas que lo protejan.
- Cualquier cambio a una vista del Consejo Asesor hay que replicarlo en `administrativos`; si no, los dos portales divergen en silencio.
- `consejo_asesor.py` es el segundo archivo de producción más modificado (14 commits en 12 meses): alta probabilidad de conflictos entre grupos de estudiantes.
- 186 de sus 210 pruebas dependen del fixture `profesores`, así que un cambio de modelo en cualquier app puede romperlas por datos y no por lógica.

**Recomendaciones puntuales**

1. Corregir primero `comisiones_login_required` y los dos decoradores que evalúan `roles` sin comprobar `None`, con una prueba por decorador (permitido, denegado, sin sesión). Hacer que `ObtenerRolesFuncionario` devuelva `[]` en lugar de `None`.
2. Extraer `views/consejo_asesor.py` + `urlpatterns/consejo_asesor.py` + las 10 vistas gemelas de `administrativos` a una app `planificacion` (o similar) con **una** implementación y un decorador que acepte ambos tipos de sesión. Mantener los nombres de ruta `prof_*` y `admn_*` como alias para no romper plantillas.
3. Partir `CrearContextoProfesor` en un núcleo mínimo (profesor y ciclo actual) y proveedores opcionales por subárea; quitar los `except:` y registrar el error.
4. Mover los decoradores a un módulo neutral (por ejemplo `eieinfo/authz.py`) y unificar "es director" en un solo predicado en `Profesor`.
5. Convertir las 7 vistas `eliminar_*` a `@require_POST` con formulario y validar `next` con `url_has_allowed_host_and_scheme`.
6. Borrar el código muerto listado; el historial de git lo conserva.

### 3.2 `administrativos`

**Responsabilidad principal:** el portal del personal administrativo (por su nombre y su prefijo `/administrativos/`).

**Responsabilidades reales observadas**

| Responsabilidad real | Evidencia |
|---|---|
| **Núcleo de datos de toda la Escuela:** personas (`Funcionario`, polimórfico), tiempo (`Ciclo`), espacio (`Lugar`, `Horario`), organización (`Jefatura`, `Comision`, `Roles`, `Encargado`), contratación (`Nombramiento`, `TipoPresupuesto`, `PresupuestoCiclo`) | `administrativos/models.py:173-1217` (17 modelos); 30 relaciones entrantes desde 12 apps: `Funcionario` 10, `Ciclo` 7, `Lugar` 5, `Nombramiento` 3, `Horario` 2 |
| Credenciales y cuentas de **todos** los funcionarios, incluidos los profesores | `Funcionario.contraseña`, `SetPassword`, `GetOrCreateUsuario`, `UpdateUsuario` (`models.py:355`, `:487-553`); `CambioContraseñaFuncionario` (`:1129-1191`); login común `LoginFuncionario` usado por `webpage/views.py:388` |
| Portal administrativo: 87 vistas sobre dominios ajenos | `views/gestion_inventario.py` (15 vistas sobre `inventario`), `views/practica_profesional.py` (13, sobre `estudiantes`), `views/estudiantes.py` (9), `views/noticias.py` (10, sobre `anuncios` y `eventos`), `views/reservaciones.py`, `views/asistencias.py` |
| Segunda copia del Consejo Asesor | `views/consejo_asesor.py` (437 líneas, 10 vistas; §2.1) |
| Procesos de negocio por lotes | `duplicar_ciclo.py` (208 líneas, 8 funciones: duplica jefaturas, cátedras, grupos, laboratorios, proyectos y comisiones de un ciclo al siguiente), `nombramientos_auto.py` (305 líneas), `reportes.py` (298 líneas, XLSX) |
| Autorización del portal | `misc.py:69-237` (5 decoradores) |
| Utilidades de plantilla usadas por otras apps, incluido el lector de Instagram | `templatetags/misc_tags.py` (127 líneas) |

**Dependencias relevantes**

- *Entrantes:* 16 apps lo importan; 30 relaciones de modelo. Es la dependencia más fuerte del sistema.
- *Salientes (9 apps):* solo 2 nacen en `models.py` y están declaradas como cadena (`'estudiantes.CambioEnfasis'` en `:968`, `'laboratorios.Laboratorio'` en `:1109`). Las otras vienen de la capa de portal: `views/*.py` (`cursos`, `estudiantes`, `inventario`, `profesores`, `anuncios`, `eventos`, `webpage`), `forms.py:8-14` (`profesores`, `estudiantes`, `webpage`) y los procesos por lotes (`cursos`, `laboratorios`, `proyectos`, `profesores`).
- **Lectura:** si se separan los modelos del portal, la app de modelos queda con fan-out 2 (ambos evitables) y el ciclo `administrativos` ↔ resto desaparece casi por completo.

**Fortalezas**

- Los modelos núcleo tienen `db_table` explícito y nombres estables (`funcionarios`, `ciclos_admin`, `lugares`, `nombramientos`), lo que facilita mover clases entre apps sin migrar datos.
- La detección de choques está encapsulada en el modelo y es reutilizable (`Horario.RevisarColisiones:813`, `RevisarColisionesResponsable:870`; `MarcarChoques` en `misc.py:246-269`).
- `models.py` tiene CC máxima 7: la complejidad no está en los modelos.
- Es el módulo con más trazas (18 de las 67 llamadas de registro).

**Debilidades**

- **Doble papel** núcleo/portal (§2.3), origen de la mayoría de los ciclos de dependencia.
- **`Funcionario` mezcla identidad, credenciales, presentación e integración:** 21 campos y 8 métodos; `SetImagenDefault` (`:472-485`), `EnviarEmail` (`:443-452`), hash de contraseña con sal manual (`:487-504`) y sincronización con `auth.User` (`:521-553`). `GetOrCreateUsuario` depende de que existan los grupos `'Profesores'` y `'Administrativos'` (`Group.objects.get`, `:537-541`) y decide por `self.__class__.__name__`.
- **Dos almacenes de contraseña:** el hash vive en `Funcionario.contraseña` y se copia a `User.password` (`:528`, `:551`). El login de funcionarios hace `django_login` y además guarda `prof_id`/`admn_id` (`profesores/forms.py:82-84`, `administrativos/forms.py:67-69`).
- **`Ciclo` es un punto único de fallo:** `ObtenerCicloActual` (`:252-255`) lanza `IndexError` si no hay ciclo actual; `SetCicloActual` asigna un atributo inexistente (`self.borrador`, `:249`); `año` usa `default=date.today().year`, evaluado al importar (`:211-212`), no al crear cada fila; la lista enlazada `ciclo_anterior`/`ciclo_siguiente` no tiene validación.
- **Cuatro formas de decir "esta persona tiene esta función":** `Roles.funcionarios` (M2M), `Encargado` (funcionario + rol; el commit `8609b97b` dice eliminar su necesidad, pero el modelo sigue y `estudiantes.RequisitosGraduacion` aún lo referencia), `Comision.encargado`/`miembros`, y `Jefatura.puesto`. Más los modelos `*Ciclo` (`ComisionCiclo`, `JefaturaCiclo`, `LugarCiclo`), que el propio código marca como "legacy" (`models.py:1044-1046`) y que fuera de `models.py` casi solo usa `duplicar_ciclo.py`.
- **Procesos por lotes sin transacción:** `duplicar_ciclo.py` hace decenas de `save()` encadenados sin `transaction.atomic`; un fallo a mitad deja el ciclo duplicado parcialmente. Se lanza desde una acción del admin (`admin.py:8`). `GenerarNombramientos` y `LimpiarNombramientos` se invocan desde `profesores/views/consejo_asesor.py:1250,1265`.
- **Defectos menores que delatan falta de pruebas:** `DEPARTAMENTOS_REV` se construye a partir de `SI_O_NO` (`models.py:163`); `SI_O_NO_REV` está definido dos veces (`:142`, `:162`); `ValidarPassword` exige 7 caracteres aunque el mensaje dice 6 (`misc.py:19-23`, `:241`).
- 25 de sus 29 `ForeignKey`/`OneToOneField` usan `DO_NOTHING`.
- 14 `except:` sin tipo.

**Riesgos de cambio**

- Cualquier cambio de campo en `Funcionario`, `Ciclo`, `Lugar` u `Horario` afecta a 12 apps y, sin migraciones versionadas (H-03), no hay forma de revisar ni revertir el cambio de esquema.
- Renombrar una fila de `roles_admin` o de `comisiones` desde `/admin/` cambia quién tiene acceso (§2.2).
- Borrar un `Funcionario` o un `Ciclo` puede fallar por integridad referencial o dejar referencias colgantes, según el motor (`DO_NOTHING`).

**Recomendaciones puntuales**

1. Separar en dos apps sin mover tablas: `nucleo` (o `organizacion`) con los 17 modelos, conservando `db_table`, y `administrativos` solo como portal. Es la intervención que más ciclos elimina por unidad de esfuerzo.
2. Sustituir `Ciclo.objects.filter(actual=True)[0]` por un acceso que falle con un mensaje claro, y agregar una restricción que garantice un solo ciclo actual.
3. Dar a `Roles` y `Comision` un campo `codigo` (slug único, no editable) y reemplazar los 19 literales por constantes; el nombre visible queda libre para editarse.
4. Decidir un único almacén de contraseña para funcionarios (el `User` de Django) y dejar de duplicar el hash.
5. Envolver `DuplicarInstanciasCicloAnterior`, `GenerarNombramientos` y `LimpiarNombramientos` en `transaction.atomic`.
6. Eliminar `Encargado` y los modelos `*Ciclo` marcados como "legacy" después de confirmar con datos de producción que no se usan (no determinable desde el repo).

### 3.3 `estudiantes`

**Responsabilidad principal:** el portal del estudiante y su expediente.

**Responsabilidades reales observadas**

| Responsabilidad real | Evidencia |
|---|---|
| Identidad y cuenta del estudiante, con datos personales y bancarios | `Estudiante` (`estudiantes/models.py:110-246`): `cedula`, `celular`, `telefono`, `direccion`, `banco`, `cuenta_bancaria`, `cuenta_iban`; `VerificacionEstudiante` (`:249`), `RecuperacionContraseña` (`:295`) |
| Régimen de horas asistente y horas estudiante | Jerarquía polimórfica `Asistencia` → `AsistenciaCurso`, `AsistenciaLaboratorio`, `AsistenciaComision`, `AsistenciaProyecto`, `AsistenciaAdministrativa` (`:350-645`); `ConcursarAsistencia` (`:707`); `HorasDeAsistencia` (`:433`); `ConfigAsistencias` (`:1282`) |
| Práctica profesional completa: flujo, notificaciones y carta en PDF | `PracticaProfesional` (`:826-1181`): 26 campos, 14 métodos, 9 de ellos `Notificar*`, más `GenerarCarta` (LaTeX) y `NumeroOficio` |
| Cambio de énfasis y requisitos de graduación | `CambioEnfasis` (`:648`), `RequisitosGraduacion` (abstracta y polimórfica, `:1184`), `RequisitosBachillerato`, `RequisitosLicenciatura` |
| Lado estudiante de Proyecto Eléctrico | `views/trabajos_finales.py` (184 líneas vivas, 7 vistas; importa 9 nombres de `trabajos_finales`) |
| Lado estudiante de préstamos de bodega | `views/bodega.py` (importa 4 nombres de `inventario`) |
| Reportes de asistencias en XLSX | `reportes.py` (139 líneas) |

**Dependencias relevantes**

- *Salientes (9 apps):* 14 relaciones de modelo (`administrativos` 6, `cursos` 6, `laboratorios` 1, `proyectos` 1); `misc.py:8-9` importa `trabajos_finales` y `trabajo_final_de_graduacion` solo para armar el contexto del menú.
- *Entrantes (10 apps):* 9 relaciones hacia `Estudiante` desde 8 apps; `administrativos.ConfirmarCambioEnfasis` apunta a `CambioEnfasis` (`administrativos/models.py:968`), lo que cierra el ciclo `administrativos` ↔ `estudiantes` a nivel de modelo.
- Ciclo con `cursos`: `cursos.Grupo.estudiantes` (`cursos/models.py:580`) y `estudiantes.Estudiante.plan_estudio` (`estudiantes/models.py:144`).

**Fortalezas**

- Ninguna función supera CC 9; las vistas son cortas (máx. 91 líneas).
- La jerarquía `Asistencia` es un uso razonable de polimorfismo: un tipo por destino de la asistencia, con campos comunes en la base.
- `CrearContextoEstudiante` (`misc.py:12-59`) es defensivo (devuelve contexto vacío sin sesión) y hace pocas consultas.

**Debilidades**

- **Modelo como motor de flujo y notificador.** `models.py` es el archivo de modelos más grande (1347 líneas, 72 funciones). `PracticaProfesional` contiene estados, numeración de oficios, generación de PDF y 9 métodos de correo. Las transiciones de estado están en `estudiantes/forms.py:544-563`, en `profesores/views/practica_profesional.py` y en `administrativos/views/practica_profesional.py` (13 vistas).
- **Defecto en flujo activo, sin prueba que lo detecte:** `GetEncargados` (`:1016-1019`) hace `Roles.objects.filter(...)` y luego `rol.funcionarios`, que no existe en un `QuerySet`; además busca `"Practica Profesional"` sin tilde. Lo llaman `NotificarSolicitudEncargado` y `NotificarSolicitudCartaInicio`, que se ejecutan al guardar el formulario de solicitud (`forms.py:555,560`) y al aprobar requisitos (`profesores/views/practica_profesional.py:71`). Por lectura estática, esos caminos terminan en `AttributeError`; no se ejecutó para confirmarlo.
- **Numeración de oficios no atómica:** `NumeroOficio` (`:989-999`) calcula `count() + 1` y guarda; dos solicitudes simultáneas pueden obtener el mismo número. La invoca la plantilla LaTeX (`CartaPracticaProfesional.tex:24`), es decir, **renderizar la carta escribe en la base**.
- **Datos del usuario hacia LaTeX sin escape** (§2.6): un `&` o un `%` en el nombre de la empresa rompe la compilación; una secuencia `\input{…}` se interpretaría.
- **Duplicación interna:** 6 métodos `Search` estructuralmente idénticos en las subclases de `Asistencia` (`:220`, `:477`, `:517`, `:549`, `:589`, `:632`), dos de ellos exactos.
- **Pruebas insuficientes para su peso:** 36 pruebas para 4111 líneas, todas dependientes del fixture `estudiantes`; ninguna cubre práctica profesional más allá de un GET (`estudiantes/tests.py:281-282`).
- **Datos sensibles en claro:** cédula, dirección y cuenta IBAN son `CharField` simples; las tablas `estudiantes` de `docker/db/init.sql` y `docker/django/testing.sql` traen filas (§7).
- 17 de 19 `ForeignKey` con `DO_NOTHING`; 9 `except:` sin tipo.
- El estudiante no tiene `User` de Django (a diferencia del funcionario): su sesión es solo `est_id` (`estudiantes/forms.py:124`).

**Riesgos de cambio**

- Tocar `PracticaProfesional` exige revisar tres apps (`estudiantes`, `profesores`, `administrativos`) y no hay pruebas del flujo.
- `Estudiante` es referenciado por 8 apps: cualquier cambio de campo se propaga sin red de seguridad.
- Subir de versión `django-polymorphic` afecta a `Asistencia` y `RequisitosGraduacion` (y a `Funcionario`, `Bien`, `Prestamo`, `PlantillaCurso`).

**Recomendaciones puntuales**

1. Corregir `GetEncargados` (usar el rol por código y devolver funcionarios) y cubrir con pruebas las dos notificaciones de práctica profesional.
2. Sacar de `PracticaProfesional` las notificaciones y la generación de la carta a un módulo de servicio (`estudiantes/practica_profesional/servicio.py`), dejando en el modelo solo estado y datos; concentrar ahí las transiciones que hoy están en un formulario y dos vistas.
3. Generar el número de oficio dentro de una transacción con bloqueo, o con una secuencia por año, y **fuera** del renderizado de la plantilla.
4. Agregar un filtro de escape para LaTeX y aplicarlo a todos los campos de usuario de `CartaPracticaProfesional.tex`.
5. Subir `Search` a la clase base `Asistencia` (o a un *manager*) y borrar las 6 copias.
6. Sustituir los volcados con datos de estudiantes por datos sintéticos (§7).

### 3.4 `firma_digital`

**Responsabilidad principal:** gestionar solicitudes de firma digital de documentos PDF por parte de la Dirección.

**Responsabilidades reales observadas**

Coinciden con el nombre; es el módulo más cohesivo de los seis.

| Responsabilidad | Evidencia |
|---|---|
| Carga de PDF, individual y por lotes | `CargarPDFView:652`, `CargarLoteIniciarAJAXView:884`, `CargarPDFLoteAJAXView:926` (`firma_digital/views.py`) |
| Descarga para firmar y recepción del firmado, con emparejamiento automático por nombre y contenido | `IniciarDescargaFirmaView:2060`, `SubirFirmadoLoteAJAXView:2590`, `_emparejar_firmado:2371` (199 líneas, CC 28) |
| Máquina de estados de la solicitud | `EstadoSolicitud` (`firma_digital/models.py:116`), `firmar_pdf` (`firma_digital/misc.py:17-64`) |
| Notificaciones por correo con registro idempotente | `NotificacionFirma` (`models.py:440-477`), `_reclamar_notificacion:280`, `_notificar_operacion_finalizada:344` |
| Control de acceso a los documentos | `_tiene_sesion_portal:1149`, `_puede_ver_pdf:1205`, `DescargarPDFAPIView:1211` |
| Recordatorio diario al director | `firma_digital/cron.py:10` |

**Dependencias relevantes**

- *Salientes:* `administrativos` (`Jefatura`, `Funcionario`, `Administrativo`), `profesores` (`Profesor`, y de `profesores.misc`: `CrearContextoProfesor` y la constante privada `_PUESTOS_FIRMA`, `firma_digital/misc.py:10`), `eieinfo`. Cinco relaciones hacia `django.contrib.auth.User` y una hacia `Funcionario` (`models.py:488`).
- *Entrantes:* ninguna (fan-in 0). `estudiantes.PracticaProfesional.NotificarDirectorFirmaDigital` (`estudiantes/models.py:1145`) solo envía un correo; no importa la app.

**Fortalezas**

- **Concurrencia tratada explícitamente:** `firmar_pdf` hace un `UPDATE` condicionado por estado y por número de revisión dentro de `transaction.atomic` (`misc.py:33-52`), lo que evita aceptar un firmado de una versión anterior. Es el único módulo con uso sistemático de transacciones (30 apariciones).
- **Notificaciones fuera de la petición:** `ThreadPoolExecutor` de 2 hilos con deduplicación local y registro persistente (`misc.py:160-239`), más una vista de reintento (`ReintentarNotifOperacionView:2691`).
- **Estados con `TextChoices`** en lugar de enteros o cadenas sueltas (`models.py:116`, `:404`, `:445`, `:450`).
- **Suite propia:** 456 pruebas, 0 dependientes de fixture, 156 con `mock`, 2 `TransactionTestCase` para la concurrencia.
- Validación del archivo (`_validar_archivo_pdf:1899`) y saneamiento del nombre en la descarga (`_sanitizar_nombre_archivo:1156`, `_safe_content_disposition:1181`).

**Debilidades**

- **Un solo archivo de 2918 líneas:** 28 clases de vista y 51 funciones de módulo, CC acumulada 492 (la mayor del sistema), 11 funciones con CC > 10 y 4 con más de 100 líneas. Es además el archivo más modificado del año (41 commits), con solo 2 autores.
- **Dependencia circular interna:** `views.py` importa de `misc.py` (`:44-48`) y `misc.py` importa de `views.py` dentro de las funciones (`misc.py:171`, `:211`). La lógica de notificación está repartida entre los dos.
- **Identidad mixta:** unas vistas usan `ProfesorOAdminLoginRequired` (sesión `prof_id`/`admn_id`, `views.py:53-59`) y otras `LoginRequiredMixin` de Django (16 clases frente a 8); `_puede_ver_pdf` compara contra `request.user.id` (`:1205-1208`) mientras `_usuario_de_sesion` reconstruye el `User` desde la sesión del portal (`misc.py:84-102`). Funciona porque el login de funcionarios hace ambas cosas (§3.2), pero son dos fuentes que pueden desincronizarse.
- **PDF dentro de la base de datos:** `PDF.data` y `SignedPDF.data` son `BinaryField` (`models.py:206`, `:302`). El tamaño de la base y de sus respaldos crece con cada documento; el resto del sistema usa `FileField` en `/media`.
- **Cola en memoria del proceso:** si gunicorn reinicia el *worker* (despliegue o `--timeout 300`), los correos encolados se pierden; lo compensan el registro `NotificacionFirma` y el reintento manual, no un mecanismo automático.
- **Regla "quién firma" duplicada** respecto a `profesores` (§3.1).
- `GuardarPDFFirmadoAPIView` está exenta de CSRF (`views.py:1268`); comprueba sesión dentro del cuerpo. Se entiende por la integración con Firmador Libre, pero es la única escritura del sistema sin CSRF.
- Settings huérfanos: `MAX_PDF_SIZE`, `FIRMADOR_LIBRE_PORT` y `CORS_ALLOWED_ORIGINS` no se leen en el código (E1 §2.2); la configuración real está en el modelo `ConfiguracionFirmaDigital`.
- Las 3 pruebas JavaScript (`firma_digital/tests_js/*.test.cjs`) no se ejecutan en el CI y no hay `package.json` que diga cómo correrlas.

**Riesgos de cambio**

- Con `_emparejar_firmado` (CC 28) y un archivo de casi 3000 líneas, cada cambio obliga a entender todo el flujo; lo sostiene la suite, no el diseño.
- Conocimiento concentrado en 2 autores.
- Cambiar el modelo de autenticación de funcionarios (§3.2) rompe las vistas que usan `request.user`.

**Recomendaciones puntuales**

1. Partir `views.py` en un paquete sin cambiar comportamiento: `views/carga.py`, `views/firma.py`, `views/descargas.py`, `views/solicitudes.py`, y mover las funciones puras (`_emparejar_firmado`, `_nombre_casa_con_pdf`, `_candidatos_por_nombre`, validaciones) a `servicios/emparejado.py`. Las 456 pruebas dan red de seguridad.
2. Reunir toda la notificación en un solo módulo (`notificaciones.py`) para eliminar el import circular.
3. Elegir una sola fuente de identidad dentro del módulo (un *mixin* que resuelva usuario y rol una vez por petición).
4. Evaluar mover los binarios a `FileField` con la misma protección que `/media/tfg/`; si se quedan en la base, documentar el impacto en los respaldos.
5. Agregar al CI un paso que ejecute `tests_js/`.
6. Importar la regla de "puede firmar" desde un único lugar público, no una constante con guion bajo de otra app.

### 3.5 Área de trabajos finales (`trabajo_final_de_graduacion`, `trabajos_finales`, `profesores/views/trabajos_finales.py`)

**Responsabilidad principal:** `trabajos_finales` sugiere todos los trabajos finales; `trabajo_final_de_graduacion`, el TFG de licenciatura.

**Responsabilidades reales observadas**

| Pieza | Qué contiene hoy | Evidencia |
|---|---|---|
| `trabajos_finales` | **Solo Proyecto Eléctrico** (curso de bachillerato): `ProyectoElectrico`, `Avance`, `Lector`, `Clasificacion`, `CitaPresentacion`, `ConcursoProyectoElectrico`, y 3 vistas públicas. Las clases de TFG están comentadas. | Clases vivas en `trabajos_finales/models.py:158-1174`; comentadas `##class AvanceTFG:674`, `##class TrabajoFinalGraduacion:706`, `##class ConcursoTFG:1177`, `##class CitaPresentacionTFG:1264` |
| `profesores/views/trabajos_finales.py` y `estudiantes/views/trabajos_finales.py` | Las vistas privadas de Proyecto Eléctrico (13 y 7), protegidas con `pe_login_required` (`trabajos_finales/misc.py:9`) | 12 rutas en `profesores/urlpatterns/proyecto_electrico.py`, 7 en `estudiantes/urlpatterns/proyecto_electrico.py` |
| `trabajo_final_de_graduacion` | El proceso nuevo de TFG (desde 2025-03-13): interés, solicitud, revisores, parecer de comisión, correcciones, y listado público. 26 vistas en un archivo para **tres actores** (estudiante, profesor, comisión) | `trabajo_final_de_graduacion/views.py:122-1347`; 13 estados enteros en `models.py:9-36` |
| `proyecto_electrico` (carpeta no instalada) | Un README que describe las rutas reales y 2 pruebas que el CI no ejecuta | E1 §3.3 |

Es decir, la duplicación señalada en H-10 no es "dos implementaciones vivas de TFG": el TFG antiguo se desactivó **comentándolo** (commit `f5a94cab`, 2025-02-15, "sin verificación flake8") y lo que convive son dos flujos hermanos (Proyecto Eléctrico y TFG) con la misma forma: concurso → asignación → avances → presentación o defensa.

**Dependencias relevantes**

- `trabajos_finales` → `administrativos` (`Ciclo`, `Nombramiento`), `estudiantes`, `profesores`, `proyectos`, `laboratorios`, `webpage` (8 relaciones de modelo salientes, las 10 `ForeignKey` con `DO_NOTHING`).
- `trabajo_final_de_graduacion` → `profesores` (5 relaciones a `Profesor`, más los decoradores y `CrearContextoProfesor`), `estudiantes` (2), `administrativos` (`Ciclo`, `Comision`, `Roles`), `cursos`, `webpage`.
- *Entrantes:* `profesores/misc.py:16` y `estudiantes/misc.py:8-9` importan modelos de ambas apps para armar el menú de **toda** vista; `profesores/views/home.py:45` borra `ArchivoTemporalTFG` al cerrar sesión.

**Fortalezas**

- El TFG nuevo sirve los archivos con control de acceso y lista blanca de campos (`views.py:1189-1255`, `CAMPOS_ARCHIVO_TFG_DESCARGABLES`), coherente con el bloqueo de `/media/tfg/` en nginx.
- Las vistas por actor comprueban pertenencia: `detalle_tfg_est` filtra por el estudiante de la sesión (`views.py:345`) y `detalle_tfg_profesor` por comité asesor (`:322-330`).
- Estados con constantes nombradas (`ESTADO_*`, `models.py:9-21`), mejor que las cadenas de `trabajos_finales` (`estados['Reprobado']`).
- 74 pruebas del TFG nuevo, 24 con fixture y el resto con datos propios.

**Debilidades**

- **1999 líneas comentadas** entre las tres piezas (§2.1): el 45 % de `trabajos_finales/models.py` y el 46 % de `trabajos_finales/forms.py` es código inactivo. Las métricas de tamaño de la Entrega 1 para esta app estaban infladas por eso (§10).
- **Nombres que engañan:** `trabajos_finales` es Proyecto Eléctrico; la comisión que da acceso al TFG nuevo se llama `"Trabajos Finales de Graduación"` (`profesores/misc.py:429`, `trabajo_final_de_graduacion/views.py:1197`), el contexto del profesor busca el rol `"Trabajos Finales de Graduación"` (`profesores/misc.py:120`), que en los datos semilla se llama `"Trabajo Final de Graduación"`, y en esos mismos datos existen las dos comisiones, en singular y en plural (§4.7).
- **Dos decoradores para la misma comisión con criterios distintos:** `comision_tfg_login_required` exige nombre exacto y toma la primera comisión (`misc.py:429`); `revisor_or_comision_tfg_login_required` usa `icontains` sobre el plural y acepta varias (`:479-480`); su comentario dice tolerar singular y plural, pero el filtro no encuentra el singular.
- **Flujo de TFG concentrado en vistas largas:** `enviar_revision_propuesta_tfg` (196 líneas, CC 29) y `parecer_comision_unificado` (133 líneas, CC 21); 10 asignaciones directas de `estado` repartidas en `views.py`, sin transacción y sin una tabla de transiciones.
- **Tablas con versión en el nombre** (`trabajo_final_de_graduacion_tfg_v6`, `concurso_tfg_v6`, `…_defensa_v6`, `…_asesorexterno_v6`; `models.py:90,115,163,199`): el esquema se versionó a mano porque no hay migraciones (H-03).
- **Código roto que nadie llama:** `TFG.NotificarEstudiante` usa `self.estudiante`, pero el campo es `estudiantes` (`models.py:154-160`); `eliminar_tfg` (`views.py:1282`) no tiene ruta.
- **Duplicación entre flujos hermanos:** `EmailConcursoProf` (`trabajos_finales/models.py:1104` y `trabajo_final_de_graduacion/models.py:210`, 82 % igual); `precarga.py` del TFG y de `solicitud_documentos_externo` casi idénticos (98 %); 4 validadores de PDF clonados en `trabajo_final_de_graduacion/forms.py:246-654`.
- **Proyecto Eléctrico casi sin pruebas:** 5 pruebas en `trabajos_finales/tests.py`, que además el CI no ejecuta (la app no está en `.drone.yml:275`).

**Riesgos de cambio**

- Quien llegue a modificar "trabajos finales" tiene que descubrir primero qué mitad del código está viva.
- El TFG nuevo depende de datos (nombre exacto de la comisión): un cambio en `/admin/` deja a la comisión sin acceso (`"Comisión de TFG no encontrada"`, `profesores/misc.py:431-433`).
- Cambiar un estado de TFG exige revisar 15 comparaciones y 10 asignaciones en un archivo de 1352 líneas.
- Proyecto Eléctrico se puede romper sin que ninguna prueba del CI lo note.

**Recomendaciones puntuales**

1. Borrar las 1999 líneas comentadas y los dos `urlpatterns/tfg.py`; dejar constancia del commit `f5a94cab` en el README de la app.
2. Renombrar la app `trabajos_finales` a `proyecto_electrico` conservando `db_table`, y eliminar la carpeta homónima vacía. Así cada app nombra un proceso.
3. Agregar `trabajos_finales` a la lista de pruebas del CI y escribir pruebas del flujo de concurso y prórroga.
4. Concentrar las transiciones de TFG en un módulo (`trabajo_final_de_graduacion/flujo.py`) con una tabla estado → estados permitidos, y llamar desde las vistas dentro de `transaction.atomic`.
5. Un solo decorador de comisión TFG, basado en un código de comisión (§3.2, recomendación 3).
6. Partir `views.py` por actor (`views/estudiante.py`, `views/profesor.py`, `views/comision.py`, `views/publico.py`).
7. Extraer `precarga.py` a un módulo común para `solicitud_documentos_externo` y TFG.

### 3.6 `webpage`

**Responsabilidad principal:** el sitio web público de la Escuela.

**Responsabilidades reales observadas**

| Responsabilidad real | Evidencia |
|---|---|
| Sitio público: 27 vistas de páginas informativas | `webpage/views.py:42-398`; 30 rutas en `webpage/urls.py` |
| **Mini gestor de contenidos** para todo el sistema: textos, imágenes, archivos y páginas identificados por nombre | `Texto`, `ImagenEstatica`, `ArchivoEstatico`, `SeccionesDocs`, `PaginaEstatica` (`webpage/models.py:7-137`); `GetTexto`, `GetImagen`, `GetDocumento` (`webpage/misc.py:40-73`): 46 llamadas a `GetTexto` con 34 claves distintas en todo el código |
| **Contexto base de plantillas de los portales** | `CrearContexto` (`misc.py:25-37`): 53 llamadas; 23 archivos de otras apps importan `webpage` |
| Buzón de sugerencias de los tres portales | `Sugerencia` (`models.py:140`), importada por `estudiantes`, `profesores` y `administrativos` |
| Estadísticas institucionales de la portada | `stats_institucionales` (`misc.py:76-124`), con valores manuales en `ConfigWebpageHome` (`models.py:231`) |
| Punto de entrada de vistas de **otras** apps | `webpage/urls.py:44-56` enruta `administrativos.views.publico.recuperar_contraseña` y `cambiar_contraseña`, y `postulaciones.formulario_postulacion` |
| Servicio de verificación de credenciales de funcionarios | `login_webservice` (`views.py:386-395`), ruta `^funcionarios/login$` (`urls.py:50`) |
| Búsqueda (Google Custom Search), contacto con reCAPTCHA, créditos | `busqueda:226`, `contact:52`, `creditos:294` |

**Dependencias relevantes**

- *Salientes (8 apps):* `misc.py:3-11` importa `anuncios`, `eventos`, `estudiantes`, `profesores`, `laboratorios`, `proyectos` y `administrativos`. Como `misc.py` es justo lo que importan las demás apps, **importar `CrearContexto` arrastra siete apps**.
- *Entrantes (12 apps):* por `misc` (19 archivos), por `models` (`Sugerencia`, `ArchivoEstatico`, `SeccionesDocs`, `Texto`) y por `forms`. Una relación de modelo: `cursos.PlanDeEstudio.textos` → `webpage.Texto` (`cursos/models.py:830`).
- Enrutamiento: está incluido en `^` en `eieinfo/urls.py:62`, **antes** de `atributos/`, `firma_digital/`, `trabajo_final_de_graduacion/` y `solicitud_documentos_externo/` (`:64-70`).

**Fortalezas**

- Vistas simples (CC máxima 6) y `models.py` sin dependencias externas.
- Los modelos de contenido tienen `unique=True` en su clave (`models.py:11,34,61,87,118`).
- `GetTexto`, `GetImagen` y `GetDocumento` registran un error cuando falta el contenido (`misc.py:48,61,73`), en vez de fallar la página.
- El formulario de contacto usa reCAPTCHA (`webpage/forms.py:9,90`) y 91 pruebas recorren las páginas públicas.

**Debilidades**

- **Tres papeles en una app** (sitio, gestor de contenidos, contexto compartido), y el más usado por otros (`misc.py`) es el más acoplado.
- **Ruta no anclada en el *include* raíz:** `re_path(r'tramites_graduacion', …)` (`urls.py:36`) no lleva `^`, de modo que cualquier URL que contenga esa cadena y llegue a `webpage` (todas las que no coincidan antes) la captura; esto incluye las de las 4 apps registradas después. Hoy no hay colisión (`git grep tramites_graduacion -- '*/urls.py'` solo devuelve esa línea), pero contradice la nota de la Entrega 1 de que todas sus rutas están ancladas (§10).
- **`login_webservice`** (`views.py:386-395`): sin CSRF, sin autenticación y sin límite de intentos; responde `Login Granted` o `401` para credenciales de funcionario. No se encontró ningún consumidor en el repo (`git grep -n "funcionarios/login"` solo devuelve la ruta y sus pruebas); no determinable si lo usa un sistema externo.
- **Contenido administrado sin escape:** `texto.contenido` aparece 29 veces dentro de `{% autoescape off %}` y `pagina.texto` una. Quien edita `Texto` en `/admin/` puede inyectar HTML y JavaScript en los portales autenticados.
- **Regla de negocio copiada:** `stats_institucionales` reimplementa "profesor activo" y lo dice en un comentario ("Replica `Profesor.estaActivo`", `misc.py:96`), además de la que ya existe en `Profesor.ObtenerActivos`.
- **Diagnóstico por `print`:** `views.py:93`, `:211` y `:220` (`print(f"[!] Omitida jefatura por error: …")`) escriben a la salida estándar en lugar del registro.
- **Pruebas atadas al volcado:** 78 de 91 dependen del fixture `prod` y 9 están en `skip` por falta de datos (`webpage/tests.py:268-471`). El nombre `prod` existe también en `administrativos/fixtures/`, así que el cargador encuentra dos archivos con el mismo nombre.
- `handler404` pasa `locals()` a la plantilla (`views.py:341-342`).
- Importa valores directamente de `eieinfo.settings` (`views.py:16`) en vez de `django.conf.settings`, patrón repetido en 6 archivos.

**Riesgos de cambio**

- Modificar `webpage/misc.py` obliga a volver a probar los tres portales, porque 19 archivos de otras apps lo importan.
- Agregar una ruta nueva en `webpage/urls.py` puede ocultar rutas de las 4 apps incluidas después.
- Borrar o renombrar un `Texto` desde `/admin/` deja páginas con secciones vacías sin que falle ninguna prueba (solo queda una línea en el registro de errores).

**Recomendaciones puntuales**

1. Mover `Texto`, `ImagenEstatica`, `ArchivoEstatico`, `SeccionesDocs`, `PaginaEstatica` y los `Get*` a una app `contenido` sin dependencias; dejar en `webpage` solo las vistas públicas.
2. Mover `CrearContexto` a un *context processor* o a una app base, de forma que los portales no importen el sitio público ni sus siete dependencias.
3. Anclar `tramites_graduacion` y mover `include('webpage.urls')` al final de `eieinfo/urls.py`.
4. Retirar `login_webservice` si no tiene consumidor conocido; si lo tiene, protegerlo con credencial de servicio y límite de intentos.
5. Sanear `Texto.contenido` al guardar (`bleach`, que ya se usa en `alumni/forms.py:139`) y declarar `bleach` en `requirements.txt` (hoy llega solo como dependencia transitiva).
6. Reemplazar las 9 pruebas en `skip` por pruebas que creen su propio anuncio, evento o laboratorio.

---

## 4. Auditoría del dominio (enunciado 7.3)

Fuente: `scripts/domain.py` (AST sobre todos los `models.py`) y su salida `scripts/dominio-eieinfo-0b3c575c.json`, más lectura directa de los modelos citados.

```bash
python3 -I docs/anexos/scripts/domain.py ~/repos/EIEInfo docs/anexos/scripts/dominio-eieinfo-0b3c575c.json
```

Cifras globales: **117 modelos** en 18 apps, unos 800 campos, 179 relaciones (134 `ForeignKey`, 38 `ManyToManyField`, 7 `OneToOneField`), de las cuales **81 cruzan de una app a otra**. Hay 6 jerarquías polimórficas con 15 subclases y un solo modelo abstracto. 84 modelos fijan `db_table` y 33 usan el nombre por defecto de Django.

### 4.1 Entidades principales

| Subdominio | Entidades centrales | App donde viven | Observación |
|---|---|---|---|
| Personas internas | `Funcionario` → `Profesor`, `Administrativo` | `administrativos`, `profesores` | `Profesor` es la entidad más referenciada desde otras apps (14 relaciones) |
| Tiempo | `Ciclo` (ciclo lectivo) | `administrativos` | 7 relaciones entrantes; 94 llamadas a `ObtenerCicloActual` |
| Espacio y agenda | `Lugar`, `Horario` | `administrativos` | `Horario` sirve a la vez para clases, consulta y reservaciones |
| Organización y carga | `Nombramiento`, `Jefatura`, `Comision`, `Roles`, `Encargado`, `TipoPresupuesto`, `PresupuestoCiclo` | `administrativos` | Cuatro mecanismos distintos para "quién hace qué" (§4.6) |
| Oferta académica | `PlantillaCurso` → `Curso`, `Catedra`, `Grupo`, `PlanDeEstudio`, `Ciclo` (bloque) | `cursos` | `Grupo` une profesor, estudiantes, horario y aula |
| Estudiantes | `Estudiante`, `Asistencia` (5 subtipos), `ConcursarAsistencia`, `PracticaProfesional`, `CambioEnfasis`, `RequisitosGraduacion` | `estudiantes` | `Estudiante` recibe 9 relaciones de 8 apps |
| Trabajos finales | `ProyectoElectrico`, `Avance`, `Lector`, `ConcursoProyectoElectrico`; `TFG`, `ComiteAsesor`, `RevisionRevisor`, `Defensa`, `ConcursoTFG` | `trabajos_finales`, `trabajo_final_de_graduacion` | Dos flujos hermanos en dos apps |
| Investigación y extensión | `Laboratorio`, `Proyecto`, `Publicacion` | `laboratorios`, `proyectos` | Con variantes por ciclo (`LaboratorioCiclo`, `ProyectoCiclo`) |
| Firma digital | `PDF`, `SignedPDF`, `LoteSolicitud`, `OperacionFirma`, `NotificacionFirma` | `firma_digital` | Único subdominio ligado a `auth.User` |
| Inventario | `Bien` → `Activo` → `Computadora`, `Componente`; `Prestamo` → 2 subtipos | `inventario` | Dos jerarquías polimórficas |
| Externos | `Alumnus`, `OfertaEmpleo`; `Postulante` y su expediente; `Solicitud` de documentos | `alumni`, `postulaciones`, `solicitud_documentos_externo` | Sin relación de modelo con `Estudiante` o `Funcionario`, salvo `Solicitud.estudiante` |
| Contenido | `Texto`, `ImagenEstatica`, `ArchivoEstatico`, `PaginaEstatica`; `Anuncio`, `Evento` | `webpage`, `anuncios`, `eventos` | Contenido identificado por nombre |

### 4.2 Diagrama entidad-relación simplificado

25 de las 117 entidades. Fuente: [`../diagramas/dominio.mmd`](../diagramas/dominio.mmd).

```mermaid
%% Diagrama entidad-relación simplificado del dominio de EIEInfo (commit 0b3c575c).
%% 25 de 117 modelos. Fuente: docs/anexos/scripts/dominio-eieinfo-0b3c575c.json
%% (generado con docs/anexos/scripts/domain.py) y lectura de los models.py citados
%% en docs/anexos/levantamiento-e2.md, sección 4.
%%
%% Convenciones:
%%   - Ciclo_admin  = administrativos.Ciclo (ciclo lectivo, tabla ciclos_admin).
%%   - Ciclo_cursos = cursos.Ciclo (bloque de un plan de estudios, tabla ciclos).
%%   - User         = django.contrib.auth.models.User.
%%   - "herencia" = herencia multi-tabla de Django (django-polymorphic en Funcionario y PlantillaCurso).
%%   - Solo se muestran algunos atributos. Los nombres con ñ se escriben sin ella
%%     (anio = campo "año"; contrasena = campo "contraseña").
erDiagram
    %% ---------- Núcleo: personas, tiempo, espacio y organización (app administrativos)
    Funcionario ||--o| Profesor : "herencia"
    Funcionario ||--o| Administrativo : "herencia"
    Funcionario |o--o| User : "usuario espejo (misma clave)"
    Lugar |o--o{ Funcionario : "oficina"
    Funcionario ||--o{ Nombramiento : "funcionario"
    Ciclo_admin ||--o{ Nombramiento : "ciclo"
    Funcionario ||--o{ Jefatura : "funcionario"
    Funcionario }o--o{ Roles : "funcionarios"
    Funcionario |o--o{ Comision : "encargado"
    Funcionario }o--o{ Comision : "miembros"
    Lugar |o--o{ Horario : "lugar"
    Funcionario |o--o{ Horario : "responsable"

    %% ---------- Oferta académica (app cursos)
    PlantillaCurso ||--o| Curso : "herencia"
    Curso ||--o{ Catedra : "curso"
    Ciclo_admin |o--o{ Catedra : "ciclo"
    Profesor |o--o{ Catedra : "coordinador"
    Catedra |o--o{ Grupo : "catedra"
    Curso ||--o{ Grupo : "curso"
    Profesor |o--o{ Grupo : "profesor"
    Grupo }o--o{ Horario : "horario y consulta"
    Grupo }o--o{ Estudiante : "estudiantes"
    PlanDeEstudio }o--o{ Ciclo_cursos : "ciclos (bloques)"
    Ciclo_cursos }o--o{ PlantillaCurso : "cursos"

    %% ---------- Estudiantes
    PlanDeEstudio |o--o{ Estudiante : "plan_estudio"
    Estudiante |o--o{ Asistencia : "estudiante"
    Funcionario ||--o{ Asistencia : "funcionario a cargo"
    Ciclo_admin |o--o{ Asistencia : "ciclo"
    Estudiante ||--o{ PracticaProfesional : "estudiante"

    %% ---------- Trabajos finales (dos apps, dos flujos hermanos)
    Estudiante |o--o{ ProyectoElectrico : "estudiante"
    Profesor ||--o{ ProyectoElectrico : "profesor guia"
    Ciclo_admin |o--o{ ProyectoElectrico : "ciclo"
    Estudiante }o--o{ TFG : "estudiantes"
    ComiteAsesor |o--o{ TFG : "comite_asesor"
    Profesor |o--o{ ComiteAsesor : "directora, asesor 1, asesor 2"
    Ciclo_admin |o--o{ TFG : "ciclo"

    %% ---------- Investigación y firma digital
    Profesor |o--o{ Laboratorio : "coordinador"
    Lugar |o--o{ Laboratorio : "lugar"
    User |o--o{ PDF : "subido_por, revisado_por"

    Funcionario {
        string nombre
        string apellidos
        string email
        text contrasena "hash PBKDF2"
        string url "perfil publico"
        bool oculto
    }
    Profesor {
        int departamento
        int categoria
        int continuidad
        decimal horas_carga
    }
    Administrativo {
        string puesto
    }
    User {
        string username "igual al email"
        string password "copia del hash"
    }
    Ciclo_admin {
        string ciclo "I, II, III"
        int anio
        bool actual "sin restriccion de unicidad"
        date inicio
        date final
    }
    Nombramiento {
        string nombre
        decimal horas_carga
        int tipo
    }
    Jefatura {
        int puesto "choices JEFATURAS"
        decimal horas_carga
    }
    Roles {
        string nombre "texto libre, sin unique"
        decimal carga
    }
    Comision {
        string nombre "texto libre, sin unique"
        string url
    }
    Lugar {
        int numero
        string edificio
        int capacidad
        bool revisar_colisiones
    }
    Horario {
        string dia
        time inicio
        time final
        date fecha_inicio
        date fecha_final
    }
    PlantillaCurso {
        string sigla
        string nombre
        int creditos
    }
    Curso {
        text descripcion
    }
    Grupo {
        int cupo
        bool choque_horario
    }
    PlanDeEstudio {
        string nombre
        int nivel
        int numero_ciclos
    }
    Ciclo_cursos {
        string nombre
        int ciclo "numero de bloque"
        int creditos
    }
    Estudiante {
        string carnet
        string cedula
        string email
        text contrasena "hash PBKDF2"
        string cuenta_iban
        bool activo
    }
    Asistencia {
        string tipo "5 subclases polimorficas"
    }
    PracticaProfesional {
        int estado
        string numero_oficio
        file carta_inicio "PDF generado con LaTeX"
    }
    ProyectoElectrico {
        int estado
        text descripcion_larga
    }
    TFG {
        string titulo
        string modalidad
        int estado "13 estados"
        file propuesta_pdf
    }
    Laboratorio {
        string url
        text descripcion_larga
    }
    PDF {
        string estado
        int revision
        binary data "PDF dentro de la base"
    }
```

### 4.3 Lectura analítica del diagrama

1. **Tres entidades sostienen el sistema: `Funcionario`/`Profesor`, `Ciclo` y `Estudiante`.** Casi toda relación entre apps termina en una de ellas (40 de 81: `Profesor` 14, `Funcionario` 10, `Estudiante` 9, `Ciclo` 7). El dominio tiene forma de estrella con un núcleo claro; lo que está enredado es el código que lo rodea (§2.4), no el modelo de datos.
2. **El núcleo está partido entre dos apps.** `Funcionario`, `Ciclo`, `Lugar` y `Horario` están en `administrativos`, pero `Profesor`, su subclase más usada, está en `profesores`. Por eso `cursos`, `laboratorios`, `proyectos` y los dos subsistemas de trabajos finales dependen de las dos apps a la vez.
3. **Unas relaciones apuntan a `Funcionario` y otras a `Profesor` para el mismo concepto.** `Comision.encargado` es `Funcionario` (`administrativos/models.py:1020`), pero el código lo compara con un `Profesor` (`profesores/misc.py:301`, `:483`); `DelegacionDirector.director` es `Funcionario` y `subdirector` es `Profesor` (`profesores/models.py:229`, `:235`); `Asistencia.funcionario` es `Funcionario` (`estudiantes/models.py:360`), mientras `Grupo.profesor` es `Profesor` (`cursos/models.py:564`). Funciona porque la herencia multi-tabla comparte la llave primaria, pero obliga a recordar en cada consulta si hay que usar `profesor` o `profesor.funcionario_ptr`.
4. **`Grupo` es el punto más conectado de la oferta académica:** une `Curso`, `Catedra`, `Profesor`, `Estudiante` y dos conjuntos de `Horario` (`cursos/models.py:562-594`). `inventario.PrestamoEstudiante`, `atributos.EvalRubrica` y `estudiantes.AsistenciaCurso` cuelgan de él. Es la entidad donde un cambio de esquema toca más subdominios.
5. **El tiempo se modela con una lista enlazada:** `Ciclo.ciclo_anterior` y `ciclo_siguiente` (`administrativos/models.py:216-221`), más la bandera `actual`. No hay restricción que impida dos ciclos actuales ni una cadena rota; `ObtenerUltimosCiclos` (`:258-272`) recorre la cadena confiando en que esté bien formada.
6. **Proyecto Eléctrico y TFG modelan lo mismo de dos formas.** `ProyectoElectrico.estudiante` es una sola llave foránea (`trabajos_finales/models.py:282`) y sus lectores son `lector_1`/`lector_2` (`:287-291`); `TFG.estudiantes` es muchos-a-muchos (`trabajo_final_de_graduacion/models.py:126`) y su comité es una entidad aparte con tres llaves fijas (`:118-120`). Ninguna comparte modelo base con la otra.
7. **`firma_digital` es una isla ligada a `auth.User`:** sus 5 relaciones de autoría van a `User` (`firma_digital/models.py:138,234,242,304,344`), no a `Funcionario`. El puente es `Funcionario.usuario` (`administrativos/models.py:416`), que puede ser nulo.

### 4.4 Relaciones importantes entre apps

| Destino | Relaciones entrantes | Desde | Evidencia (ejemplos) |
|---|---|---|---|
| `profesores.Profesor` | 14 | `trabajo_final_de_graduacion` (5), `proyectos` (3), `cursos` (2), `laboratorios` (2), `trabajos_finales` (2) | `cursos/models.py:497,564`; `trabajo_final_de_graduacion/models.py:94,118-120,264` |
| `administrativos.Funcionario` | 10 | `anuncios`, `conferencias`, `estudiantes`, `eventos`, `firma_digital`, `inventario`, `profesores` (3) | `estudiantes/models.py:360`; `inventario/models.py:522` |
| `estudiantes.Estudiante` | 9 | `atributos`, `conferencias`, `cursos`, `inventario`, `solicitud_documentos_externo`, `trabajo_final_de_graduacion` (2), `trabajos_finales` (2) | `cursos/models.py:580`; `solicitud_documentos_externo/models.py:26` |
| `auth.User` | 8 | `firma_digital` (5), `postulaciones` (2), `administrativos` (1) | `postulaciones/models.py:93,98` |
| `administrativos.Ciclo` | 7 | `estudiantes` (2), `laboratorios`, `proyectos`, `trabajo_final_de_graduacion`, `trabajos_finales` (2) | `trabajos_finales/models.py:246,313` |
| `administrativos.Lugar` | 5 | `conferencias`, `cursos`, `eventos`, `inventario`, `laboratorios` | `inventario/models.py:123` |
| `cursos.Grupo`, `cursos.PlantillaCurso` | 3 y 3 | `atributos`, `estudiantes`, `inventario` | `estudiantes/models.py:455,725,949,957` |
| `administrativos.Nombramiento` | 3 | `laboratorios`, `proyectos` (2) | `proyectos/models.py:99,102` |

Las 7 relaciones a `Ciclo` que el script marca como ambiguas (`administrativos|cursos.Ciclo`) se resolvieron por los `import` de cada archivo: todas apuntan a `administrativos.Ciclo` (`estudiantes/models.py:15`, `laboratorios/models.py:5`, `proyectos/models.py:3`, `trabajo_final_de_graduacion/models.py:7`, `trabajos_finales/models.py:9`).

**Relaciones que cierran ciclos a nivel de modelo** (las más costosas de romper):

- `administrativos.ConfirmarCambioEnfasis.cambio_enfasis` → `estudiantes.CambioEnfasis` (`administrativos/models.py:968`), contra 6 relaciones de `estudiantes` hacia `administrativos`.
- `administrativos.LugarCiclo.laboratorio` → `laboratorios.Laboratorio` (`:1109`), contra `Laboratorio.lugar` → `Lugar`.
- `cursos.Grupo.estudiantes` → `Estudiante` (`cursos/models.py:580`), contra `Estudiante.plan_estudio` → `PlanDeEstudio` (`estudiantes/models.py:144`).
- `cursos.Catedra.actividad_atributos` → `atributos.ActividadAtributos` (`cursos/models.py:502`), contra `atributos.EvalRubrica.grupo` → `Grupo`.
- `laboratorios.Laboratorio.proyectos` → `Proyecto` (`laboratorios/models.py:68`), contra `proyectos.Publicacion.laboratorios` → `Laboratorio` (`proyectos/models.py:155`).

**Política de borrado.** De 141 `ForeignKey`/`OneToOneField`: 80 `DO_NOTHING`, 36 `CASCADE`, 17 `SET_NULL` y 8 con el argumento posicional (por ejemplo `anuncios/models.py:132`). Por generación: `administrativos` 25 de 29 en `DO_NOTHING`, `estudiantes` 17 de 19, `trabajos_finales` 10 de 10, `cursos` 7 de 7, `inventario` 8 de 8; en cambio `firma_digital` usa `SET_NULL` (7) y `CASCADE` (4), y `trabajo_final_de_graduacion` `SET_NULL` (5), `CASCADE` (5) y un `DO_NOTHING`. `DO_NOTHING` deja la decisión al motor: con InnoDB el borrado falla con error de integridad; el sistema no define qué pasa con los grupos de un profesor que se va.

### 4.5 Jerarquías y herencia

| Base | Tipo | Subclases | Evidencia |
|---|---|---|---|
| `Funcionario` | Polimórfica, multi-tabla, **cruza apps** | `Profesor` (`profesores`), `Administrativo` | `administrativos/models.py:345,556`; `profesores/models.py:48` |
| `PlantillaCurso` | Polimórfica | `Curso` | `cursos/models.py:125,191`. La base tiene un `ManyToManyField` hacia su propia subclase (`:145`) |
| `Asistencia` | Polimórfica | `AsistenciaCurso`, `AsistenciaLaboratorio`, `AsistenciaComision`, `AsistenciaProyecto`, `AsistenciaAdministrativa` | `estudiantes/models.py:350,454,493,533,573,613` |
| `RequisitosGraduacion` | **Abstracta** y polimórfica | `RequisitosBachillerato`, `RequisitosLicenciatura` | `estudiantes/models.py:1184,1221,1233` |
| `Bien` | Polimórfica, dos niveles | `Activo` → `Computadora`; `Componente` | `inventario/models.py:109,192,265,345` |
| `Prestamo` | Polimórfica | `PrestamoEstudiante`, `PrestamoFuncionario` | `inventario/models.py:439,474,514` |

Observaciones:

- **Las jerarquías se usan para datos, no para comportamiento compartido.** Solo hay un modelo abstracto en todo el sistema, y por eso el comportamiento común se copia: 30 métodos `Search` en los `models.py`, la mayoría estructuralmente iguales, `SetPassword` en `Funcionario`, `Estudiante` y `Alumnus`, `EnviarEmail` en los mismos tres, y `SetHashURL`/`SetExpiracion` en los tres modelos de recuperación de contraseña (`scripts/duplicacion-eieinfo-0b3c575c.txt`).
- **`Funcionario` decide por nombre de clase** (`self.__class__.__name__ == 'Profesor'`, `administrativos/models.py:536-541`) en vez de por polimorfismo, lo que anula la ventaja de la jerarquía.
- **La herencia que cruza apps (`Funcionario` → `Profesor`) fija el orden de importación:** `profesores.models` importa `administrativos.models` (`profesores/models.py:5-6`), así que el núcleo no puede nombrar a `Profesor` en sus modelos; lo hace por nombre de clase (punto anterior) o desde su capa de vistas (`administrativos/views/delegacion_director.py:10,31`).
- Todas dependen de `django-polymorphic 3.1.0` (E1 §1.2).

### 4.6 Conceptos compartidos entre módulos

| Concepto | Dónde se define | Quién lo usa | Problema |
|---|---|---|---|
| Ciclo lectivo actual | `Ciclo.ObtenerCicloActual` (`administrativos/models.py:252`) | 28 archivos, 94 llamadas | Sin restricción ni manejo de ausencia |
| Profesor activo | `Profesor.estaActivo` (`profesores/models.py:127`), `Profesor.ObtenerActivos` (`:133`), `webpage.misc.stats_institucionales` (`webpage/misc.py:93-100`) | Login, directorio, portada | Tres implementaciones de la misma regla |
| Director o firmante | `Profesor.Director`, `Profesor.DirectorReal`, `_PUESTOS_FIRMA`, `firma_digital.views.es_director`, `administrativos.misc.ObtenerDirector` (`:59-66`), `profesores/cron.py:6` (`_obtener_director`) | Autorización, firma, correos | Cinco puntos; el subdirector cuenta o no según cuál se use |
| Función o rol de una persona | `Roles.funcionarios`, `Encargado`, `Comision.encargado`/`miembros`, `Jefatura.puesto` | Los decoradores de `profesores/misc.py` y `administrativos/misc.py` | Cuatro mecanismos; identificación por texto |
| Estado de un trámite | Enteros con `choices` por modelo (`ESTADOS_TFG`, `ESTADO_PROYECTO_ELECT`, `ESTADOS_PRACTICA_PROFESIONAL`), `TextChoices` en `firma_digital` | Vistas y formularios | Sin tabla de transiciones; se comparan por etiqueta (`get_estado_display() == 'Solicitud necesita cambios'`, `estudiantes/forms.py:551-552`) |
| Envío de correo | `eieinfo/email_service.py`, 5 funciones en `eieinfo/misc.py:41-136`, métodos `EnviarEmail` en 3 modelos, `firma_digital.misc.enviar_correo`, `trabajo_final_de_graduacion.views.enviar_correo_tfg` (`:80`) | Todo el sistema | Migración a medio hacer hacia `email_service` |
| Archivo temporal de precarga | `ArchivoTemporalTFG`, `ArchivoTemporalSolicitud` | TFG y solicitud de documentos | Dos modelos y dos `precarga.py` casi idénticos (98 %) |

### 4.7 Duplicaciones y ambigüedades conceptuales

**a) Dos `Ciclo`.**

| | `administrativos.Ciclo` | `cursos.Ciclo` |
|---|---|---|
| Significado | Ciclo lectivo (I, II o III de un año) | Bloque de un plan de estudios |
| Tabla | `ciclos_admin` | `ciclos` |
| Nombre visible | "Ciclos" | "Bloque" / "Bloques" (`cursos/models.py:871-872`) |
| Evidencia | `administrativos/models.py:205-272` | `cursos/models.py:854-887` |

El nombre de tabla está invertido respecto a la intuición (el bloque se quedó con `ciclos`). Dentro de `cursos/models.py` el identificador `Ciclo` **cambia de significado según la línea**: se importa de `administrativos` en la línea 3, se vuelve a importar como `AdminCiclo` en la 12, `Catedra.ciclo` (`:500`) usa el importado, y desde la línea 854 `Ciclo` pasa a ser la clase local; `PlanDeEstudio.ciclos` (`:832`) usa la cadena `'Ciclo'`, que Django resuelve a la local. `cursos/forms.py:6` la importa como `Ciclo as Bloque`. El equipo ya la llama "Bloque", pero la clase y la tabla no se renombraron.

**b) Dos flujos de trabajo final** (`ProyectoElectrico` en `trabajos_finales`, `TFG` en `trabajo_final_de_graduacion`), más el TFG antiguo comentado en el mismo archivo que Proyecto Eléctrico (§3.5). Conceptos repetidos: concurso (`ConcursoProyectoElectrico`, `ConcursoTFG`), evaluador externo (`Lector`, `AsesorExterno`), presentación (`CitaPresentacion`, `Defensa`).

**c) Comisiones y roles casi homónimos.** En `docker/db/init.sql` existen las comisiones "Trabajo Final de Graduación" y "Trabajos Finales de Graduación", y el rol "Trabajo Final de Graduación". El código vivo pide siempre la comisión en plural (`profesores/misc.py:429`, `trabajo_final_de_graduacion/views.py:566,780,1197`, `precarga.py:79`) y también el rol en plural (`profesores/misc.py:120`); las búsquedas en singular que quedan están en código comentado (`trabajos_finales/misc.py:44`, `models.py:933,968`). Con esos datos semilla, `Roles.objects.get(nombre="Trabajos Finales de Graduación")` no encuentra nada y el `except:` de `profesores/misc.py:126` lo oculta. Datos de producción: no determinable.

**d) Un modelo de usuario por portal.**

| Portal | Entidad | Dónde está la contraseña | Marca de sesión | ¿`auth.User`? |
|---|---|---|---|---|
| Profesores | `Profesor` (`Funcionario`) | `Funcionario.contraseña` y copia en `User.password` | `prof_id` + `django_login` (`profesores/forms.py:82-84`) | Sí, espejo |
| Administrativos | `Administrativo` (`Funcionario`) | Igual | `admn_id` + `django_login` (`administrativos/forms.py:67-69`) | Sí, espejo |
| Bodega | `Funcionario` con rol "Bodega" | `Funcionario.contraseña` | `funcionario_bodega` (`inventario/forms.py`, método `save` de `LoginBodegaForm`) | No |
| Estudiantes | `Estudiante` | `Estudiante.contraseña` | `est_id` (`estudiantes/forms.py:124`) | No |
| Alumni | `Alumnus` | `Alumnus.password` | `alumnus_id` (`alumni/forms.py:116`) | No |
| Conferencias, wiki, `/admin/` | `auth.User` | `User.password` | Sesión de Django | Sí |
| Postulación docente | `Postulante` | No tiene: código `EIE-<año>-<8 hex>` | Ninguna | No |

Son cuatro almacenes de contraseña (más el código de postulación) y seis marcas de sesión. Una misma persona puede existir como `Estudiante`, luego como `Alumnus` y luego como `Profesor` sin ningún vínculo entre los tres registros (`Alumnus.carnet` es único pero no es llave foránea a `Estudiante`, `alumni/models.py:63`).

**e) "Persona" modelada muchas veces:** además de las anteriores, `webpage.PersonaColaboradora` (`webpage/models.py:179`), `trabajo_final_de_graduacion.AsesorExterno` (`:103`), `trabajos_finales.Lector` (`:175`) y `postulaciones.Postulante`. Cada una repite nombre, apellidos, correo y teléfono con nombres de campo distintos (`nombre`/`apellidos`, `nombre1`/`apellido1`, `nombre`/`apellido`).

**f) Modelos "por ciclo" paralelos:** `ComisionCiclo`, `JefaturaCiclo`, `LugarCiclo` (`administrativos`), `LaboratorioCiclo`, `ProyectoCiclo`. El propio código dice que se conservan "como legacy" (`administrativos/models.py:1044-1046`). Fuera de `models.py`, `ComisionCiclo` y `LaboratorioCiclo` solo aparecen en `duplicar_ciclo.py`; `JefaturaCiclo` y `ProyectoCiclo` también en `profesores/views/consejo_asesor.py`. Conviven dos respuestas a "quién coordina la comisión": `Comision.encargado` (vigente) y `ComisionCiclo.encargado` (histórica).

**g) Tres modelos de recuperación de contraseña** con la misma estructura: `CambioContraseñaFuncionario` (`administrativos/models.py:1129`), `RecuperacionContraseña` (`estudiantes/models.py:295`) y `RecuperarPasswordAlumnus` (`alumni/models.py:242`).

**h) Idioma e identificadores.** `contraseña` (funcionarios y estudiantes) frente a `password` (alumni); tablas en español frente a nombres por defecto en inglés-español (`firma_digital_pdf`); cuatro tablas con sufijo `_v6`.

---

## 5. Calidad del código (enunciado 7.4)

Scripts: `complexity.py`, `duplication.py`, `views_audit.py` (salidas en `scripts/complejidad-eieinfo-0b3c575c.json`, `scripts/duplicacion-eieinfo-0b3c575c.txt` y `scripts/vistas-eieinfo-0b3c575c.txt`).

```bash
python3 -I docs/anexos/scripts/duplication.py ~/repos/EIEInfo 8      # funciones de 8 líneas o más
python3 -I docs/anexos/scripts/views_audit.py ~/repos/EIEInfo
```

### 5.1 Archivos y funciones de alta complejidad o tamaño

**Distribución.** 1408 funciones de producción; CC media 2,97; 48 con CC > 10 (3,4 %), 11 con CC > 20, ninguna > 50; 18 funciones de más de 100 líneas.

**Por app** (`complexity.py`, ordenado por CC acumulada):

| App | Funciones | CC media | CC máx. | CC > 10 | CC > 20 | > 100 líneas |
|---|---|---|---|---|---|---|
| `profesores` | 267 | 3,13 | 33 | **14** | 3 | 4 |
| `administrativos` | 266 | 2,39 | 25 | 3 | 1 | 1 |
| `firma_digital` | 140 | 4,22 | 28 | **11** | 2 | 4 |
| `trabajo_final_de_graduacion` | 72 | 4,60 | 29 | 5 | 2 | 2 |
| `estudiantes` | 156 | 2,01 | 9 | 0 | 0 | 0 |
| `cursos` | 69 | 2,91 | 18 | 4 | 0 | 1 |
| `postulaciones` | 24 | **7,17** | 21 | 4 | 1 | 1 |
| `atributos` | 46 | 2,87 | 21 | 2 | 1 | 2 |
| `eieinfo` | 14 | 4,57 | **39** | 1 | 1 | 1 |

Lectura: 30 de las 48 funciones con CC > 10 están en tres apps (`profesores`, `firma_digital`, `trabajo_final_de_graduacion`). Las dos apps más recientes de las tres tienen CC media más alta que el código de 2016–2018: el código nuevo está mejor probado, pero no es más simple.

**Las 15 funciones más complejas**

| # | CC | Líneas | Función | Ubicación | Qué concentra |
|---|---|---|---|---|---|
| 1 | 39 | 114 | `enviar_email` | `eieinfo/email_service.py:16` | Normalización de 5 listas opcionales (destinatarios, cc, bcc, reply-to, adjuntos) |
| 2 | 33 | 167 | `editar_grupo` | `profesores/views/consejo_asesor.py:98` | Varios formularios en una vista, cupo, choques de aula y de profesor, mensajes |
| 3 | 29 | 196 | `enviar_revision_propuesta_tfg` | `trabajo_final_de_graduacion/views.py:432` | Validación, precarga de archivos, cambio de estado y correos |
| 4 | 28 | 199 | `_emparejar_firmado` | `firma_digital/views.py:2371` | Emparejar un PDF firmado con su original por nombre, contenido y revisión |
| 5 | 25 | 158 | `resumen_ciclo` | `administrativos/views/consejo_asesor.py:129` | Cálculo de jornadas y presupuestos del ciclo |
| 6 | 25 | 158 | `resumen_ciclo` | `profesores/views/consejo_asesor.py:289` | Copia de la anterior (difiere en una línea) |
| 7 | 23 | 116 | `CrearContextoProfesor` | `profesores/misc.py:25` | Contexto de las 136 vistas de profesor |
| 8 | 21 | 129 | `exportar_a_excel` | `atributos/views.py:581` | Generación de XLSX celda por celda |
| 9 | 21 | 131 | `SolicitudesView.get_context_data` | `firma_digital/views.py:519` | Filtros, paginación y conteos por lote |
| 10 | 21 | 133 | `editar_postulacion` | `postulaciones/views.py:441` | Cinco *formsets* y serialización en sesión |
| 11 | 21 | 133 | `parecer_comision_unificado` | `trabajo_final_de_graduacion/views.py:935` | Parecer de comisión: aprobar, rechazar o pedir correcciones |
| 12 | 20 | 101 | `GuardarPDFFirmadoAPIView.post` | `firma_digital/views.py:1276` | Recepción del firmado desde Firmador Libre |
| 13 | 19 | 84 | `crear_horario_grupo` | `profesores/views/consejo_asesor.py:488` | Alta de horario con verificación de choques |
| 14 | 18 | 27 | `EditarCartaGrupoForm.__init__` | `cursos/forms.py:491` | Habilitar o bloquear campos según el estado |
| 15 | 18 | 95 | `CargarPDFView.post` | `firma_digital/views.py:675` | Carga individual con validaciones |

Con CC 18 también están `ActualizarSolicitudView.post` (`firma_digital/views.py:2797`), `info_grupo` (`profesores/views/consejo_asesor.py:1000`) y `concursos_proyecto_electrico` (`profesores/views/trabajos_finales.py:99`).

**Matiz sobre la número 1.** `enviar_email` encabeza la lista por la forma de contar (cada `if` dentro de una comprensión suma), pero es código lineal, sin anidamiento y con un solo efecto. Las que de verdad concentran riesgo son las de la 2 a la 7: mezclan decisión de negocio, acceso a datos y respuesta HTTP. **12 de las 15 están en módulos de vistas** (10 son vistas o métodos de vista y 2 son funciones auxiliares que reciben `request`).

**Archivos por CC acumulada**

| CC acumulada | LOC | Funciones | CC > 10 | Archivo |
|---|---|---|---|---|
| 492 | 2918 | 90 | 11 | `firma_digital/views.py` |
| 317 | 2117 | 69 | 7 | `profesores/views/consejo_asesor.py` |
| 196 | 1352 | 30 | 5 | `trabajo_final_de_graduacion/views.py` |
| 135 | 629 | 16 | 4 | `postulaciones/views.py` |
| 99 | 852 | 33 | 1 | `profesores/forms.py` |
| 97 | 1347 | 72 | 0 | `estudiantes/models.py` |
| 95 | 813 | 26 | 1 | `cursos/forms.py` |
| 89 | 759 | 21 | 2 | `atributos/views.py` |
| 87 | 1217 | 51 | 0 | `administrativos/models.py` |
| 83 | 542 | 23 | 1 | `profesores/misc.py` |

Los tres primeros son también tres de los cinco archivos de producción más modificados en 12 meses (41, 14 y 12 commits; §1.1): complejidad alta y cambio frecuente coinciden.

**Plantillas.** 38 793 líneas de HTML; las mayores: `firma_digital/templates/firma_digital/solicitudes_prof.html` (732), `webpage/templates/webpage/index.html` (576), `profesores/templates/profesores/consejo_asesor/horario_plan.html` (542). Hay 167 bloques `<script>` en línea en 117 plantillas.

### 5.2 Mezcla de responsabilidades

- **Vistas que hacen todo.** El patrón dominante es una función que comprueba permisos, arma contexto, valida, aplica reglas, cambia estado, envía correo y responde. Ejemplo: `editar_grupo` (`profesores/views/consejo_asesor.py:98-264`) decide entre formularios por la presencia de una clave en `request.POST` (`:106`, `:145`) y contiene la regla de cupo contra capacidad del aula (`:153-164`), que está copiada en `editar_horario_grupo` (`:1535-1540`).
- **Modelos que notifican, generan documentos y publican.** Llamadas de envío de correo dentro de `models.py`: `estudiantes` 20, `trabajos_finales` 9, `alumni` 8, `administrativos` 6. `anuncios/models.py:233` y `eventos/models.py:239` publican en Facebook (`PostearEnFacebook`, 96 % iguales). `cursos/models.py:306` (`Curso.ProgramaPDF`, 152 líneas) y `estudiantes/models.py:1001` generan PDF con LaTeX. `proyectos/models.py:190-196` consulta Google Scholar.
- **Formularios que abren sesión y cambian estado.** El inicio de sesión de cada portal está en el `save()` de un formulario, que escribe en `request.session` (`profesores/forms.py:67-92`, `administrativos/forms.py:53-78`, `estudiantes/forms.py:102-126`, `alumni/forms.py:94-118`, `inventario/forms.py:372-397` y `:430-455`). `trabajos_finales/forms.py` asigna `estado` 6 veces y envía 4 correos; `estudiantes/forms.py:544-563` decide la transición de la práctica profesional.
- **Módulos `misc.py` como cajón:** `profesores/misc.py` mezcla contexto de plantilla y 11 decoradores de autorización; `eieinfo/misc.py` mezcla correo, LaTeX, estilos de XLSX y utilidades de URL (`:32-230`); `administrativos/misc.py` mezcla contexto, decoradores, validación de contraseñas y el algoritmo de choques de horario (`:246-269`).
- **Plantillas con reglas:** 95 condiciones sobre `estado` en 32 plantillas, muchas comparando contra la etiqueta visible (`{% if practica_profesional.get_estado_display == 'En curso' %}`, `{% if solicitud.estado == 'Completado' %}`). Cambiar el texto de un estado cambia el comportamiento de la interfaz.

### 5.3 Duplicación

`duplication.py` sobre 788 funciones de producción de 8 líneas o más:

| Nivel | Grupos | Funciones | Líneas redundantes |
|---|---|---|---|
| Clones exactos (mismo AST) | 12 | 24 | 138 |
| Clones estructurales (mismo AST al anonimizar nombres y constantes) | 65 | 160 | 1661 |
| Homónimas con ≥ 80 % de texto igual en archivos distintos | 86 pares | — | — |

**Una de cada cinco funciones de 8 líneas o más (160 de 788) tiene al menos un clon estructural.** Los grupos principales:

| Qué se duplica | Copias | Evidencia |
|---|---|---|
| Vistas del Consejo Asesor entre `profesores` y `administrativos` | 10 funciones homónimas; `resumen_ciclo` 158 líneas, `consolidacion_aulas` 65, `nombramientos_interinos` 42, `nombramientos_continuidad` 35 | `profesores/views/consejo_asesor.py:289,1443,1077,1122` frente a `administrativos/views/consejo_asesor.py:129,373,46,91` |
| Gestión de delegación de director | 4 vistas | `profesores/views/home.py:309-437` frente a `administrativos/views/delegacion_director.py:15-150` |
| **Decoradores de autorización** | 20 decoradores con la misma estructura en 6 archivos; 3 son clones estructurales del "solo sesión" (`profesor_login_required`, `admin_login_required`, `alumni_login_required`) y otros 2 pares son idénticos salvo una cadena | `profesores/misc.py:261`, `administrativos/misc.py:69`, `alumni/misc.py:24`; `administrativos/misc.py:162` y `:201`; `profesores/misc.py:212` y `:237`; `profesores/misc.py:415` y `:510` |
| Inicio de sesión por portal | 5 `save()` de formulario y 2 vistas `login` | `profesores/forms.py:67`, `administrativos/forms.py:53`, `estudiantes/forms.py:102`, `alumni/forms.py:94`, `inventario/forms.py:372,430`; `profesores/views/publico.py:85` y `administrativos/views/publico.py:69` (95 %) |
| Recuperación y cambio de contraseña | 3 modelos y 3 juegos de vistas | `administrativos/models.py:1129`, `estudiantes/models.py:295`, `alumni/models.py:242` |
| Métodos `Search` en modelos | 30 definiciones; grupos de 6, 5 y 5 clones | `estudiantes/models.py:220,477,517,549,589,632`; `anuncios/models.py:270`, `eventos/models.py:94`, `cursos/models.py:168,476` |
| Listados de inventario | 4 vistas idénticas salvo el modelo | `administrativos/views/gestion_inventario.py:31,53,75,97` |
| Precarga de archivos | 3 funciones | `solicitud_documentos_externo/precarga.py:43,102,120` frente a `trabajo_final_de_graduacion/precarga.py:40,91,106` |
| Validadores de PDF en formularios | 4 | `trabajo_final_de_graduacion/forms.py:246,259,495,654` |
| Publicación en Facebook | 2 | `anuncios/models.py:233`, `eventos/models.py:239` |
| Vistas `recursos` y `sugerencias` de los tres portales | 3 y 3 | `estudiantes/views/home.py:55,141`, `profesores/views/home.py:223,240`, `administrativos/views/home.py:100,118` |

**Consecuencia medible de la duplicación:** el mismo defecto se copió. El patrón `rol = Roles.objects.filter(nombre=…)` seguido de `rol.funcionarios` (un `QuerySet` no tiene ese atributo) entró en el commit `8609b97b` (2020-10-06) y sigue vivo en 5 lugares: `estudiantes/models.py:1017-1018`, `inventario/forms.py:353-354` y `:411-412`, `inventario/misc.py:34-35` y `trabajos_finales/misc.py:20-21`. Este último es el decorador `pe_login_required`, que protege 4 vistas del coordinador de Proyecto Eléctrico (`profesores/views/trabajos_finales.py:282,308,373,405`) y que además tiene un `redirect` sin `return` (`trabajos_finales/misc.py:25`). En mayo de 2026 se corrigió **una** aparición del mismo patrón (`trabajos_finales/models.py:468,503`, commit `ef215199`, "…PE prorroga AttributeError") y las demás quedaron. Por lectura estática esas rutas fallan; no se ejecutaron para confirmarlo.

### 5.4 Convenciones inconsistentes

| Aspecto | Observado | Evidencia |
|---|---|---|
| Estilo de nombres de función | 320 en `CamelCase` y 958 en `snake_case` en producción (sin métodos especiales) | AST; `README.md:26-29` exige `CamelCase`; el código de 2025–2026 usa `snake_case` |
| Idioma | Prefijos en inglés (`get_`, `update_`) 208 y en español (`obtener_`, `crear_`) 80; identificadores con `ñ` junto a `password` | E1 §8.2 |
| Tipo de vista | Funciones, CBV envueltas a nivel de módulo (63), CBV con *mixin* (24) | `scripts/vistas-eieinfo-0b3c575c.txt` |
| Rutas | `re_path` con expresiones regulares en casi todo; 5 rutas sin ancla `^` | `postulaciones/urls.py:8,9,15`, `profesores/urlpatterns/consejo_asesor.py:127`, `webpage/urls.py:36` |
| Estados | Enteros con tupla y diccionario inverso (`ESTADO_PE_REV`), constantes enteras (`ESTADO_INTERES`), `TextChoices` | `trabajos_finales/models.py:23-38`, `trabajo_final_de_graduacion/models.py:9-36`, `firma_digital/models.py:116` |
| Acceso a configuración | `django.conf.settings` y, en 6 archivos, `from eieinfo.settings import …` | `eieinfo/misc.py:4`, `webpage/views.py:16`, `eieinfo/GoogleAPI.py`, `eieinfo/FacebookAPI.py` |
| *Logger* | `getLogger('eieinfo')` en 28 archivos, `getLogger('debug')` en 5, `getLogger(__name__)` en 4 | `git grep -hoE "getLogger\([^)]*\)"` |
| Manejo de errores | 51 `except:` sin tipo y 38 `except Exception` | `git grep -cE "^\s*except\s*:"` |
| Comprobación de método HTTP | `require_POST` o similar en 7 archivos; 15 vistas que borran sin comprobarlo | §3.1 |
| Estilo automático | `.flake8` excluye `settings.py` y `scripts`; flake8 3.5.0 (2017) no corre en el CI; el commit que comentó el TFG antiguo dice "sin verificación flake8" | `.flake8:9,11`; `.drone.yml`; `git log -1 f5a94cab` |
| Docstrings | 44 % de las funciones; de 27 % (`trabajos_finales`) a 71 % (`webpage`) | AST |

### 5.5 Código histórico o legado

| Elemento | Tamaño | Estado | Evidencia |
|---|---|---|---|
| Código comentado con `##` | **2025 líneas** en producción, 1999 en el área de trabajos finales | TFG antiguo desactivado sin borrar | `git grep -hE "^\s*##" -- '*.py' \| wc -l`; commit `f5a94cab` (2025-02-15) |
| Apps no instaladas | `asistencias` (830 líneas de pruebas), `proyecto_electrico`, `practica_profesional` | Solo README y pruebas que el CI no ejecuta | E1 §3.3 |
| Vistas sin ruta | `listado_postulantes3` (`postulaciones/views.py:179`), `info_horario` y `gestionar_solicitudes_asistentes_12312` (`profesores/views/consejo_asesor.py:1070,1744`), `crear_lector` (`profesores/views/trabajos_finales.py:872,972`), `eliminar_tfg` (`trabajo_final_de_graduacion/views.py:1282`, con su plantilla `confirmar_eliminar_tfg.html`) | Muertas | `views_audit.py` + `git grep -nw` de cada nombre |
| Métodos rotos sin uso o con uso marginal | `Profesor.ActualizarGruposUsuario` (`profesores/models.py:160`, solo desde `scripts/owncloud.py:36`), `TFG.NotificarEstudiante` (`trabajo_final_de_graduacion/models.py:154`), `Comision.ComisionCicloActual` (`administrativos/models.py:1048`) | Rotos | §2.1 |
| Modelos "legacy" declarados | `ComisionCiclo`, `JefaturaCiclo`, `LugarCiclo`, `LaboratorioCiclo`, `ProyectoCiclo`, `Encargado` | Tablas vivas, uso residual | `administrativos/models.py:1044-1046`; §4.7 |
| `src/server/scripts/` | 6 scripts y un CSV (último commit 2019) | Ignorado por `.gitignore:5` pero versionado; usa APIs del modelo que ya no existen | E1 §2.4; `scripts/owncloud.py:36` |
| Archivos sueltos | `src/server/eieinfo_uwsgi.ini` (el despliegue usa gunicorn; ninguna otra referencia a uwsgi), `src/server/owncloud_config.sh`, `setup.sh`, `cleangit.sh`, `src/webclients/` | Sin uso en build ni CI | `git grep -l uwsgi`; E1 §1.7 |
| Archivo vacío | `profesores/views/inventario.py` (0 líneas) | Resto de una extracción | `wc -l` |
| Settings sin efecto | `TEMPLATES` definido dos veces; `CORS_ALLOWED_ORIGINS` sin `corsheaders`; `MAX_PDF_SIZE`, `FIRMADOR_LIBRE_PORT` sin lecturas | Ruido | E1 §2.2 |
| Librerías vendorizadas | 59 MB en `static/`, con 138 archivos `.svn/` | Sin gestor de paquetes | E1 §1.8 |
| Versión en el nombre de tabla | 4 tablas `_v6` | Sustituto manual de las migraciones | `trabajo_final_de_graduacion/models.py:90,115,163,199` |

### 5.6 Puntos de acoplamiento difícil

1. **`CrearContexto*` + decorador en cada vista** (140 + 68 + 53 + 48 llamadas): no se puede probar una vista sin sesión, base de datos con ciclo actual y los modelos de 5 apps.
2. **`Ciclo.ObtenerCicloActual()`** en 28 archivos: estado global implícito leído desde modelos, formularios, vistas, decoradores y tareas programadas.
3. **Literales de rol y de comisión** en 16 archivos (§2.2): acoplamiento del código a filas concretas de la base.
4. **`from eieinfo.settings import …`** al importar el módulo (`eieinfo/misc.py:4-5`): cualquier app que importe `eieinfo.misc` evalúa `settings.py`, que a su vez importa `secret_credentials` (`settings.py:528`) y crea directorios (E1 §2.2). No se puede importar `eieinfo.misc` sin la configuración completa.
5. **Herencia `Funcionario` → `Profesor` entre apps** (§4.5).
6. **`webpage.misc`** importado por 19 archivos de portales, arrastrando 7 apps (§3.6).
7. **Rutas de archivos fijas en el código:** `/var/info/logs/` (`eieinfo/misc.py:189,192`; `settings.py:258-275`), `/var/info/media` (`settings.py:316`).
8. **Nombres de URL usados como contrato entre apps:** las vistas duplicadas existen para que cada portal tenga su `prof_*` y su `admn_*`; `estudiantes/models.py:1031-1035` construye URL del portal administrativo con `reverse_lazy('admn_practica_…')` desde un modelo.

### 5.7 Lógica de negocio en capas inadecuadas

| Capa | Lógica que contiene | Evidencia | Dónde debería estar |
|---|---|---|---|
| **Vistas** | Reglas de cupo y choque de horario; transiciones de estado del TFG (10 asignaciones); cálculo de jornadas y presupuesto | `profesores/views/consejo_asesor.py:98-264,289-446`; `trabajo_final_de_graduacion/views.py:432-627,935-1067` | Servicios de dominio invocados por la vista |
| **Decoradores** | Quién es consejo asesor, director, comisión o revisor; con consultas y efectos en sesión | `profesores/misc.py:143-543`; `administrativos/misc.py:102-111` | Un módulo de políticas con predicados probados |
| **Formularios** | Inicio de sesión, transiciones de práctica profesional y de Proyecto Eléctrico, envío de correo | `profesores/forms.py:67-92`; `estudiantes/forms.py:544-563`; `trabajos_finales/forms.py` | Los formularios validan; el servicio ejecuta |
| **Modelos** | Correo, PDF, Facebook, Scholar, numeración de oficios, construcción de URL | `estudiantes/models.py:989-1181`; `anuncios/models.py:233`; `proyectos/models.py:190` | Servicios e integraciones separados del modelo |
| **Plantillas** | Decisión de qué acciones mostrar según la etiqueta del estado (95 condiciones); numeración de oficio disparada al renderizar | `git grep -cE "\{% (el)?if [^%]*estado"`; `CartaPracticaProfesional.tex:24` | Propiedades del modelo (`puede_…`) calculadas en Python |
| **Módulos sueltos** | Duplicación de ciclo y generación de nombramientos | `administrativos/duplicar_ciclo.py`, `nombramientos_auto.py` | Es lo más parecido a una capa de servicios; le faltan transacciones y pruebas |

El sistema no tiene una capa de servicios (`git ls-files | grep -E "/(services|selectors)"` → vacío). `firma_digital/misc.py` (`firmar_pdf`) y `eieinfo/email_service.py` son los dos lugares donde ya se aplicó esa idea y sirven de modelo para el resto.

---

## 6. Pruebas y confiabilidad (enunciado 7.5)

**La suite no se ejecutó.** Todo lo que sigue sale de lectura estática: `scripts/tests_audit.py` (AST de los `tests.py`), `.drone.yml` y `docker/django/run-ut.sh`.

```bash
python3 -I docs/anexos/scripts/tests_audit.py ~/repos/EIEInfo     # salida: scripts/pruebas-eieinfo-0b3c575c.txt
```

### 6.1 Estilo de pruebas

| Aspecto | Observado | Evidencia |
|---|---|---|
| Marco | `django.test.TestCase` (155 de 167 clases), `SimpleTestCase` (9), `TransactionTestCase` (3) | `tests_audit.py` |
| Nivel | Predominan las pruebas de **vista vía cliente HTTP**: 798 de 1166 (68 %) usan `self.client` | Ídem |
| Aislamiento de lo externo | 203 pruebas (17 %) usan `mock`/`patch`; 189 de ellas están en `firma_digital` y `solicitud_documentos_externo` | Ídem |
| Datos | 454 pruebas (39 %) cargan un fixture global; el resto crea datos en `setUp` | Ídem |
| Aserciones | 3058 en total, 2,6 por prueba; 2 pruebas sin ninguna | Ídem |
| Unitarias puras (sin base ni cliente) | Minoría: `SimpleTestCase` de `firma_digital` (emparejado de nombres) y de `profesores` (render del horario) | `profesores/tests.py:3229-3544` |
| Funcionales o de navegador | No hay Selenium ni `LiveServerTestCase`; una prueba pide Chrome y se salta si no está (`profesores/tests.py:3492`) | E1 §6 |
| JavaScript | 3 archivos `firma_digital/tests_js/*.test.cjs`; sin `package.json` ni paso en el CI | `ls firma_digital/tests_js`; `git ls-files \| grep package.json` → solo en `static/` |
| Humo | 74 `curl` contra nginx en el CI | `.drone.yml:108-203` |

### 6.2 Qué partes están mejor cubiertas

| App | LOC prod. | Pruebas | Pruebas por 100 LOC | Con fixture | Con `mock` | `skip` | ¿En CI? |
|---|---|---|---|---|---|---|---|
| `firma_digital` | 4024 | 456 | **11,3** | 0 % | 34 % | 0 | Sí |
| `webpage` | 1074 | 91 | 8,5 | 86 % | 0 % | 9 | Sí |
| `solicitud_documentos_externo` | 1148 | 79 | 6,9 | 0 % | 42 % | 0 | Sí |
| `proyectos` | 517 | 25 | 4,8 | 0 % | 0 % | 0 | Sí |
| `trabajo_final_de_graduacion` | 2679 | 74 | 2,8 | 32 % | 9 % | 3 | Sí |
| `profesores` | 7653 | 210 | 2,7 | 89 % | 1 % | 2 | Sí |
| `postulaciones` | 976 | 26 | 2,7 | 100 % | 0 % | 0 | Sí |
| `anuncios` | 676 | 15 | 2,2 | 0 % | 0 % | 0 | Sí |
| `cursos` | 2187 | 40 | 1,8 | 62 % | 0 % | 0 | Sí |
| `administrativos` | 6156 | 84 | 1,4 | 89 % | 2 % | 0 | Sí |
| `conferencias` | 439 | 5 | 1,1 | 0 % | 0 % | 0 | **No** |
| `estudiantes` | 4111 | 36 | **0,9** | 100 % | 0 % | 0 | Sí |
| `eieinfo` | 1130 | 6 | 0,5 | 0 % | 17 % | 0 | **No** |
| `trabajos_finales` | 2795 | 5 | 0,2 | 0 % | 20 % | 0 | **No** |
| `atributos` | 1211 | 3 | 0,2 | 67 % | 0 % | 0 | **No** |
| `inventario` | 1622 | 1 | 0,1 | 0 % | 0 % | 0 | **No** |
| `alumni` | 986 | 1 | 0,1 | 0 % | 100 % | 0 | **No** |
| `eventos`, `laboratorios` | 580, 291 | 0 | 0 | — | — | — | — |

Lectura:

- **Mejor cubiertas:** `firma_digital` y `solicitud_documentos_externo`, con datos propios, simulación del correo y pruebas de concurrencia. Dentro de `profesores`, la planificación de horarios y aulas y la delegación de director (§3.1).
- **La densidad es engañosa en `webpage`:** 8,5 pruebas por 100 líneas, pero son pruebas de "la página responde 200", atadas al volcado y con 9 saltadas.
- **Los tres módulos más acoplados tienen la menor densidad entre los que sí corren:** `estudiantes` 0,9, `administrativos` 1,4, `cursos` 1,8.
- **Sin protección:** `trabajos_finales` (Proyecto Eléctrico), `inventario`, `atributos`, `alumni`, `eventos`, `laboratorios`.

### 6.3 Qué partes parecen frágiles

1. **Autorización.** Los 20 decoradores `*_login_required` no tienen pruebas dirigidas y cuatro tienen defectos de lógica (§2.6). Sí hay muchas pruebas que comprueban redirecciones al login, pero como efecto secundario de probar vistas, no como matriz rol × vista.
2. **Flujos con defectos que ninguna prueba detecta:** las notificaciones de práctica profesional (`estudiantes/models.py:1016-1062`), las 4 vistas del coordinador de Proyecto Eléctrico tras `pe_login_required` (`trabajos_finales/misc.py:9-30`) y el login de bodega (`inventario/forms.py:351-356`) contienen el mismo patrón roto desde 2020 (§5.3). El caso de mayo de 2026 (commit `ef215199`) muestra que estos defectos se descubren en producción.
3. **Procesos por lotes:** `duplicar_ciclo.py` y `nombramientos_auto.py` (513 líneas, sin transacción) tienen 2 menciones en `administrativos/tests.py`.
4. **Código que depende del reloj:** 58 usos de `date.today()`, `datetime.now()` o `timezone.now()` en las pruebas (33 en `profesores`, 17 en `administrativos`) y ninguna librería para congelar el tiempo (`git grep -lE "freeze_time|time_machine"` → 0). Con un fixture de fechas fijas, una prueba puede pasar hoy y fallar al cambiar de ciclo lectivo.
5. **Identificadores fijos del volcado:** `session['est_id'] = 1` (`estudiantes/tests.py:14-15`), 33 referencias a `pk`/`id` numéricos en `profesores/tests.py` y 10 en `administrativos/tests.py`.
6. **Plantillas:** 406 plantillas, 119 `autoescape off` y 95 condiciones de estado (§5.2) sin pruebas de contenido más allá de `assertContains` puntuales.

### 6.4 Qué tan confiable parece la suite

**a) Los fixtures son un volcado completo de la base, generado en el propio CI.**

- `.drone.yml:228-258` ejecuta ocho veces `manage.py dumpdata` **sin filtrar por app** y guarda el mismo volcado completo con ocho nombres (`profesores/fixtures/profesores.json`, `administrativos/fixtures/prod.json`, `webpage/fixtures/prod.json`…). `fixtures` está en `.gitignore:43`: ningún fixture está versionado.
- La base de origen se carga con `mysql … -f … < docker/django/testing.sql 2> /dev/null` (`.drone.yml:95`): `-f` hace que continúe ante errores de SQL y `2> /dev/null` los descarta. Un volcado incompatible con los modelos no detiene el pipeline en ese paso.
- `migrate` está comentado (`.drone.yml:102`): el esquema de la base de origen es el del volcado, no el de los modelos. La base de pruebas, en cambio, sí se crea con migraciones recién generadas (`.drone.yml:98-100`).
- Por eso **los volcados SQL son, en la práctica, las migraciones del proyecto**: `docker/db/init.sql` tiene 32 commits en 12 meses y `docker/django/testing.sql` 19 (`git log --since=2025-11-08 --format=%h -- <archivo> | wc -l`), con mensajes como "fix(fixtures): asigna aulas a horarios de grupos". Cada cambio de modelo exige regenerar o editar a mano un archivo de unos 500 KB.
- El nombre `prod` se usa para dos fixtures (`administrativos` y `webpage`) y 26 pruebas de `postulaciones` cargan el fixture `profesores`; `postulaciones/fixtures/postulaciones.json` se genera (`.drone.yml:258`) y ninguna prueba lo declara.
- Las pruebas afirman contra datos concretos del volcado, incluidos el nombre y la URL de perfil de una persona del personal docente (`profesores/tests.py:91-95`) y contraseñas de prueba en claro que deben coincidir con los hashes del volcado (`estudiantes/tests.py:35`). Esto apunta a que el volcado deriva de datos reales (§7.1).

**b) 13 de los 14 `skip` son por datos ausentes en el fixture.** `webpage/tests.py:268-471` (9), `trabajo_final_de_graduacion/tests.py:435-496` (3: "Se requieren al menos 2 profesores en la fixture") y `profesores/tests.py:895`. El restante pide Chrome (`profesores/tests.py:3492`).

**c) Las pruebas de humo "autenticadas" no se autentican ni pueden fallar.**

- El pipeline intenta iniciar sesión con `curl --user … --cookie-jar ./cookprof nginx/profesores/login?next=…` (`.drone.yml:167`, `:177` y `:191`, paso `test-eieinfo-urls`). `--user` envía autenticación HTTP básica en un `GET`; el login de EIEInfo es un formulario `POST` con CSRF y el código no lee la cabecera `Authorization` (`git grep -nE "HTTP_AUTHORIZATION|BasicAuthentication"` → 0). La cookie guardada es la de un visitante anónimo.
- Las 31 peticiones posteriores con `--cookie` (12 de profesores, 11 de administrativos, 8 de estudiantes) **no llevan `-f`**, así que `curl` termina con éxito aunque reciba una redirección al login o un error 500.
- Solo las 38 peticiones con `-f` a páginas públicas pueden hacer fallar el paso. Cuatro están comentadas porque fallaban ("No PaginaEstatica matches the given query", "list index out of range").

**d) Pruebas que el CI no ejecuta.** 30 funciones en 8 archivos: `asistencias` (7) y `proyecto_electrico` (2), de apps no instaladas; `eieinfo` (6), `trabajos_finales` (5), `conferencias` (5), `atributos` (3), `inventario` (1), `alumni` (1) (`.drone.yml:275` frente a `scripts/pruebas-eieinfo-0b3c575c.txt`). El CI sí genera un fixture para `atributos` (`.drone.yml:252-254`), pero no corre sus pruebas. Las 3 pruebas JavaScript tampoco.

**e) Sin umbral ni informe.** `coverage report -m` sin `--fail-under` (`.drone.yml:275-276`); no hay `.coveragerc`, así que la cobertura mide solo las 11 apps de `--source` y deja fuera `eieinfo`, `inventario`, `alumni`, `atributos`, `cursos`… El porcentaje real no es determinable sin ejecutar.

**f) El entorno local contradice al CI.** `docker/django/run-ut.sh:35-39` solo corre `administrativos` y `webpage`; `profesores` está comentado con la nota `#Fallan`. `pytest.ini` existe y pytest está instalado, pero ninguna prueba lo usa (E1 §6).

**Valoración.** La suite es **confiable en lo que cubre el código nuevo** (535 pruebas de `firma_digital` y `solicitud_documentos_externo`, autocontenidas) y **poco confiable como red de seguridad del núcleo**: 454 pruebas dependen de un volcado que nadie controla desde el código, los pasos que deberían fallar están silenciados y 31 de las 74 pruebas de humo no verifican nada. Un pipeline en verde dice que las páginas públicas responden y que el código reciente funciona; no dice nada sobre autorización, Proyecto Eléctrico, práctica profesional ni inventario.

### 6.5 Vacíos que dificultan la evolución segura

| Vacío | Por qué bloquea la evolución | Relacionado con |
|---|---|---|
| No hay pruebas de la matriz rol × vista | No se pueden unificar ni corregir los decoradores sin riesgo de abrir o cerrar accesos | H-04 |
| No hay datos de prueba construidos en código (fábricas) | Cualquier cambio de modelo rompe 454 pruebas por datos, no por lógica; y obliga a tocar los volcados | H-03, H-11 |
| No hay pruebas de los flujos de `PracticaProfesional` y `ProyectoElectrico` | Son los flujos con lógica en modelos y formularios que habría que extraer | H-09, §3.3, §3.5 |
| No hay pruebas de `duplicar_ciclo` ni de `nombramientos_auto` | Son operaciones masivas que se ejecutan una vez por ciclo | §3.2 |
| No hay pruebas de migración ni de esquema | Sin migraciones versionadas no existe "aplicar el cambio en una copia de producción" | H-03 |
| El CI no ejecuta todas las pruebas ni falla ante errores de preparación | Un cambio puede romper `trabajos_finales` o el volcado sin que nadie lo vea | H-05 |
| No hay pruebas de plantillas con contenido de usuario | No se puede retirar `autoescape off` con confianza | §2.6 |
| No se ejecutan las pruebas JavaScript | El flujo de firma por lotes depende de JS de cliente | §3.4 |

---

## 7. Seguridad y operación (enunciado 7.6)

### 7.1 Manejo de secretos: búsqueda en todo el historial

Script: `scripts/secrets_history.py` (solo `git log -p --all` y `git show`; nunca imprime valores, los compara con un HMAC de clave aleatoria). Alcance: **2909 commits, 47 ramas remotas**. Salida enmascarada: `scripts/secretos-historial-eieinfo-0b3c575c.txt` (94 coincidencias, 65 sin forma de *placeholder*; 41 archivos con nombre sensible).

```bash
python3 -I docs/anexos/scripts/secrets_history.py ~/repos/EIEInfo --all
```

| # | Tipo de secreto | Archivo | Commit (fecha) | Forma | ¿En `master`? | ¿Sigue en HEAD? |
|---|---|---|---|---|---|---|
| S-1 | **Contraseña SSH del paso `deployment` hacia `faraday.eie.ucr.ac.cr`** | `.drone.yml` (clave `password` bajo `settings`, L359 de esa versión) | Entra en `4dea1744` (2026-08-12), sale en `94bc38c8` (2026-08-13) | «ENMASCARADO», 20 car. alfanuméricos | Sí | No, pero permanece en el historial |
| S-2 | Token de bot de Telegram | `.drone.yml:313` | `71b2c589` (2024-05-18) | «ENMASCARADO», 46 car. | Sí | Sí |
| S-3 | Contraseña SMTP (`EMAIL_HOST_PASSWORD`) | `src/server/eieinfo/settings.py:345` | `3e4c2b8c` (**2016-02-25**); el valor actual es el mismo de 2016 | «ENMASCARADO», 10 car. | Sí | Sí |
| S-4 | Segunda contraseña SMTP, misma cuenta y servidor | `docker/django/secret_credentials.py` | `c4ab0c59` (2026-05-11) | «ENMASCARADO», 10 car., distinta de S-3 | Sí | Sí |
| S-5 | Credenciales de Imgur (`MARTOR_IMGUR_CLIENT_ID`, `MARTOR_IMGUR_API_KEY`) | `src/server/eieinfo/settings.py:428-429` | `67952803` (2018-01-12), sin cambios | «ENMASCARADO», 15 y 40 car. | Sí | Sí |
| S-6 | `SECRET_KEY` de Django | `src/server/eieinfo/settings.py` | Entra en `e36b1478` (2016-02-16), sale en `1344d99c` (2016-05-28) | «ENMASCARADO», 50 car. | Sí | No |
| S-7 | API key de Google Maps | `src/server/webpage/templates/webpage/index.html:529` | `3d8a54cc` (2017-01-20) | «ENMASCARADO», 39 car. (`AIza…`) | Sí | Sí |
| S-8 | Hashes PBKDF2 de contraseñas | `docker/db/init.sql`, `docker/django/testing.sql` | Desde `bae674e4` (2024-05-27) | 40 y 49 valores distintos a lo largo del historial; 30 y 16 en HEAD | Sí | Sí |
| S-9 | Copia completa del repo anidada, con `settings.py.backup2/3/4`, `db.sqlite3` (168 KB) y copia de `OwncloudProfesores.csv` | `EIEInfonoticias/EIEInfo/…` (3914 archivos) | `e561512f` (2025-11-27) | Los respaldos repiten S-3 y S-5; `backup4` trae una `SECRET_KEY` con prefijo `django-insecure` | **No**: solo en `origin/alissa-anthony` | — |
| S-10 | Volcado `BasePrueba.sql` (424 KB, 30 hashes, tablas `estudiantes`, `funcionarios`, `auth_user`, `django_session`) | `docker/django/BasePrueba.sql` | `63f3512c` (2025-06-22) | — | No: `origin/dev_postulacion_docentes`, `origin/obtener_cursos_en_prev` | — |
| S-11 | Contraseñas triviales de entornos de prueba | `.drone.yml`, `docker-compose.yml`, `docker/django/.env`, `migraciones.sh`, `run-ut.sh` | 2022–2026 | 3–8 car. | Sí | Sí |

Notas:

- **S-1 es el hallazgo nuevo más grave.** No determinable si esa contraseña sigue vigente ni a qué usuario corresponde (la línea `username` no se imprimió). Debe tratarse como comprometida.
- S-3 y S-4: dos valores distintos para la misma cuenta; al menos uno está obsoleto, pero no se puede saber cuál desde el repo.
- S-6: no determinable si producción usa hoy otra `SECRET_KEY` (vive en `eieinfo/secret/`, ignorado).
- S-7 es pública por naturaleza (va al navegador); el riesgo depende de si está restringida por dominio, no determinable.
- Descartados tras revisar la forma: `respaldo_info.sql` (`origin/obtener_cursos_en_prev`) está vacío; `src/database/eieinfo_db.sql` (2016) son 4 `CREATE TABLE` sin datos; las 3 "URL con credenciales" de los volcados son enlaces `http://mailto:…@ucr.ac.cr` mal formados en `paginas_estaticas`.
- No aparecen llaves privadas, tokens de GitHub/GitLab, AWS ni Facebook reales en ningún commit.

**Datos personales en los volcados.** `docker/db/init.sql` y `docker/django/testing.sql` traen filas en `estudiantes`, `funcionarios`, `auth_user` y `django_session`, con 85 y 100 direcciones de correo (79 y 92 de `ucr.ac.cr`). Las pruebas afirman contra el nombre y el perfil de una persona real del personal (§6.4), lo que corrige el "no determinable" de la Entrega 1: al menos parte de esos datos es real.

### 7.2 Configuración sensible

- Modo producción por nombre de host, `DEBUG = True` y `ALLOWED_HOSTS = ['*']` en cualquier otro equipo (`settings.py:483-493`); `secret_credentials` se importa después (`:528`) y puede reescribir cualquier valor (E1 H-08).
- Sesiones de 6 horas (`settings.py:229-236`); política de contraseñas de 6–7 caracteres (`administrativos/misc.py:19,241`).
- **`/media/` se sirve sin autenticación.** nginx de producción solo bloquea `/media/tfg/` (`conf/etc/nginx/sites-available/eieinfo:76-82`); el propio código lo reconoce (`trabajo_final_de_graduacion/views.py:1225-1229`: "el link directo a /media/ … no verifica nada"). Fuera de `tfg/` se suben, entre otros, cartas de práctica profesional (`upload_to=PathCartaPracticaProf`, con nombre de archivo derivado del nombre del estudiante, `estudiantes/models.py:1003-1006`), expedientes y avances de Proyecto Eléctrico (`PathExpedientePE`, `PathAvanceProyectoElectrico`), adjuntos de solicitudes (`solicitudes_adjuntos/`, `documentos_solicitud_externo/`) y fotos de estudiantes. Quien conozca o adivine la URL los descarga. Las rutas exactas que devuelven las funciones `Path*` no se revisaron.
- La imagen Docker no define `USER` (`docker/django/Dockerfile`): el contenedor corre como root. En producción el servicio usa el usuario `eieinfo` (`eieinfo.service:7-8`), sin opciones de endurecimiento de systemd.
- El pipeline monta el socket de Docker del host (E1 §1.5).

### 7.3 Riesgos en endpoints y autenticación

| Riesgo | Evidencia | Estado respecto a E1 |
|---|---|---|
| Defectos de lógica en 4 decoradores (acceso concedido a cualquier profesor con rol; errores 500 por `roles = None`) | `profesores/misc.py:186-189,305,350-355,393-397`; `administrativos/misc.py:107` | **Nuevo** |
| `pe_login_required` roto y con `redirect` sin `return` | `trabajos_finales/misc.py:20-25` | **Nuevo** |
| 15 vistas borran registros sin comprobar el método HTTP (aceptan GET; CSRF no las cubre) | §3.1; `scripts/vistas-eieinfo-0b3c575c.txt` | **Nuevo** |
| Redirección abierta: `HttpResponseRedirect(request.POST['next'])` y `request.GET['next']`; 0 usos de `url_has_allowed_host_and_scheme` | `profesores/views/publico.py:96`, `administrativos/views/publico.py:80`, `profesores/views/consejo_asesor.py:277-278`; rama `origin/fix/open-redirect-login` sin integrar | Confirmado |
| Oráculo de credenciales sin CSRF ni límite de intentos | `webpage/views.py:386-395` → `^funcionarios/login$`; sin consumidor en el repo | Confirmado |
| `csrf_exempt`: 4 en total | `webpage/views.py:386`, `conferencias/views.py:43`, `profesores/views/home.py:71` (innecesario), `firma_digital/views.py:1268` (integración con Firmador Libre) | Uno más que en E1 |
| Código de postulación = `EIE-<año>-<8 hex de uuid4>` (32 bits), sin límite de intentos; da lectura y edición de datos personales | `postulaciones/models.py:41-46`; `postulaciones/views.py:415-441` | Confirmado |
| Sin limitación de intentos en ningún login | `git grep -nE "ratelimit|axes|throttle"` → 0 | **Nuevo** |
| Vistas sin decorador: `sugerencias` (guarda datos de anónimos), `home` de bodega | `profesores/views/home.py:240`; `inventario/views/bodega.py:36` | Confirmado |
| `webservice_profesor` devuelve cédula y correo de cualquier profesor a cualquier profesor | `profesores/views/home.py:55-64` | **Nuevo** |
| Registro de funcionarios: solo envía un correo al administrador, sin captcha (vector de spam, no de alta de cuentas) | `administrativos/views/publico.py:95-120` | Resuelve el pendiente de E1 §5.3 |
| Salida sin escapar: 119 `{% autoescape off %}` en 101 plantillas y 8 `\|safe` en 6; un solo punto de saneamiento | `git grep -c "autoescape off" -- '*/templates/*'`; `alumni/forms.py:139` | **Nuevo** (E1 solo contó `\|safe`) |
| Datos de usuario en LaTeX sin escape; `pdflatex` sin tiempo límite | `CartaPracticaProfesional.tex:27-29,50`; `eieinfo/misc.py:161-167` | **Nuevo** |
| Permisos cacheados en sesión | `administrativos/misc.py:102-111,173-182,212-221` | Confirmado |

Contraejemplos: descargas de `firma_digital` y de TFG con control en la vista (§3.4, §3.5); tokens de recuperación de 122 bits con expiración de un día.

### 7.4 Dependencias problemáticas

Script: `scripts/deps_audit.py`. Salidas: `scripts/dependencias-eieinfo-0b3c575c.txt` (resumen y detalle por aviso) y `.json` (salida cruda de `pip-audit`).

Método:

- **Herramienta:** `pip-audit` 2.10.1 contra la base OSV, en modo `--no-deps --disable-pip`. Consulta cada par nombre-versión fijado con `==`; no resuelve dependencias, no instala paquetes ni ejecuta código.
- **Fecha:** consulta del 2026-11-14. Los avisos que se publiquen después cambian las cifras.
- **Conteo:** OSV publica un mismo CVE con varios identificadores (PYSEC, GHSA). Por eso se cuenta **una vulnerabilidad por grupo de alias**: los 131 avisos brutos del archivo de Docker son 82 vulnerabilidades.
- **Aplicabilidad:** se verificó contra el código de EIEInfo y, donde hizo falta, contra el código fuente de Django 4.1.3, 4.1.13 y 4.2.26. Para eso se descargaron las *wheels* al scratchpad, sin instalarlas.

**Dos archivos de requisitos.** La divergencia entre `requirements.txt` (raíz) y `docker/django/requirements.txt` ya está documentada en E1 anexo §1.2 (forks en ramas móviles, duplicados, paquetes sin fijar). Lo nuevo de esta entrega son dos cosas:

- **Qué archivo usa cada entorno.** La raíz es el de la instalación manual: lo indica `README.md:41-46`, y el commit `6ab5c8bd` lo llama "los requirements usado en produccion". Docker y el CI usan el otro (`docker/django/Dockerfile:20-22`). La referencia `releases/0.10.1` del archivo de Docker es una etiqueta fija (verificada con `git ls-remote`), así que se puede auditar como `wiki==0.10.1`.
- **El archivo de la raíz no basta para el código actual.** `postulaciones` está instalada (`src/server/eieinfo/settings.py:73`) e importa `django_countries` (`postulaciones/models.py:4`, `postulaciones/forms.py:4`). Ese paquete solo lo declara el archivo de Docker, desde el commit `2eb7af30` (2025-08-08); E1 anexo §2.2 ya había notado que faltaba en la raíz, pero no la consecuencia. Si se instala como indica el README, el proyecto no arranca. Por lo tanto, **no es determinable con qué lista de paquetes se instaló Faraday**, y el CI prueba otra distinta (además de reemplazar `settings.py` por `docker/django/settings.py`, `.drone.yml:87-88`).

**Resultado de `pip-audit`**

| Paquete | Versión | Vulns | Corrige todas | ¿La alcanza EIEInfo? |
|---|---|---|---|---|
| Pillow | 9.4.0 | 55 | 13.0.0 (36 se corrigen solo ahí) | **Sí, por los decodificadores.** EIEInfo no importa `PIL` en ningún archivo, pero la validación de `ImageField` (15 campos en 10 archivos) abre cada imagen subida y `sorl-thumbnail` la decodifica. Aplican los fallos al leer GIF, TIFF, JPEG y APNG, y los de la `libwebp` empaquetada en las *wheels* (CVE-2023-4863, escritura fuera de límites). No se alcanzan las API que habría que llamar a propósito, como `ImageMath` (CVE-2023-50447, ejecución de código), `ImageFont` o `ImageCms`. Solo suben imágenes usuarios autenticados: el registro público de egresados no pasa `request.FILES` (`alumni/views/publico.py:49`). Lo que `sorl-thumbnail` hace por dentro (recortes, filtros) no se auditó |
| Django | 4.1.3 | 20 | Sin una sola versión: 4.1.13 corrige 7; las otras 13 solo se corrigen en 4.2, 5.2 o 6.0 | 3 aplican; detalle abajo |
| gunicorn | 20.1.0 | 2 | 22.0.0 | **Sí.** Ambas son *request smuggling* (CVE-2024-1135, CVE-2024-6827), el riesgo típico de un gunicorn detrás de un *proxy* como el nginx de producción (E1). No es determinable si la configuración de nginx lo neutraliza |
| requests | 2.31.0 | 3 | 2.33.0 | Solo en el archivo de la raíz. No hay uso directo: 0 archivos lo importan y 0 `verify=False`. Llega como dependencia de otras bibliotecas |
| PyPDF2 | 1.26.0 | 2 | 1.27.9 | **No: ningún archivo del repositorio lo importa** (`git grep -il pypdf -- '*.py'` → 0). Es una dependencia muerta que se instala sin uso |
| Markdown | 3.3.4 | 1 | 3.8.1 | Indirecta: EIEInfo no importa `markdown`; lo usa `martor` (3 archivos). Es una excepción no controlada (CVE-2025-69534) |
| django-select2 | 6.3.1 | 1 | 8.4.1 | **No.** El aviso (CVE-2025-48383) solo afecta a las subclases de `HeavySelect2Mixin` (texto del aviso en OSV). EIEInfo solo usa `Select2Widget` (`administrativos/forms.py:17`, `trabajos_finales/forms.py:13`) y tiene 0 usos de `Heavy*` o `ModelSelect2*` |
| pytest | 7.2.2 | 1 | 9.0.3 | Solo desarrollo y CI (`docker/django/requirements.txt:76`) |

Sin avisos conocidos: los otros 37 paquetes fijados, incluido `wiki==0.10.1`. Quedan sin auditar los forks de `django-wiki` y `django-tagging` en ramas móviles (raíz, `:46-47`), los paquetes sin versión fija y todas las dependencias transitivas.

**Django 4.1.3: aplicabilidad de las 20 vulnerabilidades**

La última versión publicada de la rama 4.1 es la 4.1.13 (`pip index versions Django`).

| Situación | Vulnerabilidades | Por qué |
|---|---|---|
| **Aplican (3)** | CVE-2023-24580 (agotamiento de recursos al procesar *multipart*), CVE-2023-36053 (ReDoS en `EmailValidator` y `URLValidator`), CVE-2025-48432 (inyección en registros) | Varios portales aceptan subidas de archivos. Hay 27 usos de `EmailField`, `URLField` o esos validadores en producción, incluido el registro público de estudiantes (`estudiantes/models.py:130`, `estudiantes/forms.py:140`). Django escribe en el registro la ruta de cada error |
| **Mitigada (1)** | CVE-2023-31047 (la subida múltiple solo valida el último archivo) | El patrón vulnerable existe (`trabajo_final_de_graduacion/forms.py:169,537,637`), pero el `clean()` revisa cada archivo (`:275`, `:612`, `:668`) y el campo no declara validadores que se puedan saltar |
| **No alcanzables (14)** | GeoDjango y GDAL (CVE-2026-15307, -15830, -53877); *middleware* de caché (CVE-2026-48587, -8404, -48588); `_connector` en `filter(**kwargs)` (CVE-2025-64459); alias de columna (CVE-2025-57833); `Accept-Language` (CVE-2023-23969); `uri_to_iri` (CVE-2023-41164); `Truncator` con HTML (CVE-2023-43665); `PasswordResetForm` (CVE-2024-45231); solo en Windows (CVE-2023-46695, CVE-2025-64458) | EIEInfo tiene 0 usos de `contrib.gis`, `CacheMiddleware`/`cache_page`, `annotate(**…)`/`FilteredRelation`, `LocaleMiddleware`, `PasswordResetForm` y `truncate*_html`. Las funciones de caché vulnerables solo las llama `django/middleware/cache.py`, y `uri_to_iri` no la llama ningún otro módulo de Django 4.1.3. Los 4 `filter(**filtro)` usan claves fijas en el código (`trabajo_final_de_graduacion/precarga.py:97,136`, `solicitud_documentos_externo/precarga.py:108-111,149-152`). El servidor es Linux |
| **Falso positivo (1)** | CVE-2026-53878 (`DomainNameValidator`) | La clase no existe en Django 4.1.3 ni en 4.2.26: OSV marca como afectadas todas las versiones anteriores a la corrección |
| **No determinable (1)** | CVE-2026-6873 (colisión de *salt* en cookies firmadas) | EIEInfo no firma cookies propias, pero `MessageMiddleware` (`settings.py:102`) usa por defecto `FallbackStorage`, que guarda los mensajes en cookies firmadas |

**Actualizar Django rompe `trabajo_final_de_graduacion`.** Esto se verificó en el código fuente de Django:

- Desde la 4.1.9 (presente en 4.1.13 y 4.2.26), la corrección de CVE-2023-31047 hace que `FileInput.__init__` lance `ValueError` si recibe `attrs={'multiple': True}` (`django/forms/widgets.py:421-430` en 4.2.26).
- EIEInfo crea tres de esos *widgets* en el cuerpo de la clase (`trabajo_final_de_graduacion/forms.py:169,537,637`). El error salta al importar `forms.py`, que importa `views.py:29`, que importa `urls.py:2`.
- El URLconf raíz incluye ese módulo (`eieinfo/urls.py:68`), así que el fallo afecta a todo el sistema, no solo a TFG.
- Consecuencia: **cualquier actualización de Django, incluso a 4.1.13 dentro de la misma rama, exige antes cambiar esos tres *widgets*** por una subclase con `allow_multiple_selected = True`. Es un insumo directo para la hoja de ruta de la E3.

**Otras dependencias problemáticas (fuera del alcance de `pip-audit`)**

| Dependencia | Problema |
|---|---|
| `oauth2client` 3.0.0 | Biblioteca declarada obsoleta por Google; sin avisos en OSV, pero sin mantenimiento |
| `django-tagging` 0.5.0 | Incompatible con Django 4: se parchea con `sed` y con *monkeypatch* (E1 H-07) |
| `bleach` | No está declarado. Se importa en `alumni/forms.py:13` y solo llega como dependencia transitiva de `django-wiki` |
| Imágenes base | `python:buster` (Debian 10, retirado) y `mariadb` sin etiqueta. El sistema operativo y la base de datos quedan fuera de esta auditoría |

**Lectura.** Las cifras brutas (84 vulnerabilidades en el archivo de la raíz y 82 en el de Docker) exageran el riesgo, pero la exposición real sigue siendo seria:

- Pillow decodifica imágenes subidas por usuarios y tiene decenas de fallos conocidos en sus decodificadores.
- gunicorn es vulnerable a *request smuggling* en el mismo esquema de *proxy* que usa producción.
- Django tiene 3 vulnerabilidades que aplican. Además, la rama 4.1 ya no recibe parches: las 13 vulnerabilidades posteriores a 4.1.13 nunca se corregirán en ella.

Para la evolución pesan dos cosas: actualizar Django no es un cambio de versión trivial, porque primero rompe TFG; y no existe una lista única y fiable de lo que corre en producción. Todo esto alimenta H-07 (tecnologías fuera de soporte) y H-08 (configuración y entornos divergentes); ver §8.

### 7.5 Prácticas de despliegue y automatización

- Despliegue manual: el paso `deployment` solo hace `git status` y tiene `failure: ignore` (E1 H-05). S-1 muestra que en agosto de 2026 se intentó reactivarlo con la contraseña escrita en el archivo.
- La preparación del CI silencia errores (`mysql -f … 2> /dev/null`, `.drone.yml:95`) y no ejecuta `migrate` (`:102`); las pruebas de humo autenticadas no verifican nada (§6.4).
- Migraciones borradas y regeneradas en cada arranque (E1 H-03); los volcados SQL hacen de esquema (32 y 19 commits en 12 meses).
- Sin rotación de registros ni endpoint de salud (§2.8); cron no determinable en producción.
- Sin respaldo ni procedimiento de restauración documentado en el repo (`git grep -il "backup\|respaldo" -- conf docker README.md` solo devuelve comentarios del pipeline).

---

## 8. Registro consolidado de hallazgos (enunciado 7.7)

El detalle de cada hallazgo (descripción, evidencia, impacto técnico, riesgo, recomendación y prioridad) está en el documento principal, [`../entrega-2/entrega-2.md`](../entrega-2/entrega-2.md) §9. Aquí queda la consolidación: qué pasó con cada hallazgo de la Entrega 1, de qué sección sale cada uno nuevo y la trazabilidad con los candidatos del anexo de E1.

**Numeración.** Se conserva la de `entrega-1.md` (H-01 a H-12, documento entregado) y los hallazgos nuevos siguen desde H-13. El anexo de E1 (§9) usaba otra numeración, con 20 candidatos; la tabla 8.3 la traduce.

### 8.1 Registro

| ID | Título | Severidad | Alcance | Prioridad | Respecto a E1 | Evidencia en este anexo |
|---|---|---|---|---|---|---|
| H-01 | Secretos reales versionados, también en el historial | Crítica | Sistémico | P1 | Ampliado (S-1, S-3, S-6, S-9) | §7.1 |
| H-02 | Datos personales reales y credenciales en volcados y CSV versionados | Crítica | Sistémico | P1 | Ampliado (C-7: los datos son reales) | §7.1, §6.4 |
| H-03 | Sin migraciones: los volcados SQL hacen de esquema | Crítica | Sistémico | P2 | Ampliado | §2.2, §6.4, §5.5 |
| H-04 | Autenticación y autorización propias, duplicadas y sin pruebas | Alta | Sistémico | P3 | Ampliado (C-4) | §2.6, §2.7, §4.7 d), §5.3 |
| H-05 | El CI no despliega, no falla y sus pruebas de humo autenticadas no verifican nada | Alta | Sistémico | P2 | Ampliado | §6.4 c)–e), §7.5 |
| H-06 | Acoplamiento cíclico originado en el doble papel de `administrativos` | Alta | Sistémico | P3 | Ampliado (causa identificada) | §2.4, §3.2, §4.4, §5.6 |
| H-07 | Pila sin soporte con vulnerabilidades alcanzables y actualización bloqueada | Alta | Sistémico | P1 / P3 | Ampliado (pip-audit) | §7.4 |
| H-08 | Configuración y dependencias divergentes entre entornos | Alta | Sistémico | P2 | Ampliado (requisitos divergentes) | §7.2, §7.4, §5.6 |
| H-09 | `profesores` como portal "dios" que además autoriza a otras apps | Alta | Local | P3 | Ampliado | §3.1 |
| H-10 | Conceptos de dominio duplicados o ambiguos | Media | Sistémico | P4 | Corregido (C-1) y ampliado | §4.3, §4.6, §4.7 |
| H-11 | Pruebas atadas a un volcado y ausentes donde más se necesitan | Alta | Sistémico | P2 | **Severidad elevada** (Media → Alta) | §6 |
| H-12 | Observabilidad operativa débil y errores silenciados | Media | Sistémico | P2 | Ampliado | §2.8 |
| H-13 | Defectos explotables de control de acceso en endpoints concretos | Crítica | Local | P1 | **Nuevo** (reúne candidatos E1 anexo H-05, H-10, H-19) | §2.6, §3.1, §7.3 |
| H-14 | Datos de usuario renderizados sin escape (HTML y LaTeX) | Alta | Sistémico | P2 | **Nuevo** (C-5) | §2.6, §3.3, §3.6, §7.3 |
| H-15 | Archivos subidos servidos sin autenticación fuera de `/media/tfg/` | Alta | Local | P2 | **Nuevo** | §7.2 |
| H-16 | Un defecto copiado en 5 lugares rompe flujos activos sin que ninguna prueba lo detecte | Alta | Local | P1 | **Nuevo** | §5.3, §3.3, §6.3 |
| H-17 | Duplicación estructural entre portales | Media | Sistémico | P3 | **Nuevo** | §2.1, §5.3 |
| H-18 | Lógica de negocio dispersa, sin capa de servicios ni transacciones | Alta | Sistémico | P3 | **Nuevo** (candidato E1 anexo H-18) | §5.2, §5.7, §3.3, §3.5 |
| H-19 | Reglas atadas a filas concretas de la base y a un "ciclo actual" global | Media | Sistémico | P3 | **Nuevo** | §2.2, §4.4, §5.6 |
| H-20 | Código muerto, comentado y nombres que engañan | Baja | Sistémico | P4 | **Nuevo** (candidatos E1 anexo H-14 y H-15) | §5.5, §3.5 |

Distribución: 4 críticos, 11 altos, 4 medios y 1 bajo; 16 sistémicos y 4 locales.

### 8.2 Criterios

**Severidad** (se mantiene el criterio de E1 y se agrega el nivel bajo):

- **Crítica:** exposición actual de información, acceso indebido explotable hoy o riesgo de pérdida de datos.
- **Alta:** problema estructural que encarece o pone en riesgo cualquier cambio, o vulnerabilidad que requiere condiciones adicionales para explotarse.
- **Media:** dificulta el mantenimiento o produce fallos acotados, pero no compromete la operación de inmediato.
- **Baja:** deuda que confunde o estorba, sin efecto directo en la operación.

**Prioridad de atención:**

- **P1, inmediata:** antes de cualquier otro trabajo; correcciones pequeñas o rotaciones.
- **P2, corto plazo:** saneamiento que habilita el resto (esquema, CI, pruebas, configuración).
- **P3, mediano plazo:** refactorización estructural; requiere que P2 esté hecho.
- **P4, oportunista:** se resuelve al tocar la zona por otro motivo.

H-07 lleva dos prioridades: P1 para los parches dentro de la misma rama (Django 4.1.13 tras corregir los *widgets* de TFG, gunicorn 22, Pillow) y P3 para el salto a una rama LTS con soporte.

### 8.3 Trazabilidad con los candidatos del anexo de E1

| Candidato (anexo E1 §9) | Hallazgo E2 |
|---|---|
| H-01 Secretos, H-02 Contraseñas y datos personales, H-03 Migraciones, H-04 Autenticación | H-01, H-02, H-03, H-04 (mismo número) |
| H-05 Open redirect tras el login | H-13 |
| H-06 El pipeline no despliega | H-05 |
| H-07 Acoplamiento cíclico | H-06 |
| H-08 Pila fuera de soporte | H-07 |
| H-09 Configuración divergente | H-08 |
| H-10 `csrf_exempt` y oráculo de credenciales | H-13 |
| H-11 `profesores` "dios" | H-09 |
| H-12 Dominio duplicado | H-10 |
| H-13 Pruebas desbalanceadas | H-11 |
| H-14 Código muerto | H-20 |
| H-15 Documentación desactualizada | H-20 |
| H-16 Observabilidad | H-12 |
| H-17 Dependencias inconsistentes entre entornos | H-08 (y H-07) |
| H-18 Lógica de negocio en formularios y modelos | H-18 |
| H-19 Código de postulación de baja entropía | H-13 |
| H-20 Recursos estáticos vendorizados | H-07 |

---

## 9. Preguntas orientadoras (enunciado 7.7)

Las respuestas desarrolladas están en `entrega-2.md` §10. Resumen con la evidencia que las sostiene:

| Pregunta | Respuesta corta | Evidencia |
|---|---|---|
| ¿Qué problemas son locales y cuáles sistémicos? | Los locales (H-09, H-13, H-15, H-16) son casi todos **síntomas** de causas sistémicas: H-13 nace de H-04 y H-19; H-16 de H-17 y H-11 | §8.1; `entrega-2.md` §9.3 |
| ¿Qué partes serían más costosas de cambiar? | Los modelos núcleo de `administrativos` (30 relaciones entrantes de 12 apps, sin migraciones), los decoradores de autorización (5 apps, sin pruebas), el Consejo Asesor (dos copias) y la versión de Django (bloqueada por TFG) | §3.2, §2.6, §2.1, §7.4 |
| ¿Dónde existe mayor acoplamiento estructural? | El ciclo `administrativos` ↔ `profesores` ↔ `cursos` ↔ `estudiantes`, los `CrearContexto*` (309 llamadas), `webpage.misc` y la herencia `Funcionario` → `Profesor` entre apps | §2.4, §4.4, §5.6 |
| ¿Qué decisiones de diseño envejecieron mal? | Regenerar migraciones, un usuario por portal (y luego un `User` espejo), `administrativos` como núcleo y portal, roles por texto libre, volcados como fixtures, desactivar código comentándolo | §2.7, §4.7, §6.4 |
| ¿Qué riesgos afectan la evolución futura? | Sin red de pruebas en el núcleo, sin control de esquema, pila sin soporte cuya actualización ya rompe un módulo, y conocimiento concentrado (2 autores en `firma_digital`, rotación semestral) | §6.5, §7.4, §3.4 |

---

## 10. Correcciones a la Entrega 1

| # | Dato de la Entrega 1 | Valor correcto | Evidencia |
|---|---|---|---|
| C-1 | "Dos subsistemas de trabajos finales" vivos (H-10); `trabajos_finales` descrito como el "subsistema antiguo" | El TFG antiguo está **comentado** (1999 líneas `##`). `trabajos_finales` hoy solo contiene Proyecto Eléctrico; conviven dos flujos hermanos (PE y TFG), no dos TFG | `trabajos_finales/models.py:674,706,1177,1264`; commit `f5a94cab` |
| C-2 | `trabajos_finales`: 1313 LOC de modelos y 1056 de formularios; "lógica concentrada en `forms.py`" | Líneas vivas: 542 en `models.py` y 467 en `forms.py`. El tamaño estaba inflado por código comentado | §3; `git grep -cE "^\s*##"` |
| C-3 | Código comentado: `trabajos_finales` 11 líneas (E1 anexo §8.2) | 2025 líneas `##` en producción; la heurística de E1 no reconocía el prefijo `##` | `git grep -hE "^\s*##" -- '*.py' \| wc -l` |
| C-4 | "`django.contrib.auth` solo se usa para `/admin`, la wiki y `conferencias`"; el login "guarda el identificador en la sesión" | Los logins de profesores y administrativos **también** hacen `django_login` con un `User` espejo, desde 2018-02-23; `firma_digital` depende de `request.user` | `profesores/forms.py:82`, `administrativos/forms.py:67`; commit `9b66e9c9` |
| C-5 | Revisión de plantillas: "`\|safe`: 6 archivos" como superficie de XSS | Además hay 119 `{% autoescape off %}` en 101 plantillas | `git grep -c "autoescape off" -- '*/templates/*'` |
| C-6 | "Las rutas de `webpage` están ancladas" (anexo §5.1) | `webpage/urls.py:36` (`tramites_graduacion`) no lleva `^` | `webpage/urls.py:36` |
| C-7 | `init.sql`/`testing.sql`: "no determinable si son datos reales" | Al menos parte es real: las pruebas afirman contra una persona concreta del personal; incluyen `auth_user` y `django_session` | `profesores/tests.py:91-95`; §7.1 |
| C-8 | Secretos: solo árbol actual; token de Telegram como el más grave | El historial añade una contraseña SSH de producción (S-1), la `SECRET_KEY` de 2016 (S-6) y que la contraseña SMTP no cambia desde 2016 | §7.1 |
| C-9 | `csrf_exempt` en 3 vistas | Son 4 (falta `firma_digital/views.py:1268`) | `scripts/vistas-eieinfo-0b3c575c.txt` |
| C-10 | 311 funciones `CamelCase` frente a 1803 `snake_case` | En producción (sin pruebas ni métodos especiales): 320 frente a 958; las 1166 funciones de prueba inflaban `snake_case` | AST |
| C-11 | "26 archivos de producción hacen `from webpage …`" | 23 archivos de otras apps (19 importan `webpage.misc`) | `git grep -lE "^\s*from webpage"` |
| C-12 | `scripts/metricas-eieinfo-0b3c575c.json` (`n_urls`) | El JSON no cuenta `urlpatterns/` (da 12 para `profesores`); las cifras de la tabla de E1 (150, 93, 43) sí son correctas | Recuento AST de esta entrega |
| C-13 | Registro de funcionarios: "flujo de aprobación no revisado" | No crea cuentas; solo envía un correo al administrador | `administrativos/views/publico.py:95-120` |
| C-14 | Relaciones de modelo hacia `administrativos` (no se cuantificó) | 30 relaciones desde 12 apps | `scripts/dominio-eieinfo-0b3c575c.json` |
| C-15 | PyPDF2 1.26.0 listada como dependencia de PDF del sistema (E1 anexo §1.2, `entrega-1.md:88,398`) | Está declarada en ambos `requirements.txt`, pero ningún archivo la importa: es una dependencia muerta | `git grep -il pypdf -- '*.py'` → 0; §7.4 |
Se mantienen sin cambio: métricas de tamaño por app, 90 dependencias y 28 pares bidireccionales, 1166 pruebas y 14 `skip`. Los identificadores H-01 a H-12 se conservan; su contenido y, en H-11, su severidad se actualizan en §8.