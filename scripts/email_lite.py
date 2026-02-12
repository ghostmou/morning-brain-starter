"""
Sincronizar emails recientes (Gmail). Opcional: solo si hay scope Gmail y config/email.yaml.
Devuelve lista de metadatos para contexto/bitácora.
"""

import os
import sys
from pathlib import Path

_project_root = Path(__file__).resolve().parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from scripts.credentials import load_env

load_env()


def _get_credentials():
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request

    client_id = os.getenv("GOOGLE_CLIENT_ID")
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
    refresh_token = os.getenv("GOOGLE_REFRESH_TOKEN")
    if not refresh_token or not client_id or not client_secret:
        return None
    try:
        from scripts.setup_oauth import GOOGLE_SCOPES
        use_scopes = GOOGLE_SCOPES
    except ImportError:
        use_scopes = [
            "https://www.googleapis.com/auth/calendar.readonly",
            "https://www.googleapis.com/auth/gmail.readonly",
        ]
    creds = Credentials(
        token=None,
        refresh_token=refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=client_id,
        client_secret=client_secret,
        scopes=use_scopes,
    )
    try:
        creds.refresh(Request())
    except Exception:
        return None
    return creds


def get_email_config() -> dict:
    config_path = _project_root / "config" / "email.yaml"
    if not config_path.exists():
        return {}
    import yaml
    with open(config_path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def fetch_recent_emails(max_messages: int = 20, label: str = "INBOX") -> list:
    """Lista de correos recientes (id, subject, from, date)."""
    creds = _get_credentials()
    if not creds:
        return []

    try:
        from googleapiclient.discovery import build
        service = build("gmail", "v1", credentials=creds)
        results = service.users().messages().list(
            userId="me",
            maxResults=max_messages,
            labelIds=[label] if label else ["INBOX"],
        ).execute()
        messages = results.get("messages", [])
        out = []
        for m in messages:
            msg = service.users().messages().get(userId="me", id=m["id"], format="metadata").execute()
            headers = {h["name"]: h["value"] for h in msg.get("payload", {}).get("headers", [])}
            out.append({
                "id": m["id"],
                "subject": headers.get("Subject", ""),
                "from": headers.get("From", ""),
                "date": headers.get("Date", ""),
            })
        return out
    except Exception:
        return []


def _load_fake_emails_if_demo() -> list:
    """Si existe config/demo_gmail_fake.yaml (fichero local, gitignored), devuelve emails fake para demo."""
    flag = _project_root / "config" / "demo_gmail_fake.yaml"
    fake_path = _project_root / "config" / "demo" / "emails_fake.json"
    if not flag.exists() or not fake_path.exists():
        return []
    import json
    try:
        data = json.loads(fake_path.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except Exception:
        return []


def get_recent_emails_if_configured() -> list:
    """Solo ejecuta si existe config/email.yaml y Gmail está disponible.
    Si existe config/demo_gmail_fake.yaml (gitignored), devuelve datos fake para demo sin llamar a Gmail."""
    config = get_email_config()
    if not config:
        return []
    fake = _load_fake_emails_if_demo()
    if fake:
        return fake
    label = config.get("label") or "INBOX"
    max_messages = config.get("max_messages", 20)
    return fetch_recent_emails(max_messages=max_messages, label=label)


if __name__ == "__main__":
    load_env()
    emails = get_recent_emails_if_configured()
    print("Emails recientes:", len(emails))
    for e in emails[:5]:
        print(" ", e["subject"][:50], e["from"])
