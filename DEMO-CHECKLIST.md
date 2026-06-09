# Checklist – Preparar demo (opción 2: ejecución real, nombres de ficción)

Usa esta lista para preparar la demo sin exponer datos reales. El repo que compartas no debe contener nombres de clientes o proyectos reales.

---

## Antes de la demo

### 1. Calendario de demo (Google)

- [x] Crear un **calendario nuevo** solo para la demo (p. ej. "Morning demo") en la cuenta que usarás, o usar uno de prueba.
  Creado: se llama "Demo #hechoConIA"
- [x] Añadir **4–6 eventos** con títulos que usen solo nombres de ficción, por ejemplo:
  - "Reunión Tycho - seguimiento"
  - "Kick-off Mao-Kwikowski"
  - "Call Rocinante Corp"
  - "Sync MCR"
- [x] Fechas: varios **hoy** y otros en los **últimos 2–3 días** para que `run_morning.py` los liste.
- [ ] Añadir transripción fake a la call de catch-up con Rocinante Corp.

### 2. Asana (opcional)

- [x] Si quieres mostrar tareas en la demo: crear un **workspace o proyecto de prueba** en Asana.
  Creado: se llama "Demo #hechoConIA"
- [ ] Añadir tareas con **due date = hoy** y nombres genéricos (p. ej. "Revisar propuesta Tycho", "Preparar deck Rocinante").
- [ ] En `resources/secrets/.env` usar un token de Asana que apunte a ese workspace de prueba (o el mismo si solo usas demo).

### 3. Credenciales

- [ ] Ejecutar `python scripts/setup_oauth.py` en esta carpeta.
- [ ] Completar OAuth para **Google** (Calendar; Gmail si lo usas). Opcional: Asana, Gmail.
- [ ] Comprobar que `resources/secrets/.env` existe y tiene al menos `GOOGLE_*` (y `ASANA_ACCESS_TOKEN` si usas Asana). Este archivo **no se sube** (está en `.gitignore`).

### 4. Configuración de clientes (ficción)

- [ ] En `config/clients.yaml` dejar **solo clientes de ficción** (p. ej. Tycho, Rocinante, Mao-Kwikowski, Acme). Que los `substrings` matcheen los títulos de los eventos del calendario de demo.
- [ ] Si en el repo compartido quieres otro contenido por defecto: no hagas commit de tu `clients.yaml` de demo, o restáuralo antes de push.

### 5. Primera ejecución

- [ ] Desde la raíz: `python run_morning.py`.
- [ ] Comprobar que se listan los eventos del calendario de demo y que se crean/actualizan bitácoras en `context/clients/<NombreFicción>/bitacora.md`.
- [ ] Las bitácoras generadas están ignoradas por `.gitignore` (solo se versiona `_example`); no se subirán por error.

### 6. Demo alertas GA4/GSC (sintético, sin APIs extra)

- [ ] `.venv/bin/python -m scripts.anomaly_detection.cli --mode seed-demo`
- [ ] `.venv/bin/python -m scripts.anomaly_detection.cli --mode run --date 2026-06-05 --synthetic --lab-root . --client-id tycho`
- [ ] Abrir `output/anomalies/2026-06-05/tycho.html`: **5 findings**, deploy **2026-06-04** en contexto, **May 2026 core update** (**2026-05-21**, fin rollout **2026-06-02**).
- [ ] Ver `docs/ANOMALIES.md` si quieres explicar el módulo en la demo.

---

## Antes de subir el repo (compartir)

- [ ] No hay `resources/secrets/` ni `.env` en el árbol que subes (ya ignorados).
- [ ] No hay **nombres reales** de clientes o proyectos en ningún archivo (README, BOARDING, config, etc.).
- [ ] `config/clients.yaml` en el repo tiene solo ejemplos de ficción o `_example`.
- [ ] No se han añadido por error carpetas como `context/clients/MiClienteReal/` (el `.gitignore` excluye todo `context/clients/*/` salvo `_example`; aun así, revisar `git status`).

---

## Resumen

| Qué              | Dónde / cómo |
|------------------|---------------|
| Calendario demo  | Cuenta Google → calendario nuevo + eventos con nombres de ficción. |
| Asana demo       | Workspace/proyecto de prueba + tareas con due hoy. |
| Credenciales     | `resources/secrets/.env` (nunca se sube). |
| Clientes         | `config/clients.yaml` solo ficción en el repo. |
| Bitácoras        | Generadas al ejecutar; ignoradas por `.gitignore` salvo `_example`. |
