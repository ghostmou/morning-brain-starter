"""Suggested actions YAML per client — plantillas en YAML, sustitución determinista."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

import re

from scripts.anomaly_detection.detect import Finding, Severity, is_adverse, severity_display_label

DEFAULT_TEMPLATES = Path(__file__).resolve().parent / "suggested_action_templates.yaml"
_TEMPLATE_CACHE: dict[str, dict[str, str]] | None = None


def _load_templates(path: Path | None = None) -> dict[str, dict[str, str]]:
    global _TEMPLATE_CACHE
    if _TEMPLATE_CACHE is not None and path is None:
        return _TEMPLATE_CACHE
    p = path or DEFAULT_TEMPLATES
    data = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    out: dict[str, dict[str, str]] = {}
    for source_key in ("ga4", "gsc"):
        block = data.get(source_key) or {}
        out[source_key] = {str(k): str(v) for k, v in block.items()}
    if path is None:
        _TEMPLATE_CACHE = out
    return out


def _context_line(f: Finding) -> str:
    line = (
        f"{f.label} · {f.metric} {_fmt(f.value)} vs baseline {_fmt(f.baseline_mean)} "
        f"(Δ{f.delta_pct:.1f}%, z={f.z_score:.2f})"
    )
    if f.trend_7d_pct is not None:
        line += f"; semana vs anterior Δ{f.trend_7d_pct:.1f}%"
    if f.companion_metric and f.companion_value is not None and f.companion_delta_pct is not None:
        line += (
            f"; {f.companion_metric} {_fmt(f.companion_value)} "
            f"(Δ{f.companion_delta_pct:.1f}% vs baseline)"
        )
    if f.ctr_value is not None and f.ctr_baseline is not None:
        line += f"; CTR {f.ctr_value:.2f}% (habitual ~{f.ctr_baseline:.2f}%)"
    return line


def _fmt(n: float) -> str:
    v = int(round(n))
    return f"{v:,}".replace(",", ".")


def _source_key(source: str) -> str:
    return "ga4" if source == "ga4" else "gsc"


def _action_for(f: Finding, templates: dict[str, dict[str, str]] | None = None) -> str:
    tpl = _load_templates() if templates is None else templates
    key = _source_key(f.source)
    sev: Severity = f.severity
    pattern = tpl.get(key, {}).get(sev)
    if not pattern:
        return f"[{sev}] {_context_line(f)}"
    return pattern.format(context=_context_line(f))


def suggested_action_parts(
    f: Finding,
    templates: dict[str, dict[str, str]] | None = None,
) -> tuple[str, list[str]]:
    """Resumen legible (2-3 frases) + viñetas de detalle para el informe HTML."""
    tpl = _load_templates() if templates is None else templates
    key = _source_key(f.source)
    sev: Severity = f.severity
    pattern = tpl.get(key, {}).get(sev)
    full = pattern.format(context=_context_line(f)) if pattern else f"[{sev}] {_context_line(f)}"

    prefix = ""
    body = full
    m = re.match(r"^(\[[^\]]+\])\s*(.*)$", full, re.DOTALL)
    if m:
        prefix = m.group(1)
        body = m.group(2).strip()

    display = severity_display_label(sev)
    if is_adverse(sev):
        lead = (
            f"{prefix} {display} en {f.label}. "
            f"Revisar hoy el bloque de números y cruzar con bitácora y contexto de sector antes de tocar el sitio o campañas."
        ).strip()
    else:
        lead = (
            f"{prefix} {display} en {f.label}. "
            f"Confirmar que el repunte es real, entender la palanca y decidir si merece reforzarse o replicarse."
        ).strip()

    bullets = [_context_line(f)]
    if " — " in body:
        _, tail = body.split(" — ", 1)
        for chunk in re.split(r"(?<=[.;])\s+|\n+", tail):
            chunk = chunk.strip()
            if chunk:
                bullets.append(chunk)
    elif body and body != _context_line(f):
        bullets.append(body)

    return lead, bullets


def build_actions_payload(client_id: str, findings: list[Finding]) -> dict[str, Any]:
    return {
        "client_id": client_id,
        "actions": [
            {
                "control_id": f.control_id,
                "severity": f.severity,
                "metric": f.metric,
                "source": f.source,
                "narrative": f.narrative or None,
                "suggested": _action_for(f),
            }
            for f in findings
        ],
    }


def write_suggested_actions(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(payload, allow_unicode=True, sort_keys=False), encoding="utf-8")
