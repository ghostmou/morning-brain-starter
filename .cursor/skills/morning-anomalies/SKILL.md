---
name: morning-anomalies
description: Detecta anomalías diarias en GA4 y Google Search Console (caídas/subidas de clicks, impresiones, posición, sesiones, conversiones) sobre topics y páginas por cliente, y genera un informe HTML por cliente con severidad y acciones sugeridas. Usar cuando el usuario pida alertas matinales, detectar caídas de tráfico/conversiones/posiciones, revisar anomalías de cartera, ejecutar el paso de Alertas del good-morning, probar el flujo con datos sintéticos del lab, o preguntar por qué saltó un control o qué dice un informe ya generado en output/anomalies/.
---

# Morning anomalies — detección de anomalías GA4 + GSC

Skill de **referencia operativa**: ejecutar la detección, **presentar** los resultados a una persona de negocio (CMO/responsable), leer informes y explicar el sistema. Cubre qué ventanas se miran, qué datos entran, cómo se clasifica la gravedad, **cómo se cuenta el resultado** y cómo responder preguntas sobre lo detectado.

Este `SKILL.md` es el **índice operativo**: contrato, cómo presentar, glosario, vista general y CLI. El detalle por etapa vive en ficheros satélite (ver **Mapa de detalle**) que se leen **solo cuando hacen falta**.

## Contrato operativo (lo que el agente debe hacer)

- **Ejecutar, no programar:** invocar los CLI del **Anexo A**. **Nunca** escribir Python inline ni reimplementar el detector; la lógica vive en `scripts/anomaly_detection/`.
- **CWD = raíz del proyecto** (morning-brain-starter) en toda llamada CLI.
- **Una unidad = un cliente:** la salida es **un informe HTML por cliente**; el contexto compartido (bitácora, core updates, digest) aparece **una sola vez** por documento.
- **Presentar como consultor, no como dump de cifras:** al responder en chat o resumir un run, seguir el **formato de presentación de la sección 0**. No soltar una lista de Δ y z sin contexto.
- **Responder preguntas leyendo artefactos** de `output/anomalies/<fecha>/`, sin recalcular (ver `anomalies-answering.md`).
- **No inventar:** si falta un dato (finding, core update, digest, grupo monitorizado), decir explícitamente que no existe en ese run.
- **Criterio humano por encima de la etiqueta:** el sistema informa y sugiere; decisión y contacto con cliente son humanos (ver `anomalies-reporting.md` §5).

## Mapa de detalle (ficheros satélite)

Leer el fichero correspondiente **solo** cuando la tarea lo requiera. Todos viven en este mismo directorio.

| Necesito… | Fichero | Cubre |
|-----------|---------|-------|
| Explicar **cómo se detecta** y **por qué saltó** (algoritmo, ventanas, controles, gravedad) | [anomalies-detection.md](anomalies-detection.md) | Secciones 1 (detección) y 4 (severidad) |
| Saber **de dónde sale el dato** (sintético vs live, GA4/GSC) | [anomalies-data-sources.md](anomalies-data-sources.md) | Sección 2 |
| Interpretar con **contexto** (bitácora, core updates, digest, festivos) | [anomalies-context.md](anomalies-context.md) | Sección 3 |
| Editar **acciones sugeridas** o entender la **salida** (HTML/YAML/summary) | [anomalies-reporting.md](anomalies-reporting.md) | Secciones 5 (acciones) y 6 (salida) |
| **Responder preguntas en chat** sobre un informe ya generado | [anomalies-answering.md](anomalies-answering.md) | Sección 8 |

---

## 0. Cómo presentar los resultados (lo primero que debe leer el agente)

El destinatario por defecto es un **CMO o responsable de marketing que entiende el negocio** pero **no** es analista. Quiere saber, en este orden: **qué ha pasado, cuánto, si es grave y qué hacemos**. El informe HTML ya está construido con esta lógica; en **chat** el agente replica el mismo patrón.

### 0.1 Estructura de una respuesta (en chat o resumen)

1. **Titular (1 línea):** lo más relevante del run. Ej.: *"Caída de clics orgánicos del 24% con impresiones al alza: perdemos eficiencia en la SERP, no demanda."*
2. **Tabla por finding** con **rango y trayectoria**, no solo el día. Columnas mínimas:
   - métrica · **trayectoria** (últimos 4 días: `286 → 272 → 209 → 196`) · valor del día · **referencia esperada** · Δ% · **semana vs. anterior**.
   - Para clics GSC añadir **impresiones** y **CTR** (es la pareja que cuenta la historia).
3. **Lectura de consultor (3-6 líneas máx.):** interpretación de negocio, hipótesis ordenadas por probabilidad, y **qué propongo sin tocar nada todavía**. Cerrar con el umbral de escalado ("si en 3-4 días X, pasa de vigilar a actuar").

### 0.2 Cómo resumir **cualquier** tipo de resultado (tabla de traducción)

El detector siempre devuelve una **desviación** con polaridad y nivel. Traducir así, sin importar la métrica:

| Resultado del run | Cómo contarlo en una frase | Tono |
|-------------------|----------------------------|------|
| **0 findings** | "Volumen y medición dentro de lo esperado; nada que reportar hoy." | Tranquilo, sin rellenar |
| **Solo `leve`** | "Desviación pequeña; la dejo en seguimiento, no es para actuar." | Vigilar |
| **`serio`** | "Señal que merece revisión hoy: [qué] cae/sube [cuánto] y [por qué importa]." | Accionable |
| **`terrorifico`** | "Prioridad: [métrica] se ha [movido] [cuánto]; hay que validar hoy [qué]." | Urgente, directo |
| **`mejora_leve` / `alto`** | "Buena señal: [métrica] sube [cuánto]; conviene saber por qué para replicarlo." | Positivo, curioso |
| **`muy_alto`** | "Salto fuerte de [métrica] (+X%). Antes de celebrarlo, confirmar que no es un artefacto de medición." | Positivo con cautela |
| **Clics ↓ + impresiones ↑** | "Aparecemos más pero nos clican menos: problema de SERP/CTR, no de demanda." | Diagnóstico, no alarma de tráfico |
| **Pico que parece bug** (x2-x3 de un día a otro) | "Sospechoso de doble medición / cambio de tag; verificar antes de darlo por bueno." | Escéptico |

### 0.3 Reglas de redacción (consultor / responsable)

- **Sin humo ni condescendencia.** Diagnóstico → cuánto → riesgo → qué hacer. Una sola aclaración si falta un dato.
- **Rango siempre que se pueda:** un número suelto ("‑24%") dice menos que la trayectoria y el "semana vs. anterior".
- **Distinguir señal de causa:** el sistema detecta la **desviación**; la **causa** (deploy, festivo, core update, SERP) es hipótesis hasta cruzarla con el contexto compartido (`anomalies-context.md`).
- **No escalar tono por la etiqueta sola:** si la bitácora/festivo/core update explica la señal, decirlo y bajar urgencia (la etiqueta no cambia, la lectura sí).

## Cuándo usar

- Paso **Alertas** de la rutina `good-morning` (si `run_morning_anomalies: true`).
- El usuario pide **detectar / revisar anomalías** o **caídas** en GA4/GSC de uno o varios clientes.
- Preguntas sobre un **informe ya generado** (“¿por qué saltó X?”, “¿es grave?”, “¿hay core update?”).
- Probar o ejecutar el flujo con **datos sintéticos** del lab (desarrollo, onboarding, validación).

## Cuándo NO usar

- Informe **mensual** SEO completo → fuera de alcance de este starter (solo alertas diarias).
- Análisis **ad hoc** de una métrica sin el marco de controles/grupos monitorizados → consulta GA4/GSC directa.
- Crear o editar los **datos demo** → skill `generate-anomaly-demo-data` (este skill solo los consume).

## Glosario canónico (vocabulario fijo)

| Término | Significado | Dónde vive |
|---------|-------------|------------|
| **`D`** (fecha del informe) | Único día que se evalúa | flag `--date` |
| **control** | Regla que vigila una serie (fuente + métrica + grupo opcional) | `anomaly_controls.yaml` → `controls[]` |
| **grupo monitorizado** | Conjunto de **páginas** o **búsquedas (queries)** que cumplen unos filtros y se vigilan **juntos** (suma diaria). Ej.: landings bajo `/alquiler/` o queries de “alquiler excavadora”. | YAML: `query_collections` / `page_collections`; enlace desde control: `collection_id` |
| **`primary_metric`** | Métrica que dispara la alerta del control | `controls[].primary_metric` |
| **finding** | Anomalía detectada en `D` para un control | objeto `Finding` en `detect.py` |
| **severidad** | Dos escalas según polaridad. Impacto negativo: `leve` < `serio` < `terrorifico`. Señal positiva: `mejora_leve` < `alto` < `muy_alto` | `detect.py` `_severity` |
| **narrativa** | Texto legible del finding (valor vs referencia, ventana, semana vs. anterior, trayectoria, impresiones/CTR) | `finding_context.py` → `Finding.narrative` |
| **referencia esperada** | Valor "normal" contra el que se compara `D` (baseline híbrida 28d + mismo día de semana) | `Finding.baseline_mean` |
| **contexto compartido** | Bitácora + core updates + digest, una vez por cliente | bloque en `<client_id>.html` |
| **digest_skipped** | No había digest aplicable en el run | `run.meta.json` |

**Nota YAML:** en configuración el código sigue llamando `collection` / `collection_id` por compatibilidad. En documentación y respuestas al usuario usar siempre **grupo monitorizado**.

## Mapa concepto → código (fuente de verdad)

| Concepto del skill | Módulo |
|--------------------|--------|
| Filtros de grupo monitorizado | `scripts/anomaly_detection/filters.py` |
| Agregación diaria por grupo | `scripts/anomaly_detection/aggregate.py` |
| Algoritmo de detección (z-score híbrido) | `scripts/anomaly_detection/detect.py` |
| Narrativa, validación CTR y tendencia, subida de nivel | `scripts/anomaly_detection/finding_context.py` |
| Bitácora / core updates / digest | `bitacora.py` / `context_external.py` (+ `scripts/reporting/...core_updates...`) / `digest.py` |
| Plantillas de acciones sugeridas (texto) | **`anomalies-reporting.md` §5.2** + `suggested_action_templates.yaml` |
| Sustitución determinista en informe | `suggested_actions.py` (solo rellena `{context}`) |
| Informe HTML + gráficos | `report_html.py` + `chart_timeseries.py` |
| Orquestación run/seed-demo | `pipeline.py` + `python -m scripts.anomaly_detection.cli` |

---

## Vista general (orden del pipeline)

1. **Preparar contexto externo de Google** (actualizar CSV de core updates si toca).
2. **Cargar configuración del cliente** (`anomaly_controls.yaml`: grupos monitorizados + controles).
3. **Obtener series diarias** GA4/GSC (sintético o live) en ventana de **90 días** hasta `D` (ver `anomalies-data-sources.md`).
4. **Por cada control:** filtrar filas → agregar por día → **detectar** anomalía en `D` (ver `anomalies-detection.md`).
5. **Recoger contexto** (bitácora, core updates; digest opcional en `digest-fixture/`; festivos vía bitácora manual en v1) (ver `anomalies-context.md`).
6. **Generar salida:** HTML + `suggested_actions.yaml` + `summary.md` + `run.meta.json` (ver `anomalies-reporting.md`).

---

## 7. Activación en buenos días

En `good-morning/SKILL.md`:

| Clave | Uso |
|-------|-----|
| `run_morning_anomalies` | Si `true`, ejecutar paso **8 Alertas** tras bitácoras |

Dejar `false` hasta que cada cliente tenga `anomaly_controls.yaml` en `context/clients/<id>/`. Para probar sin OAuth: modo `--synthetic` con `--lab-root .`.

---

## Anexo A — Llamadas CLI

CWD = raíz del proyecto.

### A.1 Actualizar core updates (opcional)

```bash
.venv/bin/python -m scripts.reporting.sync_google_core_updates --max-age-hours 24
```

### A.2 Ejecutar detección — live (requiere OAuth GA4+GSC)

```bash
.venv/bin/python -m scripts.anomaly_detection.cli --mode run --date today --no-synthetic \
  --clients-root context/clients \
  --output-dir output/anomalies/$(date +%Y-%m-%d)
```

Digest opcional: `--news-digest-dir digest-fixture`

### A.3 Ejecutar detección — sintético (demo Tycho)

```bash
.venv/bin/python -m scripts.anomaly_detection.cli --mode run --date 2026-06-05 --synthetic \
  --lab-root . \
  --client-id tycho \
  --output-dir output/anomalies/2026-06-05
```

### A.4 Regenerar datos demo

```bash
.venv/bin/python -m scripts.anomaly_detection.cli --mode seed-demo
```

Ver skill `generate-anomaly-demo-data`.

### A.5 Comprobar credenciales

```bash
.venv/bin/python -m scripts.anomaly_detection.cli --mode test-auth
```

### A.6 Resumen en chat (sin CLI)

Leer `output/anomalies/<fecha>/summary.md` y enlazar cada `<client_id>.html`. Para el formato, usar la sección 0.
