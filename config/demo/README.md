# Demo – datos fake

- **`emails_fake.json`**: lista de emails inventados (temática The Expanse) para usar en la demo del morning cuando no quieras llamar a Gmail real.
- Para activar el modo fake: crea en la raíz de `config/` un fichero **`demo_gmail_fake.yaml`** (puede estar vacío). Ese fichero está en `.gitignore`; si existe, `email_lite` devuelve estos datos en lugar de consultar Gmail.
- **Reset:** el comando `python scripts/reset_config.py` no borra `config/demo/` ni el flag; si `demo_gmail_fake.yaml` no existe, lo (re)crea para que la demo siga disponible tras un reset.
