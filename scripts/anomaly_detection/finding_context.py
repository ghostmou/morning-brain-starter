"""Human-readable context, trend checks and CTR validation for findings."""

from __future__ import annotations

from datetime import datetime, timedelta
from statistics import mean
from typing import Literal

from scripts.anomaly_detection.detect import (
    ADVERSE_SEVERITIES,
    FAVORABLE_SEVERITIES,
    Finding,
    Severity,
    is_adverse,
    severity_display_label,
    _parse_date,
    _rolling_stats,
)
from scripts.anomaly_detection.fetch import date_window

Direction = Literal["subida", "bajada", "estable"]


def _fmt_int(n: float) -> str:
    v = int(round(n))
    return f"{v:,}".replace(",", ".")


def _fmt_pct(n: float) -> str:
    sign = "+" if n > 0 else ""
    return f"{sign}{n:.1f}%"


def _direction(delta_pct: float) -> Direction:
    if delta_pct > 5:
        return "subida"
    if delta_pct < -5:
        return "bajada"
    return "estable"


def _week_sum(series: dict[str, float], end_date: str, *, days: int = 7) -> float:
    end_dt = _parse_date(end_date)
    return sum(series.get((end_dt - timedelta(days=i)).strftime("%Y-%m-%d"), 0.0) for i in range(days))


def _consecutive_decline_days(series: dict[str, float], end_date: str, *, lookback: int = 7) -> int:
    end_dt = _parse_date(end_date)
    vals: list[float] = []
    for i in range(lookback, -1, -1):
        d = (end_dt - timedelta(days=i)).strftime("%Y-%m-%d")
        if d in series:
            vals.append(series[d])
    if len(vals) < 2:
        return 0
    streak = 0
    for i in range(len(vals) - 1, 0, -1):
        if vals[i] < vals[i - 1]:
            streak += 1
        else:
            break
    return streak


def _recent_daily_trail(series: dict[str, float], end_date: str, *, days: int = 4) -> list[tuple[str, float]]:
    end_dt = _parse_date(end_date)
    out: list[tuple[str, float]] = []
    for i in range(days - 1, -1, -1):
        d = (end_dt - timedelta(days=i)).strftime("%Y-%m-%d")
        if d in series:
            out.append((d, series[d]))
    return out


def _bump_severity(sev: Severity) -> Severity:
    """Sube un nivel dentro de su escala (negativa o positiva); no cruza polaridad."""
    for ladder in (ADVERSE_SEVERITIES, FAVORABLE_SEVERITIES):
        if sev in ladder:
            idx = ladder.index(sev)
            return ladder[min(idx + 1, len(ladder) - 1)]
    return sev


def _ctr(clicks: float, impressions: float) -> float:
    return (clicks / impressions * 100) if impressions else 0.0


def _ctr_divergence_boost(
    finding: Finding,
    series: dict[str, float],
    impressions_series: dict[str, float],
) -> bool:
    """Clicks caen mientras impresiones suben y el CTR se desploma."""
    if finding.metric != "clicks" or finding.date not in impressions_series:
        return False
    imps_d = impressions_series[finding.date]
    mu_imps, _ = _rolling_stats(impressions_series, finding.date)
    if mu_imps <= 0 or imps_d < mu_imps * 1.03:
        return False
    if finding.delta_pct > -12:
        return False
    ctr_d = _ctr(finding.value, imps_d)
    ctr_base = _ctr(finding.baseline_mean, mu_imps)
    if ctr_base <= 0 or ctr_d >= ctr_base * 0.85:
        return False
    return True


def _progressive_decline_boost(series: dict[str, float], end_date: str) -> bool:
    streak = _consecutive_decline_days(series, end_date, lookback=7)
    if streak < 3:
        return False
    trail = _recent_daily_trail(series, end_date, days=streak + 1)
    if len(trail) < 2:
        return False
    first, last = trail[0][1], trail[-1][1]
    if first <= 0:
        return False
    return (last - first) / first <= -0.18


def finalize_finding(
    finding: Finding | None,
    series: dict[str, float],
    report_date: str,
    *,
    companion_series: dict[str, float] | None = None,
    window_days: int = 90,
) -> Finding | None:
    if finding is None:
        return None

    start_date, _ = date_window(report_date, window_days)
    direction = _direction(finding.delta_pct)
    dir_word = {"subida": "subida", "bajada": "bajada", "estable": "movimiento lateral"}[direction]

    week_cur = _week_sum(series, report_date)
    week_prev = _week_sum(series, (_parse_date(report_date) - timedelta(days=7)).strftime("%Y-%m-%d"))
    trend_7d_pct = ((week_cur - week_prev) / week_prev * 100) if week_prev else 0.0

    companion_metric: str | None = None
    companion_value: float | None = None
    companion_delta_pct: float | None = None
    ctr_value: float | None = None
    ctr_baseline: float | None = None

    boosts: list[str] = []
    sev = finding.severity

    if companion_series and finding.metric == "clicks":
        companion_metric = "impressions"
        companion_value = companion_series.get(finding.date)
        if companion_value is not None:
            mu_c, _ = _rolling_stats(companion_series, finding.date)
            companion_delta_pct = ((companion_value - mu_c) / mu_c * 100) if mu_c else 0.0
            ctr_value = _ctr(finding.value, companion_value)
            ctr_baseline = _ctr(finding.baseline_mean, mu_c)
            if _ctr_divergence_boost(finding, series, companion_series):
                sev = _bump_severity(sev)
                boosts.append("CTR divergence (clics ↓ e impresiones ↑)")

    if _progressive_decline_boost(series, report_date):
        if sev == finding.severity:
            sev = _bump_severity(sev)
        boosts.append("tendencia descendente progresiva (≥3 días)")

    # Re-evaluate severity floor with boosted context for extreme combos
    if boosts and sev == finding.severity and finding.delta_pct <= -22 and trend_7d_pct <= -6:
        sev = _bump_severity(finding.severity)

    trail = _recent_daily_trail(series, report_date, days=4)
    trail_txt = " → ".join(_fmt_int(v) for _, v in trail) if trail else ""

    bullets = [
        (
            f"Día {finding.date}: {_fmt_int(finding.value)} {finding.metric} "
            f"(referencia {_fmt_int(finding.baseline_mean)}, {_fmt_pct(finding.delta_pct)}, z={finding.z_score:.2f})"
        ),
        (
            f"Ventana consultada: {start_date} a {report_date} ({window_days} días)"
        ),
        (
            f"Semana actual ({_fmt_int(week_cur)} total) vs semana anterior ({_fmt_int(week_prev)}): "
            f"{_fmt_pct(trend_7d_pct)}"
        ),
    ]
    if trail_txt:
        bullets.append(f"Trayectoria últimos días ({finding.metric}): {trail_txt}")
    if companion_value is not None and companion_delta_pct is not None:
        bullets.append(
            f"Impresiones el mismo día: {_fmt_int(companion_value)} "
            f"({_fmt_pct(companion_delta_pct)} vs referencia)"
        )
    if ctr_value is not None and ctr_baseline is not None:
        bullets.append(f"CTR estimado: {ctr_value:.2f}% (habitual ~{ctr_baseline:.2f}%)")
    if boosts:
        bullets.append(f"Validación extra: {', '.join(boosts)}")

    sev_display = severity_display_label(sev)
    adverse = is_adverse(sev)
    if adverse and finding.metric == "clicks" and ctr_value is not None and ctr_baseline and ctr_value < ctr_baseline * 0.9:
        narrative_lead = (
            f"{finding.label} muestra una {sev_display.lower()} en clics orgánicos. "
            f"Aparecemos más en la SERP pero nos clican menos: el patrón apunta a eficiencia en resultados, no a falta de demanda. "
            f"Conviene vigilar si se consolida antes de escalar."
        )
    elif adverse:
        narrative_lead = (
            f"{finding.label} registra una {sev_display.lower()} en {finding.metric}. "
            f"La desviación es suficiente para revisar hoy el bloque de números y cruzar con bitácora y contexto de sector. "
            f"No asumir causa hasta contrastar deploys, estacionalidad y cambios en Google."
        )
    else:
        narrative_lead = (
            f"{finding.label} muestra una {sev_display.lower()} en {finding.metric}. "
            f"Antes de celebrarlo o replicarlo, confirmar que no sea un artefacto de medición o un pico puntual. "
            f"Si se consolida, documentar la palanca para capitalizarla."
        )

    parts = [
        f"**{finding.date}**: {_fmt_int(finding.value)} {finding.metric} "
        f"(referencia esperada {_fmt_int(finding.baseline_mean)}, "
        f"**{_fmt_pct(finding.delta_pct)}**, z={finding.z_score:.2f}).",
        f"Ventana consultada: **{start_date}** a **{report_date}** ({window_days} días).",
        f"Semana actual ({_fmt_int(week_cur)} total) vs semana anterior ({_fmt_int(week_prev)}): **{_fmt_pct(trend_7d_pct)}**.",
    ]
    if trail_txt:
        parts.append(f"Últimos días ({finding.metric}): {trail_txt}.")
    if companion_value is not None and companion_delta_pct is not None:
        parts.append(
            f"Impresiones el mismo día: {_fmt_int(companion_value)} "
            f"({_fmt_pct(companion_delta_pct)} vs baseline)."
        )
    if ctr_value is not None and ctr_baseline is not None:
        parts.append(f"CTR estimado: **{ctr_value:.2f}%** (habitual ~{ctr_baseline:.2f}%).")
    if boosts:
        parts.append(f"Validación extra: {', '.join(boosts)}.")
    parts.append(f"Interpretación: **{dir_word}** en {finding.label}.")

    narrative = " ".join(parts)

    return Finding(
        control_id=finding.control_id,
        metric=finding.metric,
        date=finding.date,
        value=finding.value,
        baseline_mean=finding.baseline_mean,
        z_score=finding.z_score,
        delta_pct=finding.delta_pct,
        severity=sev,
        label=finding.label,
        source=finding.source,
        narrative=narrative,
        narrative_lead=narrative_lead,
        narrative_bullets=bullets,
        trend_7d_pct=trend_7d_pct,
        companion_metric=companion_metric,
        companion_value=companion_value,
        companion_delta_pct=companion_delta_pct,
        ctr_value=ctr_value,
        ctr_baseline=ctr_baseline,
    )
