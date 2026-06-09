"""Anomaly detection CLI: run | seed-demo | test-auth."""

from __future__ import annotations

import argparse
import logging
import sys
from datetime import date
from pathlib import Path

from scripts.anomaly_detection.pipeline import list_lab_clients, run_pipeline
from scripts.anomaly_detection.seed_demo import seed_demo_structure

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parents[2]


def _parse_date(s: str) -> str:
    if s.lower() in ("today", "hoy"):
        return date.today().isoformat()
    return s


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Morning anomaly detection CLI")
    p.add_argument("--mode", required=True, choices=["run", "seed-demo", "test-auth"])
    p.add_argument("--date", default="today", help="Report date YYYY-MM-DD or today")
    p.add_argument("--client-id", action="append", dest="client_ids", help="Client id (repeatable)")
    p.add_argument("--lab-root", type=Path, help="Repo root for synthetic demo (context/clients + demo-data)")
    p.add_argument("--clients-root", type=Path, help="Clients root for live mode")
    p.add_argument("--output-dir", type=Path, help="Output directory")
    p.add_argument("--synthetic", action="store_true", default=False, help="Use synthetic CSV")
    p.add_argument("--no-synthetic", action="store_true", help="Live fetch from GA4/GSC APIs")
    p.add_argument("--news-digest-dir", type=Path, help="Digest markdown directory")
    p.add_argument("--target-dir", type=Path, help="seed-demo output root (default: repo root)")
    return p


def cmd_run(args: argparse.Namespace) -> int:
    report_date = _parse_date(args.date)
    lab_root = args.lab_root
    synthetic = args.synthetic or bool(lab_root)
    if args.no_synthetic:
        synthetic = False
    if not lab_root and not args.clients_root:
        logger.error("Provide --lab-root or --clients-root")
        return 1
    client_ids = args.client_ids or []
    if lab_root and not client_ids:
        client_ids = list_lab_clients(lab_root)
    if not client_ids:
        logger.error("No clients to process")
        return 1
    out = args.output_dir or Path("output/anomalies") / report_date
    digest_dir = args.news_digest_dir
    if lab_root and not digest_dir:
        candidate = lab_root / "digest-fixture"
        if candidate.is_dir():
            digest_dir = candidate
    run_pipeline(
        report_date,
        client_ids,
        lab_root=lab_root,
        clients_root=args.clients_root,
        output_dir=out,
        synthetic=synthetic,
        news_digest_dir=digest_dir,
    )
    logger.info("Wrote reports to %s", out)
    return 0


def cmd_seed_demo(args: argparse.Namespace) -> int:
    target = args.target_dir or REPO_ROOT
    seed_demo_structure(target)
    logger.info("Seeded Tycho demo at %s", target)
    return 0


def cmd_test_auth(_args: argparse.Namespace) -> int:
    try:
        from scripts.credentials import get_secrets_dir, load_env
        from scripts.google_auth import ANALYTICS_READONLY_SCOPE, WEBMASTERS_SCOPE, get_credentials

        load_env()
        sd = get_secrets_dir()
        if not sd.exists():
            logger.error("Secrets dir missing: %s", sd)
            return 1
        get_credentials([ANALYTICS_READONLY_SCOPE, WEBMASTERS_SCOPE])
        logger.info("OAuth OK (GA4 + GSC scopes): %s", sd)
        return 0
    except Exception as e:
        logger.error("Auth check failed: %s", e)
        return 1


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.mode == "run":
        return cmd_run(args)
    if args.mode == "seed-demo":
        return cmd_seed_demo(args)
    if args.mode == "test-auth":
        return cmd_test_auth(args)
    return 1


if __name__ == "__main__":
    sys.exit(main())
