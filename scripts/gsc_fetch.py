"""
Extracción de datos de Google Search Console para el informe mensual SEO.

Obtiene métricas (clicks, impressions, ctr, position) agregadas:
  - Por página (dimension: page)
  - Por página + query (dimensions: page, query)

Usa paginación con startRow para manejar propiedades con gran volumen.
El límite máximo de la API es 25 000 filas por request.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Dict, List

from googleapiclient.discovery import build

from scripts.google_auth import WEBMASTERS_SCOPE, get_credentials
from scripts.url_utils import normalize_url as _normalize_page_url
_GSC_ROW_LIMIT = 25_000


def _gsc_service():
    creds = get_credentials([WEBMASTERS_SCOPE])  # noqa: same scope
    return build("searchconsole", "v1", credentials=creds)


def _normalize_site_url_key(url: str) -> str:
    """Compara sitios GSC ignorando barra final (excepto sc-domain:)."""
    u = (url or "").strip()
    if u.startswith("sc-domain:"):
        return u
    return u.rstrip("/")


def _property_bucket(site_url: str) -> str:
    """
    Clasifica una propiedad GSC en su tipo:
      - "domain"     → empieza por "sc-domain:"
      - "url_prefix" → cualquier otro valor (http://, https://, …)

    Usar para restringir la búsqueda en sites.list() al mismo tipo de
    propiedad que la configurada en gsc-site-url, evitando que una
    propiedad de dominio "gane" sobre la URL-prefix del mismo sitio.
    """
    if (site_url or "").strip().startswith("sc-domain:"):
        return "domain"
    return "url_prefix"


def is_gsc_site_registered(site_url: str) -> bool:
    """True si ``site_url`` coincide con alguna entrada de sites.list() (mismo sitio y mismo tipo de propiedad)."""
    try:
        sites = _gsc_service().sites().list().execute().get("siteEntry", []) or []
    except Exception:
        return True
    want = _normalize_site_url_key(site_url)
    bucket = _property_bucket(site_url)
    for entry in sites:
        u = entry.get("siteUrl") or ""
        if _property_bucket(u) == bucket and _normalize_site_url_key(u) == want:
            return True
    return False


def resolve_gsc_site_url_from_account(site_url: str) -> str:
    """
    Devuelve la URL de propiedad tal como está registrada en Search Console
    (sites.list) si hay coincidencia; si no, devuelve el valor original.

    Solo se consideran entradas del mismo tipo de propiedad (url_prefix vs
    domain) que el valor configurado en gsc-site-url. Esto evita que la
    propiedad "sc-domain:" de un mismo sitio sobreescriba la URL-prefix
    cuando ambas existen en la cuenta, garantizando que las métricas
    siempre se extraen de la propiedad elegida explícitamente.
    """
    try:
        sites = _gsc_service().sites().list().execute().get("siteEntry", []) or []
    except Exception:
        return site_url
    want = _normalize_site_url_key(site_url)
    bucket = _property_bucket(site_url)
    for entry in sites:
        u = entry.get("siteUrl") or ""
        if _property_bucket(u) == bucket and _normalize_site_url_key(u) == want:
            return u
    return site_url


def _search_analytics_query_body(
    *,
    start_date: str,
    end_date: str,
    dimensions: List[str],
    row_limit: int,
    start_row: int,
) -> Dict[str, Any]:
    """
    Cuerpo base para searchAnalytics.query.

    Incluye siempre:
      - type=web — mismo ámbito que Rendimiento > resultados de búsqueda web (no Imágenes/Discover).
      - dataState=all — mismo valor por defecto que la API (incluye datos aún no finalizados en rangos recientes).
    """
    return {
        "startDate": start_date,
        "endDate": end_date,
        "dimensions": dimensions,
        "rowLimit": row_limit,
        "startRow": start_row,
        "type": "web",
        "dataState": "all",
    }


def diagnose_gsc_url_metrics(
    site_url: str,
    page_url: str,
    start_date: str,
    end_date: str,
) -> None:
    """
    Diagnóstico en consola: compara totales dimensión ``page`` vs suma de filas ``query``
    con filtro de página (mismos criterios que la API).

    Útil para reconciliar con la UI: la fila por URL en la pestaña Páginas debe
    coincidir con la dimensión ``page``; la suma de la tabla de consultas (filtrada
    por URL) suele ser menor por consultas no mostradas.
    """
    site_url = resolve_gsc_site_url_from_account(site_url)
    svc = _gsc_service()

    body_page = _search_analytics_query_body(
        start_date=start_date,
        end_date=end_date,
        dimensions=["page"],
        row_limit=10,
        start_row=0,
    )
    body_page["dimensionFilterGroups"] = [
        {
            "filters": [
                {
                    "dimension": "page",
                    "operator": "equals",
                    "expression": page_url.strip(),
                }
            ]
        }
    ]
    r1 = svc.searchanalytics().query(siteUrl=site_url, body=body_page).execute()
    row_p = (r1.get("rows") or [None])[0]

    start_row = 0
    sum_q_clicks = 0
    sum_q_imp = 0
    n_q = 0
    while True:
        body_q = _search_analytics_query_body(
            start_date=start_date,
            end_date=end_date,
            dimensions=["query"],
            row_limit=_GSC_ROW_LIMIT,
            start_row=start_row,
        )
        body_q["dimensionFilterGroups"] = [
            {
                "filters": [
                    {
                        "dimension": "page",
                        "operator": "equals",
                        "expression": page_url.strip(),
                    }
                ]
            }
        ]
        r2 = svc.searchanalytics().query(siteUrl=site_url, body=body_q).execute()
        rows = r2.get("rows") or []
        if not rows:
            break
        for r in rows:
            sum_q_clicks += int(r.get("clicks", 0))
            sum_q_imp += int(r.get("impressions", 0))
        n_q += len(rows)
        if len(rows) < _GSC_ROW_LIMIT:
            break
        start_row += len(rows)

    print(f"GSC diagnose  siteUrl={site_url!r}")
    print(f"  rango: {start_date} → {end_date}")
    print(f"  página: {page_url}")
    if row_p:
        print(
            "  dimensión [page] (filtro equals):  "
            f"clicks={int(row_p.get('clicks', 0))}  "
            f"impressions={int(row_p.get('impressions', 0))}  "
            f"ctr={row_p.get('ctr')}  position={row_p.get('position')}"
        )
    else:
        print("  dimensión [page]: (sin filas)")
    print(
        f"  suma tablas [query] filtrada por página:  clicks={sum_q_clicks}  "
        f"impressions={sum_q_imp}  (filas query={n_q})"
    )
    print(
        "  Nota: en GSC la fila de la pestaña Páginas usa el total por URL; "
        "la suma de consultas visibles puede ser menor."
    )


def _query_paginated(
    service,
    site_url: str,
    start_date: str,
    end_date: str,
    dimensions: List[str],
    *,
    row_limit: int = _GSC_ROW_LIMIT,
) -> List[Dict[str, Any]]:
    """
    searchAnalytics.query con paginación por startRow.

    Args:
        service: Servicio GSC autenticado.
        site_url: Propiedad GSC (p. ej. 'https://www.example.com/').
        start_date: Fecha inicio YYYY-MM-DD.
        end_date: Fecha fin YYYY-MM-DD.
        dimensions: Lista de dimensiones (e.g. ['page'], ['query']).
        row_limit: Filas por petición (máx. 25 000 según API).

    Returns:
        Lista de dicts con keys, clicks, impressions, ctr, position.
    """
    start_row = 0
    all_rows: List[Dict[str, Any]] = []
    while True:
        body = _search_analytics_query_body(
            start_date=start_date,
            end_date=end_date,
            dimensions=dimensions,
            row_limit=row_limit,
            start_row=start_row,
        )
        resp = (
            service.searchanalytics()
            .query(siteUrl=site_url, body=body)
            .execute()
        )
        rows = resp.get("rows", []) or []
        if not rows:
            break
        all_rows.extend(rows)
        if len(rows) < row_limit:
            break
        start_row += len(rows)
    return all_rows


def _parse_rows(raw_rows: List[Dict[str, Any]], key_names: List[str]) -> List[Dict[str, Any]]:
    """Transforma las filas crudas de la API en dicts con nombres de campo explícitos."""
    result: List[Dict[str, Any]] = []
    for r in raw_rows:
        keys = r.get("keys", [])
        row: Dict[str, Any] = {}
        for i, name in enumerate(key_names):
            row[name] = keys[i] if i < len(keys) else ""
        row["clicks"] = int(r.get("clicks", 0))
        row["impressions"] = int(r.get("impressions", 0))
        row["ctr"] = round(float(r.get("ctr", 0)), 4)
        row["position"] = round(float(r.get("position", 0)), 2)
        result.append(row)
    return result


def filter_gsc_page_rows_to_sitemap(
    rows: List[Dict[str, Any]],
    sitemap_urls: List[str],
) -> List[Dict[str, Any]]:
    """Limita filas Search Analytics ``page`` a URLs del sitemap (normalizadas).

    Si ``sitemap_urls`` está vacío, devuelve ``rows`` sin cambios (alcance =
    propiedad completa).
    """
    if not sitemap_urls:
        return rows
    allowed = {_normalize_page_url(u) for u in sitemap_urls if u}
    if not allowed:
        return rows
    out = [r for r in rows if _normalize_page_url(r.get("page", "")) in allowed]
    out.sort(key=lambda x: int(x.get("clicks", 0)), reverse=True)
    return out


def filter_gsc_by_month_to_sitemap(
    by_month: Dict[str, List[Dict[str, Any]]],
    sitemap_urls: List[str],
) -> Dict[str, List[Dict[str, Any]]]:
    """Aplica :func:`filter_gsc_page_rows_to_sitemap` a cada lista mensual."""
    if not sitemap_urls:
        return by_month
    return {mk: filter_gsc_page_rows_to_sitemap(rows, sitemap_urls) for mk, rows in by_month.items()}


def fetch_query_count(
    site_url: str,
    start_date: str,
    end_date: str,
) -> int:
    """
    Devuelve el número total de queries únicas en GSC para el rango de fechas.

    Consulta la dimensión 'query' con paginación completa y cuenta las filas.
    El valor no se almacena: solo se devuelve el conteo.
    """
    site_url = resolve_gsc_site_url_from_account(site_url)
    service = _gsc_service()
    raw = _query_paginated(service, site_url, start_date, end_date, dimensions=["query"])
    return len(raw)


def fetch_by_page(
    site_url: str,
    start_date: str,
    end_date: str,
) -> List[Dict[str, Any]]:
    """
    Métricas GSC agregadas por página para el rango de fechas.

    Devuelve lista de dicts: {page, clicks, impressions, ctr, position}.
    Ordenadas por clicks descendente.

    Nota (reconciliación con la UI de GSC): la API con dimensión ``page`` devuelve
    los totales a nivel URL que **incluyen** tráfico atribuido a consultas no
    mostradas en el desglose (p. ej. consultas anonimizadas). Por eso **no**
    coinciden con la suma manual de filas ``page``+``query`` para la misma URL ni
    con totales basados solo en consultas visibles en la tabla; es el
    comportamiento documentado de Search Console.
    """
    site_url = resolve_gsc_site_url_from_account(site_url)
    service = _gsc_service()
    raw = _query_paginated(service, site_url, start_date, end_date, dimensions=["page"])
    rows = _parse_rows(raw, ["page"])
    rows.sort(key=lambda x: x["clicks"], reverse=True)
    return rows


def fetch_by_date_and_page(
    site_url: str,
    start_date: str,
    end_date: str,
) -> List[Dict[str, Any]]:
    """
    Métricas GSC por día y página (dimensión ``date`` + ``page``).

    Devuelve lista de dicts: {date, page, clicks, impressions, ctr, position}.
    ``date`` en formato YYYY-MM-DD según la API.
    """
    site_url = resolve_gsc_site_url_from_account(site_url)
    service = _gsc_service()
    raw = _query_paginated(service, site_url, start_date, end_date, dimensions=["date", "page"])
    return _parse_rows(raw, ["date", "page"])


def fetch_by_date_and_query(
    site_url: str,
    start_date: str,
    end_date: str,
) -> List[Dict[str, Any]]:
    """
    Métricas GSC por día y query (dimensión ``date`` + ``query``).

    Devuelve lista de dicts: {date, query, clicks, impressions, ctr, position}.
    """
    site_url = resolve_gsc_site_url_from_account(site_url)
    service = _gsc_service()
    raw = _query_paginated(service, site_url, start_date, end_date, dimensions=["date", "query"])
    return _parse_rows(raw, ["date", "query"])


def aggregate_gsc_by_page_per_month(
    date_page_rows: List[Dict[str, Any]],
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Agrupa filas ``fetch_by_date_and_page`` por mes civil (YYYY-MM) y por ``page``,
    sumando impresiones y clicks (misma forma que ``fetch_by_page`` por mes).

    ``position`` y ``ctr`` se recalculan de forma aproximada (ctr = clicks/impressions).
    """
    acc: Dict[tuple[str, str], Dict[str, float]] = defaultdict(
        lambda: {"impressions": 0.0, "clicks": 0.0}
    )
    for r in date_page_rows:
        d = (r.get("date") or "")[:10]
        if len(d) < 10:
            continue
        ym = d[:7]
        page = r.get("page") or ""
        k = (ym, page)
        acc[k]["impressions"] += float(r.get("impressions", 0))
        acc[k]["clicks"] += float(r.get("clicks", 0))

    out: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for (ym, page), met in acc.items():
        imp = int(met["impressions"])
        clk = int(met["clicks"])
        ctr = round(clk / imp, 4) if imp else 0.0
        out[ym].append(
            {
                "page": page,
                "clicks": clk,
                "impressions": imp,
                "ctr": ctr,
                "position": 0.0,
            }
        )
    for ym in out:
        out[ym].sort(key=lambda x: x["clicks"], reverse=True)
    return dict(out)


def fetch_by_page_query(
    site_url: str,
    start_date: str,
    end_date: str,
) -> List[Dict[str, Any]]:
    """
    Métricas GSC por combinación página+query para el rango de fechas.

    Devuelve lista de dicts: {page, query, clicks, impressions, ctr, position}.
    Necesario para contar queries únicas filtradas a un conjunto de URLs (p. ej. el sitemap).

    Nota: el volumen de filas es mucho mayor que fetch_by_page (puede superar
    el millón en propiedades grandes). La paginación de 25 000 filas por request
    gestiona esto automáticamente.
    """
    site_url = resolve_gsc_site_url_from_account(site_url)
    service = _gsc_service()
    raw = _query_paginated(service, site_url, start_date, end_date, dimensions=["page", "query"])
    return _parse_rows(raw, ["page", "query"])


def fetch_by_date_page_query(
    site_url: str,
    start_date: str,
    end_date: str,
) -> List[Dict[str, Any]]:
    """
    Métricas GSC por fecha + página + consulta (mismo rango que el informe).

    Devuelve dicts con ``date``, ``page``, ``query``, ``clicks``, ``impressions``, ``ctr``, ``position``.
    Sirve para derivar en cliente el agregado de periodo (como :func:`fetch_by_page_query`)
    y el desglose mensual sin N llamadas ``fetch_by_page_query`` por mes.
    """
    site_url = resolve_gsc_site_url_from_account(site_url)
    service = _gsc_service()
    raw = _query_paginated(
        service, site_url, start_date, end_date, dimensions=["date", "page", "query"]
    )
    return _parse_rows(raw, ["date", "page", "query"])


def _merge_page_query_rows(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Agrupa filas con la misma (page, query) sumando clicks/impressions; recalcula ctr y position."""
    acc: Dict[tuple[str, str], Dict[str, float]] = {}
    for r in rows:
        page = r.get("page") or ""
        query = r.get("query") or ""
        k = (page, query)
        if k not in acc:
            acc[k] = {"clicks": 0.0, "impressions": 0.0, "pos_imp": 0.0}
        clk = float(r.get("clicks", 0))
        imp = float(r.get("impressions", 0))
        pos = float(r.get("position", 0))
        acc[k]["clicks"] += clk
        acc[k]["impressions"] += imp
        acc[k]["pos_imp"] += pos * imp
    out: List[Dict[str, Any]] = []
    for (page, query), met in acc.items():
        imp = int(met["impressions"])
        clk = int(met["clicks"])
        ctr = round(clk / imp, 4) if imp else 0.0
        pos_avg = round(met["pos_imp"] / imp, 2) if imp else 0.0
        out.append(
            {
                "page": page,
                "query": query,
                "clicks": clk,
                "impressions": imp,
                "ctr": ctr,
                "position": pos_avg,
            }
        )
    return out


def merge_date_page_query_to_period(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Convierte filas ``date``+``page``+``query`` en el mismo formato que :func:`fetch_by_page_query`
    sobre el periodo completo (sin dimensión fecha).
    """
    return _merge_page_query_rows(rows)


def partition_date_page_query_by_month(
    rows: List[Dict[str, Any]],
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Particiona filas ``date``+``page``+``query`` por mes civil (``YYYY-MM``).

    Cada mes contiene listas con la misma forma que :func:`fetch_by_page_query` para ese recorte.
    """
    by_month: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for r in rows:
        d = (r.get("date") or "")[:10]
        if len(d) < 10:
            continue
        ym = d[:7]
        by_month[ym].append(
            {
                "page": r.get("page", ""),
                "query": r.get("query", ""),
                "clicks": int(r.get("clicks", 0)),
                "impressions": int(r.get("impressions", 0)),
                "ctr": float(r.get("ctr", 0)),
                "position": float(r.get("position", 0)),
            }
        )
    merged: Dict[str, List[Dict[str, Any]]] = {}
    for ym, chunk in by_month.items():
        merged[ym] = _merge_page_query_rows(chunk)
    return merged


