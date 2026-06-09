from scripts.anomaly_detection.chart_timeseries import ChartEvent, build_timeseries_svg


def test_svg_nonempty_and_highlight():
    series = {f"2026-06-{i:02d}": float(i * 10) for i in range(1, 8)}
    svg = build_timeseries_svg(series, highlight_date="2026-06-05", metric_label="clicks")
    assert "<svg" in svg
    assert "polyline" in svg
    assert "circle" in svg
    assert "clicks" in svg
    assert "Día evaluado" in svg
    assert "Día D" in svg
    assert "viewBox" in svg


def test_svg_companion_and_baseline():
    series = {f"2026-06-{i:02d}": float(100 - i) for i in range(1, 8)}
    companion = {f"2026-06-{i:02d}": float(1000 + i * 10) for i in range(1, 8)}
    svg = build_timeseries_svg(
        series,
        highlight_date="2026-06-05",
        metric_label="clicks",
        baseline=95.0,
        adverse=True,
        companion_series=companion,
        companion_label="impressions",
    )
    assert "impressions" in svg
    assert "referencia" in svg
    assert svg.count("polyline") == 2


def test_svg_context_event_markers():
    series = {f"2026-06-{i:02d}": float(100 + i) for i in range(1, 10)}
    events = [
        ChartEvent("2026-06-04", "deploy", "Deploy portal sector 7"),
        ChartEvent("2026-05-21", "core_update", "May 2026 core update"),
    ]
    svg = build_timeseries_svg(
        series,
        highlight_date="2026-06-05",
        metric_label="sessions",
        events=events,
    )
    assert "stroke-dasharray" in svg
    assert "D deploy" in svg
    assert "U update" in svg
    assert ">D<" in svg or "D</text>" in svg


def test_svg_y_axis_scale_labels():
    series = {"2026-06-01": 100.0, "2026-06-02": 200.0, "2026-06-03": 150.0}
    svg = build_timeseries_svg(series, highlight_date="2026-06-02", metric_label="clicks")
    assert ">100<" in svg or ">100.0<" in svg
    assert ">200<" in svg or ">200.0<" in svg
