from pathlib import Path

from scripts.anomaly_detection.digest import load_digest_snippet


def test_digest_missing_dir():
    skipped, lines = load_digest_snippet(None, "2026-06-01")
    assert skipped is True
    assert lines == []


def test_digest_fixture(tmp_path: Path):
    d = tmp_path / "digests"
    d.mkdir()
    (d / "2026-06-01.md").write_text("Hoy hubo un core update en Ranking y revisamos GSC.\n", encoding="utf-8")
    skipped, lines = load_digest_snippet(d, "2026-06-01")
    assert skipped is False
    assert len(lines) >= 1
