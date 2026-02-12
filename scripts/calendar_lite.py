"""
Eventos de hoy y recientes (ayer o últimos 7 días) desde Google Calendar.
Usa solo los calendarios indicados en config o el nombre pasado por parámetro/env.
No expone lista de calendarios; solo el calendario activo y sus eventos.

Incluye: descripción del evento, invitados (con responseStatus), enlace Meet,
rango de fechas (today, this_week, next_week, YYYY-MM-DD:YYYY-MM-DD),
cruzar con clientes/proyectos, aceptar/rechazar invitaciones (requiere scope
calendar.events), resumir agenda desde descripciones.
Transcripciones: las de Meet se guardan en Drive; la descripción del evento
puede contener enlaces a notas o documentos.
"""

import argparse
import os
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# CWD = project root
_project_root = Path(__file__).resolve().parent.parent
if str(_project_root) not in os.sys.path:
    os.sys.path.insert(0, str(_project_root))

from scripts.credentials import load_env

load_env()

# Scope para aceptar/rechazar y añadir Meet; si no está en el token, re-ejecutar setup_oauth.
SCOPE_READONLY = "https://www.googleapis.com/auth/calendar.readonly"
SCOPE_EVENTS = "https://www.googleapis.com/auth/calendar.events"
# Scope Meet: activar transcripción real en el space (spaces.patch). Sin él solo se usa recordatorio en descripción.
SCOPE_MEET_SETTINGS = "https://www.googleapis.com/auth/meetings.space.settings"

# Marcador en la descripción del evento para recordatorio de transcripción (evita duplicados).
TRANSCRIPTION_REMINDER_MARKER = "Transcripción: activar al iniciar la reunión en Meet."

# Base URL Meet REST API (v2)
MEET_API_BASE = "https://meet.googleapis.com/v2"


def _get_credentials(scopes: Optional[List[str]] = None):
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request

    client_id = os.getenv("GOOGLE_CLIENT_ID")
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
    refresh_token = os.getenv("GOOGLE_REFRESH_TOKEN")
    if not refresh_token or not client_id or not client_secret:
        raise ValueError("Faltan GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET o GOOGLE_REFRESH_TOKEN en .env")
    # Al refrescar usar siempre los mismos scopes con los que se emitió el token (setup_oauth)
    try:
        from scripts.setup_oauth import GOOGLE_SCOPES
        use_scopes = GOOGLE_SCOPES
    except ImportError:
        use_scopes = scopes if scopes else [SCOPE_READONLY]
    creds = Credentials(
        token=None,
        refresh_token=refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=client_id,
        client_secret=client_secret,
        scopes=use_scopes,
    )
    creds.refresh(Request())
    return creds


def _get_calendar_names_config() -> list:
    """Nombres de calendarios: primero config/calendar.local.yaml (gitignored), si no config/calendar.yaml. Vacío = primary."""
    import yaml
    for filename in ("calendar.local.yaml", "calendar.yaml"):
        path = _project_root / "config" / filename
        if path.exists():
            data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
            names = data.get("calendars") or []
            out = [n.strip() for n in names if n and str(n).strip()]
            if out:
                return out
    return []


def get_active_calendar_names(calendar_name: Optional[str] = None) -> list:
    """
    Nombres de calendarios que se usan en esta instancia.
    No llama a la API; nunca lista todos los calendarios.
    Prioridad: argumento calendar_name > env CALENDAR_NAME > config (calendar.local.yaml / calendar.yaml).
    """
    if calendar_name is not None and str(calendar_name).strip():
        return [str(calendar_name).strip()]
    env_name = os.getenv("CALENDAR_NAME", "").strip()
    if env_name:
        return [env_name]
    names = _get_calendar_names_config()
    if names:
        return names
    return ["primary"]


def list_all_calendars() -> List[Dict[str, Any]]:
    """Lista todos los calendarios de la cuenta (nombre, id, primary)."""
    from googleapiclient.discovery import build
    creds = _get_credentials()
    service = build("calendar", "v3", credentials=creds)
    cal_list = service.calendarList().list().execute()
    return [
        {
            "summary": (cal.get("summary") or "").strip() or "(sin nombre)",
            "id": cal.get("id", ""),
            "primary": cal.get("primary", False),
        }
        for cal in cal_list.get("items", [])
    ]


def _resolve_calendar_ids(service, names_override: Optional[list] = None) -> list:
    """Resuelve nombres a calendar IDs. Si names_override, usa solo esos; si no, get_active_calendar_names()."""
    names = names_override if names_override is not None else get_active_calendar_names()
    if not names:
        return ["primary"]
    names_lower = [n.lower() for n in names]
    cal_list = service.calendarList().list().execute()
    ids = []
    for cal in cal_list.get("items", []):
        summary = (cal.get("summary") or "").strip()
        if summary.lower() in names_lower:
            ids.append(cal["id"])
    if not ids:
        return ["primary"]
    return ids


def fetch_events(
    date_min: datetime,
    date_max: datetime,
    calendar_ids: list = None,
    calendar_name: Optional[str] = None,
) -> list:
    from googleapiclient.discovery import build

    creds = _get_credentials()
    service = build("calendar", "v3", credentials=creds)
    if calendar_ids is None:
        names = get_active_calendar_names(calendar_name=calendar_name)
        calendar_ids = _resolve_calendar_ids(service, names_override=names)

    out = []
    for cal_id in calendar_ids:
        events_result = (
            service.events()
            .list(
                calendarId=cal_id,
                timeMin=date_min.isoformat() + "Z",
                timeMax=date_max.isoformat() + "Z",
                singleEvents=True,
                orderBy="startTime",
            )
            .execute()
        )
        items = events_result.get("items", [])
        for e in items:
            start = e.get("start", {})
            start_str = start.get("dateTime") or start.get("date", "")
            conf = e.get("conferenceData", {}) or {}
            entry = (conf.get("entryPoints") or [])
            hangout = ""
            for ep in entry:
                if (ep.get("entryPointType") or "").upper() == "VIDEO":
                    hangout = ep.get("uri", "") or ""
                    break
            if not hangout and entry:
                hangout = entry[0].get("uri", "") or ""
            attendees_raw = e.get("attendees", [])
            attendees_emails = [a.get("email", "") for a in attendees_raw]
            attendees_detail = [
                {
                    "email": a.get("email", ""),
                    "displayName": a.get("displayName", ""),
                    "responseStatus": a.get("responseStatus", "needsAction"),
                    "self": a.get("self", False),
                }
                for a in attendees_raw
            ]
            # Adjuntos (p. ej. "Notes - Call..." / transcripción enlazada desde Meet)
            attachments_raw = e.get("attachments") or []
            attachments = [
                {
                    "fileId": a.get("fileId"),
                    "fileUrl": (a.get("fileUrl") or "").strip(),
                    "title": (a.get("title") or "").strip(),
                }
                for a in attachments_raw
            ]
            out.append({
                "id": e.get("id"),
                "calendar_id": cal_id,
                "summary": e.get("summary", "(sin título)"),
                "start": start_str,
                "description": (e.get("description") or "").strip(),
                "attachments": attachments,
                "location": (e.get("location") or "").strip(),
                "htmlLink": (e.get("htmlLink") or "").strip(),
                "hangoutLink": hangout,
                "attendees": attendees_emails,
                "attendees_detail": attendees_detail,
                "status": e.get("status", ""),
                "organizer": (e.get("organizer") or {}).get("email", ""),
            })
    out.sort(key=lambda x: x.get("start", ""))
    return out


def get_today_and_recent(
    days_recent: int = 7,
    calendar_name: Optional[str] = None,
) -> tuple:
    """Devuelve (eventos_hoy, eventos_recientes) para el calendario activo."""
    tz = datetime.utcnow()
    today_start = datetime(tz.year, tz.month, tz.day)
    today_end = today_start + timedelta(days=1)
    recent_start = today_start - timedelta(days=days_recent)

    events_today = fetch_events(today_start, today_end, calendar_name=calendar_name)
    events_recent = fetch_events(recent_start, today_start, calendar_name=calendar_name)
    return events_today, events_recent


def get_week_range_utc(date_ref: datetime = None) -> tuple:
    """Rango de la semana (Lun 00:00 UTC a Lun+7d)."""
    ref = date_ref or datetime.utcnow()
    week_start = (ref - timedelta(days=ref.weekday())).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    week_end = week_start + timedelta(days=7)
    return week_start, week_end


def get_week_events(date_ref: datetime = None, calendar_name: Optional[str] = None) -> list:
    """Eventos de la semana actual (UTC) para el calendario activo."""
    week_start, week_end = get_week_range_utc(date_ref)
    return fetch_events(week_start, week_end, calendar_name=calendar_name)


def parse_date_range(spec: str, ref: Optional[datetime] = None) -> Tuple[datetime, datetime]:
    """
    Convierte un especificador de rango en (date_min, date_max) UTC.
    Acepta: "today", "this_week" / "this week", "next_week" / "next week",
    o "YYYY-MM-DD:YYYY-MM-DD" (dos fechas inclusivas).
    """
    ref = ref or datetime.utcnow()
    spec = (spec or "").strip().lower().replace(" ", "_")
    if spec in ("today", "hoy"):
        start = ref.replace(hour=0, minute=0, second=0, microsecond=0)
        return start, start + timedelta(days=1)
    if spec in ("this_week", "week", "esta_semana"):
        week_start, week_end = get_week_range_utc(ref)
        return week_start, week_end
    if spec in ("next_week", "next_week", "proxima_semana"):
        week_start, week_end = get_week_range_utc(ref)
        next_start = week_end
        next_end = next_start + timedelta(days=7)
        return next_start, next_end
    if ":" in spec:
        parts = spec.split(":", 1)
        try:
            d1 = datetime.strptime(parts[0].strip()[:10], "%Y-%m-%d")
            d2 = datetime.strptime(parts[1].strip()[:10], "%Y-%m-%d")
            if d1 > d2:
                d1, d2 = d2, d1
            end = d2.replace(hour=23, minute=59, second=59, microsecond=999999)
            return d1.replace(hour=0, minute=0, second=0, microsecond=0), end + timedelta(seconds=1)
        except ValueError:
            pass
    week_start, week_end = get_week_range_utc(ref)
    return week_start, week_end


def get_events_in_range(
    range_spec: str,
    calendar_name: Optional[str] = None,
    date_ref: Optional[datetime] = None,
) -> list:
    """Eventos en el rango indicado (today, this_week, next_week o YYYY-MM-DD:YYYY-MM-DD)."""
    date_min, date_max = parse_date_range(range_spec, date_ref)
    return fetch_events(date_min, date_max, calendar_name=calendar_name)


def match_events_to_clients(events: list) -> list:
    """
    Añade a cada evento las claves 'client' y opcionalmente 'project' según
    config/clients.yaml y context/clients/<client>/projects/*/matches.yaml.
    """
    try:
        from scripts.bitacora_append import load_clients_config, match_client
    except ImportError:
        return events
    clients = load_clients_config()
    if not clients:
        return events
    import yaml
    out = []
    for e in events:
        ev = dict(e)
        summary = ev.get("summary", "")
        client = match_client(summary, clients)
        ev["client"] = client
        ev["project"] = None
        if client:
            projects_dir = _project_root / "context" / "clients" / client / "projects"
            if projects_dir.exists():
                for proj_dir in projects_dir.iterdir():
                    if not proj_dir.is_dir():
                        continue
                    matches_file = proj_dir / "matches.yaml"
                    if not matches_file.exists():
                        continue
                    try:
                        data = yaml.safe_load(matches_file.read_text(encoding="utf-8")) or {}
                        keywords = (data.get("calendar") or {}).get("matching") or {}
                        kws = keywords.get("keywords") or []
                        summary_lower = summary.lower()
                        if any(kw and kw.lower() in summary_lower for kw in kws):
                            ev["project"] = proj_dir.name
                            break
                    except Exception:
                        pass
        out.append(ev)
    return out


def summarize_agenda(events: list, max_chars_per_desc: int = 120) -> str:
    """
    Resumen breve de la agenda usando título y, si existe, la descripción del evento.
    Una o dos líneas por evento.
    """
    lines = []
    for e in events:
        start = (e.get("start") or "")[:16]
        summary = (e.get("summary") or "(sin título)").strip()
        desc = (e.get("description") or "").strip()
        line = f"  {start} – {summary}"
        if desc:
            first_line = desc.split("\n")[0].strip()
            if len(first_line) > max_chars_per_desc:
                first_line = first_line[: max_chars_per_desc - 3] + "..."
            line += "\n    " + first_line
        lines.append(line)
    return "\n".join(lines) if lines else "  (ningún evento)"


def get_notes_or_transcript_refs(event: dict) -> str:
    """
    Referencias a notas o transcripciones: descripción del evento y enlaces que parezcan Drive/Doc.
    Las transcripciones de Meet se guardan en Drive; no se leen desde aquí.
    """
    desc = (event.get("description") or "").strip()
    if not desc:
        return ""
    refs = [desc]
    url_pattern = re.compile(r"https?://[^\s<>]+(?:drive\.google\.com|docs\.google\.com)[^\s<>]*")
    for url in url_pattern.findall(desc):
        refs.append("Enlace: " + url[:80] + ("..." if len(url) > 80 else ""))
    return "\n".join(refs) if len(refs) > 1 else desc


def get_google_doc_ids_from_event(event: dict) -> List[str]:
    """
    Extrae los IDs de Google Docs del evento: primero de los adjuntos (attachments)
    (p. ej. "Notes - Call..." que Meet enlaza como attachment con fileId/fileUrl),
    luego de la descripción si hay enlaces a Docs/Drive.
    Útil para luego abrir el Doc con docs_lite.fetch_doc_plain_text(doc_id).
    """
    ids = []
    seen = set()
    # 1) Adjuntos: fileId es el ID de Drive/Doc; también podemos extraer de fileUrl
    for a in (event.get("attachments") or []):
        file_id = (a.get("fileId") or "").strip()
        if file_id and file_id not in seen:
            seen.add(file_id)
            ids.append(file_id)
        file_url = (a.get("fileUrl") or "").strip()
        if file_url:
            try:
                from scripts.docs_lite import extract_doc_ids_from_text
                for doc_id in extract_doc_ids_from_text(file_url):
                    if doc_id not in seen:
                        seen.add(doc_id)
                        ids.append(doc_id)
            except ImportError:
                pass
    # 2) Descripción: enlaces a docs.google.com o drive.google.com
    desc = (event.get("description") or "").strip()
    if desc:
        try:
            from scripts.docs_lite import extract_doc_ids_from_text
            for doc_id in extract_doc_ids_from_text(desc):
                if doc_id not in seen:
                    seen.add(doc_id)
                    ids.append(doc_id)
        except ImportError:
            pass
    return ids


def read_transcription_for_date(
    date_iso: str,
    client_filter: Optional[str] = None,
    calendar_name: Optional[str] = None,
) -> Tuple[Optional[dict], Optional[str]]:
    """
    Obtiene los eventos del día date_iso (YYYY-MM-DD), opcionalmente filtra por cliente,
    busca el primero que tenga en la descripción un enlace a Google Docs (transcripción)
    y devuelve (evento, texto_plano_del_doc) o (None, None) si no hay evento con Doc.

    Requiere Google Docs API y scope documents.readonly (scripts/setup_oauth.py).
    """
    events = get_events_in_range(f"{date_iso}:{date_iso}", calendar_name=calendar_name)
    events = match_events_to_clients(events)
    if client_filter:
        client_lower = client_filter.strip().lower()
        events = [e for e in events if (e.get("client") or "").lower() == client_lower]
    for e in events:
        doc_ids = get_google_doc_ids_from_event(e)
        if doc_ids:
            try:
                from scripts import docs_lite
                text = docs_lite.fetch_doc_plain_text(doc_ids[0])
                if text is not None:
                    return (e, text)
                # Enlace encontrado pero no se pudo leer el Doc (permisos, API, etc.)
                return (e, None)
            except Exception:
                return (e, None)
    return (None, None)


def _event_summary_to_slug(summary: str) -> str:
    """Genera un slug legible para el fichero de transcripción (minúsculas, guiones)."""
    s = (summary or "").strip()[:80]
    s = re.sub(r"[^\w\s\-]", "", s, flags=re.UNICODE)
    s = re.sub(r"\s+", "-", s).strip("-").lower()
    return s or "call"


def _first_project_for_client(project_root: Path, client: str) -> Optional[str]:
    """Devuelve el nombre del primer proyecto del cliente (para usar si no matchea matches.yaml)."""
    projects_dir = project_root / "context" / "clients" / client / "projects"
    if not projects_dir.is_dir():
        return None
    for d in sorted(projects_dir.iterdir()):
        if d.is_dir() and not d.name.startswith("_"):
            return d.name
    return None


def import_transcriptions_from_calendar(
    project_root: Path,
    date_iso: str,
    calendar_name: Optional[str] = None,
    skip_existing: bool = True,
) -> List[Path]:
    """
    Busca calls del día date_iso con Doc enlazado, obtiene el contenido de cada Doc,
    guarda en context/clients/<cliente>/projects/<proyecto>/meetings/transcripcion-YYYY-MM-DD-<slug>.md
    y devuelve la lista de rutas guardadas.

    Requiere scope documents.readonly (Google Docs API).
    """
    events = get_events_in_range(f"{date_iso}:{date_iso}", calendar_name=calendar_name)
    events = match_events_to_clients(events)
    saved = []
    for e in events:
        client = e.get("client")
        if not client:
            continue
        doc_ids = get_google_doc_ids_from_event(e)
        if not doc_ids:
            continue
        project = e.get("project") or _first_project_for_client(project_root, client)
        if not project:
            continue
        summary = (e.get("summary") or "").strip()
        slug = _event_summary_to_slug(summary)
        meetings_dir = project_root / "context" / "clients" / client / "projects" / project / "meetings"
        meetings_dir.mkdir(parents=True, exist_ok=True)
        out_path = meetings_dir / f"transcripcion-{date_iso}-{slug}.md"
        if skip_existing and out_path.exists():
            continue
        try:
            from scripts import docs_lite
            text = docs_lite.fetch_doc_plain_text(doc_ids[0])
            if text is None:
                continue
        except Exception:
            continue
        header = "# Transcripción – %s\n\n" % (summary or slug)
        header += "**Evento:** %s  \n" % (summary or "(sin título)")
        header += "**Fecha:** %s  \n" % date_iso
        header += "**Proyecto:** %s  \n" % project
        header += "**Origen:** Doc enlazado en Calendar (adjunto del evento)\n\n---\n\n"
        header += text if text.startswith("===") else "=== Transcripción ===\n\n" + text
        out_path.write_text(header, encoding="utf-8")
        saved.append(out_path)
    return saved


def respond_to_event(
    calendar_id: str,
    event_id: str,
    response: str,
    calendar_name: Optional[str] = None,
) -> dict:
    """
    Aceptar, rechazar o marcar como tentativa una invitación.
    response: "accepted" | "declined" | "tentative".
    Requiere scope calendar.events (re-ejecutar setup_oauth si hace falta).
    Devuelve el evento actualizado.
    """
    from googleapiclient.discovery import build

    creds = _get_credentials([SCOPE_READONLY, SCOPE_EVENTS])
    service = build("calendar", "v3", credentials=creds)
    event = service.events().get(calendarId=calendar_id, eventId=event_id).execute()
    attendees = list(event.get("attendees", []))
    idx_self = None
    for i, a in enumerate(attendees):
        if a.get("self"):
            idx_self = i
            break
    if idx_self is None:
        my_email = os.getenv("GOOGLE_CALENDAR_EMAIL", "").strip().lower()
        if my_email:
            for i, a in enumerate(attendees):
                if (a.get("email") or "").lower() == my_email:
                    idx_self = i
                    break
    if idx_self is None:
        raise ValueError("No se encontró al usuario actual en la lista de invitados (usa GOOGLE_CALENDAR_EMAIL en .env si hace falta)")
    status = response.strip().lower()
    if status not in ("accepted", "declined", "tentative"):
        raise ValueError("response debe ser accepted, declined o tentative")
    attendees[idx_self]["responseStatus"] = status
    body = {"attendees": attendees}
    updated = service.events().patch(
        calendarId=calendar_id,
        eventId=event_id,
        body=body,
        sendUpdates="all",
    ).execute()
    return updated


def add_meet_to_event(
    calendar_id: str,
    event_id: str,
    calendar_name: Optional[str] = None,
) -> dict:
    """
    Añade una videollamada de Google Meet a un evento existente.
    Requiere scope calendar.events. Devuelve el evento actualizado con hangoutLink.
    """
    from googleapiclient.discovery import build

    creds = _get_credentials([SCOPE_READONLY, SCOPE_EVENTS])
    service = build("calendar", "v3", credentials=creds)
    # requestId debe ser único por solicitud; usar event_id + timestamp
    request_id = f"{event_id}-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
    body = {
        "conferenceData": {
            "createRequest": {
                "requestId": request_id,
                "conferenceSolutionKey": {"type": "hangoutsMeet"},
            }
        }
    }
    updated = (
        service.events()
        .patch(
            calendarId=calendar_id,
            eventId=event_id,
            body=body,
            conferenceDataVersion=1,
            sendUpdates="all",
        )
        .execute()
    )
    return updated


def _meeting_code_from_hangout(hangout_link: str) -> Optional[str]:
    """Extrae el meeting code del enlace Meet (ej. https://meet.google.com/abc-mnop-xyz -> abc-mnop-xyz)."""
    if not (hangout_link or "").strip():
        return None
    link = (hangout_link or "").strip()
    prefix = "https://meet.google.com/"
    if not link.startswith(prefix):
        return None
    code = link[len(prefix) :].split("?")[0].strip("/")
    return code if code else None


def enable_meet_transcription_for_space(meeting_code: str) -> bool:
    """
    Activa la transcripción automática en el space de Meet (Meet API spaces.patch).
    meeting_code: código tipo abc-mnop-xyz (del enlace meet.google.com/...).
    Requiere scope meetings.space.settings. Devuelve True si se aplicó correctamente.
    """
    if not (meeting_code or "").strip():
        return False
    import json as _json
    from urllib.request import Request as UrlRequest, urlopen
    from urllib.error import HTTPError, URLError
    from google.auth.transport.requests import Request

    try:
        creds = _get_credentials([SCOPE_READONLY, SCOPE_EVENTS, SCOPE_MEET_SETTINGS])
    except Exception:
        return False
    creds.refresh(Request())
    token = creds.token
    if not token:
        return False
    space_name = meeting_code.strip()
    url = f"{MEET_API_BASE}/spaces/{space_name}?updateMask=config.artifactConfig.transcriptionConfig"
    body = {
        "config": {
            "artifactConfig": {
                "transcriptionConfig": {"autoTranscriptionGeneration": "ON"},
            }
        }
    }
    data = _json.dumps(body).encode("utf-8")
    req = UrlRequest(
        url,
        data=data,
        method="PATCH",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urlopen(req, timeout=15) as resp:
            return resp.status == 200
    except (HTTPError, URLError, OSError):
        return False


def add_transcription_reminder_to_event(
    calendar_id: str,
    event_id: str,
    calendar_name: Optional[str] = None,
    use_meet_api_if_available: bool = True,
) -> Optional[dict]:
    """
    Activa la transcripción para el evento: primero intenta Meet API (spaces.patch) si hay scope;
    si no, añade un recordatorio en la descripción del evento.
    Solo actúa si el evento tiene Meet y (para descripción) la descripción no contiene ya el recordatorio.
    Requiere scope calendar.events para el recordatorio; meetings.space.settings para la activación real.
    Devuelve el evento actualizado (Calendar) o un dict con clave "transcription_activated" si se usó Meet API; None si no se modificó.
    """
    from googleapiclient.discovery import build

    creds = _get_credentials([SCOPE_READONLY, SCOPE_EVENTS])
    service = build("calendar", "v3", credentials=creds)
    event = service.events().get(calendarId=calendar_id, eventId=event_id).execute()
    conf = event.get("conferenceData", {}) or {}
    entry = conf.get("entryPoints") or []
    hangout_uri = ""
    for ep in entry:
        if (ep.get("entryPointType") or "").upper() == "VIDEO":
            hangout_uri = ep.get("uri", "") or ""
            break
    if not hangout_uri and entry:
        hangout_uri = entry[0].get("uri", "") or ""
    if not hangout_uri:
        return None
    meeting_code = _meeting_code_from_hangout(hangout_uri)
    if use_meet_api_if_available and meeting_code and enable_meet_transcription_for_space(meeting_code):
        return {"id": event_id, "transcription_activated": True, "summary": event.get("summary")}
    desc = (event.get("description") or "").strip()
    if TRANSCRIPTION_REMINDER_MARKER in desc:
        return None
    new_desc = (desc + "\n\n" + TRANSCRIPTION_REMINDER_MARKER).strip()
    updated = (
        service.events()
        .patch(
            calendarId=calendar_id,
            eventId=event_id,
            body={"description": new_desc},
            sendUpdates="none",
        )
        .execute()
    )
    return updated


def events_where_im_invited_or_organizer(events: list, my_email: Optional[str] = None) -> list:
    """
    Filtra eventos donde el usuario actual es organizador o está en la lista de invitados.
    my_email: si no se pasa, se usa GOOGLE_CALENDAR_EMAIL; si no está, se usa 'self' en attendees_detail.
    """
    if not events:
        return []
    my_email = (my_email or os.getenv("GOOGLE_CALENDAR_EMAIL", "").strip()).lower()
    out = []
    for e in events:
        organizer = (e.get("organizer") or "").strip().lower()
        if my_email and organizer == my_email:
            out.append(e)
            continue
        for a in e.get("attendees_detail", []):
            if a.get("self"):
                out.append(e)
                break
            if my_email and (a.get("email") or "").lower() == my_email:
                out.append(e)
                break
    return out


def has_transcription_reminder(event: dict) -> bool:
    """True si la descripción del evento ya contiene el recordatorio de transcripción."""
    return TRANSCRIPTION_REMINDER_MARKER in ((event.get("description") or "").strip())


def ensure_meet_on_events(
    events: list,
    calendar_name: Optional[str] = None,
) -> List[Tuple[dict, dict]]:
    """
    Añade Meet a cada evento que no tenga hangoutLink. Solo eventos con id y calendar_id.
    Devuelve lista de (evento_original, evento_actualizado) por cada uno modificado.
    """
    added = []
    for e in events:
        if (e.get("hangoutLink") or "").strip():
            continue
        cid = e.get("calendar_id")
        eid = e.get("id")
        if not cid or not eid:
            continue
        try:
            updated = add_meet_to_event(cid, eid, calendar_name=calendar_name)
            added.append((e, updated))
        except Exception:
            pass
    return added


def ensure_transcription_reminder_on_events(
    events: list,
    only_with_meet: bool = True,
    only_mine_or_im_invited: bool = False,
    my_email: Optional[str] = None,
    calendar_name: Optional[str] = None,
) -> List[Tuple[dict, dict]]:
    """
    Añade recordatorio de transcripción a eventos que tengan Meet y no lo tengan ya.
    Si only_with_meet=True, solo eventos con hangoutLink. Si only_mine_or_im_invited=True,
    solo donde soy organizador o invitado. Devuelve (evento, evento_actualizado) por cada uno modificado.
    """
    cand = events
    if only_mine_or_im_invited:
        cand = events_where_im_invited_or_organizer(cand, my_email=my_email)
    added = []
    for e in cand:
        if only_with_meet and not (e.get("hangoutLink") or "").strip():
            continue
        if has_transcription_reminder(e):
            continue
        cid = e.get("calendar_id")
        eid = e.get("id")
        if not cid or not eid:
            continue
        try:
            updated = add_transcription_reminder_to_event(cid, eid, calendar_name=calendar_name)
            if updated is not None:
                added.append((e, updated))
        except Exception:
            pass
    return added


def _print_events(events: list, show_attendees: bool = False, show_match: bool = False, show_summary: bool = False) -> None:
    """Imprime eventos; opcionalmente invitados, cliente/proyecto y resumen con descripción."""
    if show_summary and events:
        print(summarize_agenda(events))
        return
    for e in events:
        start = (e.get("start") or "")[:16]
        summary = (e.get("summary") or "(sin título)")[:60]
        line = f"  {start}  {summary}"
        if show_match and e.get("client"):
            line += f"  [cliente: {e['client']}" + (f" | proyecto: {e['project']}" if e.get("project") else "") + "]"
        print(line)
        if show_attendees:
            for a in e.get("attendees_detail", []):
                email = a.get("email", "")
                name = (a.get("displayName") or "").strip() or email
                status = a.get("responseStatus", "needsAction")
                print(f"    – {name} ({status})")
        elif (e.get("description") or "").strip():
            first = (e["description"].split("\n")[0] or "").strip()[:80]
            if first:
                print("    " + first + ("..." if len(first) >= 80 else ""))


def cli():
    """CLI: --calendar, --range, --week, --today, --list-calendars, --attendees, --match-clients, --summary, --respond."""
    parser = argparse.ArgumentParser(
        description="Calendario: eventos por rango, invitados, cliente/proyecto, resumen, aceptar/rechazar."
    )
    parser.add_argument(
        "--calendar",
        type=str,
        default=None,
        metavar="NOMBRE",
        help="Único calendario a usar por nombre (prioritario sobre CALENDAR_NAME y config)",
    )
    parser.add_argument(
        "--range",
        type=str,
        default=None,
        metavar="SPEC",
        help="Rango: today, this_week, next_week, o YYYY-MM-DD:YYYY-MM-DD",
    )
    parser.add_argument(
        "--week",
        action="store_true",
        help="Mostrar eventos de esta semana (UTC)",
    )
    parser.add_argument(
        "--today",
        action="store_true",
        help="Mostrar hoy y recientes (por defecto si no --range ni --week)",
    )
    parser.add_argument(
        "--which-calendar",
        action="store_true",
        help="Solo imprimir el nombre del calendario en uso",
    )
    parser.add_argument(
        "--list-calendars",
        action="store_true",
        help="Listar todos los calendarios de la cuenta (nombre, principal)",
    )
    parser.add_argument(
        "--attendees",
        action="store_true",
        help="Mostrar invitados y estado de respuesta de cada evento",
    )
    parser.add_argument(
        "--match-clients",
        action="store_true",
        help="Cruzar títulos con clientes y proyectos (config/clients.yaml, matches.yaml)",
    )
    parser.add_argument(
        "--summary",
        action="store_true",
        help="Resumir agenda usando descripciones de los eventos",
    )
    parser.add_argument(
        "--respond",
        type=str,
        nargs=2,
        metavar=("accept|decline|tentative", "EVENT_ID"),
        help="Aceptar o rechazar invitación (requiere scope calendar.events)",
    )
    parser.add_argument(
        "--add-meet",
        action="store_true",
        help="Añadir videollamada Meet a los eventos del rango que no la tengan (requiere scope calendar.events)",
    )
    parser.add_argument(
        "--add-transcription-reminder",
        action="store_true",
        help="Activar transcripción en eventos con Meet (Meet API o recordatorio en descripción)",
    )
    parser.add_argument(
        "--transcription-all",
        action="store_true",
        help="Con --add-transcription-reminder: aplicar a todas las citas con Meet del rango (no solo donde soy organizador/invitado)",
    )
    parser.add_argument(
        "--add-meet-my-events-only",
        action="store_true",
        help="Con --add-meet: solo eventos donde soy organizador o invitado",
    )
    parser.add_argument(
        "--read-transcription",
        action="store_true",
        help="Leer transcripción: evento del día (o --read-transcription-date) con enlace a Google Docs en la descripción; imprime el contenido del Doc. Ver .cursor/commands/calendar-meet-transcription.md.",
    )
    parser.add_argument(
        "--read-transcription-date",
        type=str,
        default=None,
        metavar="YYYY-MM-DD",
        help="Con --read-transcription: fecha del evento (por defecto: ayer).",
    )
    parser.add_argument(
        "--read-transcription-client",
        type=str,
        default=None,
        metavar="CLIENTE",
        help="Con --read-transcription: filtrar por cliente (ej: mcr).",
    )
    parser.add_argument(
        "--import-transcriptions",
        action="store_true",
        help="Importar transcripciones del día indicado (o ayer): busca calls con Doc, guarda en context/.../meetings/.",
    )
    parser.add_argument(
        "--import-transcriptions-date",
        type=str,
        default=None,
        metavar="YYYY-MM-DD",
        help="Con --import-transcriptions: fecha (por defecto: ayer).",
    )
    args = parser.parse_args()

    calendar_override = args.calendar.strip() if (args.calendar and args.calendar.strip()) else None
    active_names = get_active_calendar_names(calendar_name=calendar_override)

    if args.which_calendar:
        for n in active_names:
            print(n)
        return 0

    if args.list_calendars:
        if not os.getenv("GOOGLE_CLIENT_ID") or not os.getenv("GOOGLE_REFRESH_TOKEN"):
            print("Configura Google en .env (CLIENT_ID, CLIENT_SECRET, REFRESH_TOKEN).", file=sys.stderr)
            return 1
        for c in list_all_calendars():
            prim = " (principal)" if c.get("primary") else ""
            print(" ", c["summary"] + prim)
        return 0

    if args.read_transcription:
        if not os.getenv("GOOGLE_CLIENT_ID") or not os.getenv("GOOGLE_REFRESH_TOKEN"):
            print("Configura Google en .env (CLIENT_ID, CLIENT_SECRET, REFRESH_TOKEN).", file=sys.stderr)
            return 1
        date_iso = args.read_transcription_date
        if not date_iso:
            date_iso = (datetime.utcnow() - timedelta(days=1)).strftime("%Y-%m-%d")
        event, text = read_transcription_for_date(
            date_iso,
            client_filter=args.read_transcription_client,
            calendar_name=calendar_override,
        )
        if event and text:
            print("Evento:", (event.get("summary") or "(sin título)").strip(), file=sys.stderr)
            print(text)
            return 0
        if event and text is None:
            print(
                "Enlace al Doc encontrado (adjunto o descripción) pero no se pudo leer el contenido. "
                "Revisa: Google Docs API activada en GCP y token con scope documents.readonly (re-ejecuta scripts/setup_oauth.py).",
                file=sys.stderr,
            )
        else:
            print(
                "No hay evento con enlace a Google Docs (adjunto o descripción) para esa fecha"
                + (" y cliente." if args.read_transcription_client else "."),
                file=sys.stderr,
            )
        return 1

    if args.import_transcriptions:
        if not os.getenv("GOOGLE_CLIENT_ID") or not os.getenv("GOOGLE_REFRESH_TOKEN"):
            print("Configura Google en .env (CLIENT_ID, CLIENT_SECRET, REFRESH_TOKEN).", file=sys.stderr)
            return 1
        date_iso = args.import_transcriptions_date
        if not date_iso:
            date_iso = (datetime.utcnow() - timedelta(days=1)).strftime("%Y-%m-%d")
        try:
            saved = import_transcriptions_from_calendar(
                _project_root,
                date_iso,
                calendar_name=calendar_override,
            )
            if saved:
                print("Transcripciones – Importadas %d call(s) de %s." % (len(saved), date_iso), file=sys.stderr)
                for p in saved:
                    print(str(p))
            else:
                print("Transcripciones – Sin calls con Doc para %s." % date_iso, file=sys.stderr)
        except Exception as ex:
            print("Transcripciones – Error:", ex, file=sys.stderr)
            return 1
        return 0

    if args.respond:
        resp_type, event_id = args.respond[0].strip().lower(), args.respond[1].strip()
        if resp_type not in ("accept", "accepted", "decline", "declined", "tentative", "yes", "no"):
            print("Uso: --respond accept|decline|tentative EVENT_ID", file=sys.stderr)
            return 1
        if resp_type in ("accept", "yes"):
            resp_type = "accepted"
        elif resp_type in ("decline", "no"):
            resp_type = "declined"
        if not os.getenv("GOOGLE_CLIENT_ID") or not os.getenv("GOOGLE_REFRESH_TOKEN"):
            print("Configura Google en .env.", file=sys.stderr)
            return 1
        try:
            from googleapiclient.discovery import build
            creds = _get_credentials([SCOPE_READONLY, SCOPE_EVENTS])
            service = build("calendar", "v3", credentials=creds)
            cal_ids = _resolve_calendar_ids(service, names_override=active_names)
            calendar_id = cal_ids[0] if cal_ids else "primary"
            respond_to_event(calendar_id, event_id, resp_type, calendar_name=calendar_override)
            print("Hecho:", resp_type, "para evento", event_id)
        except Exception as ex:
            print("Error al responder:", ex, file=sys.stderr)
            if "calendar.events" in str(ex) or "403" in str(ex):
                print("Puede que necesites re-ejecutar setup_oauth con scope calendar.events.", file=sys.stderr)
            return 1
        return 0

    if not os.getenv("GOOGLE_CLIENT_ID") or not os.getenv("GOOGLE_REFRESH_TOKEN"):
        print("Configura Google en .env (CLIENT_ID, CLIENT_SECRET, REFRESH_TOKEN).", file=sys.stderr)
        return 1

    events = []
    range_label = ""

    if args.range:
        date_min, date_max = parse_date_range(args.range)
        range_label = f"{date_min.strftime('%Y-%m-%d')} -> {date_max.strftime('%Y-%m-%d')}"
        events = get_events_in_range(args.range, calendar_name=calendar_override)
    elif args.week:
        week_start, week_end = get_week_range_utc()
        range_label = f"Semana (UTC): {week_start.strftime('%Y-%m-%d')} -> {week_end.strftime('%Y-%m-%d')}"
        events = get_week_events(calendar_name=calendar_override)
    else:
        today, recent = get_today_and_recent(calendar_name=calendar_override)
        events = today + recent
        range_label = "Hoy y recientes (7 días)"

    # --add-meet: añadir Meet a eventos que no lo tengan
    if args.add_meet and events:
        to_process = events_where_im_invited_or_organizer(events) if args.add_meet_my_events_only else events
        added_meet = ensure_meet_on_events(to_process, calendar_name=calendar_override)
        if added_meet:
            print("Meet añadido a", len(added_meet), "evento(s):")
            for orig, _ in added_meet:
                print("  ", (orig.get("start") or "")[:16], (orig.get("summary") or "(sin título)")[:50])
            if args.add_transcription_reminder:
                # Refetch para que los nuevos eventos tengan hangoutLink
                if args.range:
                    events = get_events_in_range(args.range, calendar_name=calendar_override)
                elif args.week:
                    events = get_week_events(calendar_name=calendar_override)
                else:
                    today, recent = get_today_and_recent(calendar_name=calendar_override)
                    events = today + recent
        else:
            print("Ningún evento sin Meet en el rango (o no se pudo añadir).")

    # --add-transcription-reminder: activar transcripción en eventos con Meet
    if args.add_transcription_reminder and events:
        only_mine = not args.transcription_all
        added_trans = ensure_transcription_reminder_on_events(
            events,
            only_with_meet=True,
            only_mine_or_im_invited=only_mine,
            calendar_name=calendar_override,
        )
        if added_trans:
            print("Transcripción activada en", len(added_trans), "cita(s):")
            for orig, _ in added_trans:
                print("  ", (orig.get("start") or "")[:16], (orig.get("summary") or "(sin título)")[:50])
        elif not args.add_meet:
            print("Ningún evento con Meet sin transcripción (o ya la tenían).")

    if args.add_meet or args.add_transcription_reminder:
        return 0

    if args.match_clients and events:
        events = match_events_to_clients(events)

    print("Calendario:", active_names[0] if active_names else "primary")
    print(range_label)
    if not events:
        print("(ningún evento)")
    else:
        _print_events(events, show_attendees=args.attendees, show_match=args.match_clients, show_summary=args.summary)
        if not args.summary:
            print("Total:", len(events), "eventos")
    return 0


if __name__ == "__main__":
    sys.exit(cli())
