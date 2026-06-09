# Morning Brain Starter

Una versión ligera de rutina matinal: resumen de reuniones desde Google Calendar, bitácoras por cliente y, opcionalmente, tareas (Asana) y contexto de emails (Gmail).

Este proyecto está basado en las rutinas mañaneras de [Alfonso Moure](https://www.alfonsomoure.com), CEO y consultor de SEO técnico, WPO y analítica digital técnica de [bigmomo](https://bigmomo.com).

> ### 📬 Suscríbete a mi newsletter
>
> En mi Substack comparto cómo construir tu propio stack de IA para **SEO, automatización, analítica y productividad**: rutinas matinales, agentes, detección de anomalías y trucos para liberarte de las tareas rutinarias y centrarte en lo importante.
>
> ### 👉 [**Suscríbete aquí »**](https://alfonsomoure.substack.com)
>
> *¿Quieres ver de dónde sale el detector de anomalías de este repo? Empieza por el post ["Tu dashboard te miente: detección de anomalías con IA"](https://alfonsomoure.substack.com/p/deteccion-de-anomalias-con-ia).*

## Qué hace

- **Resumen de reuniones:** eventos de hoy y recientes desde tu Google Calendar.
- **Bitácoras por cliente:** las reuniones se van acumulando en un archivo por cliente (según configuración).
- **Opcional – Tareas:** si usas Asana, puedes listar y ordenar tus tareas del día.
- **Opcional – Emails:** si usas Gmail, puedes sincronizar emails recientes como contexto adicional.
- **Opcional – Alertas GA4/GSC:** detección de anomalías diarias e informe HTML por cliente (modo demo sintético sin APIs o live con OAuth). Ver [docs/ANOMALIES.md](docs/ANOMALIES.md).

**Solo Google Calendar es obligatorio.** El proyecto funciona igual con solo Calendar: reuniones de hoy, recientes y bitácoras. Asana y Gmail son opcionales.

## Si vienes de GitHub: tu copia del proyecto

Lo primero que conviene hacer es tener tu propia copia. Así puedes personalizar cosas sin miedo a tocar el “original” y, si solo quieres usarlo en tu equipo, no tienes por qué publicar nada en internet.

Tienes dos opciones sencillas:

**Opción 1: Hacer un fork (recomendado si quieres personalizar o contribuir)**  
Un fork es una copia del repositorio en tu cuenta de GitHub. Puedes cambiar lo que quieras en tu copia; si algún día quieres proponer mejoras al proyecto original, ya tienes el fork listo.

1. En la página del proyecto en GitHub, haz clic en **Fork** (arriba a la derecha).
2. Elige tu cuenta; GitHub creará una copia bajo tu usuario (por ejemplo `tu-usuario/morning-brain-starter`).
3. En tu equipo, clona **tu fork** (no el repositorio original):
   ```bash
   git clone https://github.com/tu-usuario/morning-brain-starter.git
   cd morning-brain-starter
   ```
4. A partir de aquí, sigue la [Configuración guiada](#configuración-guiada-recomendada) o el [Setup rápido](#setup-rápido-manual).

**Opción 2: Solo usarlo en local (sin fork)**  
Si no quieres tener el proyecto en tu cuenta de GitHub y solo usarlo en tu ordenador:

1. En la página del repo en GitHub: **Code** → **Download ZIP**, y descomprime donde quieras; o clona una vez (sin hacer fork):
   ```bash
   git clone https://github.com/<cuenta>/morning-brain-starter.git
   cd morning-brain-starter
   ```
   Sustituye `<cuenta>` por el usuario o organización donde esté alojado el repo.
2. Si clonaste con git, puedes usar git en local para tus cambios; no hace falta configurar un remoto ni hacer push a ningún sitio.
3. Sigue la [Configuración guiada](#configuración-guiada-recomendada) o el [Setup rápido](#setup-rápido-manual).

## Requisitos

- **Python 3.9 o superior.** Si no lo tienes: [Descargar Python](https://www.python.org/downloads/) (instalador oficial). En Windows, marca la opción **"Add Python to PATH"** durante la instalación. Para comprobar: `python --version` o `python3 --version` (en Mac/Linux a menudo solo existe `python3`; si `python` da "command not found", usa `python3`).
- Cuenta de Google (para Calendar)
- Opcional: cuenta de Asana (para tareas)
- Opcional: Gmail (misma cuenta Google) para sincronización de emails

## Configuración guiada (recomendada)

Si prefieres que te guíen paso a paso desde Cursor con el chat, abre esta carpeta en Cursor, abre el chat (Ctrl+L o Cmd+L) y escribe algo como: **"Quiero configurar el morning routine"** o **"Sigue el procedimiento de boarding"**. El asistente creará un entorno virtual (`.venv`) solo para este proyecto, instalará las dependencias y te guiará con las credenciales paso a paso; no hace falta que uses la terminal tú mismo.

Ver también: [BOARDING.md](BOARDING.md) para la guía escrita.

## Setup rápido (manual)

1. Clona o copia esta carpeta en tu equipo.
2. Crea un entorno virtual (recomendado) e instala dependencias:
   ```bash
   python3 -m venv .venv   # o: python -m venv .venv (en Windows suele ser python)
   .venv\Scripts\activate   # Windows
   # o: source .venv/bin/activate   # Mac/Linux
   pip install -r requirements.txt
   ```
   Si `python` no existe en tu sistema (común en macOS), usa `python3` en los comandos.
3. Copia el fichero de ejemplo de credenciales y rellénalo:
   ```bash
   mkdir -p resources/secrets
   cp .env.example resources/secrets/.env
   ```
   Qué poner en cada variable: [CREDENTIALS.md](CREDENTIALS.md).
4. Ejecuta el asistente de configuración (Google es obligatorio; Asana y Gmail se pueden omitir):
   ```bash
   python3 scripts/setup_oauth.py   # o .venv/bin/python scripts/setup_oauth.py (Mac/Linux)
   ```
5. Si quieres bitácoras por cliente, edita `config/clients.yaml` con los nombres de tus clientes y cómo reconocerlos en el título de los eventos.

## Ejecutar el morning

Desde la raíz del proyecto. Si configuraste con el boarding, usa el Python del venv:

```bash
.venv/bin/python run_morning.py   # Mac/Linux
.venv\Scripts\python.exe run_morning.py   # Windows
```

O activa el venv (`source .venv/bin/activate` o `.venv\Scripts\activate`) y luego `python run_morning.py`.

Verás un resumen de reuniones de hoy, recientes, tareas (si configuraste Asana), emails (si configuraste Gmail) y las bitácoras actualizadas.

### Calendario a usar

Por defecto se usa el calendario principal o los listados en `config/calendar.yaml` (o `config/calendar.local.yaml`). Para fijar **un solo calendario por nombre** sin tocar la config:

- En `.env`: `CALENDAR_NAME=Nombre exacto del calendario`
- Por CLI: `python3 -m scripts.calendar_lite --calendar "Nombre exacto"` (o `python` si está en el PATH). Con las opciones siguientes.

### Opciones del CLI de calendario (`python3 -m scripts.calendar_lite`)

- **`--range SPEC`** – Citas en un rango: `today`, `this_week`, `next_week`, o `YYYY-MM-DD:YYYY-MM-DD`.
- **`--week`** / **`--today`** – Esta semana (UTC) o hoy + recientes (por defecto).
- **`--attendees`** – Ver invitados y estado (aceptado/rechazado/pendiente).
- **`--match-clients`** – Cruzar títulos con clientes y proyectos (`config/clients.yaml`, `matches.yaml`).
- **`--summary`** – Resumir agenda usando las descripciones de los eventos.
- **`--respond accept|decline|tentative EVENT_ID`** – Aceptar o rechazar una invitación (requiere scope `calendar.events`; el setup OAuth ya lo pide).
- **`--add-meet`** – Añadir videollamada Google Meet a los eventos del rango que no la tengan. Opción **`--add-meet-my-events-only`** para limitar a citas donde eres organizador o invitado.
- **`--add-transcription-reminder`** – Activar transcripción en eventos con Meet: por defecto solo en citas donde eres organizador o invitado; con **`--transcription-all`** se aplica a todas las citas del rango que tengan Meet. Si tienes el scope Meet (`meetings.space.settings`), se activa la transcripción en el space (Meet API); si no, se añade un recordatorio en la descripción.
- **`--which-calendar`** – Mostrar solo el nombre del calendario en uso.

Las transcripciones de Meet se guardan en Drive. Con el scope **meetings.space.settings** (y Google Meet API activada en GCP) el script puede **activar la transcripción** en el space de Meet para citas que ya tengan enlace; sin ese scope se añade un recordatorio en la descripción. La **rutina morning** (`run_morning.py`) añade Meet donde falte y activa transcripción (o recordatorio) en las que ya tengan Meet. Ver `.cursor/commands/calendar-meet-transcription.md` para todos los comandos y requisitos.

## Reset configuración

Para borrar credenciales, tokens y el entorno virtual (`.venv`) y dejar el proyecto como recién clonado (por ejemplo para cambiar de cuenta o que otra persona configure desde cero):

```bash
python3 scripts/reset_config.py   # o python, o .venv/bin/python
```

Elimina el contenido de `resources/secrets/` y el directorio `.venv`. No borra la demo: mantiene `config/demo/` y (re)crea `config/demo_gmail_fake.yaml` para que el circuito de emails fake siga disponible. Luego puedes volver a configurar con el boarding o con `python3 scripts/setup_oauth.py`.

## Alertas GA4/GSC (demo rápido)

Sin configurar APIs adicionales puedes probar el detector con datos ficticios del cliente demo **Tycho**:

```bash
.venv/bin/python -m scripts.anomaly_detection.cli --mode seed-demo
.venv/bin/python -m scripts.anomaly_detection.cli --mode run \
  --date 2026-06-05 --synthetic --lab-root . --client-id tycho
```

Abre `output/anomalies/2026-06-05/tycho.html`. Documentación completa: [docs/ANOMALIES.md](docs/ANOMALIES.md).

## Estructura de carpetas

- `resources/secrets/` – Aquí va tu `.env` (no se sube a control de versiones).
- `config/clients.yaml` – Mapeo cliente ↔ títulos de eventos para las bitácoras.
- `config/calendar.yaml` – Nombres de calendarios que revisa el morning (si está vacío, se usa solo el principal). Opcionalmente, en `.env` puedes poner `CALENDAR_NAME=Nombre` para usar un único calendario.
- `config/email.yaml` – Opcional: configuración para sincronizar emails (Gmail).
- `config/demo/` – Emails fake para demo (The Expanse). Si creas `config/demo_gmail_fake.yaml` (gitignored), el morning usa esos en lugar de Gmail real. Ver `config/demo/README.md`.
- `config/asana_order.yaml` – Orden de tareas por día (Lunes–Viernes); criterio en `context/addons/asana-order-by-day.md`.
- `context/clients/<nombre>/bitacora.md` – Bitácora por cliente (se crea al ejecutar).
- `context/clients/<nombre>/anomaly_controls.yaml` – Opcional: controles de alertas GA4/GSC.
- `demo-data/<cliente>/` – CSV sintéticos para pruebas sin API.
- `data/google_core_updates.csv` – Contexto de actualizaciones Google (sync opcional).
- `scripts/anomaly_detection/` – Pipeline de detección de anomalías.
- `docs/ANOMALIES.md` – Guía del módulo de alertas.

> **Nota:** Recuerda revisar el fichero `LICENSE` del proyecto. El uso de este software se realiza bajo los términos de la licencia indicada; no se ofrecen garantías de ningún tipo y lo utilizas bajo tu propio riesgo.