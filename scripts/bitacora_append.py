"""
Añadir reuniones, emails (Gmail), tareas (Asana) y transcripciones del día anterior a bitácoras por cliente.
Lee config/clients.yaml para matchear evento/email/proyecto -> cliente.
Las transcripciones se buscan en context/clients/<cliente>/projects/<proyecto>/meetings/transcripcion-YYYY-MM-DD-*.md.
"""

import os
import re
from datetime import datetime
from pathlib import Path

_project_root = Path(__file__).resolve().parent.parent
if str(_project_root) not in os.sys.path:
    os.sys.path.insert(0, str(_project_root))


def load_clients_config() -> dict:
    config_path = _project_root / "config" / "clients.yaml"
    if not config_path.exists():
        return {}
    import yaml
    with open(config_path, encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return data.get("clients", {})


def match_client(text: str, clients: dict) -> str:
    """Devuelve el nombre del cliente si el texto matchea; si no, None."""
    if not text:
        return None
    summary_lower = text.lower()
    for client_name, substrings in clients.items():
        if client_name.startswith("_"):
            continue
        if isinstance(substrings, str):
            substrings = [substrings]
        for sub in substrings:
            if sub and sub.lower() in summary_lower:
                return client_name
    return None


def _email_date_to_iso(date_str: str) -> str:
    """Convierte fecha de cabecera email (ej. 'Fri, 7 Feb 2025 09:12:00 +0000') a YYYY-MM-DD."""
    if not date_str or not date_str.strip():
        return datetime.utcnow().strftime("%Y-%m-%d")
    try:
        # Eliminar parte de zona/hora si molesta; intentar parsear día/mes/año
        parts = date_str.strip().split()
        if len(parts) >= 3:
            # "Fri, 7 Feb 2025" o "7 Feb 2025"
            day = None
            month = None
            year = None
            for p in parts:
                if p.isdigit() and len(p) <= 2:
                    day = int(p)
                elif p.isdigit() and len(p) == 4:
                    year = int(p)
                elif p.lower() in ("jan", "feb", "mar", "apr", "may", "jun",
                                   "jul", "aug", "sep", "oct", "nov", "dec"):
                    months = ("jan", "feb", "mar", "apr", "may", "jun",
                              "jul", "aug", "sep", "oct", "nov", "dec")
                    month = months.index(p.lower()) + 1
            if day and month and year:
                return "%04d-%02d-%02d" % (year, month, day)
    except Exception:
        pass
    return datetime.utcnow().strftime("%Y-%m-%d")


def append_to_bitacora(client_slug: str, line: str, skip_if_exists: bool = True) -> bool:
    """Añade una línea a la bitácora del cliente. Si skip_if_exists y la línea ya existe, no escribe. Devuelve True si escribió."""
    context_dir = _project_root / "context" / "clients"
    client_dir = context_dir / client_slug
    client_dir.mkdir(parents=True, exist_ok=True)
    bitacora = client_dir / "bitacora.md"
    if not bitacora.exists():
        bitacora.write_text("# Bitácora – " + client_slug + "\n\n", encoding="utf-8")
    if skip_if_exists:
        content = bitacora.read_text(encoding="utf-8")
        if line.strip() in content:
            return False
    with open(bitacora, "a", encoding="utf-8") as f:
        f.write(line + "\n")
    return True


def process_events(events: list) -> list:
    """Para cada evento, matchea cliente y append a bitácora. Devuelve lista de (cliente, línea) añadidos."""
    clients = load_clients_config()
    if not clients:
        return []
    added = []
    for e in events:
        summary = e.get("summary", "")
        client = match_client(summary, clients)
        if not client:
            continue
        start = e.get("start", "")[:10] if isinstance(e.get("start"), str) else ""
        attendees = e.get("attendees", [])
        att_str = ", ".join(attendees[:3]) if attendees else ""
        line = "- **%s** %s – %s" % (start, summary, att_str)
        if append_to_bitacora(client, line):
            added.append((client, line))
    return added


def process_emails(emails: list) -> list:
    """Para cada email, matchea cliente por asunto o remitente y append a bitácora. Devuelve lista de (cliente, línea) añadidos."""
    clients = load_clients_config()
    if not clients:
        return []
    added = []
    for e in emails:
        subject = (e.get("subject") or "").strip()
        from_ = (e.get("from") or "").strip()
        text_to_match = subject + " " + from_
        client = match_client(text_to_match, clients)
        if not client:
            continue
        date_iso = _email_date_to_iso(e.get("date") or "")
        short_from = (from_[:40] + "…") if len(from_) > 40 else from_
        line = "- **%s** Email: %s (%s)" % (date_iso, subject[:70] + ("…" if len(subject) > 70 else ""), short_from)
        if append_to_bitacora(client, line):
            added.append((client, line))
    return added


def process_asana_tasks(tasks: list) -> list:
    """Para cada tarea de Asana, matchea cliente por nombre de proyecto y append a bitácora. Devuelve lista de (cliente, línea) añadidos."""
    clients = load_clients_config()
    if not clients:
        return []
    added = []
    for t in tasks:
        project_name = (t.get("project_name") or "").strip()
        client = match_client(project_name, clients)
        if not client:
            continue
        name = (t.get("name") or "").strip()
        due_on = t.get("due_on") or datetime.utcnow().strftime("%Y-%m-%d")
        status_label = "[hecha]" if t.get("completed") else "[pendiente]"
        line = "- **%s** Tarea %s: %s (proyecto: %s)" % (due_on, status_label, name[:60] + ("…" if len(name) > 60 else ""), project_name[:30] or "—")
        if append_to_bitacora(client, line):
            added.append((client, line))
    return added


# Patrón: transcripcion-YYYY-MM-DD-slug.md
_TRANSCRIPTION_FILENAME_RE = re.compile(r"^transcripcion-(\d{4}-\d{2}-\d{2})-(.+)\.md$", re.IGNORECASE)


def _parse_transcription_path(path: Path) -> tuple:
    """Extrae (date_iso, slug) del nombre del fichero. Si no matchea, devuelve (None, None)."""
    name = path.name
    m = _TRANSCRIPTION_FILENAME_RE.match(name)
    if not m:
        return (None, None)
    return (m.group(1), m.group(2).strip())


def _transcription_title_from_file(path: Path) -> str:
    """Lee la primera línea del fichero; si es '# Transcripción – Título', devuelve 'Título'. Si no, ''. """
    try:
        first = path.read_text(encoding="utf-8").splitlines()
        if not first:
            return ""
        line = first[0].strip()
        for prefix in ("# Transcripción – ", "# Transcripción - "):
            if line.startswith(prefix):
                return line[len(prefix):].strip()[:80] or ""
        if line.startswith("#"):
            return line.lstrip("#").strip()[:80] or ""
    except Exception:
        pass
    return ""


def collect_transcriptions_for_date(project_root: Path, date_iso: str) -> list:
    """
    Recorre context/clients/*/projects/*/meetings/transcripcion-*.md y devuelve
    las que corresponden a date_iso (YYYY-MM-DD). Cada elemento es un dict con:
    client, project, date_iso, path, slug, title (opcional, desde primera línea).
    """
    clients_dir = project_root / "context" / "clients"
    if not clients_dir.is_dir():
        return []
    entries = []
    for client_dir in clients_dir.iterdir():
        if not client_dir.is_dir() or client_dir.name.startswith("_"):
            continue
        projects_dir = client_dir / "projects"
        if not projects_dir.is_dir():
            continue
        for project_dir in projects_dir.iterdir():
            if not project_dir.is_dir():
                continue
            meetings_dir = project_dir / "meetings"
            if not meetings_dir.is_dir():
                continue
            for path in meetings_dir.glob("transcripcion-*.md"):
                file_date, slug = _parse_transcription_path(path)
                if file_date != date_iso:
                    continue
                title = _transcription_title_from_file(path)
                entries.append({
                    "client": client_dir.name,
                    "project": project_dir.name,
                    "date_iso": file_date,
                    "path": path,
                    "slug": slug or path.stem,
                    "title": title or slug or path.stem,
                })
    return entries


def process_transcriptions(entries: list) -> list:
    """
    Para cada transcripción del día anterior, añade una línea a la bitácora del cliente.
    Devuelve lista de (cliente, línea) añadidos.
    """
    added = []
    for e in entries:
        client = e.get("client")
        if not client:
            continue
        date_iso = e.get("date_iso", "")
        project = e.get("project", "")
        raw_title = (e.get("title") or e.get("slug") or "").strip()
        title = raw_title[:60] + ("…" if len(raw_title) > 60 else "")
        line = "- **%s** Transcripción: %s (proyecto: %s)" % (date_iso, title, project)
        if append_to_bitacora(client, line):
            added.append((client, line))
    return added


def process_completed_tasks(entries: list) -> list:
    """
    Para cada tarea realizada (completada el día anterior en Asana), matchea cliente por
    nombre de proyecto o de tarea y añade una línea a la bitácora, incorporando la descripción
    si existe. entries: lista de dict con name, project_name, date_iso, notes.
    Devuelve lista de (cliente, línea) añadidos.
    """
    clients = load_clients_config()
    if not clients:
        return []
    added = []
    for e in entries:
        name = (e.get("name") or "").strip()
        project_name = (e.get("project_name") or "").strip()
        date_iso = e.get("date_iso", "")
        notes = (e.get("notes") or "").strip()
        text_to_match = (project_name + " " + name).strip()
        client = match_client(text_to_match, clients)
        if not client:
            continue
        title = (name[:60] + "…") if len(name) > 60 else name
        line = "- **%s** Tarea realizada: %s (proyecto: %s)" % (date_iso, title, project_name or "—")
        if append_to_bitacora(client, line):
            added.append((client, line))
        if notes:
            desc_snippet = notes[:200].rstrip() + ("…" if len(notes) > 200 else "")
            desc_line = "  " + desc_snippet.replace("\n", " ")
            if append_to_bitacora(client, desc_line):
                added.append((client, desc_line))
    return added


if __name__ == "__main__":
    # Test con eventos de ejemplo
    test_events = [
        {"summary": "Reunión ejemplo cliente", "start": "2025-02-08", "attendees": ["a@b.com"]},
    ]
    added = process_events(test_events)
    print("Eventos añadidos:", added)
