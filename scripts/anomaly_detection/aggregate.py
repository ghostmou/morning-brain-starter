"""Aggregate daily metrics by collection."""

from __future__ import annotations

from collections import defaultdict
from typing import Any


def _to_float(v: Any) -> float:
    if v is None or v == "":
        return 0.0
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def sum_by_date(rows: list[dict[str, Any]], metrics: list[str]) -> dict[str, dict[str, float]]:
    """date -> {metric: sum}."""
    out: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    for row in rows:
        d = (row.get("date") or "").strip()
        if not d:
            continue
        for m in metrics:
            out[d][m] += _to_float(row.get(m))
    return {d: dict(vals) for d, vals in out.items()}


def series_for_metric(daily: dict[str, dict[str, float]], metric: str) -> dict[str, float]:
    return {d: vals.get(metric, 0.0) for d, vals in sorted(daily.items())}
