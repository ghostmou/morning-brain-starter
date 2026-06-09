"""Inline SVG time series for findings (dual axis, baseline, context event markers)."""

from __future__ import annotations

import html
from dataclasses import dataclass
from datetime import datetime

PRIMARY_COLOR = "#0d6efd"
COMPANION_COLOR = "#6f42c1"
BASELINE_COLOR = "#9aa0a6"
ADVERSE_COLOR = "#dc3545"
FAVORABLE_COLOR = "#198754"
DEPLOY_COLOR = "#fd7e14"
CORE_UPDATE_COLOR = "#6f42c1"
GRID_COLOR = "#e9ecef"


@dataclass(frozen=True)
class ChartEvent:
    """Vertical marker on the chart (deploy, core update, etc.)."""

    date: str
    kind: str
    label: str

    @property
    def stroke(self) -> str:
        if self.kind == "deploy":
            return DEPLOY_COLOR
        if self.kind == "core_update":
            return CORE_UPDATE_COLOR
        return "#6c757d"

    @property
    def badge_letter(self) -> str:
        if self.kind == "deploy":
            return "D"
        if self.kind == "core_update":
            return "U"
        return "·"


def _fmt_value(v: float) -> str:
    if abs(v) >= 1000:
        return f"{v/1000:.1f}k".replace(".0k", "k")
    if abs(v) >= 100:
        return f"{v:.0f}"
    if abs(v - round(v)) < 0.05:
        return f"{v:.0f}"
    return f"{v:.1f}"


def _fmt_date_short(iso: str) -> str:
    try:
        return datetime.strptime(iso, "%Y-%m-%d").strftime("%d %b")
    except ValueError:
        return iso


def _parse_date(iso: str) -> datetime | None:
    try:
        return datetime.strptime(iso, "%Y-%m-%d")
    except ValueError:
        return None


def _x_for_date(target: str, dates: list[str], x_at) -> float | None:
    if not dates:
        return None
    if target in dates:
        return x_at(dates.index(target))
    t = _parse_date(target)
    if t is None:
        return None
    d0 = _parse_date(dates[0])
    d1 = _parse_date(dates[-1])
    if d0 is None or d1 is None or t < d0 or t > d1:
        return None
    for i in range(len(dates) - 1):
        a = _parse_date(dates[i])
        b = _parse_date(dates[i + 1])
        if a is None or b is None:
            continue
        if a <= t <= b:
            span = (b - a).total_seconds() or 1
            frac = (t - a).total_seconds() / span
            return x_at(i) + frac * (x_at(i + 1) - x_at(i))
    return None


def _polyline(series: dict[str, float], dates: list[str], x_at, y_at, color: str) -> str:
    pts = " ".join(
        f"{x_at(i):.1f},{y_at(series[d]):.1f}" for i, d in enumerate(dates) if d in series
    )
    if not pts:
        return ""
    return (
        f"<polyline fill='none' stroke='{color}' stroke-width='2.5' "
        f"stroke-linecap='round' stroke-linejoin='round' points='{pts}'/>"
    )


def _area_fill(series: dict[str, float], dates: list[str], x_at, y_at, base_y: float, color: str) -> str:
    if not series:
        return ""
    pts_top = " ".join(
        f"{x_at(i):.1f},{y_at(series[d]):.1f}" for i, d in enumerate(dates) if d in series
    )
    if not pts_top:
        return ""
    x_last = x_at(len(dates) - 1)
    x_first = x_at(0)
    path = f"M {x_first:.1f},{base_y:.1f} L {pts_top.replace(' ', ' L ')} L {x_last:.1f},{base_y:.1f} Z"
    return f"<path d='{path}' fill='{color}' opacity='0.12'/>"


def _event_markers_svg(
    events: list[ChartEvent],
    dates: list[str],
    x_at,
    *,
    margin_top: float,
    plot_bottom: float,
    margin_left: float,
) -> str:
    if not events:
        return ""
    parts: list[str] = []
    stacked: dict[float, int] = {}
    for ev in events:
        x = _x_for_date(ev.date, dates, x_at)
        if x is None:
            continue
        rx = round(x, 1)
        stack = stacked.get(rx, 0)
        stacked[rx] = stack + 1
        badge_y = margin_top - 8 - stack * 18
        parts.append(
            f"<line x1='{x:.1f}' y1='{margin_top}' x2='{x:.1f}' y2='{plot_bottom:.1f}' "
            f"stroke='{ev.stroke}' stroke-width='1.5' stroke-dasharray='4,3' opacity='0.75'/>"
        )
        parts.append(
            f"<circle cx='{x:.1f}' cy='{badge_y:.1f}' r='9' fill='{ev.stroke}' opacity='0.95'/>"
            f"<text x='{x:.1f}' y='{badge_y + 3.5:.1f}' text-anchor='middle' font-size='10' "
            f"font-weight='700' fill='#fff'>{html.escape(ev.badge_letter)}</text>"
        )
        short = html.escape(ev.label[:28] + ("…" if len(ev.label) > 28 else ""))
        parts.append(
            f"<text x='{x:.1f}' y='{plot_bottom + 14:.1f}' text-anchor='middle' font-size='8' "
            f"fill='{ev.stroke}'>{html.escape(_fmt_date_short(ev.date))}</text>"
        )
        parts.append(
            f"<title>{html.escape(ev.date)} — {short}</title>"
        )
    return "".join(parts)


def build_timeseries_svg(
    series: dict[str, float],
    *,
    highlight_date: str,
    metric_label: str = "Métrica",
    baseline: float | None = None,
    adverse: bool = True,
    companion_series: dict[str, float] | None = None,
    companion_label: str | None = None,
    events: list[ChartEvent] | None = None,
    width: int = 640,
    height: int = 260,
) -> str:
    if not series:
        return "<svg xmlns='http://www.w3.org/2000/svg' width='640' height='40'></svg>"

    dates = sorted(series.keys())
    vals = [series[d] for d in dates]
    vmin, vmax = min(vals), max(vals)
    if baseline is not None:
        vmin, vmax = min(vmin, baseline), max(vmax, baseline)
    if vmax == vmin:
        vmax = vmin + 1

    margin_left = 56
    margin_right = 56 if companion_series else 20
    margin_top = 28
    margin_bottom = 52
    plot_w = width - margin_left - margin_right
    plot_h = height - margin_top - margin_bottom
    plot_bottom = margin_top + plot_h

    def x_at(i: int) -> float:
        return margin_left + (i / max(len(dates) - 1, 1)) * plot_w

    def y_at(v: float) -> float:
        return margin_top + plot_h - ((v - vmin) / (vmax - vmin)) * plot_h

    y_ticks = [vmin, (vmin + vmax) / 2, vmax]
    y_tick_svg = ""
    for v in y_ticks:
        y = y_at(v)
        y_tick_svg += (
            f"<line x1='{margin_left}' y1='{y:.1f}' x2='{margin_left + plot_w}' y2='{y:.1f}' "
            f"stroke='{GRID_COLOR}' stroke-width='1'/>"
            f"<text x='{margin_left - 8}' y='{y + 4:.1f}' text-anchor='end' "
            f"font-size='10' fill='{PRIMARY_COLOR}'>{html.escape(_fmt_value(v))}</text>"
        )

    companion_svg = ""
    if companion_series:
        cvals = [companion_series[d] for d in dates if d in companion_series]
        if cvals:
            cmin, cmax = min(cvals), max(cvals)
            if cmax == cmin:
                cmax = cmin + 1

            def cy_at(v: float) -> float:
                return margin_top + plot_h - ((v - cmin) / (cmax - cmin)) * plot_h

            for v in (cmin, (cmin + cmax) / 2, cmax):
                y = cy_at(v)
                companion_svg += (
                    f"<text x='{margin_left + plot_w + 8}' y='{y + 4:.1f}' text-anchor='start' "
                    f"font-size='10' fill='{COMPANION_COLOR}'>{html.escape(_fmt_value(v))}</text>"
                )
            companion_svg += _polyline(companion_series, dates, x_at, cy_at, COMPANION_COLOR)

    baseline_svg = ""
    if baseline is not None:
        by = y_at(baseline)
        baseline_svg = (
            f"<line x1='{margin_left}' y1='{by:.1f}' x2='{margin_left + plot_w}' y2='{by:.1f}' "
            f"stroke='{BASELINE_COLOR}' stroke-width='1.2' stroke-dasharray='5,4'/>"
            f"<text x='{margin_left + 4}' y='{by - 4:.1f}' font-size='9' fill='{BASELINE_COLOR}'>"
            f"referencia {html.escape(_fmt_value(baseline))}</text>"
        )

    event_svg = _event_markers_svg(
        events or [],
        dates,
        x_at,
        margin_top=margin_top,
        plot_bottom=plot_bottom,
        margin_left=margin_left,
    )

    area_svg = _area_fill(series, dates, x_at, y_at, plot_bottom, PRIMARY_COLOR)
    primary_svg = _polyline(series, dates, x_at, y_at, PRIMARY_COLOR)

    x_indices = sorted({0, len(dates) // 2, len(dates) - 1})
    x_tick_svg = ""
    for i in x_indices:
        x = x_at(i)
        x_tick_svg += (
            f"<text x='{x:.1f}' y='{height - 28}' text-anchor='middle' "
            f"font-size='10' fill='#6c757d'>{html.escape(_fmt_date_short(dates[i]))}</text>"
        )

    hi_marker = ""
    dot_color = ADVERSE_COLOR if adverse else FAVORABLE_COLOR
    if highlight_date in dates:
        hi_idx = dates.index(highlight_date)
        hx, hy = x_at(hi_idx), y_at(series[highlight_date])
        hi_marker = (
            f"<circle cx='{hx:.1f}' cy='{hy:.1f}' r='6' fill='{dot_color}' stroke='#fff' stroke-width='2'/>"
            f"<text x='{hx:.1f}' y='{hy - 12:.1f}' text-anchor='middle' font-size='9' font-weight='600' "
            f"fill='{dot_color}'>Día D</text>"
        )

    safe_metric = html.escape(metric_label)
    legend_y = height - 8
    legend = (
        f"<line x1='{margin_left}' y1='{legend_y}' x2='{margin_left + 22}' y2='{legend_y}' "
        f"stroke='{PRIMARY_COLOR}' stroke-width='2.5'/>"
        f"<text x='{margin_left + 28}' y='{legend_y + 4}' font-size='10' fill='#495057'>{safe_metric}</text>"
    )
    cursor = margin_left + 28 + max(len(metric_label) * 6, 36) + 16
    if companion_series and companion_label:
        safe_comp = html.escape(companion_label)
        legend += (
            f"<line x1='{cursor}' y1='{legend_y}' x2='{cursor + 22}' y2='{legend_y}' "
            f"stroke='{COMPANION_COLOR}' stroke-width='2.5'/>"
            f"<text x='{cursor + 28}' y='{legend_y + 4}' font-size='10' fill='#495057'>{safe_comp}</text>"
        )
        cursor += 28 + max(len(companion_label) * 6, 36) + 16
    legend += (
        f"<circle cx='{cursor}' cy='{legend_y}' r='4' fill='{dot_color}'/>"
        f"<text x='{cursor + 8}' y='{legend_y + 4}' font-size='10' fill='#495057'>Día evaluado</text>"
    )
    if events:
        cursor += 100
        legend += (
            f"<line x1='{cursor}' y1='{legend_y - 6}' x2='{cursor}' y2='{legend_y + 6}' "
            f"stroke='{DEPLOY_COLOR}' stroke-width='2' stroke-dasharray='3,2'/>"
            f"<text x='{cursor + 6}' y='{legend_y + 4}' font-size='9' fill='#495057'>D deploy</text>"
        )
        cursor += 70
        legend += (
            f"<line x1='{cursor}' y1='{legend_y - 6}' x2='{cursor}' y2='{legend_y + 6}' "
            f"stroke='{CORE_UPDATE_COLOR}' stroke-width='2' stroke-dasharray='3,2'/>"
            f"<text x='{cursor + 6}' y='{legend_y + 4}' font-size='9' fill='#495057'>U update</text>"
        )

    axis = (
        f"<line x1='{margin_left}' y1='{plot_bottom}' x2='{margin_left + plot_w}' "
        f"y2='{plot_bottom}' stroke='#adb5bd' stroke-width='1'/>"
        f"<line x1='{margin_left}' y1='{margin_top}' x2='{margin_left}' "
        f"y2='{plot_bottom}' stroke='#adb5bd' stroke-width='1'/>"
    )

    return (
        f"<svg xmlns='http://www.w3.org/2000/svg' width='100%' viewBox='0 0 {width} {height}' "
        f"role='img' aria-label='Serie temporal {safe_metric}' class='chart-svg'>"
        f"<rect x='{margin_left}' y='{margin_top}' width='{plot_w}' height='{plot_h}' "
        f"fill='#f8f9fa' rx='4'/>"
        f"{y_tick_svg}{event_svg}{axis}{baseline_svg}{area_svg}"
        f"{companion_svg}{primary_svg}{hi_marker}{x_tick_svg}{legend}</svg>"
    )


def escape_text(s: str) -> str:
    return html.escape(s, quote=True)
