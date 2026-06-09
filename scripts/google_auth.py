"""Google OAuth from resources/secrets/.env (refresh token)."""

from __future__ import annotations

import os
from typing import List

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

from scripts.credentials import load_env

ANALYTICS_READONLY_SCOPE = "https://www.googleapis.com/auth/analytics.readonly"
WEBMASTERS_SCOPE = "https://www.googleapis.com/auth/webmasters.readonly"


def get_credentials(required_scopes: List[str] | None = None) -> Credentials:
    load_env()
    client_id = os.getenv("GOOGLE_CLIENT_ID")
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
    refresh_token = os.getenv("GOOGLE_REFRESH_TOKEN")
    if not refresh_token or not client_id or not client_secret:
        raise ValueError(
            "Missing GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET or GOOGLE_REFRESH_TOKEN in .env"
        )
    try:
        from scripts.setup_oauth import GOOGLE_SCOPES

        use_scopes = GOOGLE_SCOPES
    except ImportError:
        use_scopes = required_scopes or [WEBMASTERS_SCOPE]
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
