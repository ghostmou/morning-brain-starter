#!/usr/bin/env python3
"""
Elimina la configuración local (credenciales, tokens y venv) para dejar el proyecto como recién clonado.
No modifica código ni config/clients.yaml ni config/email.yaml.
No borra config/demo/ ni el flag de emails fake; lo (re)crea para que la demo siga disponible.
"""

import shutil
import sys
from pathlib import Path

_project_root = Path(__file__).resolve().parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from scripts.credentials import get_secrets_dir


def _ensure_demo_gmail_flag() -> None:
    """Asegura que exista config/demo_gmail_fake.yaml para que la demo con emails fake siga disponible tras un reset."""
    flag = _project_root / "config" / "demo_gmail_fake.yaml"
    if not flag.exists():
        flag.parent.mkdir(parents=True, exist_ok=True)
        flag.write_text("# Activar modo demo para Gmail (emails fake)\n", encoding="utf-8")


def main():
    removed = []

    # 1) Vaciar resources/secrets/
    secrets_dir = get_secrets_dir()
    if secrets_dir.exists():
        for f in secrets_dir.iterdir():
            if f.is_file():
                f.unlink()
                removed.append(f"secrets/{f.name}")

    # 2) Eliminar el venv del proyecto
    venv_dir = _project_root / ".venv"
    if venv_dir.exists() and venv_dir.is_dir():
        shutil.rmtree(venv_dir)
        removed.append(".venv")

    # 3) No borrar config/demo/ ni demo_gmail_fake.yaml; (re)crear el flag para que la demo siga disponible
    _ensure_demo_gmail_flag()

    if removed:
        print("Configuración eliminada:", ", ".join(removed))
        print("Puedes volver a configurar con el boarding o ejecutando: python scripts/setup_oauth.py")
        print("(Demo: config/demo/ y flag de emails fake se mantienen.)")
    else:
        print("No había credenciales ni .venv. Nada que resetear.")
        print("(Demo: config/demo/ y flag de emails fake se mantienen.)")


if __name__ == "__main__":
    main()
