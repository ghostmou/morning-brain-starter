# Actualizar bitácoras

Cuando el usuario pida **actualizar las bitácoras** o ejecutar solo el **paso de bitácoras** de la mañana, sigue el **skill bitacora-update** (`.cursor/skills/bitacora-update/SKILL.md`).

Ese skill describe cómo funciona el proceso (fuentes: eventos de calendario, emails, tareas de Asana, transcripciones del día anterior) y el comando exacto a ejecutar.

**Comando (desde la raíz del proyecto):**

```bash
.venv/bin/python scripts/morning_step_bitacora.py
```

Para la rutina matinal completa (calendario + Asana + email + bitácoras), usa el **skill good-morning** (`.cursor/skills/good-morning/SKILL.md`) o el comando **morning-routine**.
