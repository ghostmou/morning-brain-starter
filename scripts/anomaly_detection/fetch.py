"""Load GA4/GSC daily rows from synthetic CSV or live APIs."""

from __future__ import annotations

import csv
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)


def _read_csv(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    with open(path, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def load_synthetic_bundle(demo_dir: Path) -> dict[str, list[dict[str, Any]]]:
    return {
        "ga4": _read_csv(demo_dir / "ga4_daily.csv"),
        "gsc_page": _read_csv(demo_dir / "gsc_page_daily.csv"),
        "gsc_query": _read_csv(demo_dir / "gsc_query_daily.csv"),
    }


def date_window(end_date: str, days: int = 90) -> tuple[str, str]:
    end = datetime.strptime(end_date, "%Y-%m-%d")
    start = (end - timedelta(days=days - 1)).strftime("%Y-%m-%d")
    return start, end_date


def filter_rows_by_date(rows: list[dict[str, Any]], end_date: str, days: int = 90) -> list[dict[str, Any]]:
    if not end_date:
        return rows
    start, _ = date_window(end_date, days)
    return [r for r in rows if start <= (r.get("date") or "") <= end_date]


def _normalize_ga4_date(raw: str) -> str:
    s = (raw or "").strip()
    if len(s) == 8 and s.isdigit():
        return f"{s[:4]}-{s[4:6]}-{s[6:8]}"
    return s[:10]


def _load_client_meta(client_dir: Path) -> dict[str, Any]:
    path = client_dir / "client.yaml"
    if not path.exists():
        return {}
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def _infer_gsc_site_url(meta: dict[str, Any]) -> str:
    url = (meta.get("gsc_site_url") or "").strip()
    if url:
        return url
    for domain in meta.get("email_domains") or []:
        d = (domain or "").strip()
        if d and "@" not in d:
            return f"sc-domain:{d}"
    return ""


def _fetch_ga4_daily(property_id: str, start_date: str, end_date: str) -> list[dict[str, Any]]:
    from google.analytics.data_v1beta.services.beta_analytics_data import BetaAnalyticsDataClient
    from google.analytics.data_v1beta.types import DateRange, Dimension, Metric, RunReportRequest

    from scripts.google_auth import ANALYTICS_READONLY_SCOPE, get_credentials
    from scripts.page_path_normalize import normalize_ga4_path

    creds = get_credentials([ANALYTICS_READONLY_SCOPE])
    client = BetaAnalyticsDataClient(credentials=creds)
    prop = f"properties/{property_id}"
    out: list[dict[str, Any]] = []
    offset = 0
    limit = 100_000
    while True:
        req = RunReportRequest(
            property=prop,
            dimensions=[Dimension(name="date"), Dimension(name="pagePath")],
            metrics=[Metric(name="sessions"), Metric(name="conversions")],
            date_ranges=[DateRange(start_date=start_date, end_date=end_date)],
            limit=limit,
            offset=offset,
        )
        response = client.run_report(request=req)
        if not response.rows:
            break
        for row in response.rows:
            d = _normalize_ga4_date(row.dimension_values[0].value)
            path = normalize_ga4_path((row.dimension_values[1].value or "").strip())
            if path == "(other)":
                continue
            out.append(
                {
                    "date": d,
                    "page_path": path,
                    "sessions": int(row.metric_values[0].value or "0"),
                    "conversions": float(row.metric_values[1].value or "0"),
                }
            )
        if len(response.rows) < limit:
            break
        offset += len(response.rows)
    return out


def load_live_bundle(client_dir: Path, report_date: str, *, days: int = 90) -> dict[str, list[dict[str, Any]]]:
    """Fetch GA4 + GSC daily rows for the anomaly window ending on report_date."""
    from scripts.gsc_fetch import (
        fetch_by_date_and_page,
        fetch_by_date_and_query,
        resolve_gsc_site_url_from_account,
    )

    meta = _load_client_meta(client_dir)
    start_date, end_date = date_window(report_date, days)
    bundle: dict[str, list[dict[str, Any]]] = {"ga4": [], "gsc_page": [], "gsc_query": []}

    property_id = str(meta.get("ga4_property_id") or "").strip()
    if property_id:
        logger.info("GA4 live fetch property=%s %s..%s", property_id, start_date, end_date)
        bundle["ga4"] = _fetch_ga4_daily(property_id, start_date, end_date)
    else:
        logger.warning("No ga4_property_id in %s/client.yaml", client_dir)

    gsc_site = _infer_gsc_site_url(meta)
    if gsc_site:
        from scripts.search_console.fetch_performance import _get_service, fetch_daily_traffic

        resolved = resolve_gsc_site_url_from_account(gsc_site)
        logger.info("GSC live fetch site=%s %s..%s", resolved, start_date, end_date)
        svc = _get_service()
        site_daily = fetch_daily_traffic(svc, resolved, start_date, end_date)
        bundle["gsc_site_daily"] = [
            {
                "date": r["date"],
                "clicks": r["clicks"],
                "impressions": r["impressions"],
                "position": r.get("position", 0),
            }
            for r in site_daily
        ]
        bundle["gsc_page"] = fetch_by_date_and_page(resolved, start_date, end_date)
        bundle["gsc_query"] = fetch_by_date_and_query(resolved, start_date, end_date)
    else:
        logger.warning("No gsc_site_url (or email_domains) in %s/client.yaml", client_dir)

    return bundle
