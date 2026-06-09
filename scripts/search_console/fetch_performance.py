"""
Fetch Google Search Console performance data (clicks, impressions, queries) for a site.
Writes CSV suitable for reports. Uses OAuth (webmasters.readonly).

Usage:
  .venv/bin/python -m scripts.search_console.fetch_performance \\
    --site-url "https://example.com/" --start-date 2025-01-01 --end-date 2026-03-18 \\
    --output-dir ./data/gsc-export
"""

from __future__ import annotations

import argparse
import csv
from datetime import datetime
from pathlib import Path

from googleapiclient.discovery import build

from scripts.google_auth import WEBMASTERS_SCOPE, get_credentials


def _get_service():
    creds = get_credentials([WEBMASTERS_SCOPE])
    return build("searchconsole", "v1", credentials=creds)


def list_sites(service) -> list[dict]:
    """List sites (properties) the user has access to (Search Console v1 has no list; return empty)."""
    try:
        # searchconsole v1 does not expose sites.list in the same way; rely on user-provided siteUrl
        return []
    except Exception:
        return []


def query_search_analytics(
    service,
    site_url: str,
    start_date: str,
    end_date: str,
    dimensions: list[str] | None = None,
    row_limit: int = 25000,
    dimension_filter_groups: list[dict] | None = None,
) -> list[dict]:
    """Run searchAnalytics.query; returns list of rows with keys, clicks, impressions, ctr, position."""
    body = {
        "startDate": start_date,
        "endDate": end_date,
        "rowLimit": row_limit,
    }
    if dimensions:
        body["dimensions"] = dimensions
    if dimension_filter_groups:
        body["dimensionFilterGroups"] = dimension_filter_groups
    try:
        resp = (
            service.searchanalytics()
            .query(siteUrl=site_url, body=body)
            .execute()
        )
        return resp.get("rows", []) or []
    except Exception as e:
        raise RuntimeError(f"GSC query failed for {site_url}: {e}") from e


def fetch_daily_traffic(
    service, site_url: str, start_date: str, end_date: str
) -> list[dict]:
    """Fetch daily aggregates (dimension: date). Optionally with filter (e.g. query contains X)."""
    return _fetch_daily_impl(service, site_url, start_date, end_date, dimension_filter_groups=None)


def _fetch_daily_impl(
    service,
    site_url: str,
    start_date: str,
    end_date: str,
    dimension_filter_groups: list[dict] | None = None,
) -> list[dict]:
    rows = query_search_analytics(
        service,
        site_url,
        start_date,
        end_date,
        dimensions=["date"],
        dimension_filter_groups=dimension_filter_groups,
    )
    out = []
    for r in rows:
        keys = r.get("keys", [])
        out.append({
            "date": keys[0] if keys else "",
            "clicks": int(r.get("clicks", 0)),
            "impressions": int(r.get("impressions", 0)),
            "ctr": round(float(r.get("ctr", 0)), 4),
            "position": round(float(r.get("position", 0)), 2),
        })
    return out


# Brand terms for Natursun (incl. misspellings)
GSC_BRAND_QUERY_TERMS = ["natursun", "natursan", "natursum"]


def fetch_daily_traffic_brand(
    service, site_url: str, start_date: str, end_date: str
) -> list[dict]:
    """Fetch daily traffic for brand queries only (sum of natursun, natursan, natursum)."""
    by_date: dict[str, dict] = {}
    for term in GSC_BRAND_QUERY_TERMS:
        filter_groups = [
            {
                "groupType": "and",
                "filters": [
                    {"dimension": "query", "operator": "contains", "expression": term}
                ],
            }
        ]
        rows = _fetch_daily_impl(
            service, site_url, start_date, end_date, dimension_filter_groups=filter_groups
        )
        for r in rows:
            d = r["date"]
            if d not in by_date:
                by_date[d] = {"date": d, "clicks": 0, "impressions": 0}
            by_date[d]["clicks"] += r["clicks"]
            by_date[d]["impressions"] += r["impressions"]
    return [by_date[d] for d in sorted(by_date.keys())]


def fetch_top_queries(
    service, site_url: str, start_date: str, end_date: str, limit: int = 500
) -> list[dict]:
    """Fetch top queries by clicks (dimension: query)."""
    rows = query_search_analytics(
        service, site_url, start_date, end_date,
        dimensions=["query"],
        row_limit=limit,
    )
    out = []
    for r in rows:
        keys = r.get("keys", [])
        out.append({
            "query": keys[0] if keys else "",
            "clicks": int(r.get("clicks", 0)),
            "impressions": int(r.get("impressions", 0)),
            "ctr": round(float(r.get("ctr", 0)), 4),
            "position": round(float(r.get("position", 0)), 2),
        })
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description="Fetch GSC performance data")
    parser.add_argument("--site-url", required=True, help="GSC property URL (e.g. https://www.natursun.es/ or sc-domain:natursun.es)")
    parser.add_argument("--start-date", default="2025-01-01", help="Start date YYYY-MM-DD")
    parser.add_argument("--end-date", default=None, help="End date YYYY-MM-DD (default: today)")
    parser.add_argument("--output-dir", required=True, help="Directory to write CSV files")
    parser.add_argument("--list-sites", action="store_true", help="Only list accessible sites and exit")
    args = parser.parse_args()

    end_date = args.end_date or datetime.now().strftime("%Y-%m-%d")
    out_dir = Path(args.output_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    service = _get_service()

    if args.list_sites:
        sites = list_sites(service)
        print("Sites (properties) accessible:")
        for s in sites:
            print(f"  {s.get('siteUrl', '')}")
        return 0

    site_url = args.site_url.strip()
    start_date = args.start_date.strip()
    # Validate dates
    if start_date >= end_date:
        print("start-date must be before end-date", flush=True)
        return 1

    # Daily performance (total)
    daily = fetch_daily_traffic(service, site_url, start_date, end_date)
    daily_by_date = {r["date"]: r for r in daily} if daily else {}

    # Daily performance brand (natursun, natursan, natursum)
    daily_brand = fetch_daily_traffic_brand(service, site_url, start_date, end_date)
    brand_by_date = {r["date"]: r for r in daily_brand} if daily_brand else {}

    daily_path = out_dir / "gsc_daily.csv"
    if daily_by_date:
        rows_out = []
        for date in sorted(daily_by_date.keys()):
            t = daily_by_date[date]
            b = brand_by_date.get(date, {"clicks": 0, "impressions": 0})
            rows_out.append({
                "date": date,
                "clicks": t["clicks"],
                "impressions": t["impressions"],
                "ctr": t.get("ctr", 0),
                "position": t.get("position", 0),
                "clicks_brand": b["clicks"],
                "impressions_brand": b["impressions"],
                "clicks_nobrand": t["clicks"] - b["clicks"],
                "impressions_nobrand": t["impressions"] - b["impressions"],
            })
        with open(daily_path, "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(
                f,
                fieldnames=[
                    "date", "clicks", "impressions", "ctr", "position",
                    "clicks_brand", "impressions_brand", "clicks_nobrand", "impressions_nobrand",
                ],
            )
            w.writeheader()
            w.writerows(rows_out)
        print(f"Wrote {len(rows_out)} rows to {daily_path} (incl. marca vs no marca)")
    else:
        print("No daily data returned from GSC", flush=True)

    # Top queries
    queries = fetch_top_queries(service, site_url, start_date, end_date)
    queries_path = out_dir / "gsc_queries.csv"
    if queries:
        with open(queries_path, "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=["query", "clicks", "impressions", "ctr", "position"])
            w.writeheader()
            w.writerows(queries)
        print(f"Wrote {len(queries)} rows to {queries_path}")
    else:
        print("No query data returned from GSC", flush=True)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
