"""Generate synthetic Tycho demo CSV + controls for morning-brain-starter."""

from __future__ import annotations

import csv
import random
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

ANOMALY_DATE = "2026-06-05"
CLIENT_ID = "tycho"
GSC_BASE = "https://tycho-station.example"

CONTROLS_YAML = """query_collections:
  - id: topic_sector7
    label: "Sector 7 (queries)"
    match_mode: any
    filters:
      - type: contains
        value: "sector 7"
      - type: contains
        value: "materiales estación"

  - id: topic_nave7
    label: "Nave 7 (queries)"
    match_mode: any
    filters:
      - type: contains
        value: "nave 7"

page_collections:
  - id: landings_sector7
    label: "Portal sector 7"
    match_mode: any
    filters:
      - type: contains
        value: "/sector-7/"

  - id: landings_nave7
    label: "Landings Nave 7"
    match_mode: any
    filters:
      - type: contains
        value: "/nave-7/"

controls:
  - id: GA4_SECTOR7_01
    source: ga4
    collection_id: landings_sector7
    metrics: [sessions, conversions]
    primary_metric: conversions
    label: "GA4 conversiones sector 7"

  - id: GSC_TOPIC_S7_01
    source: gsc_query
    collection_id: topic_sector7
    metrics: [clicks, impressions, position]
    primary_metric: clicks
    label: "GSC clics topic sector 7"

  - id: GA4_SITE_01
    source: ga4
    metrics: [sessions, conversions]
    primary_metric: sessions
    label: "GA4 sesiones sitio"

  - id: GSC_TOPIC_N7_01
    source: gsc_query
    collection_id: topic_nave7
    metrics: [clicks, impressions, position]
    primary_metric: clicks
    label: "GSC clics topic Nave 7"

  - id: GSC_PAGE_N7_01
    source: gsc_page
    collection_id: landings_nave7
    metrics: [clicks, impressions, position]
    primary_metric: clicks
    label: "GSC clics landings Nave 7"
"""

DEPLOY_BITACORA = (
    "## 2026-06-04 · Deploy portal sector 7\n"
    "Publicado nuevo formulario de solicitud de presupuesto en `/sector-7/materiales/`; "
    "cambios en eventos GA4 de conversión. Vigilar métricas tras el despliegue.\n"
)

QUERIES_S7 = [
    "materiales estación tycho sector 7",
    "construcción estación tycho sector 7",
    "suministros sector 7 tycho",
]

QUERIES_N7 = [
    "nave 7 tycho construcción",
    "proyecto nave 7 estación tycho",
    "integración motores nave 7",
]

OTHER_QUERIES = [
    "tycho estación aduanas muelle",
    "opa formación seguridad muelle",
]

GA4_PATHS: list[tuple[str, float, float]] = [
    ("/sector-7/materiales/", 420, 85),
    ("/sector-7/", 180, 12),
    ("/nave-7/", 95, 8),
    ("/nave-7/progreso/", 70, 5),
    ("/", 520, 22),
    ("/contacto/", 45, 4),
]


def _date_range(end: str, days: int = 90) -> list[str]:
    end_dt = datetime.strptime(end, "%Y-%m-%d")
    start = end_dt - timedelta(days=days - 1)
    out: list[str] = []
    d = start
    while d <= end_dt:
        out.append(d.strftime("%Y-%m-%d"))
        d += timedelta(days=1)
    return out


def _base_value(d: str, base: float) -> float:
    wd = datetime.strptime(d, "%Y-%m-%d").weekday()
    wk = 0.85 if wd in (5, 6) else 1.0
    noise = random.uniform(0.95, 1.05)
    return base * wk * noise


def generate_demo_csvs(demo_dir: Path, *, anomaly_date: str = ANOMALY_DATE) -> None:
    demo_dir.mkdir(parents=True, exist_ok=True)
    dates = _date_range(anomaly_date)
    random.seed(20260605)
    ga4_rows: list[dict[str, Any]] = []
    gsc_page_rows: list[dict[str, Any]] = []
    gsc_query_rows: list[dict[str, Any]] = []

    dip_days = ("2026-06-03", "2026-06-04", anomaly_date)
    dip_factors = {"2026-06-03": 0.88, "2026-06-04": 0.82, anomaly_date: 0.72}
    boost_factors = {"2026-06-03": 1.08, "2026-06-04": 1.15, anomaly_date: 1.32}

    for d in dates:
        dip = dip_factors.get(d, 1.0)
        boost = boost_factors.get(d, 1.0)
        site_sess_factor = dip if d in dip_days else 1.0

        for path, sess_base, conv_base in GA4_PATHS:
            sess = _base_value(d, sess_base) * site_sess_factor
            conv = _base_value(d, conv_base)
            if "/sector-7/materiales/" in path and d in dip_days:
                conv *= dip_factors.get(d, 1.0) * 0.92
            ga4_rows.append(
                {
                    "date": d,
                    "page_path": path,
                    "sessions": f"{sess:.0f}",
                    "conversions": f"{conv:.1f}",
                }
            )

        for q in QUERIES_S7:
            clicks = _base_value(d, 280.0) * (dip if d in dip_days else 1.0)
            imp = _base_value(d, 6200.0)
            pos = 7.2 + (0.4 * dip_days.index(d) if d in dip_days else 0)
            gsc_query_rows.append(
                {
                    "date": d,
                    "query": q,
                    "clicks": f"{clicks:.0f}",
                    "impressions": f"{imp:.0f}",
                    "position": f"{pos:.1f}",
                }
            )

        for q in QUERIES_N7:
            clicks = _base_value(d, 195.0) * boost
            imp = _base_value(d, 3400.0) * (1.05 if d in boost_factors else 1.0)
            pos = 6.1 - (0.2 if d in boost_factors else 0)
            gsc_query_rows.append(
                {
                    "date": d,
                    "query": q,
                    "clicks": f"{clicks:.0f}",
                    "impressions": f"{imp:.0f}",
                    "position": f"{max(pos, 4.0):.1f}",
                }
            )

        for q in OTHER_QUERIES:
            gsc_query_rows.append(
                {
                    "date": d,
                    "query": q,
                    "clicks": f"{_base_value(d, 55):.0f}",
                    "impressions": f"{_base_value(d, 1800):.0f}",
                    "position": "11.5",
                }
            )

        for page_path, click_base in (
            ("/sector-7/materiales/", 310),
            ("/sector-7/", 140),
            ("/nave-7/", 160),
            ("/nave-7/progreso/", 120),
        ):
            factor = dip if "sector-7" in page_path and d in dip_days else 1.0
            if "nave-7" in page_path:
                factor = boost
            clicks = _base_value(d, click_base) * factor
            gsc_page_rows.append(
                {
                    "date": d,
                    "page": f"{GSC_BASE}{page_path}",
                    "clicks": f"{clicks:.0f}",
                    "impressions": f"{_base_value(d, 5000):.0f}",
                    "position": "8.0",
                }
            )

    _write_csv(demo_dir / "ga4_daily.csv", ga4_rows, ["date", "page_path", "sessions", "conversions"])
    _write_csv(
        demo_dir / "gsc_page_daily.csv",
        gsc_page_rows,
        ["date", "page", "clicks", "impressions", "position"],
    )
    _write_csv(
        demo_dir / "gsc_query_daily.csv",
        gsc_query_rows,
        ["date", "query", "clicks", "impressions", "position"],
    )


def _write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def _merge_bitacora(client_dir: Path) -> None:
    path = client_dir / "bitacora.md"
    if path.exists():
        text = path.read_text(encoding="utf-8")
        if "2026-06-04" in text and "Deploy portal sector 7" in text:
            return
        if not text.endswith("\n"):
            text += "\n"
        text += "\n" + DEPLOY_BITACORA
        path.write_text(text, encoding="utf-8")
    else:
        path.write_text("# Bitácora – Tycho\n\n" + DEPLOY_BITACORA, encoding="utf-8")


def _patch_client_yaml(client_dir: Path) -> None:
    path = client_dir / "client.yaml"
    extra = (
        "ga4_property_id: \"000000000\"\n"
        "gsc_site_url: \"https://tycho-station.example/\"\n"
    )
    if path.exists():
        text = path.read_text(encoding="utf-8")
        if "ga4_property_id" not in text:
            if not text.endswith("\n"):
                text += "\n"
            text += extra
            path.write_text(text, encoding="utf-8")
    else:
        path.write_text(
            "id: tycho\nname: Tycho\ndescription: Cliente demo\n" + extra,
            encoding="utf-8",
        )


def seed_demo_structure(target_dir: Path | None = None) -> Path:
    """Write Tycho client config + demo CSV under starter layout."""
    root = target_dir or Path(__file__).resolve().parents[2]
    client_dir = root / "context" / "clients" / CLIENT_ID
    demo_dir = root / "demo-data" / CLIENT_ID
    client_dir.mkdir(parents=True, exist_ok=True)
    (client_dir / "anomaly_controls.yaml").write_text(CONTROLS_YAML, encoding="utf-8")
    _patch_client_yaml(client_dir)
    _merge_bitacora(client_dir)
    generate_demo_csvs(demo_dir)
    digest_dir = root / "digest-fixture"
    digest_dir.mkdir(parents=True, exist_ok=True)
    (digest_dir / "2026-06-05.md").write_text(
        "Resumen ficticio: comunicados OPA sobre logística en sector 7; "
        "posible **actualización de algoritmo** en búsqueda (vigilar GSC).\n",
        encoding="utf-8",
    )
    return client_dir
