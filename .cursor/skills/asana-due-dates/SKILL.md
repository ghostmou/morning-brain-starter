---
name: asana-due-dates
description: >-
  Mueve fechas de vencimiento de tareas Asana entre días (misma semana, semana siguiente o días concretos), en bloque o solo algunas tareas por nombre. Usar cuando el usuario pida reprogramar, aplazar, mover vencimientos en Asana, o gestionar due dates sin el morning routine completo.
---

# Asana: fechas de vencimiento (due dates)

## Requisitos

- `ASANA_ACCESS_TOKEN` en `.env` (ver skill boarding / credenciales).
- Ejecutar desde la **raíz del repo** con `.venv/bin/python`.

Las palabras `today`, `yesterday`, `tomorrow` se resuelven en **fecha UTC** (mismo criterio que el resto de `asana_lite`). Para un día exacto, usar `YYYY-MM-DD`.

## Comandos (CLI)

Toda la lógica está en `scripts/asana_lite.py`.

### Mover de un día a otro (masivo o selectivo)

```bash
.venv/bin/python scripts/asana_lite.py --move-due FROM TO
```

- **FROM / TO:** `YYYY-MM-DD` o `today` | `yesterday` | `tomorrow`.
- Solo afecta a tareas **pendientes** con `due_on` = FROM (misma lógica que `get_tasks_due_on`).

**Solo algunas tareas** (nombre **exacto** como en Asana):

```bash
.venv/bin/python scripts/asana_lite.py --move-due FROM TO --only "Nombre tarea 1" "Nombre tarea 2"
```

**Simular** (listar sin escribir en Asana):

```bash
.venv/bin/python scripts/asana_lite.py --move-due FROM TO --dry-run
```

### Desplazar N días (útil: “el mismo día la semana que viene”)

```bash
.venv/bin/python scripts/asana_lite.py --shift-due FROM_DATE OFFSET_DAYS
```

Ejemplo: tareas con vencimiento el lunes pasado → **+7** días = mismo día la semana siguiente.

```bash
.venv/bin/python scripts/asana_lite.py --shift-due 2026-04-21 7 --dry-run
.venv/bin/python scripts/asana_lite.py --shift-due 2026-04-21 7
```

Con filtro por nombre: añadir `--only` como arriba.

### Atajo ya existente (ayer → hoy)

Sigue siendo válido y no se solapa con `--move-due`:

```bash
.venv/bin/python scripts/asana_lite.py --move-yesterday-to-today
```

Equivale a `--move-due yesterday today` sin `--only`.

## Patrones de uso

| Objetivo | Enfoque |
|----------|---------|
| Misma semana, otro día | `--move-due` con dos fechas `YYYY-MM-DD` de esa semana |
| Semana siguiente, mismo día del mes / mismo offset | `--shift-due FECHA 7` (u otro número de días) |
| Solo 2–3 tareas | `--move-due` + `--only` |
| Comprobar antes de tocar datos | siempre `--dry-run` primero |

## API interna (si el agente llama desde Python)

Tras `load_env` / import del módulo:

- `resolve_due_date_arg(spec)` → `YYYY-MM-DD`
- `tasks_pending_due_on(from_iso, only_names=None)`
- `move_tasks_due(from_iso, to_iso, only_names=None, dry_run=False)` → `(n, lista_tareas)`
- `shift_tasks_due(from_iso, offset_days, only_names=None, dry_run=False)`

## Errores habituales

- **`--only` sin coincidencias:** el CLI avisa “sin coincidencia en la fecha de origen”. Revisar nombre exacto y que el `due_on` sea el FROM esperado.
- **No mezclar modos:** solo una de `--move-yesterday-to-today`, `--completed-yesterday-to-bitacora`, `--move-due`, `--shift-due` por invocación.

## Relación con el morning routine

El paso “ayer → hoy” del skill `good-morning` usa `--move-yesterday-to-today`. Para reprogramaciones más finas, usar este skill y `asana_lite.py` como arriba.
