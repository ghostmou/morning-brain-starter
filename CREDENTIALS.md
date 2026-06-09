# Credenciales

Todas las variables se definen en `resources/secrets/.env`. No subas ese archivo ni compartas su contenido.

## Obligatorio (Google Calendar)

ℹ️ **Recomendación:** Crea un **proyecto nuevo en Google Cloud** solo para este uso (morning-brain-starter). Así mantienes las credenciales y las APIs separadas de otros proyectos.

ℹ️ **Si aún no tienes proyecto ni credenciales en Google Cloud:** [Crear proyecto y credenciales OAuth en Google Cloud](https://developers.google.com/workspace/guides/create-credentials). En ese proyecto, **activa estas APIs** (APIs y servicios → Biblioteca): **Google Calendar API**, **Gmail API**, **Google Docs API** (transcripciones en Drive) y **Google Meet API** (para activar transcripción en el space de Meet desde el script). Luego: Crear credenciales → ID de cliente OAuth 2.0, tipo "Aplicación de escritorio".

| Variable | Descripción | Dónde obtenerla |
|----------|-------------|------------------|
| `GOOGLE_CLIENT_ID` | ID de cliente OAuth 2.0 | Google Cloud Console → tu proyecto → APIs y servicios → Credenciales → Crear credenciales → ID de cliente OAuth 2.0 (tipo "Aplicación de escritorio") |
| `GOOGLE_CLIENT_SECRET` | Secret del cliente OAuth | Mismo lugar; se muestra al crear el ID de cliente |
| `GOOGLE_REFRESH_TOKEN` | Token de refresco | Se obtiene al ejecutar `python scripts/setup_oauth.py` la primera vez (abre el navegador para que inicies sesión con Google) |

ℹ️ APIs a activar en el proyecto: **Google Calendar API**, **Gmail API**, **Google Docs API** y **Google Meet API** (esta última para poder activar la transcripción en citas con Meet desde el script).

## Opcional (alertas GA4 + Search Console)

Si usas el módulo de **anomalías matinales** (`docs/ANOMALIES.md`), activa también:

- **Google Analytics Data API** (lectura GA4)
- **Google Search Console API** (lectura GSC)

Regenera el token OAuth para incluir los scopes nuevos:

```bash
.venv/bin/python scripts/setup_oauth.py --regenerate
```

Comprobar:

```bash
.venv/bin/python -m scripts.anomaly_detection.cli --mode test-auth
```

No hace falta variable extra en `.env`: se reutilizan `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET` y `GOOGLE_REFRESH_TOKEN`.

ℹ️ **Leer transcripciones desde Calendar:** el script `scripts/read_transcription_from_calendar.py` obtiene la call de ayer (o la fecha que indiques), busca en la descripción del evento un enlace a Google Docs y muestra el contenido. Necesita el scope **documents.readonly**. Si generaste el token antes de que se añadiera este scope, vuelve a ejecutar `scripts/setup_oauth.py` para que el token incluya acceso a Docs.

## Opcional (Asana)

| Variable | Descripción | Dónde obtenerla |
|----------|-------------|------------------|
| `ASANA_ACCESS_TOKEN` | Token de acceso personal | Asana → Mi perfil (icono) → Configuración → Aplicaciones → Token de acceso personal. Crear y copiar el token. |
| `ASANA_WORKSPACE_GID` | GID del workspace | En Asana, al cambiar de workspace la URL incluye el número (ej. `.../0/1234567890/...`). O con la API: `GET https://app.asana.com/api/1.0/workspaces` (con tu token) y copia el `gid` del workspace que uses. Si no lo pones, se usa el primero de la cuenta. |
| `ASANA_INBOX_PROJECT_GID` | GID del proyecto "My Tasks" / inbox | En Asana, abre **My Tasks** (Mis tareas). La URL tiene la forma `.../0/1234567890/...` — ese número es el GID del proyecto. Si no lo pones, se listan todas las tareas asignadas a ti en el workspace con fecha hoy. |
| `ASANA_USER_NAME` | Tu nombre para el resumen | Asana → Mi perfil: aparece tu nombre. Opcional; sirve para mostrar "Tareas de [nombre]" en el morning. |
| `ASANA_TEAM_GID` | GID del team (solo para scripts que crean proyectos) | Opcional. Si usas `scripts/asana_seed_tasks.py` para crear proyectos de cliente y tu workspace es organización, pon aquí el GID de un team donde seas miembro completo (aparece en la URL del team en Asana). Si no, crea los proyectos Acme, MCR, Mao-Kwikowski, Rocinante y Tycho a mano y ejecuta el script. |

Si no defines `ASANA_ACCESS_TOKEN`, el morning no intentará conectar con Asana; seguirá funcionando con Calendar y bitácoras.

## Opcional (Gmail)

Gmail usa el mismo OAuth de Google. El token que generas con `setup_oauth.py` ya incluye Calendar y Gmail. No hace falta una variable extra; solo tener activada la **Gmail API** en el proyecto de Google Cloud.

## Variable de entorno opcional

- `SECRETS_DIR`: ruta absoluta al directorio donde está tu `.env`. Si no se define, se usa `resources/secrets` dentro del proyecto.

## Seguridad

- No subas `resources/secrets/.env` a ningún repositorio.
- No pegues tokens ni secretos en el chat ni en archivos que sí se suban.
- Si crees que has expuesto un token, revócalo o regenera uno nuevo en Google/Asana.
