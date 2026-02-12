#!/usr/bin/env python3
"""
Lee la transcripción del Google Doc enlazado en la descripción de una call del calendario
(fecha = ayer por defecto, opcionalmente filtrada por cliente).

La lógica vive en calendar_lite.read_transcription_for_date(); este script es un atajo.
Uso recomendado desde CLI de calendar: ver .cursor/commands/calendar-meet-transcription.md

Uso (desde la raíz del proyecto):
  .venv/bin/python scripts/read_transcription_from_calendar.py --client mcr
  .venv/bin/python scripts/read_transcription_from_calendar.py --client mcr --date 2026-02-11
"""

import argparse
import sys
from datetime import datetime, timedelta
from pathlib import Path

_project_root = Path(__file__).resolve().parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from scripts.credentials import load_env

load_env()

from scripts import calendar_lite


def main():
    parser = argparse.ArgumentParser(
        description="Leer transcripción del Google Doc enlazado en la call del calendario (delega en calendar_lite)."
    )
    parser.add_argument("--client", "-c", type=str, default=None, help="Filtrar por cliente (ej: mcr).")
    parser.add_argument("--date", type=str, default=None, help="Fecha YYYY-MM-DD (por defecto: ayer).")
    args = parser.parse_args()

    date_iso = args.date or (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    event, text = calendar_lite.read_transcription_for_date(
        date_iso, client_filter=args.client
    )
    if event and text:
        print("Evento:", (event.get("summary") or "(sin título)").strip(), file=sys.stderr)
        print(text)
        return 0
    if not event:
        print(
            "No hay evento con enlace a Google Docs en la descripción para esa fecha"
            + (" y cliente." if args.client else "."),
            file=sys.stderr,
        )
    else:
        print(
            "No se pudo leer el documento (API Docs y scope documents.readonly?).",
            file=sys.stderr,
        )
    return 1


if __name__ == "__main__":
    sys.exit(main())
