"""Minimal reporting helpers for anomaly context."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Optional


def load_core_updates_in_range(
    start_date: str,
    end_date: str,
    csv_path: Optional[Path] = None,
) -> list[dict]:
    if csv_path is None:
        csv_path = Path(__file__).resolve().parents[2] / "data" / "google_core_updates.csv"
    if not csv_path.exists():
        return []
    out = []
    try:
        with open(csv_path, encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                d = (row.get("date") or "").strip()
                if not d or d < start_date or d > end_date:
                    continue
                out.append({"date": d, "title": (row.get("title") or "").strip()})
    except (OSError, csv.Error):
        pass
    return sorted(out, key=lambda x: x["date"], reverse=True)
