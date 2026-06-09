import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]


def test_cli_run_synthetic(tmp_path: Path):
    lab = tmp_path / "lab"
    cmd = [
        sys.executable,
        "-m",
        "scripts.anomaly_detection.cli",
        "--mode",
        "seed-demo",
        "--target-dir",
        str(lab),
    ]
    subprocess.run(cmd, cwd=REPO, env={**__import__("os").environ, "PYTHONPATH": str(REPO)}, check=True)
    assert (lab / "demo-data" / "tycho" / "gsc_query_daily.csv").exists()
    out = tmp_path / "output"
    cmd2 = [
        sys.executable,
        "-m",
        "scripts.anomaly_detection.cli",
        "--mode",
        "run",
        "--date",
        "2026-06-05",
        "--synthetic",
        "--lab-root",
        str(lab),
        "--client-id",
        "tycho",
        "--output-dir",
        str(out),
    ]
    r = subprocess.run(
        cmd2,
        cwd=REPO,
        env={**__import__("os").environ, "PYTHONPATH": str(REPO)},
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stderr
    assert (out / "tycho.html").exists()
    controls = (lab / "context" / "clients" / "tycho" / "anomaly_controls.yaml").read_text()
    assert "query_collections" in controls
