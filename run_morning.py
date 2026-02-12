#!/usr/bin/env python3
"""
Morning routine: Calendar (obligatorio), Asana y Gmail opcionales, transcripciones, bitácoras.
Cada paso tiene su llamada CLI equivalente; no hace falta ejecutar run_morning.py.
Ver .cursor/skills/good-morning/SKILL.md para comandos por paso.

Ejecutar desde la raíz: .venv/bin/python run_morning.py [--step N] [--show-cli]
  --step 1..7   Solo ese paso
  --show-cli    Imprimir los comandos CLI sin ejecutar
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path

_project_root = Path(__file__).resolve().parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))
os.chdir(_project_root)

_CLI_PREFIX = ".venv/bin/python"

_CLI_COMMANDS = {
    1: f"{_CLI_PREFIX} scripts/calendar_lite.py --today --add-meet --add-meet-my-events-only --add-transcription-reminder",
    2: f"{_CLI_PREFIX} scripts/asana_lite.py --move-yesterday-to-today",
    3: f"{_CLI_PREFIX} scripts/asana_lite.py",
    4: f"{_CLI_PREFIX} scripts/email_lite.py",
    5: f"{_CLI_PREFIX} scripts/calendar_lite.py --import-transcriptions",
    6: f"{_CLI_PREFIX} scripts/asana_lite.py --completed-yesterday-to-bitacora",
    7: f"{_CLI_PREFIX} scripts/morning_step_bitacora.py",
}

_STEP_LABELS = {
    1: "Calendario (hoy + Meet + transcripciones)",
    2: "Asana (mover tareas de ayer a hoy)",
    3: "Asana (listar tareas de hoy)",
    4: "Email",
    5: "Transcripciones (importar ayer)",
    6: "Asana (tareas realizadas ayer → bitácora)",
    7: "Bitácoras",
}


def main():
    parser = argparse.ArgumentParser(
        description="Morning routine. Cada paso tiene CLI equivalente (ver --show-cli).",
    )
    parser.add_argument(
        "--step",
        type=int,
        choices=[1, 2, 3, 4, 5, 6, 7],
        default=None,
        help="Ejecutar solo este paso.",
    )
    parser.add_argument(
        "--show-cli",
        action="store_true",
        help="Imprimir los comandos CLI sin ejecutar.",
    )
    args = parser.parse_args()

    if args.show_cli:
        print("Comandos CLI de la morning routine (desde la raíz del proyecto):\n")
        for i in range(1, 8):
            print(f"  Paso {i} – {_STEP_LABELS[i]}:")
            print(f"    {_CLI_COMMANDS[i]}\n")
        return 0

    steps = [args.step] if args.step else [1, 2, 3, 4, 5, 6, 7]
    for i, s in enumerate(steps):
        if i == 0:
            print("=== Morning routine ===\n", flush=True)
        print(f"[Paso {s}] {_STEP_LABELS[s]}\n  CLI: {_CLI_COMMANDS[s]}\n", flush=True)
        ret = subprocess.run(_CLI_COMMANDS[s], shell=True, cwd=_project_root)
        if ret.returncode != 0:
            sys.exit(ret.returncode)

    print("\n---")
    print("Hecho con ayuda del morning-brain-starter")
    return 0


if __name__ == "__main__":
    sys.exit(main() or 0)
