"""
Sync google_core_updates.csv from Google Search Status Dashboard incidents.json.
"""

from __future__ import annotations

import csv
import json
import logging
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import URLError
from urllib.request import Request, urlopen

logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CSV = REPO_ROOT / "data" / "google_core_updates.csv"
DEFAULT_SYNC_MARKER = REPO_ROOT / "data" / ".core_updates_synced_at"
INCIDENTS_URL = "https://status.search.google.com/incidents.json"
RANKING_SERVICE = "Ranking"
USER_AGENT = "morning-brain-starter/1.0 (google-core-updates-sync)"


@dataclass(frozen=True)
class CoreUpdateRow:
    date: str
    title: str

    @property
    def key(self) -> tuple[str, str]:
        return (self.date, self.title)


def _parse_iso_date(iso: str) -> str:
    if not iso:
        return ""
    return iso.strip()[:10]


def incident_to_row(incident: dict[str, Any]) -> CoreUpdateRow | None:
    service = (incident.get("service_name") or "").strip()
    if service != RANKING_SERVICE:
        products = incident.get("affected_products") or []
        if not any((p.get("title") or "") == RANKING_SERVICE for p in products):
            return None
    date = _parse_iso_date(incident.get("begin") or incident.get("created") or "")
    title = (incident.get("external_desc") or "").strip()
    if not date or not title:
        return None
    title = re.sub(r"<[^>]+>", "", title).strip()
    return CoreUpdateRow(date=date, title=title)


def fetch_ranking_incidents(url: str = INCIDENTS_URL, timeout: float = 30.0) -> list[CoreUpdateRow]:
    req = Request(url, headers={"User-Agent": USER_AGENT})
    with urlopen(req, timeout=timeout) as resp:
        raw = resp.read().decode("utf-8")
    data = json.loads(raw)
    if not isinstance(data, list):
        raise RuntimeError("incidents.json: expected JSON array")
    rows: list[CoreUpdateRow] = []
    seen: set[tuple[str, str]] = set()
    for item in data:
        if not isinstance(item, dict):
            continue
        row = incident_to_row(item)
        if row and row.key not in seen:
            seen.add(row.key)
            rows.append(row)
    return rows


def load_csv_rows(path: Path) -> list[CoreUpdateRow]:
    if not path.exists():
        return []
    rows: list[CoreUpdateRow] = []
    with open(path, encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for r in reader:
            d = (r.get("date") or "").strip()
            t = (r.get("title") or "").strip()
            if d and t:
                rows.append(CoreUpdateRow(date=d, title=t))
    return rows


def merge_rows(existing: list[CoreUpdateRow], remote: list[CoreUpdateRow]) -> list[CoreUpdateRow]:
    by_key: dict[tuple[str, str], CoreUpdateRow] = {r.key: r for r in existing}
    for r in remote:
        by_key[r.key] = r
    merged = list(by_key.values())
    merged.sort(key=lambda x: x.date, reverse=True)
    return merged


def write_csv(path: Path, rows: list[CoreUpdateRow]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["date", "title"])
        for r in rows:
            w.writerow([r.date, r.title])


def write_sync_marker(marker_path: Path) -> None:
    marker_path.parent.mkdir(parents=True, exist_ok=True)
    marker_path.write_text(datetime.now(timezone.utc).isoformat(), encoding="utf-8")


def should_skip_sync(marker_path: Path, max_age_hours: float) -> bool:
    if max_age_hours <= 0 or not marker_path.exists():
        return False
    try:
        text = marker_path.read_text(encoding="utf-8").strip()
        last = datetime.fromisoformat(text.replace("Z", "+00:00"))
        if last.tzinfo is None:
            last = last.replace(tzinfo=timezone.utc)
        age_h = (datetime.now(timezone.utc) - last).total_seconds() / 3600
        return age_h < max_age_hours
    except (OSError, ValueError):
        return False


def sync_core_updates(
    output_csv: Path | None = None,
    marker_path: Path | None = None,
    *,
    dry_run: bool = False,
    max_age_hours: float = 0,
    incidents_url: str = INCIDENTS_URL,
) -> dict[str, Any]:
    csv_path = output_csv or DEFAULT_CSV
    marker = marker_path or DEFAULT_SYNC_MARKER
    if should_skip_sync(marker, max_age_hours):
        return {
            "skipped": True,
            "reason": f"sync younger than {max_age_hours}h",
            "csv_path": str(csv_path),
        }
    existing = load_csv_rows(csv_path)
    remote = fetch_ranking_incidents(url=incidents_url)
    merged = merge_rows(existing, remote)
    added = len(merged) - len({r.key for r in existing})
    result: dict[str, Any] = {
        "skipped": False,
        "csv_path": str(csv_path),
        "existing_count": len(existing),
        "remote_count": len(remote),
        "merged_count": len(merged),
        "added_or_updated": max(0, added),
        "dry_run": dry_run,
    }
    if not dry_run:
        write_csv(csv_path, merged)
        write_sync_marker(marker)
    return result


if __name__ == "__main__":
    import argparse

    logging.basicConfig(level=logging.INFO)
    p = argparse.ArgumentParser(description="Sync Google core updates CSV")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--max-age-hours", type=float, default=0)
    args = p.parse_args()
    r = sync_core_updates(dry_run=args.dry_run, max_age_hours=args.max_age_hours)
    print(r)
