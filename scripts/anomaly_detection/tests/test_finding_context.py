from scripts.anomaly_detection.detect import evaluate_series
from scripts.anomaly_detection.finding_context import finalize_finding

# Fictional scaled series (same shape as a CTR-divergence fixture, not copied from any client).
_SCALE = 0.35


def _ctr_divergence_clicks() -> dict[str, float]:
    raw = {
        "2026-05-23": 919,
        "2026-05-24": 1209,
        "2026-05-25": 1507,
        "2026-05-26": 1513,
        "2026-05-27": 1307,
        "2026-05-28": 1187,
        "2026-05-29": 989,
        "2026-05-30": 887,
        "2026-05-31": 1166,
        "2026-06-01": 1433,
        "2026-06-02": 1357,
        "2026-06-03": 1188,
        "2026-06-04": 1075,
        "2026-06-05": 837,
    }
    return {d: round(v * _SCALE, 1) for d, v in raw.items()}


def _ctr_divergence_impressions() -> dict[str, float]:
    raw = {
        "2026-05-23": 65148,
        "2026-05-24": 66857,
        "2026-05-25": 74865,
        "2026-05-26": 75904,
        "2026-05-27": 75935,
        "2026-05-28": 71386,
        "2026-05-29": 68964,
        "2026-05-30": 67806,
        "2026-05-31": 67384,
        "2026-06-01": 75622,
        "2026-06-02": 76276,
        "2026-06-03": 69783,
        "2026-06-04": 65191,
        "2026-06-05": 76162,
    }
    return {d: round(v * _SCALE, 1) for d, v in raw.items()}


def test_ctr_divergence_boosts_severity():
    clicks = _ctr_divergence_clicks()
    imps = _ctr_divergence_impressions()
    base = evaluate_series(
        clicks,
        "2026-06-05",
        control_id="GSC_TOPIC_S7_01",
        metric="clicks",
        source="gsc_query",
        label="Topic sector 7 (queries)",
    )
    assert base is not None
    assert base.severity == "leve"
    final = finalize_finding(base, clicks, "2026-06-05", companion_series=imps)
    assert final is not None
    assert final.severity in ("serio", "terrorifico")
    assert final.narrative
    assert "CTR" in final.narrative
    assert final.trend_7d_pct is not None
