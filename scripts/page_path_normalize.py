"""
Normalize page paths for alignment between GA4 (pagePath) and GSC (page dimension URLs).

GA4 exports store relative paths without trailing slash except root ``/``.
"""

from __future__ import annotations

from urllib.parse import unquote, urlparse


def normalize_ga4_path(path: str) -> str:
    """Match GA4 export: strip trailing slash except keep ``/`` for root."""
    if not path or path == "(other)" or path == "(not set)":
        return path
    return path.rstrip("/") or "/"


def gsc_page_url_to_page_path(page_url: str, *, strip_query: bool = True) -> str:
    """
    Turn GSC ``page`` dimension (full URL) into the same ``page_path`` key as GA4 CSVs.

    Decodes percent-encoding in the path. Query string is dropped when strip_query is True.
    """
    raw = (page_url or "").strip()
    if not raw:
        return "/"
    parsed = urlparse(raw)
    path = parsed.path or "/"
    path = unquote(path) or "/"
    if not strip_query and parsed.query:
        path = f"{path}?{parsed.query}"
    return normalize_ga4_path(path)

