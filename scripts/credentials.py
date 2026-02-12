"""
Resolución del directorio de secretos y carga de .env.
Toda credencial debe vivir en resources/secrets/ (o SECRETS_DIR).
"""

import os
from pathlib import Path


def get_secrets_dir() -> Path:
    """Directorio donde están .env y los token files.

    Prioridad:
    1. SECRETS_DIR (variable de entorno, ruta absoluta)
    2. CWD/resources/secrets
    """
    explicit = os.getenv("SECRETS_DIR")
    if explicit:
        p = Path(explicit).resolve()
        p.mkdir(parents=True, exist_ok=True)
        return p
    cwd = Path.cwd()
    secrets = cwd / "resources" / "secrets"
    secrets.mkdir(parents=True, exist_ok=True)
    return secrets


def get_env_path() -> Path:
    """Ruta al .env dentro del directorio de secretos."""
    return get_secrets_dir() / ".env"


def load_env() -> None:
    """Carga el .env del directorio de secretos en os.environ."""
    from dotenv import load_dotenv
    env_path = get_env_path()
    if env_path.exists():
        load_dotenv(env_path)
