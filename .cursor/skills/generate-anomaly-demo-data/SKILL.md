# Generate anomaly demo data

Regenera CSV sintéticos, `anomaly_controls.yaml` y configuración del cliente demo **Tycho** (ficción The Expanse). Sin llamadas a APIs.

## Comando principal

```bash
.venv/bin/python -m scripts.anomaly_detection.cli --mode seed-demo
```

Escribe en la raíz del proyecto:

- `context/clients/tycho/` — `anomaly_controls.yaml`, `client.yaml` (GA4/GSC fake), bitácora (añade entrada deploy si falta)
- `demo-data/tycho/` — CSV GA4 + GSC (90 días)
- `digest-fixture/2026-06-05.md` — noticia ficticia opcional

### Directorio custom

```bash
.venv/bin/python -m scripts.anomaly_detection.cli --mode seed-demo --target-dir /tmp/morning-demo
```

## Incidentes plantados (fecha informe `2026-06-05`)

| ID | Control | Efecto |
|----|---------|--------|
| INC-01 | `GA4_SECTOR7_01` | Caída conversiones en `/sector-7/materiales/` |
| INC-02 | `GSC_TOPIC_S7_01` | Caída clics topic sector 7 |
| INC-03 | `GA4_SITE_01` | Caída sesiones sitio (sin grupo) |
| INC-04 | `GSC_TOPIC_N7_01` | Subida clics topic Nave 7 |
| INC-05 | `GSC_PAGE_N7_01` | Subida clics landings `/nave-7/` |

**Contexto narrativo:** deploy web **2026-06-04** en bitácora; **May 2026 core update** real (**2026-05-21**, fin **2026-06-02**) en `data/google_core_updates.csv` (sync con `scripts.reporting.sync_google_core_updates`).

## Verificar detección

```bash
.venv/bin/python -m scripts.anomaly_detection.cli --mode run --date 2026-06-05 --synthetic \
  --lab-root . \
  --client-id tycho \
  --output-dir output/anomalies/2026-06-05
```

Esperado: **5 findings** (3 malas, 2 buenas) en `tycho.html`, con bitácora y core update en el bloque de contexto.

## Colecciones (v1)

Filtros: `regex`, `contains`, `starts_with`, `ends_with`.

Ver `query_collections` y `page_collections` en `context/clients/tycho/anomaly_controls.yaml`.

## Criterios datos sintéticos

- **Bajadas creíbles:** ~20–35% en la métrica primaria, preferiblemente **2–3 días** de deslizamiento.
- **Mejoras:** subidas ~30–45% para señales positivas (`mejora_*` / `muy_alto`).
- Tras cambiar CSV, volver a ejecutar `run` con `--date` = último día del escenario.
- Detalle del informe HTML: skill `morning-anomalies` → `anomalies-reporting.md`.
