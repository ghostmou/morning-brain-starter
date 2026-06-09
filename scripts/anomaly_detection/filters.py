"""Row matchers for query/page collections."""

from __future__ import annotations

import re
from typing import Any

from scripts.anomaly_detection.config import CollectionSpec, FilterSpec


def _field_for_source(source: str, row: dict[str, Any]) -> str:
    if source in ("gsc_query",):
        return (row.get("query") or "").strip()
    if source in ("gsc_page",):
        return (row.get("page") or row.get("page_path") or "").strip()
    return (row.get("page_path") or row.get("page") or "").strip()


def single_filter_matches(text: str, f: FilterSpec) -> bool:
    if f.type == "contains":
        return f.value.lower() in text.lower()
    if f.type == "starts_with":
        return text.lower().startswith(f.value.lower())
    if f.type == "ends_with":
        return text.lower().endswith(f.value.lower())
    if f.type == "regex":
        return bool(f.compile_regex().search(text))
    return False


def filter_matches(text: str, spec: FilterSpec) -> bool:
    return single_filter_matches(text, spec)


def row_matches_collection(
    row: dict[str, Any],
    collection: CollectionSpec,
    *,
    dimension_key: str = "query",
) -> bool:
    text = (row.get(dimension_key) or row.get("page_path") or row.get("page") or "").strip()
    if not collection.filters:
        return False
    results = [filter_matches(text, f) for f in collection.filters]
    if collection.match_mode == "all":
        return all(results)
    return any(results)


def filter_rows(
    rows: list[dict[str, Any]],
    collection: CollectionSpec,
    *,
    dimension_key: str,
) -> list[dict[str, Any]]:
    return [r for r in rows if row_matches_collection(r, collection, dimension_key=dimension_key)]
