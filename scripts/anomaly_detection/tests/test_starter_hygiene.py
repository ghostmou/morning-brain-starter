"""Hygiene for the public starter: allowlist-only checks, no real client data.

IMPORTANT: this file must NOT contain any real agency client names, domains or
property ids. The whitelist approach below verifies that only the fictional demo
universe is present, without ever enumerating private slugs. The deep scan that
needs the real client list lives on the private brain side (see the
`sync-morning-brain-starter` skill), never in this public repo.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]

# Fictional demo universe only (The Expanse + _example). Anything else under
# context/clients/ or demo-data/ is treated as a leak.
ALLOWED_CONTEXT_CLIENT_DIRS = frozenset({
    "tycho",
    "acme",
    "mcr",
    "rocinante",
    "mao-kwikowski",
    "_example",
})
ALLOWED_DEMO_DATA_DIRS = frozenset({"tycho"})

# Generic structural markers that should never appear in the public repo. These
# are NOT client names: they are brain-internal paths, identity and tooling that
# only make sense inside the private fork.
FORBIDDEN_PATTERNS = [
    r"flavours/mou",
    r"bigmomo-brain",
    r"scripts\.common",
    r"bin/anomaly-cli",
    r"nested clone",
    r"\bBMO\b",
    r"bmo@bigmomo",
    r"Co-Authored-By",
    r"hechoConIA-2026-directo-alertas",
    r"demo_rentheavy",
]

SCAN_ROOTS = [
    REPO_ROOT / ".cursor",
    REPO_ROOT / "docs",
    REPO_ROOT / "data",
    REPO_ROOT / "scripts" / "anomaly_detection",
    REPO_ROOT / "scripts" / "reporting",
    REPO_ROOT / "scripts" / "gsc_fetch.py",
    REPO_ROOT / "scripts" / "url_utils.py",
    REPO_ROOT / "scripts" / "search_console",
    REPO_ROOT / "scripts" / "google_auth.py",
    REPO_ROOT / "demo-data",
    REPO_ROOT / "digest-fixture",
    REPO_ROOT / "context" / "clients",
    REPO_ROOT / "README.md",
    REPO_ROOT / "BOARDING.md",
    REPO_ROOT / "DEMO-CHECKLIST.md",
    REPO_ROOT / "CREDENTIALS.md",
]

README_ALLOWED_BIGMOMO = REPO_ROOT / "README.md"
SKIP_SCAN_FILENAMES = frozenset({"test_starter_hygiene.py"})


def _iter_files(*, include_output: bool = False) -> list[Path]:
    out: list[Path] = []
    for root in SCAN_ROOTS:
        if root.is_file():
            if root.name not in SKIP_SCAN_FILENAMES:
                out.append(root)
            continue
        if not root.is_dir():
            continue
        for p in root.rglob("*"):
            if not p.is_file():
                continue
            if p.name in SKIP_SCAN_FILENAMES:
                continue
            if any(part in {".venv", "__pycache__"} for part in p.parts):
                continue
            if not include_output and "output" in p.parts:
                continue
            if p.suffix in {".pyc", ".png", ".jpg"}:
                continue
            out.append(p)
    if include_output:
        anomalies = REPO_ROOT / "output" / "anomalies"
        if anomalies.is_dir():
            for p in anomalies.rglob("*"):
                if p.is_file() and p.suffix not in {".pyc", ".png", ".jpg"}:
                    out.append(p)
    return sorted(set(out))


def _allowed_bigmomo_in_readme_only(path: Path, line: str) -> bool:
    if path.resolve() != README_ALLOWED_BIGMOMO.resolve():
        return False
    return "bigmomo" in line.lower() or "alfonso moure" in line.lower()


def test_context_clients_dirs_are_fictional_only():
    clients_dir = REPO_ROOT / "context" / "clients"
    if not clients_dir.is_dir():
        pytest.skip("no context/clients")
    found = sorted(
        p.name for p in clients_dir.iterdir() if p.is_dir() and not p.name.startswith(".")
    )
    unexpected = [name for name in found if name not in ALLOWED_CONTEXT_CLIENT_DIRS]
    assert not unexpected, (
        "Only fictional client dirs are allowed in context/clients; "
        f"unexpected: {unexpected}. Allowed: {sorted(ALLOWED_CONTEXT_CLIENT_DIRS)}"
    )


def test_demo_data_dirs_are_tycho_only():
    demo_dir = REPO_ROOT / "demo-data"
    if not demo_dir.is_dir():
        pytest.skip("no demo-data")
    found = sorted(p.name for p in demo_dir.iterdir() if p.is_dir())
    unexpected = [name for name in found if name not in ALLOWED_DEMO_DATA_DIRS]
    assert not unexpected, f"demo-data must only contain {sorted(ALLOWED_DEMO_DATA_DIRS)}; found: {unexpected}"


def test_output_anomalies_only_fictional_clients():
    """Every per-client artifact in output must map to an allowed fictional id."""
    anomalies = REPO_ROOT / "output" / "anomalies"
    if not anomalies.is_dir():
        pytest.skip("no output/anomalies")
    generic = {"run.meta", "summary"}
    for path in anomalies.rglob("*"):
        if not path.is_file() or path.suffix in {".pyc", ".png", ".jpg"}:
            continue
        stem = path.stem
        # strip known suffixes like "-suggested_actions"
        client_part = stem.split("-suggested_actions")[0].split(".")[0]
        if client_part in generic or stem in generic:
            continue
        assert client_part in ALLOWED_CONTEXT_CLIENT_DIRS, (
            f"Output artifact not tied to a fictional client: {path} (parsed '{client_part}')"
        )


@pytest.mark.parametrize("pattern", FORBIDDEN_PATTERNS)
def test_no_forbidden_structural_strings(pattern: str):
    rx = re.compile(pattern, re.IGNORECASE)
    for path in _iter_files(include_output=True):
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for i, line in enumerate(text.splitlines(), start=1):
            if rx.search(line):
                if pattern.lower() == "bigmomo" and _allowed_bigmomo_in_readme_only(path, line):
                    continue
                pytest.fail(f"Forbidden {pattern!r} in {path}:{i}: {line[:120]}")
