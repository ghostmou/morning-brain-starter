"""Parse client bitácora markdown for entries near anomaly date."""

from __future__ import annotations

import re
from datetime import datetime, timedelta
from pathlib import Path

DATE_RE = re.compile(r"\b(20\d{2}-\d{2}-\d{2})\b")


def extract_dated_lines(text: str, center_date: str, *, window_days: int = 7, max_entries: int = 5) -> list[str]:
    center = datetime.strptime(center_date, "%Y-%m-%d")
    lo = center - timedelta(days=window_days)
    hi = center + timedelta(days=window_days)
    entries: list[tuple[datetime, str]] = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        for m in DATE_RE.finditer(line):
            try:
                d = datetime.strptime(m.group(1), "%Y-%m-%d")
            except ValueError:
                continue
            if lo <= d <= hi:
                entries.append((d, line))
                break
    entries.sort(key=lambda x: x[0], reverse=True)
    seen: set[str] = set()
    out: list[str] = []
    for _, ln in entries:
        if ln in seen:
            continue
        seen.add(ln)
        out.append(ln)
        if len(out) >= max_entries:
            break
    return out


def load_bitacora_snippets(client_dir: Path, anomaly_date: str) -> list[str]:
    paths = [client_dir / "bitacora.md"]
    projects = client_dir / "projects"
    if projects.is_dir():
        for p in sorted(projects.glob("*/bitacora.md")):
            paths.append(p)
    lines: list[str] = []
    for path in paths:
        if path.exists():
            lines.extend(extract_dated_lines(path.read_text(encoding="utf-8"), anomaly_date))
    return lines[:5]
