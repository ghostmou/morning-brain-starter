#!/usr/bin/env python3
"""
Setup OAuth de Google: un solo flujo que pide TODOS los permisos necesarios para
Calendar, Meet, Gmail y Google Docs. El token resultante se guarda en GOOGLE_REFRESH_TOKEN.

Asana no se configura aquí: el token de Asana (ASANA_ACCESS_TOKEN) se pone directamente
en resources/secrets/.env cuando lo tengas.

Ejecutar desde la raíz del proyecto:
  .venv/bin/python scripts/setup_oauth.py
  .venv/bin/python scripts/setup_oauth.py --regenerate   # forzar nuevo token

Si python no existe, usar python3.
"""

import argparse
import os
import sys
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))
os.chdir(project_root)

from scripts.credentials import get_secrets_dir, get_env_path, load_env


# Todos los scopes de Google que usa el proyecto (Calendar, Meet, Gmail, Docs).
# Deben coincidir con lo que usan calendar_lite, email_lite y docs_lite al refrescar.
GOOGLE_SCOPES = [
    # Calendar: leer eventos y modificar (añadir Meet, aceptar/rechazar, descripción)
    "https://www.googleapis.com/auth/calendar.readonly",
    "https://www.googleapis.com/auth/calendar.events",
    # Meet: activar transcripción en el space de la videollamada
    "https://www.googleapis.com/auth/meetings.space.settings",
    # Gmail: leer correo reciente (morning, bitácoras)
    "https://www.googleapis.com/auth/gmail.readonly",
    # Docs: leer contenido de Docs enlazados (transcripciones en eventos de Calendar)
    "https://www.googleapis.com/auth/documents.readonly",
]


def read_env_lines() -> list:
    env_path = get_env_path()
    if not env_path.exists():
        return []
    return env_path.read_text(encoding="utf-8").splitlines()


def write_env_line(key: str, value: str, lines: list) -> list:
    out = []
    done = False
    for line in lines:
        if line.strip().startswith(key + "="):
            out.append(f"{key}={value}")
            done = True
        else:
            out.append(line)
    if not done:
        out.append(f"{key}={value}")
    return out


def save_env(lines: list) -> None:
    get_secrets_dir().mkdir(parents=True, exist_ok=True)
    get_env_path().write_text("\n".join(lines) + "\n", encoding="utf-8")


def do_google_oauth(scopes: list) -> str:
    from google_auth_oauthlib.flow import InstalledAppFlow

    client_id = os.getenv("GOOGLE_CLIENT_ID")
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
    if not client_id or not client_secret:
        print("Falta GOOGLE_CLIENT_ID o GOOGLE_CLIENT_SECRET en .env.")
        print("Copia .env.example a resources/secrets/.env y rellena esos valores.")
        print("Ver CREDENTIALS.md para dónde obtenerlos.")
        sys.exit(1)
    flow = InstalledAppFlow.from_client_config(
        {
            "installed": {
                "client_id": client_id,
                "client_secret": client_secret,
                "redirect_uris": ["http://localhost"],
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
            }
        },
        scopes=scopes,
    )
    creds = flow.run_local_server(port=0)
    return creds.refresh_token


def main():
    parser = argparse.ArgumentParser(
        description="OAuth de Google: un solo flujo con todos los permisos (Calendar, Meet, Gmail, Docs)."
    )
    parser.add_argument(
        "--regenerate",
        action="store_true",
        help="Regenerar el token aunque ya exista GOOGLE_REFRESH_TOKEN en .env",
    )
    args = parser.parse_args()

    load_env()
    env_path = get_env_path()
    if not env_path.exists():
        print("No existe resources/secrets/.env")
        print("Copia .env.example a resources/secrets/.env y rellena GOOGLE_CLIENT_ID y GOOGLE_CLIENT_SECRET.")
        sys.exit(1)

    has_token = bool(os.getenv("GOOGLE_REFRESH_TOKEN", "").strip())
    if has_token and not args.regenerate:
        print("Ya tienes GOOGLE_REFRESH_TOKEN en .env.")
        print("Para regenerar el token con todos los permisos, ejecuta:")
        print("  .venv/bin/python scripts/setup_oauth.py --regenerate")
        print("\n(Asana: configura ASANA_ACCESS_TOKEN directamente en .env cuando lo tengas.)")
        return

    print("Conectar Google (todos los permisos en un solo paso)")
    print("Se abrirá el navegador. Autoriza:")
    print("  • Calendar (ver y editar eventos, Meet)")
    print("  • Meet (activar transcripción)")
    print("  • Gmail (leer correo)")
    print("  • Google Docs (leer documentos enlazados, p. ej. transcripciones)")
    print()
    refresh = do_google_oauth(GOOGLE_SCOPES)
    lines = read_env_lines()
    lines = write_env_line("GOOGLE_REFRESH_TOKEN", refresh, lines)
    save_env(lines)
    print("Token guardado en GOOGLE_REFRESH_TOKEN.")
    print("\nAsana: cuando tengas tu Personal Access Token, añade ASANA_ACCESS_TOKEN en .env.")
    print("Listo. Prueba: .venv/bin/python run_morning.py")


if __name__ == "__main__":
    main()
