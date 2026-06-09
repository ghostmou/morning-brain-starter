from scripts.anomaly_detection.bitacora import extract_dated_lines


def test_bitacora_window():
    text = """
## 2026-05-28
Algo antiguo fuera de ventana.

2026-06-01 — Deploy checkout v2.
"""
    lines = extract_dated_lines(text, "2026-06-02", window_days=7)
    assert any("Deploy" in ln for ln in lines)
    assert not any("antiguo" in ln for ln in lines)
