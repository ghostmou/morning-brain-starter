"""Run anomaly detection for one or more clients."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from scripts.anomaly_detection.aggregate import series_for_metric, sum_by_date
from scripts.anomaly_detection.bitacora import load_bitacora_snippets
from scripts.anomaly_detection.config import (
    AnomalyConfig,
    CollectionSpec,
    ControlSpec,
    client_paths,
    load_anomaly_config,
)
from scripts.anomaly_detection.context_external import core_updates_for_window
from scripts.anomaly_detection.detect import SEVERITY_ORDER, Finding, evaluate_series
from scripts.anomaly_detection.finding_context import finalize_finding
from scripts.anomaly_detection.digest import load_digest_snippet
from scripts.anomaly_detection.fetch import filter_rows_by_date, load_live_bundle, load_synthetic_bundle
from scripts.anomaly_detection.filters import filter_rows
from scripts.anomaly_detection.report_html import SharedContext, build_client_report_html, max_severity
from scripts.anomaly_detection.suggested_actions import build_actions_payload, write_suggested_actions
DEFAULT_CORE_CSV = Path(__file__).resolve().parents[2] / "data" / "google_core_updates.csv"


def _dimension_key(source: str) -> str:
    if source == "gsc_query":
        return "query"
    if source == "gsc_page":
        return "page"
    return "page_path"


def _rows_for_source(bundle: dict[str, list[dict[str, Any]]], source: str) -> list[dict[str, Any]]:
    if source == "ga4":
        return bundle["ga4"]
    if source == "gsc_page":
        return bundle["gsc_page"]
    return bundle["gsc_query"]


def _collection_for_control(
    cfg: AnomalyConfig,
    control: ControlSpec,
) -> CollectionSpec | None:
    if not control.collection_id:
        return None
    return cfg.collection_by_id(control.collection_id)


def _site_daily_rows(bundle: dict[str, list[dict[str, Any]]], source: str) -> list[dict[str, Any]]:
    daily = bundle.get("gsc_site_daily") or []
    if not daily:
        return []
    if source == "gsc_page":
        return [
            {"date": r["date"], "page": "(site total)", **{k: r[k] for k in ("clicks", "impressions", "position") if k in r}}
            for r in daily
        ]
    return [
        {"date": r["date"], "query": "(site total)", **{k: r[k] for k in ("clicks", "impressions", "position") if k in r}}
        for r in daily
    ]


def evaluate_control(
    control: ControlSpec,
    cfg: AnomalyConfig,
    bundle: dict[str, list[dict[str, Any]]],
    report_date: str,
) -> tuple[Finding | None, dict[str, float]]:
    coll = _collection_for_control(cfg, control)
    if coll:
        rows = _rows_for_source(bundle, control.source)
        rows = filter_rows_by_date(rows, report_date)
        dim = _dimension_key(control.source)
        rows = filter_rows(rows, coll, dimension_key=dim)
    elif control.source in ("gsc_query", "gsc_page") and bundle.get("gsc_site_daily"):
        rows = filter_rows_by_date(_site_daily_rows(bundle, control.source), report_date)
    else:
        rows = filter_rows_by_date(_rows_for_source(bundle, control.source), report_date)
    if not rows:
        return None, {}
    daily = sum_by_date(rows, control.metrics)
    series = series_for_metric(daily, control.primary_metric)
    companion_series: dict[str, float] | None = None
    if control.primary_metric == "clicks" and "impressions" in control.metrics:
        companion_series = series_for_metric(daily, "impressions")
    label = control.label or (coll.label if coll else control.id)
    finding = finalize_finding(
        evaluate_series(
            series,
            report_date,
            control_id=control.id,
            metric=control.primary_metric,
            source=control.source,
            label=label,
        ),
        series,
        report_date,
        companion_series=companion_series,
    )
    return finding, series, companion_series


def run_client(
    client_id: str,
    report_date: str,
    *,
    lab_root: Path | None = None,
    clients_root: Path | None = None,
    output_dir: Path,
    synthetic: bool = True,
    news_digest_dir: Path | None = None,
    core_updates_csv: Path | None = None,
) -> dict[str, Any]:
    client_dir, demo_dir = client_paths(client_id, clients_root=clients_root, lab_root=lab_root)
    cfg_path = client_dir / "anomaly_controls.yaml"
    if not cfg_path.exists():
        raise FileNotFoundError(f"Missing {cfg_path}")
    cfg = load_anomaly_config(cfg_path)
    mode = "synthetic" if synthetic else "live"
    bundle: dict[str, list[dict[str, Any]]] = {"ga4": [], "gsc_page": [], "gsc_query": []}
    if synthetic and demo_dir:
        bundle = load_synthetic_bundle(demo_dir)
    elif not synthetic:
        bundle = load_live_bundle(client_dir, report_date)
    digest_skipped, digest_snippets = load_digest_snippet(news_digest_dir, report_date)
    core_csv = core_updates_csv or DEFAULT_CORE_CSV
    shared = SharedContext(
        mode=mode,
        bitacora_lines=load_bitacora_snippets(client_dir, report_date),
        core_updates=core_updates_for_window(report_date, csv_path=core_csv),
        digest_skipped=digest_skipped,
        digest_snippets=digest_snippets,
    )
    findings: list[Finding] = []
    series_map: dict[str, dict[str, float]] = {}
    companion_map: dict[str, dict[str, float]] = {}
    for ctrl in cfg.controls:
        f, series, companion = evaluate_control(ctrl, cfg, bundle, report_date)
        if series:
            series_map[ctrl.id] = series
        if companion:
            companion_map[ctrl.id] = companion
        if f:
            findings.append(f)
    findings.sort(key=lambda fd: SEVERITY_ORDER.get(fd.severity, 99))
    out_client = output_dir
    out_client.mkdir(parents=True, exist_ok=True)
    html_path = out_client / f"{client_id}.html"
    html_path.write_text(
        build_client_report_html(
            client_id,
            report_date,
            shared,
            findings,
            series_by_control=series_map,
            companion_by_control=companion_map,
        ),
        encoding="utf-8",
    )
    actions_path = out_client / f"{client_id}-suggested_actions.yaml"
    write_suggested_actions(actions_path, build_actions_payload(client_id, findings))
    return {
        "client_id": client_id,
        "findings_count": len(findings),
        "max_severity": max_severity(findings),
        "html_path": str(html_path),
        "findings": [f.control_id for f in findings],
    }


def write_summary_md(output_dir: Path, rows: list[dict[str, Any]], *, digest_skipped: bool) -> Path:
    path = output_dir / "summary.md"
    lines = [
        "# Anomalías — resumen",
        "",
        f"Generado: {datetime.now().isoformat(timespec='seconds')}",
        "",
        "| client_id | severidad_max | findings_count | informe |",
        "|-----------|---------------|----------------|---------|",
    ]
    for r in rows:
        sev = r.get("max_severity") or "—"
        lines.append(
            f"| {r['client_id']} | {sev} | {r['findings_count']} | `{Path(r['html_path']).name}` |"
        )
    if digest_skipped:
        lines.extend(["", "_Digest de noticias: omitido (directorio vacío o ausente)._"])
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def run_pipeline(
    report_date: str,
    client_ids: list[str],
    *,
    lab_root: Path | None = None,
    clients_root: Path | None = None,
    output_dir: Path,
    synthetic: bool = True,
    news_digest_dir: Path | None = None,
) -> dict[str, Any]:
    results: list[dict[str, Any]] = []
    digest_skipped = True
    if news_digest_dir:
        from scripts.anomaly_detection.digest import load_digest_snippet

        digest_skipped, _ = load_digest_snippet(news_digest_dir, report_date)
    for cid in client_ids:
        results.append(
            run_client(
                cid,
                report_date,
                lab_root=lab_root,
                clients_root=clients_root,
                output_dir=output_dir,
                synthetic=synthetic,
                news_digest_dir=news_digest_dir,
            )
        )
    write_summary_md(output_dir, results, digest_skipped=digest_skipped)
    meta = {
        "report_date": report_date,
        "synthetic": synthetic,
        "clients": results,
        "digest_skipped": digest_skipped,
        "lab_root": str(lab_root) if lab_root else None,
    }
    (output_dir / "run.meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    return meta


def list_lab_clients(lab_root: Path) -> list[str]:
    for clients_dir in (lab_root / "context" / "clients", lab_root / "clients"):
        if clients_dir.is_dir():
            return sorted(
                p.name
                for p in clients_dir.iterdir()
                if p.is_dir() and (p / "anomaly_controls.yaml").exists()
            )
    return []
