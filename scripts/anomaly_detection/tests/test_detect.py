from scripts.anomaly_detection.detect import evaluate_series, _severity


def _series(base: float, drop_date: str, drop_factor: float) -> dict[str, float]:
    from datetime import datetime, timedelta

    end = datetime.strptime(drop_date, "%Y-%m-%d")
    s = {}
    for i in range(40):
        d = (end - timedelta(days=39 - i)).strftime("%Y-%m-%d")
        # small noise so rolling std > 0
        s[d] = base * (0.98 + (i % 5) * 0.01)
    s[drop_date] = base * drop_factor
    return s


def test_detect_drop_finding():
    series = _series(100.0, "2026-06-02", 0.3)
    f = evaluate_series(
        series,
        "2026-06-02",
        control_id="T1",
        metric="clicks",
        source="gsc_query",
        label="Test",
    )
    assert f is not None
    assert f.severity in ("serio", "terrorifico")
    assert f.z_score < 0


def test_detect_rise_finding_is_favorable():
    series = _series(100.0, "2026-06-02", 1.8)
    f = evaluate_series(
        series,
        "2026-06-02",
        control_id="T2",
        metric="clicks",
        source="gsc_query",
        label="Test",
    )
    assert f is not None
    assert f.severity in ("alto", "muy_alto")
    assert f.z_score > 0


def test_detect_std_zero_returns_none():
    series = {f"2026-06-{d:02d}": 5.0 for d in range(1, 10)}
    assert evaluate_series(series, "2026-06-09", control_id="x", metric="m", source="ga4", label="L") is None


def test_severity_thresholds_adverse():
    assert _severity(-4, -60, higher_is_bad=False) == "terrorifico"
    assert _severity(-2.5, -30, higher_is_bad=False) == "serio"
    assert _severity(-1.6, -16, higher_is_bad=False) == "leve"
    assert _severity(0, 0, higher_is_bad=False) is None


def test_severity_thresholds_favorable():
    assert _severity(4, 60, higher_is_bad=False) == "muy_alto"
    assert _severity(2.5, 30, higher_is_bad=False) == "alto"
    assert _severity(1.6, 16, higher_is_bad=False) == "mejora_leve"


def test_severity_position_polarity_inverted():
    # En position, subir es malo y bajar es bueno.
    assert _severity(3, 60, higher_is_bad=True) == "terrorifico"
    assert _severity(-3, -60, higher_is_bad=True) == "muy_alto"
