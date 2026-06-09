"""Normalización de URL compartida para el informe mensual SEO.

Centraliza la lógica de normalización que antes estaba duplicada en
cluster_metrics, sitemap_urls y gsc_url_inspection.
"""

from __future__ import annotations

from urllib.parse import urlparse, urlunparse


def normalize_url(url: str) -> str:
    """Quita trailing slash (excepto raíz) y fragmentos; devuelve URL completa.

    Las URL sin scheme (relativas) se devuelven tal cual para evitar pérdida de datos.
    """
    u = (url or "").strip()
    if not u:
        return ""
    parsed = urlparse(u)
    if not parsed.scheme:
        return u
    parsed = parsed._replace(fragment="")
    path = parsed.path or "/"
    if path != "/":
        path = path.rstrip("/")
    parsed = parsed._replace(path=path)
    return urlunparse(parsed)


def match_key(url: str) -> str:
    """Clave estable para deduplicar el sitemap y hacer joins con GA4/GSC/cluster.

    Coincide con :func:`normalize_url` (sin barra final salvo raíz, sin fragmento).
    """
    return normalize_url(url)


def sanitize_url_for_inspection(url: str) -> str:
    """Strip y quita fragmento; no altera el path (p. ej. conserva ``/`` final).

    Para URLs sin scheme (relativas) devuelve el string tal cual, igual que
    :func:`normalize_url`.
    """
    u = (url or "").strip()
    if not u:
        return ""
    parsed = urlparse(u)
    if not parsed.scheme:
        return u
    parsed = parsed._replace(fragment="")
    return urlunparse(parsed)
