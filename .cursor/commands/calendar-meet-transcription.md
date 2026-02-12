# Calendario: Meet y transcripciones

Comandos y reglas para **añadir videollamadas Meet** a citas y **activar transcripciones** (recordatorio en descripción o activación real vía Meet API).

## Requisitos

- **Scope Calendar:** `calendar.events` (añadir Meet a eventos, editar descripción). El setup OAuth (`scripts/setup_oauth.py`) ya lo pide.
- **Scope Meet:** `https://www.googleapis.com/auth/meetings.space.settings` para activar la **transcripción real** en el space de Meet (Meet API). El setup OAuth lo pide desde que se añadió; si el usuario configuró OAuth antes, debe borrar `GOOGLE_REFRESH_TOKEN` del `.env` y volver a ejecutar `scripts/setup_oauth.py` para obtener el scope Meet. Sin este scope se usa solo el recordatorio en la descripción del evento.
- **Google Meet API:** debe estar habilitada en el proyecto de Google Cloud (APIs y servicios → Biblioteca → "Google Meet API").

## Comandos CLI (calendar_lite)

Ejecutar desde la **raíz del proyecto**, con el Python del venv:

```bash
# Mac/Linux
.venv/bin/python -m scripts.calendar_lite [OPCIONES]

# Windows
.venv\Scripts\python.exe -m scripts.calendar_lite [OPCIONES]
```

### Añadir Meet a citas

- **`--add-meet`** – Añade videollamada Google Meet a los eventos del rango que **no** tengan enlace Meet.
  - Por defecto aplica a **todos** los eventos del rango (hoy, semana o `--range`).
  - **`--add-meet-my-events-only`** – Limita a eventos donde el usuario es **organizador o invitado** (recomendado para no modificar citas ajenas).

Ejemplos:

```bash
# Añadir Meet a todas las citas de la semana
.venv/bin/python -m scripts.calendar_lite --week --add-meet

# Solo a citas donde soy organizador o invitado (hoy + recientes)
.venv/bin/python -m scripts.calendar_lite --today --add-meet --add-meet-my-events-only
```

### Activar transcripciones

- **`--add-transcription-reminder`** – En eventos que **ya tengan Meet**:
  1. Si hay scope Meet (`meetings.space.settings`): activa la **transcripción automática** en el space de Meet (Meet API `spaces.patch` con `transcriptionConfig.autoTranscriptionGeneration = ON`).
  2. Si no hay scope Meet: añade en la **descripción** del evento el recordatorio: *"Transcripción: activar al iniciar la reunión en Meet."*
  - Por defecto solo se aplica a eventos donde el usuario es **organizador o invitado**.
  - **`--transcription-all`** – Junto con `--add-transcription-reminder`: aplicar a **todas** las citas del rango que tengan Meet (útil cuando el calendario es compartido o no se detecta al usuario como invitado).

Ejemplos:

```bash
# Activar transcripción solo en citas donde soy organizador/invitado (semana)
.venv/bin/python -m scripts.calendar_lite --week --add-transcription-reminder

# Activar transcripción en TODAS las citas con Meet de la semana (usar cuando pidan "activar en todas las llamadas")
.venv/bin/python -m scripts.calendar_lite --week --add-transcription-reminder --transcription-all

# Añadir Meet donde falte y luego activar transcripción (solo mis citas)
.venv/bin/python -m scripts.calendar_lite --today --add-meet --add-transcription-reminder --add-meet-my-events-only
```

### Leer transcripción (Doc enlazado en el evento)

El evento puede tener el Doc enlazado de dos formas: (1) **adjunto** del evento (p. ej. "Notes - Call..." que Meet añade como attachment con `fileId`/`fileUrl`) o (2) **descripción** del evento con un enlace a docs.google.com / drive.google.com. Desde aquí se buscan ambos y se abre el Doc para mostrar el contenido.

- **`--read-transcription`** – Busca en el calendario un evento del día (por defecto **ayer**) que tenga en la descripción un enlace a Google Docs (`docs.google.com/document/d/...` o `drive.google.com/open?id=...`), abre ese Doc con la API y **imprime el texto**.
- **`--read-transcription-date YYYY-MM-DD`** – Fecha del evento (por defecto: ayer).
- **`--read-transcription-client CLIENTE`** – Filtrar por cliente (ej: `mcr`).

**Requisitos:** Google Docs API activada en GCP y scope `documents.readonly` en el token (si el token se creó antes, re-ejecutar `scripts/setup_oauth.py`).

Ejemplos:

```bash
# Transcripción de la call de ayer con MCR
.venv/bin/python -m scripts.calendar_lite --read-transcription --read-transcription-client mcr

# Fecha concreta
.venv/bin/python -m scripts.calendar_lite --read-transcription --read-transcription-date 2026-02-11 --read-transcription-client mcr
```

**Atajo (script):** `scripts/read_transcription_from_calendar.py` hace lo mismo (usa `calendar_lite.read_transcription_for_date`). Ej.: `.venv/bin/python scripts/read_transcription_from_calendar.py --client mcr --date 2026-02-11`

### Rango de fechas

- **`--today`** (por defecto si no se indica otro) – Hoy y últimos 7 días.
- **`--week`** – Semana actual (UTC).
- **`--range SPEC`** – `today`, `this_week`, `next_week` o `YYYY-MM-DD:YYYY-MM-DD`.

### Calendario

- **`--calendar NOMBRE`** – Usar solo ese calendario por nombre (prioritario sobre `CALENDAR_NAME` y `config/calendar.yaml`).

## Rutina morning (run_morning.py)

En cada ejecución del morning, **después** de listar el calendario:

1. **Meet:** Se añade videollamada Meet a las citas de **hoy y últimos 7 días** donde el usuario es organizador o invitado y **no** tienen Meet.
2. **Transcripción:** En las citas que **ya tengan Meet** (incluidas las recién creadas) y donde sea organizador o invitado, se activa la transcripción (Meet API si hay scope; si no, recordatorio en la descripción).

Mensajes esperados:

- `Meet – Añadida videollamada a N cita(s).`
- `Transcripción – Recordatorio añadido en N cita(s) con Meet.` (o equivalente si se usa Meet API)

Si falta el scope `calendar.events`, estas acciones se omiten sin fallar. Si falta el scope Meet, solo se usa el recordatorio en la descripción.

## Reglas para el agente

- Al guiar o ejecutar **añadir Meet** o **transcripción**, usar siempre el Python del venv (`.venv/bin/python` en Mac/Linux, `.venv\Scripts\python.exe` en Windows) desde la raíz del proyecto.
- Para **solo mis citas** (Meet), recomendar o usar **`--add-meet-my-events-only`** con `--add-meet`.
- Cuando el usuario pida **activar transcripciones en todas las llamadas** (o en todas las citas con Meet del calendario), usar **`--add-transcription-reminder --transcription-all`** para aplicar a todas las citas del rango que tengan Meet, sin filtrar por organizador/invitado.
- La **transcripción real** (Meet API) requiere que el usuario haya concedido el scope `meetings.space.settings` (re-ejecutar `setup_oauth.py` con ese scope si se desea). En otro caso el comportamiento por defecto es el recordatorio en la descripción.
