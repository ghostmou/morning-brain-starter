from scripts.anomaly_detection.detect import Finding
from scripts.anomaly_detection.report_html import (
    BOOTSTRAP_CSS,
    SharedContext,
    build_client_report_html,
    context_chart_events,
)


def test_single_html_two_sections_and_escape():
    findings = [
        Finding("GSC_TOPIC_01", "clicks", "2026-06-02", 10, 100, -3, -90, "terrorifico", "Topic", "gsc_query"),
        Finding("GA4_CAT_01", "conversions", "2026-06-02", 5, 50, -2.5, -90, "serio", "GA4", "ga4"),
    ]
    shared = SharedContext(mode="synthetic", bitacora_lines=["2026-06-01 deploy"], core_updates=[])
    html = build_client_report_html("acme", "2026-06-02", shared, findings, series_by_control={})
    assert html.count("id='finding-") == 2
    assert html.count("id='shared'") == 1
    assert BOOTSTRAP_CSS in html
    assert "bootstrap" in html
    assert "<script>" not in html
    assert "finding-GSC_TOPIC_01" in html
    xss = build_client_report_html(
        "x",
        "2026-06-02",
        shared,
        [
            Finding(
                "X",
                "clicks",
                "2026-06-02",
                1,
                1,
                0,
                0,
                "leve",
                "<img onerror=alert(1)>",
                "gsc_query",
            )
        ],
    )
    assert "<img onerror" not in xss
    assert "&lt;img" in xss


def test_narrative_bold_and_xss():
    f = Finding(
        "C1", "clicks", "2026-06-05", 100, 200, -2.5, -50, "serio", "Topic", "gsc_query",
        narrative="**2026-06-05**: caída fuerte <script>alert(1)</script>",
        narrative_lead="Caída seria <script>alert(1)</script> en clics.",
        narrative_bullets=["Día 2026-06-05: 100 clicks"],
    )
    shared = SharedContext(mode="live")
    html = build_client_report_html("acme", "2026-06-05", shared, [f], series_by_control={})
    assert "Bajada seria" in html
    assert "Leyenda de severidad" in html
    assert "<ul class='mb-3'>" in html
    assert "card bg-light" in html
    assert "<script>alert(1)</script>" not in html
    assert "&lt;script&gt;" in html


def test_exec_summary_links_to_findings():
    findings = [
        Finding("G1", "clicks", "2026-06-04", 50, 100, -2, -50, "leve", "GSC", "gsc_query"),
        Finding("G2", "sessions", "2026-06-04", 9000, 4000, 2, 120, "muy_alto", "GA4", "ga4"),
    ]
    html = build_client_report_html("x", "2026-06-04", SharedContext(mode="synthetic"), findings)
    assert "href='#finding-G1'" in html
    assert "Bajada leve" in html
    assert "Subida muy alta" in html


def test_context_chart_events_deploy_and_update():
    shared = SharedContext(
        mode="synthetic",
        bitacora_lines=["## 2026-06-04 · Deploy portal sector 7"],
        core_updates=[{"date": "2026-05-21", "title": "May 2026 core update"}],
    )
    events = context_chart_events(shared)
    kinds = {e.kind for e in events}
    assert "deploy" in kinds
    assert "core_update" in kinds
    html = build_client_report_html("tycho", "2026-06-05", shared, [], series_by_control={})
    assert "Hitos en el gráfico" in html
    assert "D deploy" in html or "Deploy portal" in html
