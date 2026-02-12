# Good morning (morning-brain-starter)

## Cuándo usarlo

Cuando el usuario pida ejecutar la **rutina matinal**, el **morning routine**, un **resumen del día** o **reuniones de hoy** en el contexto de este proyecto (morning-brain-starter).

## Comportamiento en CLI (amabilidad e ilustración)

Al ejecutar el morning routine paso a paso en la terminal:

1. **Anuncia cada paso antes de ejecutarlo.** Di en una frase breve qué vas a hacer (p. ej. «Voy a revisar tu calendario de hoy y dejar las calls listas con Meet y transcripción») y luego lanza el comando. Así el usuario ve qué está pasando en cada momento.
2. **Tono cercano y positivo.** Añade una frase breve y amable cuando anuncies el paso (sin exagerar): que se note que estás acompañando el inicio del día. La información principal —qué paso se ejecuta— debe seguir clara y concisa.

Ejemplo de estilo al anunciar: *«Ahora miro tu agenda de hoy y preparo las videollamadas con Meet y recordatorio de transcripción.»* → ejecutar comando. No hace falta repetir el comando en texto; con anunciar el paso y ejecutarlo basta.

## Qué hace

- **Paso 1 – Calendario:** eventos de hoy y recientes; añade Meet y activa transcripciones en calls del día.
- **Paso 2 – Asana (mover ayer → hoy):** tareas pendientes con fecha de ayer se pasan a hoy para no perderlas.
- **Paso 3 – Asana (listar/ordenar hoy):** tareas con due_date = hoy; se añaden al proyecto My tasks (`ASANA_INBOX_PROJECT_GID` en `.env`), se ordenan según `config/asana_order.yaml` y se listan.
- **Paso 4 – Email (opcional):** emails recientes (si `config/email.yaml`).
- **Paso 5 – Transcripciones:** busca calls de ayer con Doc enlazado e importa a `context/.../meetings/transcripcion-*.md`.
- **Paso 6 – Asana (tareas realizadas ayer → bitácora):** recoge las tareas completadas el día anterior en Asana, lee su descripción e incorpora una entrada (y la descripción) en la bitácora del cliente, igual que con las transcripciones.
- **Paso 7 – Bitácoras:** entradas en `context/clients/<cliente>/bitacora.md` (reuniones, emails, Asana hoy, transcripciones, tareas realizadas ayer). Ver skill bitacora-update.

Cada acción tiene su **llamada CLI exacta**; no hace falta usar `run_morning.py`.

---

## Llamadas CLI por paso (desde la raíz)

Cada paso tiene una descripción de lo que hace; la **llamada CLI** indicada es la que ejecuta esa acción.

**Paso 1 – Calendario (hoy + Meet + transcripciones)**  
Obtiene los eventos de hoy y de los últimos días desde Google Calendar, muestra un resumen y, en las citas donde eres organizador o invitado: añade videollamada Meet si no la tienen y activa el recordatorio de transcripción en las que ya tienen Meet. Así las calls del día quedan listas para grabar transcripción.  
*Anuncio sugerido:* «Reviso tu agenda de hoy y dejo las videollamadas listas con Meet y recordatorio de transcripción.»  
La siguiente llamada CLI hace eso:

```bash
.venv/bin/python scripts/calendar_lite.py --today --add-meet --add-meet-my-events-only --add-transcription-reminder
```

**Paso 2 – Asana (mover tareas de ayer a hoy)**  
Busca en Asana las tareas asignadas a ti con fecha de vencimiento **ayer** y que siguen pendientes (no completadas), y les cambia la fecha a **hoy**. Así las tareas que quedaron colgadas ayer pasan a tu día actual y no se pierden. Solo tiene efecto si está configurado `ASANA_ACCESS_TOKEN` en `.env`.  
*Anuncio sugerido:* «Pasando las tareas que quedaron de ayer a hoy para que no se te escape ninguna.»  
La siguiente llamada CLI hace eso:

```bash
.venv/bin/python scripts/asana_lite.py --move-yesterday-to-today
```

**Paso 3 – Asana (listar y ordenar tareas de hoy)**  
Obtiene todas tus tareas con fecha **hoy** en el workspace. Si en `.env` está definido **`ASANA_INBOX_PROJECT_GID`** (el proyecto o sección “My tasks”), el script **añade** al ese proyecto cualquier tarea de hoy que aún no esté en él; así todas las tareas del día quedan en la sección indicada. Luego las ordena según `config/asana_order.yaml` y las muestra. Necesita `ASANA_ACCESS_TOKEN` y, para que añada a My tasks, `ASANA_INBOX_PROJECT_GID` (y opcionalmente `ASANA_WORKSPACE_GID`).  
*Anuncio sugerido:* «Listando y ordenando tus tareas de hoy para que tengas el día claro.»  
La siguiente llamada CLI hace eso:

```bash
.venv/bin/python scripts/asana_lite.py
```

**Paso 4 – Email**  
Obtiene los emails recientes (bandeja configurada en `config/email.yaml`) y los muestra para contexto. Solo se ejecuta si existe `config/email.yaml` y Gmail está configurado.  
*Anuncio sugerido:* «Echando un vistazo a los correos recientes para que no te pierdas nada.»  
La siguiente llamada CLI hace eso:

```bash
.venv/bin/python scripts/email_lite.py
```

**Paso 5 – Transcripciones (importar ayer)**  
Busca en el calendario las calls del día anterior que tengan un Google Doc enlazado (p. ej. notas o transcripción de Meet), descarga el contenido de cada Doc y lo guarda en `context/clients/<cliente>/projects/<proyecto>/meetings/transcripcion-YYYY-MM-DD-<slug>.md`. Así el contexto local tiene las transcripciones de ayer sin tocar Gmail/Calendar manualmente.  
*Anuncio sugerido:* «Importando las transcripciones de las calls de ayer a tu contexto.»  
La siguiente llamada CLI hace eso:

```bash
.venv/bin/python scripts/calendar_lite.py --import-transcriptions
```
Opcional: `--import-transcriptions-date YYYY-MM-DD` para otra fecha.

**Paso 6 – Asana (tareas realizadas ayer → bitácora)**  
Recoge en Asana las tareas que **completaste el día anterior** (realizadas ayer), lee el nombre y la descripción (notes) de cada una y añade en la bitácora del cliente correspondiente una línea con la tarea realizada y, debajo, un resumen de la descripción (igual que se hace con las transcripciones). El cliente se deduce por el nombre del proyecto o de la tarea según `config/clients.yaml`. Solo tiene efecto si está configurado `ASANA_ACCESS_TOKEN`.  
*Anuncio sugerido:* «Pasando lo que cerraste ayer en Asana a la bitácora de cada cliente.»  
La siguiente llamada CLI hace eso:

```bash
.venv/bin/python scripts/asana_lite.py --completed-yesterday-to-bitacora
```

**Paso 7 – Bitácoras**  
Obtiene de nuevo eventos (calendario), tareas de hoy (Asana) y emails (Gmail), importa si hace falta las transcripciones de ayer, recoge las tareas realizadas ayer y añade entradas en `context/clients/<cliente>/bitacora.md` por cada reunión, email, tarea, transcripción o tarea realizada que matchee con los clientes de `config/clients.yaml`. Un solo comando actualiza todas las bitácoras.  
*Anuncio sugerido:* «Actualizando las bitácoras de tus clientes con todo lo del día.»  
La siguiente llamada CLI hace eso:

```bash
.venv/bin/python scripts/morning_step_bitacora.py
```
*Nota:* el paso 7 también importa transcripciones y procesa tareas realizadas ayer; los pasos 5 y 6 sirven para ejecutar solo esa parte si lo necesitas.

---

## Resumen (copiar/pegar)

CWD = raíz del proyecto.

```bash
.venv/bin/python scripts/calendar_lite.py --today --add-meet --add-meet-my-events-only --add-transcription-reminder
.venv/bin/python scripts/asana_lite.py --move-yesterday-to-today
.venv/bin/python scripts/asana_lite.py
.venv/bin/python scripts/email_lite.py
.venv/bin/python scripts/calendar_lite.py --import-transcriptions
.venv/bin/python scripts/asana_lite.py --completed-yesterday-to-bitacora
.venv/bin/python scripts/morning_step_bitacora.py
```

**Atajo (todo en uno):**
```bash
.venv/bin/python run_morning.py
```

**Ver comandos sin ejecutar:**
```bash
.venv/bin/python run_morning.py --show-cli
```

**Solo un paso:**
```bash
.venv/bin/python run_morning.py --step 3
```
(Pasos 1–7.)

---

## Dónde está todo

- **Skill:** `.cursor/skills/good-morning/SKILL.md`
- **Comando:** `.cursor/commands/morning-routine.md`
- **Scripts:** `scripts/calendar_lite.py`, `scripts/asana_lite.py`, `scripts/email_lite.py`, `scripts/morning_step_bitacora.py`
- **Orquestador:** `run_morning.py` (opcional)
