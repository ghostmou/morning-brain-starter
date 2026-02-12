# Reset configuración (morning-brain-starter)

Borra las credenciales, tokens y el entorno virtual (`.venv`) para dejar el proyecto como recién clonado. No toca código ni `config/clients.yaml` / `config/email.yaml`. **No borra la demo:** mantiene `config/demo/` y (re)crea `config/demo_gmail_fake.yaml` para que el circuito de emails fake siga disponible.

## Comando

Desde la raíz del proyecto (con el Python del sistema o uno que no sea el del .venv de este proyecto):

```bash
python scripts/reset_config.py
```

Si ya no tienes .venv, cualquier `python` vale.

## Qué hace

- Elimina todo el contenido de `resources/secrets/` (`.env`, tokens JSON, etc.). El directorio se mantiene; solo se vacía.
- **Elimina el directorio `.venv`** (entorno virtual creado en el boarding) para que no quede nada del entorno de Python del proyecto.
- **No elimina** `config/demo/` (emails fake) ni `config/demo_gmail_fake.yaml`: si el flag no existe, lo crea para que la demo con emails fake siga disponible tras el reset.
- Para volver a usar el morning con credenciales reales, hay que seguir de nuevo el boarding (que creará un nuevo venv) o ejecutar `python scripts/setup_oauth.py` y completar OAuth.

## Cuándo usarlo

- Cambiar de cuenta Google/Asana.
- Dejar el repo listo para que otra persona lo configure desde cero.
- Probar el boarding de nuevo sin credenciales ni venv previos.
