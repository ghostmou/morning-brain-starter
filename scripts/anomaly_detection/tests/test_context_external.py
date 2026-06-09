from pathlib import Path

from scripts.anomaly_detection.context_external import core_updates_for_window


def test_core_updates_in_range(tmp_path: Path):
    csv = tmp_path / "core.csv"
    csv.write_text("date,title\n2026-06-01,June test update\n2020-01-01,Old\n", encoding="utf-8")
    rows = core_updates_for_window("2026-06-02", csv_path=csv)
    assert len(rows) == 1
    assert rows[0]["title"] == "June test update"
