"""Optional news digest snippets for shared context."""

from __future__ import annotations

import re
from pathlib import Path

KEYWORDS = re.compile(
    r"\b(core update|google search|gsc|search console|ga4|medición|measurement|ranking)\b",
    re.IGNORECASE,
)


def load_digest_snippet(digest_dir: Path | None, reference_date: str) -> tuple[bool, list[str]]:
    """
    Returns (skipped, lines).
    skipped=True if dir missing/empty or no matching file.
    """
    if not digest_dir or not digest_dir.is_dir():
        return True, []
    files = sorted(digest_dir.glob("*.md"), reverse=True)
    if not files:
        return True, []
    target = digest_dir / f"{reference_date}.md"
    path = target if target.exists() else files[0]
    text = path.read_text(encoding="utf-8")
    snippets: list[str] = []
    for para in re.split(r"\n\s*\n", text):
        para = para.strip()
        if para and KEYWORDS.search(para):
            snippets.append(para[:500])
    if not snippets:
        return True, []
    return False, snippets[:3]
