"""Single HTML report per client: CMO-readable summary + per-finding detail."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from scripts.anomaly_detection.bitacora import DATE_RE
from scripts.anomaly_detection.chart_timeseries import ChartEvent, build_timeseries_svg, escape_text
from scripts.anomaly_detection.detect import (
    ADVERSE_SEVERITIES,
    FAVORABLE_SEVERITIES,
    Finding,
    SEVERITY_ORDER,
    is_adverse,
    severity_display_label,
)
from scripts.anomaly_detection.suggested_actions import suggested_action_parts

_BOLD_RE = re.compile(r"\*\*(.+?)\*\*")
_DEPLOY_RE = re.compile(r"deploy|despliegue|publicado|lanzamiento", re.IGNORECASE)

BOOTSTRAP_CSS = (
    "https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css"
)


@dataclass
class SharedContext:
    mode: str
    bitacora_lines: list[str] = field(default_factory=list)
    core_updates: list[dict[str, Any]] = field(default_factory=list)
    digest_skipped: bool = True
    digest_snippets: list[str] = field(default_factory=list)


def max_severity(findings: list[Finding]) -> str | None:
    if not findings:
        return None
    return min(findings, key=lambda f: SEVERITY_ORDER.get(f.severity, 99)).severity


def context_chart_events(shared: SharedContext) -> list[ChartEvent]:
    """Deploy lines from bitácora + core update vertical markers for charts."""
    events: list[ChartEvent] = []
    seen_dates: set[tuple[str, str]] = set()
    for ln in shared.bitacora_lines:
        if not _DEPLOY_RE.search(ln):
            continue
        for m in DATE_RE.finditer(ln):
            d = m.group(1)
            key = (d, "deploy")
            if key in seen_dates:
                continue
            seen_dates.add(key)
            label = ln.replace("##", "").strip()[:60]
            events.append(ChartEvent(date=d, kind="deploy", label=label or "Deploy"))
    for u in shared.core_updates:
        d = (u.get("date") or "").strip()
        if not d:
            continue
        key = (d, "core_update")
        if key in seen_dates:
            continue
        seen_dates.add(key)
        title = (u.get("title") or "Core update").strip()
        events.append(ChartEvent(date=d, kind="core_update", label=title))
    events.sort(key=lambda e: e.date)
    return events


_STYLE = (
    "<style>"
    ".sev-badge{display:inline-block;padding:.2rem .55rem;border-radius:50rem;color:#fff;"
    "font-size:.78rem;font-weight:600;vertical-align:middle}"
    ".sev-badge.terrorifico{background:#842029}.sev-badge.serio{background:#dc3545}"
    ".sev-badge.leve{background:#cc9a06}.sev-badge.muy_alto{background:#146c43}"
    ".sev-badge.alto{background:#198754}.sev-badge.mejora_leve{background:#6a8a2a}"
    ".chart-wrap{background:#fff;border:1px solid #dee2e6;border-radius:.5rem;padding:.75rem;margin:1rem 0}"
    ".chart-svg{display:block;max-width:100%;height:auto}"
    ".event-pill{font-size:.8rem}"
    ".event-pill.deploy{border-color:#fd7e14!important;color:#984c0c}"
    ".event-pill.update{border-color:#6f42c1!important;color:#432874}"
    "a.anchor-finding{text-decoration:none}"
    "a.anchor-finding:hover{text-decoration:underline}"
    "@media print{.navbar,.d-print-none{display:none!important}}"
    "</style>"
)


def _render_markdown_inline(text: str) -> str:
    escaped = escape_text(text)
    return _BOLD_RE.sub(r"<strong>\1</strong>", escaped)


def _fmt(n: float) -> str:
    return f"{int(round(n)):,}".replace(",", ".")


def _fmt_pct(n: float | None) -> str:
    if n is None:
        return "—"
    sign = "+" if n > 0 else ""
    return f"{sign}{n:.1f}%"


def _direction_word(f: Finding) -> str:
    if f.delta_pct > 5:
        return "subida"
    if f.delta_pct < -5:
        return "bajada"
    return "desviación"


def _headline(findings: list[Finding]) -> str:
    if not findings:
        return (
            "<div class='alert alert-success mb-4' role='alert'>"
            "<strong>Sin alertas.</strong> Ningún control cruzó umbral en el día evaluado."
            "</div>"
        )
    worst = findings[0]
    adverse = [f for f in findings if is_adverse(f.severity)]
    favorable = [f for f in findings if not is_adverse(f.severity)]
    alert_cls = "alert-warning" if adverse else "alert-success"
    bits = []
    if adverse:
        bits.append(
            f"<strong>{len(adverse)} señal(es) de impacto negativo</strong>"
            f" (máx. {escape_text(severity_display_label(worst.severity))})"
        )
    if favorable:
        bits.append(f"{len(favorable)} señal(es) positiva(s)")
    lead = " · ".join(bits)
    dir_w = _direction_word(worst)
    detail = (
        f"Lo más relevante: <strong>{escape_text(worst.label)}</strong> — "
        f"{dir_w} de {escape_text(worst.metric)}: {_fmt(worst.value)} vs referencia {_fmt(worst.baseline_mean)} "
        f"({_fmt_pct(worst.delta_pct)})."
    )
    return f"<div class='alert {alert_cls} mb-4' role='alert'>{lead}.<br>{detail}</div>"


def _color_legend() -> str:
    items = []
    for sev in ADVERSE_SEVERITIES + FAVORABLE_SEVERITIES:
        label = severity_display_label(sev)
        items.append(f"<span class='sev-badge {sev}'>{escape_text(label)}</span>")
    return (
        "<div class='small text-muted mb-3'>"
        "<strong>Leyenda de severidad</strong> (mismo color en resumen y detalle): "
        + " ".join(items)
        + "</div>"
    )


def _exec_summary_list(findings: list[Finding]) -> str:
    if not findings:
        return "<p class='text-muted mb-0'>Sin desviaciones detectadas.</p>"

    blocks: list[str] = []
    for title, severities in (
        ("Impacto negativo", ADVERSE_SEVERITIES),
        ("Señales positivas", FAVORABLE_SEVERITIES),
    ):
        group_items: list[str] = []
        for sev in severities:
            matched = [f for f in findings if f.severity == sev]
            for f in matched:
                badge = severity_display_label(sev)
                group_items.append(
                    f"<li class='mb-1'><a class='anchor-finding' href='#finding-{escape_text(f.control_id)}'>"
                    f"<span class='sev-badge {sev}'>{escape_text(badge)}</span> "
                    f"{escape_text(f.label)}</a></li>"
                )
        if group_items:
            blocks.append(
                f"<li class='mb-2'><strong>{title}</strong>"
                f"<ul class='list-unstyled ms-3 mt-1'>{''.join(group_items)}</ul></li>"
            )
    return f"<ul class='list-unstyled mb-0'>{''.join(blocks)}</ul>"


def _context_timeline(shared: SharedContext) -> str:
    events = context_chart_events(shared)
    if not events:
        return ""
    pills = []
    for ev in events:
        cls = "deploy" if ev.kind == "deploy" else "update"
        icon = "🚀" if ev.kind == "deploy" else "📡"
        pills.append(
            f"<span class='badge rounded-pill bg-light text-dark border event-pill {cls} me-2 mb-2'>"
            f"{icon} <strong>{escape_text(ev.date)}</strong> — {escape_text(ev.label[:50])}"
            f"{'…' if len(ev.label) > 50 else ''}</span>"
        )
    return (
        "<div class='mb-3'><h6 class='text-muted mb-2'>Hitos en el gráfico</h6>"
        f"<div>{''.join(pills)}</div>"
        "<p class='small text-muted mb-0'>"
        "<span class='text-warning'>D</span> = deploy en bitácora · "
        "<span style='color:#6f42c1'>U</span> = core update Google"
        "</p></div>"
    )


def _metrics_table(f: Finding) -> str:
    rows = [
        ("Día evaluado", escape_text(f.date)),
        (f"Valor ({escape_text(f.metric)})", _fmt(f.value)),
        ("Referencia esperada", _fmt(f.baseline_mean)),
        ("Δ vs referencia", f"{_fmt_pct(f.delta_pct)} (z={f.z_score:.2f})"),
    ]
    if f.trend_7d_pct is not None:
        rows.append(("Semana vs. anterior", _fmt_pct(f.trend_7d_pct)))
    if f.companion_metric and f.companion_value is not None:
        rows.append(
            (
                f"{escape_text(f.companion_metric)} (mismo día)",
                f"{_fmt(f.companion_value)} ({_fmt_pct(f.companion_delta_pct)})",
            )
        )
    if f.ctr_value is not None and f.ctr_baseline is not None:
        rows.append(("CTR", f"{f.ctr_value:.2f}% (habitual ~{f.ctr_baseline:.2f}%)"))
    body = "".join(f"<tr><th scope='row' class='text-muted'>{k}</th><td>{v}</td></tr>" for k, v in rows)
    return (
        "<div class='table-responsive'><table class='table table-sm table-bordered metrics mb-3'>"
        f"<tbody>{body}</tbody></table></div>"
    )


def _narrative_block(f: Finding) -> str:
    lead = f.narrative_lead or f.narrative or ""
    bullets = f.narrative_bullets
    parts = [
        "<p class='mb-2'><strong>Qué ha pasado:</strong> ",
        _render_markdown_inline(lead),
        "</p>",
    ]
    if bullets:
        parts.append("<ul class='mb-3'>")
        for b in bullets:
            parts.append(f"<li>{escape_text(b)}</li>")
        parts.append("</ul>")
    return "".join(parts)


def _action_block(f: Finding) -> str:
    lead, bullets = suggested_action_parts(f)
    parts = [
        "<div class='card bg-light border-0 mb-0'>",
        "<div class='card-body py-3'>",
        "<p class='mb-2'><strong>Acción sugerida:</strong> ",
        escape_text(lead),
        "</p>",
    ]
    if bullets:
        parts.append("<ul class='mb-0 small'>")
        for b in bullets:
            parts.append(f"<li>{escape_text(b)}</li>")
        parts.append("</ul>")
    parts.append("</div></div>")
    return "".join(parts)


def build_client_report_html(
    client_id: str,
    report_date: str,
    shared: SharedContext,
    findings: list[Finding],
    *,
    series_by_control: dict[str, dict[str, float]] | None = None,
    companion_by_control: dict[str, dict[str, float]] | None = None,
) -> str:
    series_by_control = series_by_control or {}
    companion_by_control = companion_by_control or {}
    chart_events = context_chart_events(shared)

    nav_links = ["<a class='nav-link d-inline px-1' href='#shared'>Contexto</a>"]
    for f in findings:
        nav_links.append(
            f"<a class='nav-link d-inline px-1' href='#finding-{escape_text(f.control_id)}'>"
            f"{escape_text(f.label)}</a>"
        )

    parts = [
        "<!DOCTYPE html><html lang='es'><head>",
        "<meta charset='utf-8'/>",
        "<meta name='viewport' content='width=device-width, initial-scale=1'/>",
        f"<link href='{BOOTSTRAP_CSS}' rel='stylesheet'/>",
        f"<title>Anomalías — {escape_text(client_id)}</title>",
        _STYLE,
        "</head><body class='bg-light'>",
        "<div class='container py-4' style='max-width:960px'>",
        "<header class='mb-4'>",
        f"<h1 class='h2 mb-1'>{escape_text(client_id)}</h1>",
        f"<p class='text-muted mb-0'>Alertas GA4 + Search Console · día evaluado "
        f"<strong>{escape_text(report_date)}</strong> · modo {escape_text(shared.mode)} · "
        "referencia: media móvil 28 días + mismo día de semana</p>",
        "</header>",
        _headline(findings),
        "<div class='card shadow-sm mb-4'>",
        "<div class='card-body'>",
        "<h2 class='h5 card-title'>Resumen ejecutivo</h2>",
        _color_legend(),
        _exec_summary_list(findings),
        f"<nav class='nav small mt-3 pt-2 border-top'>{''.join(nav_links)}</nav>",
        "</div></div>",
        "<div id='shared' class='card shadow-sm mb-4'>",
        "<div class='card-body'>",
        "<h2 class='h5 card-title'>Contexto compartido</h2>",
        "<p class='text-muted small'>Mismo para todos los controles: lo que ya sabíamos antes de mirar los números.</p>",
        _context_timeline(shared),
    ]
    if shared.bitacora_lines:
        parts.append("<h3 class='h6 mt-3'>Bitácora del cliente (±7 días)</h3><ul class='small'>")
        for ln in shared.bitacora_lines:
            deploy_cls = " class='fw-semibold text-warning'" if _DEPLOY_RE.search(ln) else ""
            parts.append(f"<li{deploy_cls}>{escape_text(ln)}</li>")
        parts.append("</ul>")
    if shared.core_updates:
        parts.append("<h3 class='h6 mt-3'>Actualizaciones de Google en ventana</h3><ul class='small'>")
        for u in shared.core_updates:
            parts.append(
                f"<li><span class='badge text-bg-light border' style='color:#6f42c1'>"
                f"{escape_text(u['date'])}</span> {escape_text(u['title'])}</li>"
            )
        parts.append("</ul>")
    else:
        parts.append("<p class='text-muted small'>Sin core/spam updates de Google en la ventana del informe.</p>")
    if shared.digest_skipped:
        parts.append("<p class='text-muted small'>Digest de noticias: no disponible o sin coincidencias.</p>")
    elif shared.digest_snippets:
        parts.append("<h3 class='h6 mt-3'>Contexto de sector (digest)</h3>")
        for sn in shared.digest_snippets:
            parts.append(f"<p class='small'>{_render_markdown_inline(sn)}</p>")
    parts.append("</div></div>")

    if not findings:
        parts.append(
            "<div class='card shadow-sm mb-3'><div class='card-body'>"
            "<h2 class='h5'>Sin alertas</h2>"
            "<p class='mb-0'>No se detectaron desviaciones relevantes en los controles configurados.</p>"
            "</div></div>"
        )

    for f in findings:
        adverse = is_adverse(f.severity)
        svg = build_timeseries_svg(
            series_by_control.get(f.control_id, {}),
            highlight_date=f.date,
            metric_label=f.metric,
            baseline=f.baseline_mean,
            adverse=adverse,
            companion_series=companion_by_control.get(f.control_id),
            companion_label=f.companion_metric,
            events=chart_events,
        )
        sev_label = severity_display_label(f.severity)
        scale = "impacto negativo" if adverse else "señal positiva"
        border = "border-danger" if adverse and f.severity in ("serio", "terrorifico") else ""
        parts.extend(
            [
                f"<div class='card shadow-sm mb-4 {border}' id='finding-{escape_text(f.control_id)}'>",
                "<div class='card-body'>",
                f"<h2 class='h5 card-title'>{escape_text(f.label)} "
                f"<span class='sev-badge {f.severity}'>{escape_text(sev_label)}</span></h2>",
                f"<p class='text-muted small'>Control <code>{escape_text(f.control_id)}</code> · "
                f"fuente {escape_text(f.source)} · {scale}</p>",
                _metrics_table(f),
                _narrative_block(f),
                f"<div class='chart-wrap'>{svg}</div>",
                _action_block(f),
                "</div></div>",
            ]
        )
    parts.append(
        "<footer class='text-center text-muted small py-3 d-print-none'>"
        "Informe generado localmente · morning-brain-starter</footer>"
    )
    parts.append("</div></body></html>")
    return "".join(parts)
