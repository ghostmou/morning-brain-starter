# Alertas GA4 + GSC (anomalías matinales)

Extensión opcional del morning routine: detecta desviaciones en métricas de Google Analytics 4 y Google Search Console y genera un **informe HTML por cliente** con severidad, contexto (bitácora, core updates) y acciones sugeridas.

## Quick start (demo sintético, sin OAuth)

```bash
.venv/bin/python -m scripts.anomaly_detection.cli --mode seed-demo
.venv/bin/python -m scripts.anomaly_detection.cli --mode run \
  --date 2026-06-05 --synthetic --lab-root . --client-id tycho
open output/anomalies/2026-06-05/tycho.html
```

El demo **Tycho** incluye 5 findings (3 malas, 2 buenas), deploy en bitácora del **2026-06-04** y **May 2026 core update** real (**2026-05-21**, rollout completo **2026-06-02** según [Google Search Status Dashboard](https://status.search.google.com/incidents/wdAXJk6LRRihEjpzEeWE)).

## Modo live (OAuth)

1. Activar en Google Cloud: **Analytics Data API** y **Search Console API**.
2. Regenerar token: `.venv/bin/python scripts/setup_oauth.py` (incluye scopes GA4+GSC).
3. Por cliente en `context/clients/<id>/`:
   - `client.yaml`: `ga4_property_id`, `gsc_site_url`
   - `anomaly_controls.yaml`: grupos monitorizados + controles
4. Ejecutar:

```bash
.venv/bin/python -m scripts.anomaly_detection.cli --mode test-auth
.venv/bin/python -m scripts.anomaly_detection.cli --mode run --date today --no-synthetic \
  --clients-root context/clients --client-id <id>
```

## Estructura

| Ruta | Contenido |
|------|-----------|
| `context/clients/<id>/anomaly_controls.yaml` | Controles y colecciones |
| `demo-data/<id>/*.csv` | Datos sintéticos (modo `--synthetic`) |
| `data/google_core_updates.csv` | Actualizaciones Google (sync remoto opcional) |
| `output/anomalies/<fecha>/` | HTML, YAML, `summary.md`, `run.meta.json` |
| `scripts/anomaly_detection/` | Pipeline de detección |

## Core updates

```bash
.venv/bin/python -m scripts.reporting.sync_google_core_updates
```

Fusiona incidentes Ranking desde el dashboard público de Google en `data/google_core_updates.csv`.

## Integración morning routine

En `.cursor/skills/good-morning/SKILL.md`, activar `run_morning_anomalies: true` para el paso 8.

## Skills

- `morning-anomalies` — ejecutar, presentar y responder preguntas
- `generate-anomaly-demo-data` — regenerar CSV demo Tycho

## Calibración (recomendado)

Las dos primeras semanas en un cliente nuevo: revisar informes en modo observación antes de escalar alertas al cliente final.
