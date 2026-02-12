# Actualizar bitácoras (morning-brain-starter)

## Cuándo usarlo

Cuando el usuario pida **actualizar las bitácoras**, **escribir en la bitácora**, **añadir entradas a bitácora** o ejecutar solo el **paso de bitácoras** de la rutina matinal en este proyecto.

## Cómo funciona el proceso

La actualización de bitácora **añade líneas** a `context/clients/<cliente>/bitacora.md` por cliente. No reescribe el fichero: hace append de nuevas entradas. Evita duplicados: si la misma línea ya existe, no se vuelve a escribir.

**Matcheo a cliente:** se usa `config/clients.yaml`. Cada cliente tiene una lista de substrings (nombre de cliente, proyecto, etc.). Cualquier texto que se matchea (título del evento, asunto/remitente del email, nombre del proyecto de Asana) asigna la entrada a ese cliente. Los clientes cuyo nombre empieza por `_` se ignoran.

**Orden de ejecución interno:** el script obtiene calendario, Asana, email y transcripciones del día anterior; luego procesa eventos, emails, tareas Asana y transcripciones, y para cada ítem que matchea un cliente hace append a su `bitacora.md`.

---

## Fuentes de datos que se usan

### 1. Eventos de calendario (reuniones)

- **Origen:** Google Calendar. Eventos de **hoy** y de los **últimos 7 días** (misma llamada que en el paso 1 de la rutina matinal).
- **Datos usados:** `summary` (título), `start` (fecha), `attendees` (invitados).
- **Línea en bitácora:** `- **YYYY-MM-DD** Título – invitado1, invitado2, ...`
- **Matcheo:** por título del evento contra los substrings del cliente en `config/clients.yaml`.

### 2. Emails (Gmail)

- **Origen:** Gmail (o datos demo si existe `config/demo_gmail_fake.yaml`). Configuración en `config/email.yaml` (label, max_messages).
- **Datos usados:** `subject`, `from`, `date`.
- **Línea en bitácora:** `- **YYYY-MM-DD** Email: asunto (remitente)`
- **Matcheo:** por asunto + remitente contra los substrings del cliente.

### 3. Tareas de Asana

- **Origen:** Asana. Tareas con **due_date = hoy** asignadas al usuario (o las del proyecto configurado en `ASANA_INBOX_PROJECT_GID`).
- **Datos usados:** `name`, `due_on`, `project_name`, **`completed`** (estado de la tarea).
- **Línea en bitácora:** `- **YYYY-MM-DD** Tarea [hecha]: nombre (proyecto: …)` o `Tarea [pendiente]: ...` según el estado en Asana.
- **Matcheo:** por nombre del proyecto contra los substrings del cliente.

**Resumen:** la bitácora usa **eventos de calendario**, **emails recientes**, **tareas de Asana de hoy** y **transcripciones del día anterior**. El script que orquesta las fuentes y escribe en las bitácoras es `scripts/morning_step_bitacora.py` (que usa `scripts/bitacora_append.py` para el append).

### 4. Transcripciones del día anterior

- **Origen:** Ficheros en `context/clients/<cliente>/projects/<proyecto>/meetings/transcripcion-YYYY-MM-DD-*.md`. El script filtra por **fecha = ayer** (día anterior al de ejecución).
- **Datos usados:** fecha del nombre del fichero, cliente y proyecto por ruta, título desde la primera línea del markdown (opcional).
- **Línea en bitácora:** `- **YYYY-MM-DD** Transcripción: título o slug (proyecto: …)`.
- **Matcheo:** el cliente viene de la ruta (`context/clients/<cliente>/...`), no de `config/clients.yaml`.

---

## Comando para ejecutar

Desde la **raíz del proyecto**, con `.venv/bin/python` (o `python3`):

```bash
.venv/bin/python scripts/morning_step_bitacora.py
```

No uses solo `scripts/bitacora_append.py`: ese módulo no obtiene los datos de calendario, Asana ni email; solo expone funciones que reciben listas. El paso completo es siempre `morning_step_bitacora.py`.

**Salida esperada:** mensaje del tipo "Bitácoras – Añadidas entradas para: [clientes] (reuniones: N, email: N, Asana: N, transcripciones: N)" o "Bitácoras – Sin reuniones, emails, tareas ni transcripciones que matcheen clientes."

---

## Relación con la rutina matinal

Este paso es el **paso 4** de la rutina de buenos días. La rutina completa está en el **skill good-morning** (`.cursor/skills/good-morning/SKILL.md`) y en el comando **morning-routine** (`.cursor/commands/morning-routine.md`). Si el usuario pide solo “actualizar bitácoras”, ejecuta este skill/comando; si pide “rutina matinal”, sigue el good-morning skill y en el paso 4 usará este proceso.
