"""Load anomaly_controls.yaml and client metadata."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

FILTER_TYPES = frozenset({"regex", "contains", "starts_with", "ends_with"})
MATCH_MODES = frozenset({"any", "all"})
SOURCES = frozenset({"ga4", "gsc_page", "gsc_query"})


@dataclass
class FilterSpec:
    type: str
    value: str = ""
    pattern: str = ""

    def compile_regex(self) -> re.Pattern[str]:
        pat = self.pattern or self.value
        try:
            return re.compile(pat, re.IGNORECASE)
        except re.error as e:
            raise ValueError(f"Invalid regex: {pat!r}") from e


@dataclass
class CollectionSpec:
    id: str
    label: str
    match_mode: str = "any"
    filters: list[FilterSpec] = field(default_factory=list)


@dataclass
class ControlSpec:
    id: str
    source: str
    metrics: list[str]
    primary_metric: str
    collection_id: str | None = None
    label: str | None = None


@dataclass
class AnomalyConfig:
    query_collections: list[CollectionSpec]
    page_collections: list[CollectionSpec]
    controls: list[ControlSpec]

    def collection_by_id(self, cid: str) -> CollectionSpec | None:
        for c in self.query_collections + self.page_collections:
            if c.id == cid:
                return c
        return None


def _parse_filter(raw: dict[str, Any]) -> FilterSpec:
    ftype = (raw.get("type") or "").strip().lower()
    if ftype not in FILTER_TYPES:
        raise ValueError(f"Unknown filter type: {ftype}")
    if ftype == "regex":
        pat = raw.get("pattern") or raw.get("value") or ""
        if not pat:
            raise ValueError("regex filter requires pattern")
        re.compile(pat, re.IGNORECASE)
        return FilterSpec(type=ftype, pattern=pat)
    val = (raw.get("value") or "").strip()
    if not val:
        raise ValueError(f"{ftype} filter requires value")
    return FilterSpec(type=ftype, value=val)


def _parse_collection(raw: dict[str, Any]) -> CollectionSpec:
    cid = (raw.get("id") or "").strip()
    if not cid:
        raise ValueError("collection missing id")
    mode = (raw.get("match_mode") or "any").strip().lower()
    if mode not in MATCH_MODES:
        raise ValueError(f"invalid match_mode: {mode}")
    filters = [_parse_filter(f) for f in (raw.get("filters") or [])]
    return CollectionSpec(
        id=cid,
        label=(raw.get("label") or cid).strip(),
        match_mode=mode,
        filters=filters,
    )


def _parse_control(raw: dict[str, Any]) -> ControlSpec:
    cid = (raw.get("id") or "").strip()
    source = (raw.get("source") or "").strip().lower()
    if source not in SOURCES:
        raise ValueError(f"control {cid}: unknown source {source}")
    metrics = list(raw.get("metrics") or [])
    primary = (raw.get("primary_metric") or (metrics[0] if metrics else "")).strip()
    if not primary:
        raise ValueError(f"control {cid}: primary_metric required")
    return ControlSpec(
        id=cid,
        source=source,
        metrics=metrics,
        primary_metric=primary,
        collection_id=(raw.get("collection_id") or "").strip() or None,
        label=(raw.get("label") or "").strip() or None,
    )


def load_anomaly_config(path: Path) -> AnomalyConfig:
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return AnomalyConfig(
        query_collections=[_parse_collection(c) for c in (data.get("query_collections") or [])],
        page_collections=[_parse_collection(c) for c in (data.get("page_collections") or [])],
        controls=[_parse_control(c) for c in (data.get("controls") or [])],
    )


def _starter_client_dir(lab_root: Path, client_id: str) -> Path:
    ctx = lab_root / "context" / "clients" / client_id
    if ctx.is_dir() or (lab_root / "context" / "clients").is_dir():
        return ctx
    return lab_root / "clients" / client_id


def client_paths(
    client_id: str,
    *,
    clients_root: Path | None = None,
    lab_root: Path | None = None,
) -> tuple[Path, Path | None]:
    """Return (client_dir, demo_data_dir). demo_data_dir set only for lab/synthetic."""
    if lab_root:
        return _starter_client_dir(lab_root, client_id), lab_root / "demo-data" / client_id
    if not clients_root:
        raise ValueError("clients_root or lab_root required")
    return clients_root / client_id, None
