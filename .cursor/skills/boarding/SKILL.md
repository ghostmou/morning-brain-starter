---
name: boarding
description: Guía paso a paso para configurar el morning routine en morning-brain-starter (Python, venv, credenciales Google, OAuth, Asana, calendarios, primera ejecución). Usar cuando el usuario pida configurar el morning routine, seguir el boarding o preparar el proyecto por primera vez.
---

# Boarding – Configurar morning routine

Cuando el usuario pida **configurar el morning routine** o **seguir el boarding**, guiar paso a paso **solo dentro de morning-brain-starter**. No modificar otros proyectos del workspace.

## Al empezar el boarding

- **Empieza con un saludo breve y agradable.** Usa un emoji de saludo (👋). Agradece que esté usando el proyecto, di que le vas a guiar paso a paso y que no tiene que preocuparse por la terminal. Tono cercano y un poco festivo, sin pasarte. Por ejemplo: "👋 ¡Hola! Gracias por usar el morning-brain-starter. Te voy a guiar paso a paso; yo me encargo de ejecutar lo que haga falta, tú solo confirma cuando te lo pida. 🐍 Empezamos comprobando que tienes Python instalado." Una o dos frases, luego pasa al paso 1.

## Principio general: tú ejecutas, el usuario no

- **No propongas comandos de terminal al usuario.** Asume que no sabe usar la terminal. Ejecuta tú los comandos necesarios (pip install, setup_oauth, run_morning) desde la raíz del proyecto, pidiendo permiso cuando sea apropiado.
- **Excepción:** si Python no está instalado, no puedes instalarlo por él; indícale que lo descargue desde [python.org/downloads](https://www.python.org/downloads/) (y en Windows "Add Python to PATH"), que abra una terminal nueva y que te avise cuando haya terminado. Entonces tú ejecutas `python --version` o `python3 --version` para comprobar.
- **Python en terminal:** en Mac/Linux a menudo solo existe `python3`; si un comando con `python` falla con "command not found", usar **`python3`** (o `.venv/bin/python` si ya existe el venv).

## Información paso a paso, no en bloque

- **Pide la información de uno en uno** y **para para seguir después**, recordando en qué paso estás. Para las credenciales de Google: no pidas que las peguen en el chat; indícales que las escriban **directamente en el fichero** `resources/secrets/.env` y que te confirmen cuando hayan terminado cada una.
- ℹ️ **Seguridad:** No pidas nunca credenciales en el chat. Indica al usuario que no debe pegar claves, tokens ni secretos en un LLM en la nube (como este chat) por razones de seguridad; que use solo el fichero .env en su equipo.
- Al reanudar, di explícitamente en qué paso continuamos (ej.: "Continuamos con el paso 3: ahora escribe el **GOOGLE_CLIENT_SECRET** en el .env, junto a esa variable, guarda y dime cuando esté.").

## Indicadores y emojis en tus respuestas

Usa emojis en los mensajes que dirijas al usuario durante el boarding para que entienda de un vistazo qué está pasando. No abuses; uno o dos por mensaje suelen bastar.

- **✅** – Paso completado correctamente.
- **❌** – Fallo o error; indica cómo corregirlo.
- **ℹ️** – Nota informativa (enlaces, recordatorios, seguridad).
- **🐍** – Python / comprobación de versión.
- **📦** – Entorno virtual o instalación de dependencias.
- **🔐** – Credenciales, .env, datos sensibles.
- **🌐** – OAuth, navegador, conexión con Google.
- **📋** – Asana, tareas o listas.
- **📅** – Calendario, morning, primera ejecución.
- **🎉** – Cierre exitoso (junto con ✅).

## Pasos (qué hace el agente)

### 1. Comprobar Python

- Antes de ejecutar, di algo breve con 🐍, por ejemplo: "🐍 Comprobando que tienes Python instalado..."
- Ejecuta tú en la terminal: **primero** `python3 --version` (en Mac/Linux suele existir; si falla, probar `python --version`). Debe ser 3.9 o superior.
- ✅ Si la versión es correcta, confirma con algo tipo: "✅ Python X.X detectado. Siguiente paso: entorno y dependencias." ❌ Si no está instalado o es antigua: indica con ❌ y que descargue desde python.org, en Windows "Add Python to PATH", terminal nueva, y que te avise cuando esté listo; entonces repite la comprobación.

### 2. Crear venv e instalar dependencias

- Anuncia con 📦, por ejemplo: "📦 Creando el entorno virtual e instalando dependencias..."
- **Crear un entorno virtual solo para este proyecto:** Ejecuta tú desde la raíz: `python3 -m venv .venv` (Mac/Linux; si falla "command not found", probar `python -m venv .venv`). En Windows suele ser `python -m venv .venv`. Así las dependencias no se mezclan con el resto del sistema. ℹ️ El directorio `.venv` queda en la raíz del proyecto y está en `.gitignore`.
- **Instala las dependencias** directamente (no pidas permiso; es seguro): ejecuta tú **usando el pip del venv**: `.venv/bin/pip install -r requirements.txt` (Mac/Linux) o `.venv\Scripts\pip install -r requirements.txt` (Windows). Desde la raíz de morning-brain-starter.
- En todos los pasos siguientes donde ejecutes `python` o scripts, usa el Python del venv: `.venv/bin/python` (Mac/Linux) o `.venv\Scripts\python.exe` (Windows). Por ejemplo: `.venv/bin/python scripts/setup_oauth.py`, `.venv/bin/python run_morning.py`.
- ✅ Si termina bien: "✅ Entorno listo. Ahora vamos con las credenciales de Google." ❌ Si falla, muestra el error y la solución.

### 3. Crear el .env y pedir credenciales de Google (paso a paso)

- Anuncia con 🔐, por ejemplo: "🔐 Vamos con las credenciales de Google. Primero creo el fichero..."
- **Crear el fichero:** Crea tú `resources/secrets/.env` copiando el contenido de `.env.example` (asegúrate de que existe el directorio `resources/secrets/`). Comenta al usuario: "🔐 He creado el fichero de credenciales en `resources/secrets/.env`. Vamos a rellenarlo con tus datos de Google, uno por uno. **Escribe cada valor directamente en ese fichero** (no lo pegues aquí en el chat)."
- ℹ️ **Seguridad:** Di algo como: "ℹ️ No te pido que pegues las credenciales en el chat por seguridad. Nunca pegues claves, tokens ni secretos en un LLM en la nube como este; usa solo el fichero .env en tu equipo."
- **GOOGLE_CLIENT_ID (solo esto primero):** Explica que es el "ID de cliente OAuth 2.0" de tipo "Aplicación de escritorio" en Google Cloud. ℹ️ **Recomendación:** crear un **proyecto nuevo en GCP** solo para este uso (morning-brain-starter). ℹ️ Si no tiene proyecto aún: [Crear proyecto y credenciales OAuth en Google Cloud](https://developers.google.com/workspace/guides/create-credentials). En ese proyecto debe **activar estas APIs** (APIs y servicios → Biblioteca): **Google Calendar API**, **Gmail API**, **Google Docs API** (transcripciones en Drive) y **Google Meet API** (activar transcripción en Meet). Luego crear credenciales → ID de cliente OAuth 2.0, tipo "Aplicación de escritorio". Los **permisos que se pedirán al usuario** en el paso 5 (OAuth) son: ver y editar eventos de Calendar (añadir Meet, aceptar/rechazar), ver correo en Gmail, y configurar Meet (transcripción). Indica que abra `resources/secrets/.env`, escriba el valor junto a `GOOGLE_CLIENT_ID=` (sin espacios extra), guarde el fichero y te confirme cuando esté. **Para aquí** hasta que confirme.
- **GOOGLE_CLIENT_SECRET (solo esto después):** Al reanudar, di por ejemplo: "🔐 Perfecto. Ahora el **GOOGLE_CLIENT_SECRET**: es el 'Secret del cliente' en la misma pantalla de Google Cloud. Escríbelo en el .env junto a `GOOGLE_CLIENT_SECRET=`, guarda y dime cuando esté." **Para aquí** hasta que confirme.
- No pidas GOOGLE_REFRESH_TOKEN; se obtiene en el paso 5 (OAuth).
- ✅ Cuando confirme: "✅ Credenciales de Google en el .env. Siguiente: te pregunto si quieres Asana." ❌ Si algo falla (archivo, permisos), indica la solución.

### 4. Preguntar si quiere Asana

- **Pregunta con 📋** y **para aquí hasta que el usuario responda.** No pases al paso 5 (OAuth) hasta que diga explícitamente sí o no. Por ejemplo: "📋 ¿Quieres configurar Asana para listar tus tareas del día en el morning? Responde sí o no y seguimos."
- Cuando responda **sí**:
  - El **token** lo pedirá el script en la terminal cuando ejecutemos el asistente (paso 5). Se obtiene en Asana → Mi perfil → Configuración → Aplicaciones → Token de acceso personal. Que lo pegue en la terminal, no en el chat.
  - **Opcional pero recomendable:** puede añadir al .env después (o ahora, si lo tiene) estas variables; así el morning usa el workspace y el proyecto correctos. Indica dónde conseguir cada una (o remite a CREDENTIALS.md):
    - **ASANA_WORKSPACE_GID:** en Asana, la URL al cambiar de workspace incluye el número (ej. `.../0/1234567890/...`). O llamar a la API `GET https://app.asana.com/api/1.0/workspaces` con el token y copiar el `gid` del workspace que use. Si no lo pone, se usa el primero de la cuenta.
    - **ASANA_INBOX_PROJECT_GID:** abrir **My Tasks** (Mis tareas) en Asana; en la URL aparece el GID del proyecto (el número en `.../0/1234567890/...`). Si no lo pone, se listan todas las tareas asignadas a él en el workspace con fecha hoy.
    - **ASANA_USER_NAME:** su nombre en Asana (Mi perfil). Opcional; sirve para mostrar "Tareas de [nombre]" en el resumen.
  - Después de explicar, **confirma:** "Cuando estés listo, dime **OK** o **sigo** y ejecuto el asistente de configuración (paso 5)." No ejecutes el paso 5 hasta que diga OK o equivalente.
- Cuando responda **no**, di algo breve (ej. "Perfecto, lo omitimos.") y entonces sí pasa al paso 5 (OAuth para Google).

### 5. OAuth (conectar cuenta Google: Calendar, Meet, Gmail)

- Anuncia con 🌐, por ejemplo: "🌐 Ahora vamos a conectar tu cuenta de Google. Voy a ejecutar el asistente de configuración: se abrirá el navegador para que inicies sesión y autorices los permisos. **El token incluirá:** Calendar (ver y editar eventos, añadir Meet), Meet (activar transcripción en reuniones), Gmail (lectura). ¿Puedo ejecutarlo? Se abrirá el navegador."
- Si acepta, **ejecuta tú** en la terminal con el Python del venv: `.venv/bin/python scripts/setup_oauth.py` (Mac/Linux) o `.venv\Scripts\python.exe scripts/setup_oauth.py` (Windows), desde la raíz. El script escribirá el GOOGLE_REFRESH_TOKEN en el .env. Si el usuario dijo que quería Asana, el script le preguntará en la terminal por el token de Asana.
- **Refrescar el token (si ya tenía uno antiguo):** Si el usuario ya tenía GOOGLE_REFRESH_TOKEN pero le faltan permisos (p. ej. añadir Meet o transcripción), indicar que borre o vacíe la línea `GOOGLE_REFRESH_TOKEN` en `resources/secrets/.env`, guarde, y luego ejecute de nuevo el setup para obtener un token nuevo con todos los permisos: `.venv/bin/python scripts/setup_oauth.py` (Mac/Linux) o `.venv\Scripts\python.exe scripts/setup_oauth.py` (Windows).
- ✅ Si el flujo termina bien: "✅ Google (y Asana si lo configuraste) listo." Si configuró Asana, añade: "ℹ️ Opcional: puedes añadir al .env **ASANA_WORKSPACE_GID**, **ASANA_INBOX_PROJECT_GID** y **ASANA_USER_NAME** para afinar qué workspace y proyecto usar; en CREDENTIALS.md tienes dónde conseguir cada uno." Luego: "¿Quieres configurar bitácoras por cliente?" ❌ Si hay error de login o permisos, indica qué hacer.

### 6. Clientes (bitácoras)

- Pregunta si quiere configurar bitácoras por cliente (mapear eventos del calendario a clientes en `config/clients.yaml`). Puedes usar 📅 o 📋. Si sí: explica brevemente el formato (nombre cliente → substrings en el título del evento) y ofrécete a editar `config/clients.yaml` con los nombres que te indique, o a dejarlo con el ejemplo. Si no, omite. ✅/❌ según corresponda.

### 7. Calendarios a revisar

- **Pregunta con 📅** y **espera la respuesta del usuario antes de seguir.** Por ejemplo: "📅 ¿Qué calendarios quieres que revise el morning? Dime los **nombres exactos** como aparecen en Google Calendar (por ejemplo: 'Trabajo', 'Personal', 'Morning demo'). Si quieres usar solo el calendario principal, di 'solo el principal' o 'ninguno'. Cuando me des la lista, los guardo y el morning solo revisará esos."
- **Para aquí** hasta que responda. Si dice "solo el principal" o "ninguno" o no quiere elegir: deja `config/calendar.yaml` con `calendars: []` (o no lo crees; el código usa primary si está vacío). Si da nombres: escribe o actualiza `config/calendar.yaml` con la lista bajo `calendars:` (formato YAML, por ejemplo `calendars:\n  - Trabajo\n  - Personal`). ℹ️ Los nombres deben coincidir con los de Google Calendar (puede verlos en calendar.google.com en el lateral).
- ✅ Confirma: "✅ Calendarios guardados. A partir de ahora el morning solo revisará esos." Luego pasa al paso 8.

### 8. Primera ejecución del morning

- Anuncia con 📅, por ejemplo: "📅 Voy a ejecutar el morning una primera vez para comprobar que todo funciona." **No propongas un comando;** ejecuta tú en la terminal con el Python del venv: `.venv/bin/python run_morning.py` (Mac/Linux) o `.venv\Scripts\python.exe run_morning.py` (Windows), desde la raíz.
- Muestra o resume la salida al usuario. Explica qué debería ver: eventos de los calendarios elegidos, opcionalmente Asana/email, y líneas en bitácoras si hay match.
- ✅ Si la ejecución termina sin errores. ❌ Si falla, con el error y pasos para corregir.

### Al terminar todos los pasos bien

- Cierra con **✅** y **🎉** y una frase breve de cierre alegre, sin pasarte. Por ejemplo: "✅ 🎉 **¡Listo!** Ya tienes el morning configurado. Cuando quieras, podemos ejecutarlo de nuevo o ajustar clientes/bitácoras." O: "✅ 🎉 **Todo listo.** A partir de ahora el morning está listo para usarse cuando lo necesites." Tono cercano y positivo, una línea.

### Refrescar el token de Google (obtener de nuevo los permisos)

Si el token actual no tiene los permisos necesarios (p. ej. para añadir Meet o activar transcripciones), hay que obtener un token nuevo:

1. En `resources/secrets/.env`, borra o deja vacía la línea `GOOGLE_REFRESH_TOKEN=...` (guarda el fichero).
2. Desde la raíz del proyecto ejecuta:

```bash
.venv/bin/python scripts/setup_oauth.py
```

(En Windows: `.venv\Scripts\python.exe scripts/setup_oauth.py`)

Se abrirá el navegador para que autorices de nuevo; el script guardará el nuevo token en el .env.

---

No ejecutar git init. Al reanudar tras una pausa, indica siempre en qué paso continuáis (con el emoji del paso si aplica, p. ej. 🔐 para credenciales).
