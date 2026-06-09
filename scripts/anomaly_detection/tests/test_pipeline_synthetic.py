from pathlib import Path

import pytest

from scripts.anomaly_detection.pipeline import run_pipeline
from scripts.anomaly_detection.seed_demo import seed_demo_structure


@pytest.fixture
def lab_root(tmp_path: Path) -> Path:
    seed_demo_structure(tmp_path)
    return tmp_path


def test_pipeline_produces_tycho_html_and_summary(lab_root: Path, tmp_path: Path):
    out = tmp_path / "out"
    meta = run_pipeline(
        "2026-06-05",
        ["tycho"],
        lab_root=lab_root,
        output_dir=out,
        synthetic=True,
        news_digest_dir=lab_root / "digest-fixture",
    )
    assert meta["clients"][0]["findings_count"] >= 5
    html = out / "tycho.html"
    assert html.exists()
    text = html.read_text(encoding="utf-8")
    assert "GA4_SECTOR7_01" in text
    assert "GSC_TOPIC_N7_01" in text
    assert (out / "summary.md").exists()
    assert (out / "run.meta.json").exists()
