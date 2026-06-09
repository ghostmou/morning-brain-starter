"""External context: Google core updates in range."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from scripts.reporting.report_logic import load_core_updates_in_range


def core_updates_for_window(
    anomaly_date: str,
    *,
    days_before: int = 21,
    days_after: int = 3,
    csv_path: Path | None = None,
) -> list[dict[str, Any]]:
    from datetime import datetime, timedelta

    end = datetime.strptime(anomaly_date, "%Y-%m-%d")
    start = (end - timedelta(days=days_before)).strftime("%Y-%m-%d")
    end_s = (end + timedelta(days=days_after)).strftime("%Y-%m-%d")
    return load_core_updates_in_range(start, end_s, csv_path=csv_path)
