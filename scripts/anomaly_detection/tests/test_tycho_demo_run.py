"""Integration: Tycho synthetic run has 5 findings, context deploy + core update."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from scripts.anomaly_detection.pipeline import run_pipeline
from scripts.anomaly_detection.seed_demo import seed_demo_structure

REPO_ROOT = Path(__file__).resolve().parents[3]
REPORT_DATE = "2026-06-05"
NEGATIVE_BADGES = frozenset({"leve", "serio", "terrorifico"})
POSITIVE_BADGES = frozenset({"mejora_leve", "mejora_alto", "alto", "muy_alto"})


@pytest.fixture(scope="module")
def tycho_out(tmp_path_factory) -> Path:
    root = tmp_path_factory.mktemp("tycho_lab")
    seed_demo_structure(root)
    out = root / "output"
    run_pipeline(
        REPORT_DATE,
        ["tycho"],
        lab_root=root,
        output_dir=out,
        synthetic=True,
        news_digest_dir=root / "digest-fixture",
    )
    return out


def test_five_findings_in_meta(tycho_out: Path):
    meta = json.loads((tycho_out / "run.meta.json").read_text(encoding="utf-8"))
    client = meta["clients"][0]
    assert client["client_id"] == "tycho"
    assert client["findings_count"] >= 5
    assert len(client["findings"]) >= 5


def test_html_findings_mix_and_context(tycho_out: Path):
    html = (tycho_out / "tycho.html").read_text(encoding="utf-8")
    assert "tycho" in html.lower()
    assert "bootstrap" in html
    assert html.count("id='finding-") >= 5
    badges = re.findall(r"class='sev-badge ([^']+)'", html)
    neg = sum(1 for b in badges if b in NEGATIVE_BADGES)
    pos = sum(1 for b in badges if b in POSITIVE_BADGES)
    assert neg >= 3
    assert pos >= 2
    assert "2026-06-04" in html
    assert re.search(r"deploy|sector\s*7", html, re.IGNORECASE)
    assert "2026-05-21" in html
    assert re.search(r"May 2026 core update", html, re.IGNORECASE)
    assert "D deploy" in html or "U update" in html


def test_suggested_actions_and_summary(tycho_out: Path):
    summary = (tycho_out / "summary.md").read_text(encoding="utf-8")
    assert "tycho" in summary
    assert "terrorifico" in summary or "5" in summary
    yaml_path = tycho_out / "tycho-suggested_actions.yaml"
    assert yaml_path.exists()
    assert len(yaml_path.read_text(encoding="utf-8").strip()) > 20


@pytest.mark.skipif(
    not (REPO_ROOT / "demo-data" / "tycho" / "ga4_daily.csv").exists(),
    reason="versioned demo-data not present",
)
def test_repo_tycho_demo_data_run(tmp_path: Path):
    out = tmp_path / "out"
    meta = run_pipeline(
        REPORT_DATE,
        ["tycho"],
        lab_root=REPO_ROOT,
        output_dir=out,
        synthetic=True,
        news_digest_dir=REPO_ROOT / "digest-fixture",
    )
    assert meta["clients"][0]["findings_count"] >= 5
    assert (out / "tycho.html").exists()
