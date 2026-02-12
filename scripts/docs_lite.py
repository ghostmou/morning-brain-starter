"""
Leer contenido de Google Docs (p. ej. transcripciones enlazadas desde eventos de Calendar).
Requiere scope https://www.googleapis.com/auth/documents.readonly y Google Docs API activada en GCP.
"""

import os
import re
from pathlib import Path
from typing import List, Optional

_project_root = Path(__file__).resolve().parent.parent
if str(_project_root) not in os.sys.path:
    os.sys.path.insert(0, str(_project_root))

from scripts.credentials import load_env

load_env()

SCOPE_DOCS_READONLY = "https://www.googleapis.com/auth/documents.readonly"

# Al refrescar, usar los mismos scopes que setup_oauth.py (token emitido con todos)
def _scopes_for_refresh():
    try:
        from scripts.setup_oauth import GOOGLE_SCOPES
        return GOOGLE_SCOPES
    except ImportError:
        return [SCOPE_DOCS_READONLY]

# docs.google.com/document/d/DOC_ID/edit o /view o sin sufijo
_DOC_ID_RE = re.compile(
    r"https?://(?:www\.)?docs\.google\.com/document/d/([a-zA-Z0-9_-]+)(?:/[\w-]*)?",
    re.IGNORECASE,
)
# drive.google.com/open?id=ID o file/d/ID (el ID puede ser de un Doc)
_DRIVE_OPEN_RE = re.compile(
    r"https?://(?:drive|docs)\.google\.com/open\?id=([a-zA-Z0-9_-]+)",
    re.IGNORECASE,
)
_DRIVE_FILE_RE = re.compile(
    r"https?://drive\.google\.com/file/d/([a-zA-Z0-9_-]+)(?:/[\w-]*)?",
    re.IGNORECASE,
)


def _get_credentials():
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request

    client_id = os.getenv("GOOGLE_CLIENT_ID")
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
    refresh_token = os.getenv("GOOGLE_REFRESH_TOKEN")
    if not refresh_token or not client_id or not client_secret:
        raise ValueError("Faltan GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET o GOOGLE_REFRESH_TOKEN en .env")
    creds = Credentials(
        token=None,
        refresh_token=refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=client_id,
        client_secret=client_secret,
        scopes=_scopes_for_refresh(),
    )
    creds.refresh(Request())
    return creds


def extract_doc_ids_from_text(text: str) -> List[str]:
    """
    Extrae IDs de Google Docs de un texto (p. ej. descripción de evento).
    Acepta: docs.google.com/document/d/ID, drive.google.com/open?id=ID, drive.google.com/file/d/ID.
    Devuelve lista de IDs únicos en orden de aparición.
    """
    if not (text or "").strip():
        return []
    seen = set()
    out = []
    for regex in (_DOC_ID_RE, _DRIVE_OPEN_RE, _DRIVE_FILE_RE):
        for m in regex.finditer(text):
            doc_id = m.group(1)
            if doc_id not in seen:
                seen.add(doc_id)
                out.append(doc_id)
    return out


def _doc_content_to_plain_text(body: dict) -> str:
    """
    Convierte el body de un Document (Docs API) en texto plano.
    body tiene "content": [ { "paragraph": { "elements": [ { "textRun": { "content": "..." } } ] } }, ... ]
    """
    if not body:
        return ""
    parts = []
    for item in body.get("content") or []:
        if "paragraph" in item:
            for el in (item["paragraph"].get("elements") or []):
                run = el.get("textRun") or {}
                content = (run.get("content") or "").strip()
                if content:
                    parts.append(content)
        elif "table" in item:
            for row in (item["table"].get("tableRows") or []):
                row_texts = []
                for cell in (row.get("tableCells") or []):
                    for content_el in (cell.get("content") or []):
                        if "paragraph" in content_el:
                            for pe in (content_el["paragraph"].get("elements") or []):
                                tr = (pe.get("textRun") or {}).get("content") or ""
                                if tr.strip():
                                    row_texts.append(tr.strip())
                if row_texts:
                    parts.append(" | ".join(row_texts))
    return "\n".join(parts)


# Títulos de pestañas que consideramos "notas" o "transcripción" (case-insensitive, coincidencia parcial)
_TAB_TITLE_NOTES = ("notes", "notas")
_TAB_TITLE_TRANSCRIPTION = ("transcripción", "transcription")


def _is_notes_tab(title: str) -> bool:
    t = (title or "").strip().lower()
    return any(n in t for n in _TAB_TITLE_NOTES)


def _is_transcription_tab(title: str) -> bool:
    t = (title or "").strip().lower()
    return any(tr in t for tr in _TAB_TITLE_TRANSCRIPTION)


def _get_all_tabs_flat(tabs: list) -> list:
    """Recorre tabs y childTabs recursivamente; devuelve lista plana de tab dicts."""
    out = []
    for tab in tabs or []:
        out.append(tab)
        out.extend(_get_all_tabs_flat(tab.get("childTabs") or []))
    return out


def fetch_doc_plain_text(doc_id: str) -> Optional[str]:
    """
    Obtiene el contenido de un Google Doc como texto plano.
    Si el documento tiene pestañas (tabs), recopila Notas y Transcripción/Transcription.
    doc_id: el ID del documento (de la URL docs.google.com/document/d/DOC_ID/...).
    Devuelve None si no se puede leer (sin permiso, no existe, etc.).
    """
    try:
        from googleapiclient.discovery import build

        creds = _get_credentials()
        service = build("docs", "v1", credentials=creds)
        doc = service.documents().get(
            documentId=doc_id,
            includeTabsContent=True,
        ).execute()

        tabs = doc.get("tabs") or []
        if not tabs:
            # Sin tabs: contenido en document.body (legacy)
            body = doc.get("body") or {}
            return _doc_content_to_plain_text(body).strip() or None

        all_tabs = _get_all_tabs_flat(tabs)
        notes_parts = []
        transcription_parts = []

        for tab in all_tabs:
            props = tab.get("tabProperties") or {}
            title = (props.get("title") or "").strip()
            document_tab = tab.get("documentTab") or {}
            body = document_tab.get("body") or {}
            text = _doc_content_to_plain_text(body).strip()
            if not text:
                continue
            if _is_transcription_tab(title):
                transcription_parts.append(text)
            elif _is_notes_tab(title):
                notes_parts.append(text)

        # Orden: Notas primero, luego Transcripción
        sections = []
        if notes_parts:
            sections.append("=== Notas ===\n" + "\n".join(notes_parts))
        if transcription_parts:
            sections.append("=== Transcripción ===\n" + "\n".join(transcription_parts))
        if not sections:
            # Si no matcheó ningún tab por nombre, devolver todo el contenido del primer tab (legacy)
            first_tab = all_tabs[0] if all_tabs else {}
            body = (first_tab.get("documentTab") or {}).get("body") or {}
            return _doc_content_to_plain_text(body).strip() or None
        return "\n\n".join(sections)
    except Exception:
        return None
