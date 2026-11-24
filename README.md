# Auditoría de diseño de software — EIEInfo (IE0417)

Repositorio de trabajo para la auditoría de diseño de software del sistema
[EIEInfo](https://git.ucr.ac.cr/eieinfo/EIEInfo) — curso IE0417, Universidad de Costa Rica.

Commit auditado: `0b3c575c` (rama `master`, 2026-11-04). El enunciado es
`Auditoría de diseño de software del sistema EIEInfo.pdf` (no se incluye en el repositorio).

## Entregas

| Entrega | Documento | Pregunta que responde |
|---|---|---|
| 1. Levantamiento y diagnóstico inicial | [`docs/entrega-1/entrega-1.md`](docs/entrega-1/entrega-1.md) | ¿Qué sistema tenemos enfrente y cuáles son sus principales rasgos de diseño? |
| 2. Auditoría profunda de diseño, calidad y riesgos | [`docs/entrega-2/entrega-2.md`](docs/entrega-2/entrega-2.md) | ¿Cuáles son los principales problemas de diseño del sistema, por qué importan y cómo se relacionan entre sí? |
| 3. Informe final y propuesta de evolución | [`docs/entrega-3/entrega-3.md`](docs/entrega-3/entrega-3.md) | Si el sistema tuviera que seguir evolucionando durante los próximos años, ¿qué debería hacerse primero, qué después y bajo qué estrategia? |

## Anexos

| Anexo | Contenido |
|---|---|
| [`docs/anexos/levantamiento-e1.md`](docs/anexos/levantamiento-e1.md) | Levantamiento técnico de la Entrega 1: métricas por app, dependencias, configuración, CI/CD y pruebas |
| [`docs/anexos/levantamiento-e2.md`](docs/anexos/levantamiento-e2.md) | Evidencia detallada de la Entrega 2, trazabilidad de los hallazgos y correcciones a la Entrega 1 |
| [`docs/anexos/scripts/`](docs/anexos/scripts/) | Scripts de medición (análisis estático, sin ejecutar EIEInfo) y sus salidas para `0b3c575c` |

## Diagramas principales

Fuentes Mermaid en [`docs/diagramas/`](docs/diagramas/); cada una está incluida en el documento que la usa.

| Diagrama | Entrega |
|---|---|
| [`dependencias-apps.mmd`](docs/diagramas/dependencias-apps.mmd): grafo de dependencias entre apps | 1 |
| [`dominio.mmd`](docs/diagramas/dominio.mmd): modelo entidad-relación simplificado | 2 |
| [`relaciones-hallazgos.mmd`](docs/diagramas/relaciones-hallazgos.mmd): relaciones causales entre hallazgos | 2 |
| [`arquitectura-actual.mmd`](docs/diagramas/arquitectura-actual.mmd) y [`arquitectura-objetivo.mmd`](docs/diagramas/arquitectura-objetivo.mmd): arquitectura actual y monolito modular objetivo | 3 |
| [`despliegue-objetivo.mmd`](docs/diagramas/despliegue-objetivo.mmd): operación y CI objetivo | 3 |
| [`hoja-de-ruta.mmd`](docs/diagramas/hoja-de-ruta.mmd): fases y dependencias entre intervenciones | 3 |

## Reproducir las verificaciones

```bash
# métricas por app y dependencias (requiere un clon de EIEInfo; no lo ejecuta)
python3 -I docs/anexos/scripts/metrics.py ~/repos/EIEInfo /tmp/metricas.json
# coherencia interna de la Entrega 3 (solo lee este repositorio)
python3 -I docs/anexos/scripts/trazabilidad_e3.py
```

## Estructura

```
docs/
├── entrega-1/   # Primera entrega
├── entrega-2/   # Segunda entrega
├── entrega-3/   # Tercera entrega
├── diagramas/   # Fuentes Mermaid (.mmd)
└── anexos/      # Levantamientos, scripts y sus salidas
```
