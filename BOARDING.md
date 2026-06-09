# Configuración paso a paso (boarding)

Esta guía te lleva de cero a tener el morning routine funcionando, usando Cursor y el chat. **No hace falta que sepas usar la terminal:** el asistente ejecutará los comandos por ti y te pedirá la información paso a paso.

## Paso 1: Abrir el proyecto en Cursor

1. Abre Cursor (el editor de código).
2. Menú **File → Open Folder** (o **Archivo → Abrir carpeta**).
3. Elige la carpeta **morning-brain-starter** (donde está este README).

## Paso 2: Abrir el chat

1. Pulsa **Ctrl+L** (Windows/Linux) o **Cmd+L** (Mac) para abrir el panel del chat.
2. O usa el icono de chat en la barra lateral.

## Paso 3: Pedir ayuda para configurar

En el chat escribe algo como:

- "Quiero configurar el morning routine"
- "Sigue el procedimiento de boarding"
- "Ayúdame a configurar este proyecto paso a paso"

El asistente hará lo siguiente **por ti** (sin pedirte que copies comandos):

- Comprobar si tienes Python instalado (él ejecuta la comprobación). Si no lo tienes, te dirá cómo descargarlo e instalarlo y te esperará; cuando estés listo, seguirá.
- Crear un **entorno virtual (venv) solo para este proyecto** (carpeta `.venv` en la raíz) e instalar ahí las dependencias. Así todo queda aislado del resto de tu sistema.
- **Crear el fichero de credenciales** `resources/secrets/.env` a partir del ejemplo.
- Pedirte que **rellenes tú** el .env con los datos de Google, **uno por uno**: primero el ID de cliente, luego el secret. Te dirá que los escribas **directamente en el fichero** (no en el chat). ℹ️ **Seguridad:** no te pedirá que pegues credenciales aquí; nunca pegues claves, tokens ni secretos en un LLM en la nube como este chat. ℹ️ **Recomendación:** crear un proyecto nuevo en Google Cloud solo para esto. ℹ️ Si no tienes proyecto en Google Cloud, te dará un enlace y te indicará que actives en ese proyecto la **Calendar API**, la **Gmail API** y la **Google Docs API** (para transcripciones): [Crear proyecto y credenciales OAuth en Google Cloud](https://developers.google.com/workspace/guides/create-credentials).
- **Preguntarte si quieres configurar Asana** (para listar tareas del día). Si sí, al ejecutar el asistente te pedirá en la terminal que pegues tu token de Asana (no en el chat).
- Ejecutar el asistente de configuración (OAuth): te pedirá permiso, se abrirá el navegador para que inicies sesión con Google. **El token se crea para Calendar y Gmail a la vez**, así no tienes que repetir el proceso. El token de refresco se guarda solo.
- Preguntarte si quieres configurar bitácoras por cliente y, si sí, ayudarte con `config/clients.yaml`.
- **Preguntarte qué calendarios quieres que revise el morning** (nombres exactos como en Google Calendar). Los guarda en `config/calendar.yaml`; a partir de entonces el morning solo usa esos. Si dices "solo el principal" o "ninguno", se usa el calendario principal.
- **Ejecutar el morning una primera vez** para comprobar que todo va bien (no tendrás que ejecutar nada tú).

## Opcional: alertas GA4/GSC

Si quieres el módulo de anomalías (ver [docs/ANOMALIES.md](docs/ANOMALIES.md)):

- **Demo sin APIs extra:** el asistente puede ejecutar `seed-demo` + run sintético con el cliente ficticio Tycho.
- **Live:** activar Analytics Data API y Search Console API en Google Cloud y regenerar OAuth (`scripts/setup_oauth.py --regenerate`).

## Qué esperar

- **Emojis en cada paso:** el asistente usará emojis para que veas de un vistazo qué está haciendo (🐍 Python, 📦 entorno/dependencias, 🔐 credenciales, 🌐 conexión Google, 📋 Asana, 📅 morning, ✅ listo, ❌ error, 🎉 fin).
- **✅ / ❌:** **✅** cuando un paso se complete bien y **❌** cuando algo falle.
- **ℹ️:** notas informativas (enlaces, aclaraciones).
- **Él ejecuta la terminal:** no te pedirá que pegues comandos (salvo que debas instalar Python tú mismo si no lo tienes).
- **Navegador:** al configurar Google, se abrirá el navegador para que inicies sesión.
- **Pausas:** te pedirá cada dato (por ejemplo cada credencial) y parará hasta que respondas; luego recordará en qué paso seguís.

Si algo falla (verás **❌**), describe en el chat el mensaje de error o lo que ves y el asistente te ayudará a corregirlo.
