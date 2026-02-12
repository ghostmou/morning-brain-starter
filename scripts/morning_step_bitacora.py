#!/usr/bin/env python3
"""
Paso de bitácoras de la rutina matinal: obtiene eventos (calendario), tareas (Asana),
emails (Gmail) y transcripciones del día anterior, y añade entradas a
context/clients/<cliente>/bitacora.md según config/clients.yaml.
Ejecutar desde la raíz del proyecto. Usado por el comando morning-routine (paso 4).
"""

import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

_project_root = Path(__file__).resolve().parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))
os.chdir(_project_root)

from scripts.credentials import load_env

load_env()

from scripts import calendar_lite
from scripts import asana_lite
from scripts import email_lite
from scripts import bitacora_append


def main():
    events = []
    try:
        today, recent = calendar_lite.get_today_and_recent(days_recent=7)
        events = today + recent
    except Exception as ex:
        print("Calendario – Error al obtener eventos:", ex, file=sys.stderr)

    tasks = []
    if os.getenv("ASANA_ACCESS_TOKEN"):
        try:
            tasks = asana_lite.get_tasks_today()
        except Exception as ex:
            print("Asana – Error:", ex, file=sys.stderr)

    emails = []
    if (_project_root / "config" / "email.yaml").exists():
        try:
            emails = email_lite.get_recent_emails_if_configured()
        except Exception as ex:
            print("Email – Error:", ex, file=sys.stderr)

    # Transcripciones del día anterior: importar desde Calendar → contexto
    try:
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        imported = calendar_lite.import_transcriptions_from_calendar(_project_root, yesterday)
        if imported:
            print("Transcripciones – Importadas %d call(s) de ayer." % len(imported), file=sys.stderr)
    except Exception as ex_imp:
        if "documents.readonly" not in str(ex_imp) and "403" not in str(ex_imp):
            print("Transcripciones – Error al importar:", ex_imp, file=sys.stderr)

    # Transcripciones del día anterior (ficheros en context/clients/.../meetings/transcripcion-YYYY-MM-DD-*.md)
    transcription_entries = []
    try:
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        transcription_entries = bitacora_append.collect_transcriptions_for_date(_project_root, yesterday)
    except Exception as ex:
        print("Transcripciones – Error al listar:", ex, file=sys.stderr)

    # Tareas realizadas ayer (Asana): descripción → bitácora
    completed_entries = []
    if os.getenv("ASANA_ACCESS_TOKEN"):
        try:
            yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
            completed_entries = asana_lite.get_tasks_completed_on(yesterday)
        except Exception as ex:
            print("Asana (tareas realizadas) – Error:", ex, file=sys.stderr)

    try:
        added_events = bitacora_append.process_events(events)
        added_emails = bitacora_append.process_emails(emails)
        added_tasks = bitacora_append.process_asana_tasks(tasks)
        added_transcriptions = bitacora_append.process_transcriptions(transcription_entries)
        added_completed = bitacora_append.process_completed_tasks(completed_entries)
        all_added = added_events + added_emails + added_tasks + added_transcriptions + added_completed
        if all_added:
            clients_updated = list({c for c, _ in all_added})
            print(
                "Bitácoras – Añadidas entradas para:",
                clients_updated,
                "(reuniones: %d, email: %d, Asana: %d, transcripciones: %d, tareas realizadas: %d)"
                % (len(added_events), len(added_emails), len(added_tasks), len(added_transcriptions), len(added_completed)),
            )
        else:
            print("Bitácoras – Sin reuniones, emails, tareas ni transcripciones que matcheen clientes.")
    except Exception as ex:
        print("Bitácoras – Error:", ex, file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
