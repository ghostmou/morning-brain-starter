"""Z-score + same-weekday detection on aggregated series."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from statistics import mean, pstdev
from typing import Literal

Severity = Literal[
    # Impacto negativo (la desviación perjudica al negocio)
    "leve",
    "serio",
    "terrorifico",
    # Señal positiva (la desviación favorece al negocio)
    "mejora_leve",
    "alto",
    "muy_alto",
]

ADVERSE_SEVERITIES: tuple[Severity, ...] = ("leve", "serio", "terrorifico")
FAVORABLE_SEVERITIES: tuple[Severity, ...] = ("mejora_leve", "alto", "muy_alto")

# Orden para "peor primero": negativos por gravedad, luego positivos por intensidad.
SEVERITY_ORDER: dict[str, int] = {
    "terrorifico": 0,
    "serio": 1,
    "leve": 2,
    "muy_alto": 3,
    "alto": 4,
    "mejora_leve": 5,
}

SEVERITY_LABELS: dict[str, str] = {
    "terrorifico": "Terrorífico",
    "serio": "Serio",
    "leve": "Leve",
    "muy_alto": "Muy alto",
    "alto": "Alto",
    "mejora_leve": "Mejora leve",
}

SEVERITY_DISPLAY_ADVERSE: dict[str, str] = {
    "leve": "Bajada leve",
    "serio": "Bajada seria",
    "terrorifico": "Bajada terrorífica",
}

SEVERITY_DISPLAY_FAVORABLE: dict[str, str] = {
    "mejora_leve": "Mejora leve",
    "alto": "Subida alta",
    "muy_alto": "Subida muy alta",
}


def is_adverse(severity: str) -> bool:
    return severity in ADVERSE_SEVERITIES


def severity_display_label(severity: str) -> str:
    """Etiqueta legible con dirección (bajada/subida) para informes y badges."""
    if is_adverse(severity):
        return SEVERITY_DISPLAY_ADVERSE.get(severity, SEVERITY_LABELS.get(severity, severity))
    return SEVERITY_DISPLAY_FAVORABLE.get(severity, SEVERITY_LABELS.get(severity, severity))


@dataclass
class Finding:
    control_id: str
    metric: str
    date: str
    value: float
    baseline_mean: float
    z_score: float
    delta_pct: float
    severity: Severity
    label: str
    source: str
    narrative: str = ""
    narrative_lead: str = ""
    narrative_bullets: list[str] = field(default_factory=list)
    trend_7d_pct: float | None = None
    companion_metric: str | None = None
    companion_value: float | None = None
    companion_delta_pct: float | None = None
    ctr_value: float | None = None
    ctr_baseline: float | None = None


def _parse_date(s: str) -> datetime:
    return datetime.strptime(s, "%Y-%m-%d")


def _weekday(s: str) -> int:
    return _parse_date(s).weekday()


def _prior_same_weekday_values(
    series: dict[str, float],
    target_date: str,
    *,
    weeks: int = 2,
) -> list[float]:
    wd = _weekday(target_date)
    target_dt = _parse_date(target_date)
    vals: list[float] = []
    for d, v in series.items():
        if d >= target_date:
            continue
        if _weekday(d) != wd:
            continue
        delta_days = (target_dt - _parse_date(d)).days
        if 0 < delta_days <= 7 * weeks:
            vals.append(v)
    return vals


def _rolling_stats(series: dict[str, float], target_date: str, window_days: int = 28) -> tuple[float, float]:
    target_dt = _parse_date(target_date)
    vals: list[float] = []
    for d, v in series.items():
        if d >= target_date:
            continue
        if (target_dt - _parse_date(d)).days <= window_days:
            vals.append(v)
    if len(vals) < 3:
        return 0.0, 0.0
    mu = mean(vals)
    sd = pstdev(vals) if len(vals) > 1 else 0.0
    return mu, sd


def _severity(z: float, delta_pct: float, *, higher_is_bad: bool) -> Severity | None:
    """Clasifica la desviación en una escala negativa o positiva.

    Se normaliza el signo para que ``adv_*`` positivo signifique siempre
    "adverso para el negocio" (subir es malo en ``position``; bajar es malo en
    clicks/conversions/etc.). Misma magnitud de umbrales en ambos sentidos:
    una caída de -25% es ``serio`` y una subida de +25% es ``alto``.
    """
    sign = 1.0 if higher_is_bad else -1.0
    adv_z = z * sign
    adv_delta = delta_pct * sign
    # Impacto negativo
    if adv_z >= 3.5 or adv_delta >= 50:
        return "terrorifico"
    if adv_z >= 2.0 or adv_delta >= 25:
        return "serio"
    if adv_z >= 1.5 or adv_delta >= 15:
        return "leve"
    # Señal positiva
    if adv_z <= -3.5 or adv_delta <= -50:
        return "muy_alto"
    if adv_z <= -2.0 or adv_delta <= -25:
        return "alto"
    if adv_z <= -1.5 or adv_delta <= -15:
        return "mejora_leve"
    return None


def metric_higher_is_bad(metric: str) -> bool:
    return metric in ("position", "avg_position")


def evaluate_series(
    series: dict[str, float],
    target_date: str,
    *,
    control_id: str,
    metric: str,
    source: str,
    label: str,
    min_history: int = 7,
) -> Finding | None:
    if target_date not in series:
        return None
    value = series[target_date]
    if len([d for d in series if d < target_date]) < min_history:
        return None
    mu, sd = _rolling_stats(series, target_date)
    weekday_vals = _prior_same_weekday_values(series, target_date)
    if weekday_vals:
        mu_w = mean(weekday_vals)
        if mu == 0:
            mu = mu_w
        else:
            mu = (mu + mu_w) / 2
    if sd == 0:
        if weekday_vals and len(weekday_vals) > 1:
            sd = pstdev(weekday_vals)
        if sd == 0:
            return None
    z = (value - mu) / sd
    delta_pct = ((value - mu) / mu * 100) if mu else 0.0
    higher_bad = metric_higher_is_bad(metric)
    sev = _severity(z, delta_pct, higher_is_bad=higher_bad)
    if sev is None:
        return None
    return Finding(
        control_id=control_id,
        metric=metric,
        date=target_date,
        value=value,
        baseline_mean=mu,
        z_score=z,
        delta_pct=delta_pct,
        severity=sev,
        label=label,
        source=source,
    )
