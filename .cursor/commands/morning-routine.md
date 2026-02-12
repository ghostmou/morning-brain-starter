# Rutina de buenos días

Ejecuta la rutina matinal **en orden** (pasos 1 → 7). La definición completa está en el **skill good-morning** (`.cursor/skills/good-morning/SKILL.md`): ahí están los pasos, comandos exactos y qué esperar.

**Qué hacer:** abre el skill good-morning y sigue el plan. Cada paso tiene su llamada CLI; no hace falta usar run_morning.py.

**Comandos por paso (desde la raíz):**

| Paso | Acción | CLI |
|------|--------|-----|
| 1 | Calendario (hoy + Meet + transcripciones) | `.venv/bin/python scripts/calendar_lite.py --today --add-meet --add-meet-my-events-only --add-transcription-reminder` |
| 2 | Asana (mover tareas de ayer a hoy) | `.venv/bin/python scripts/asana_lite.py --move-yesterday-to-today` |
| 3 | Asana (listar tareas de hoy) | `.venv/bin/python scripts/asana_lite.py` |
| 4 | Email | `.venv/bin/python scripts/email_lite.py` |
| 5 | Transcripciones (importar ayer) | `.venv/bin/python scripts/calendar_lite.py --import-transcriptions` |
| 6 | Asana (tareas realizadas ayer → bitácora) | `.venv/bin/python scripts/asana_lite.py --completed-yesterday-to-bitacora` |
| 7 | Bitácoras | `.venv/bin/python scripts/morning_step_bitacora.py` |

**Atajo todo en uno:**
```bash
.venv/bin/python run_morning.py
```

**Ver comandos sin ejecutar:**
```bash
.venv/bin/python run_morning.py --show-cli
```
