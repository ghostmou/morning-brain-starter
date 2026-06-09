# Morning anomalies — Acciones sugeridas y salida (secciones 5 y 6)

> Fichero de referencia del skill `morning-anomalies`. Volver al índice: [SKILL.md](SKILL.md).
> Leer para editar las plantillas de acción sugerida o para entender la estructura de los artefactos de salida (HTML, YAML, summary).

## 5. Acciones sugeridas (texto editable por humanos)

Cada finding genera una línea en `<client_id>-suggested_actions.yaml` y el mismo párrafo en su sección del informe HTML.

### 5.1 División de responsabilidades

| Quién | Qué hace |
|-------|----------|
| **Humano (este skill + YAML)** | Redactar y mantener los **textos** de cada acción (checklists, tono, cuándo actuar). |
| **Código (`suggested_actions.py`)** | Solo sustituir `{context}` por la línea determinista (label, métrica, valor vs baseline, Δ%, z, semana vs anterior, impresiones y CTR cuando aplique) y escribir YAML/HTML. **No** inventar copy en Python. |

**Para cambiar las propuestas:** editar las plantillas de **§5.2** y reflejar el mismo texto en:

`scripts/anomaly_detection/suggested_action_templates.yaml`

(El YAML es lo que lee el CLI en runtime; el skill es la referencia legible.)

### 5.2 Plantillas maestras

Placeholder único que rellena el código: **`{context}`** = resumen numérico del finding (label, métrica, valor vs baseline, Δ%, z, y cuando aplica semana vs anterior, impresiones y CTR).

Prefijos fijos: `[Seguimiento]` = próximo ciclo · `[Hoy]` = revisar hoy · `[Urgente]` = prioridad inmediata · `[Positivo]` = señal favorable.

Hay seis severidades por fuente (tres negativas, tres positivas). Los textos maestros viven en `scripts/anomaly_detection/suggested_action_templates.yaml`; abajo el resumen de intención.

#### GA4 (`source: ga4`)

| Severidad | Prefijo · idea |
|-----------|----------------|
| **leve** | `[Seguimiento]` Anotar y revisar en el próximo pase; descartar festivo o cambio menor. |
| **serio** | `[Hoy]` Revisar tracking GA4/GTM, deploys, checkout y campañas que cambien el mix. |
| **terrorifico** | `[Urgente]` Validar evento/conversión, sesiones del grupo, checkout/atribución; cruzar contexto antes de tocar campañas. |
| **mejora_leve** | `[Positivo]` Subida leve; anotar qué cambió para confirmar si es real y replicable. |
| **alto** | `[Positivo]` Mejora clara; identificar la palanca y valorar reforzarla/extenderla. |
| **muy_alto** | `[Positivo]` Salto fuerte; descartar artefacto de medición y, si es real, capitalizar. |

#### GSC (`source: gsc_page` o `gsc_query`)

| Severidad | Prefijo · idea |
|-----------|----------------|
| **leve** | `[Seguimiento]` Revisar en próximo ciclo: SERP, estacionalidad y un día más de datos. |
| **serio** | `[Hoy]` Páginas del grupo, cannibalización, cobertura y core update en la ventana. |
| **terrorifico** | `[Urgente]` URLs principales, pérdida de impresiones vs clicks, penalización o bug GSC; documentar antes de cambios masivos. |
| **mejora_leve** | `[Positivo]` Subida leve de visibilidad/clics; vigilar si consolida y anotar a qué se debe. |
| **alto** | `[Positivo]` Ganancia clara en SERP; identificar URLs/queries, CTR y posición; reforzar donde aplique. |
| **muy_alto** | `[Positivo]` Salto fuerte; descartar estacionalidad o SERP puntual; si es estructural, mantenerlo. |

### 5.3 Regla de producto

El sistema **informa y sugiere**; la decisión final (y el contacto con cliente) sigue siendo humana, sobre todo en niveles **`leve`** y **señales positivas**, y cuando el contexto (festivo, deploy, cambio de SERP) explica la señal. Una señal positiva fuerte (`muy_alto`) merece la misma higiene de verificación que una negativa: confirmar que no es un artefacto de medición antes de presentarla como logro.

---

## 6. Salida que debe leer el agente

```
output/anomalies/<YYYY-MM-DD>/
  summary.md                         # tabla clientes + severidad máx + enlace HTML
  <client_id>.html                   # informe único
  <client_id>-suggested_actions.yaml
  run.meta.json                      # digest_skipped, synthetic/live, lista findings
```

### 6.1 Estructura del informe HTML (`<client_id>.html`)

Pensado para leerse de arriba abajo como una presentación a negocio:

1. **Cabecera:** cliente, día evaluado, modo (live/synthetic) y recordatorio de la referencia (media móvil 28d + mismo día de semana).
2. **Titular** (caja destacada): cuántas señales negativas/positivas y la más relevante en una frase. Verde si no hay impacto negativo.
3. **Resumen ejecutivo:** recuento por nivel en las dos escalas (impacto negativo / señales positivas).
4. **Navegación** a contexto y a cada finding por su label.
5. **Contexto compartido** (una vez): bitácora ±7 días, core/spam updates en ventana, digest si aplica.
6. **Una sección por finding** (ordenadas de peor a mejor): título + **badge de severidad** de color, tabla de métricas (día, valor, referencia, Δ/z, semana vs. anterior, impresiones, CTR), narrativa **"Qué ha pasado"**, **gráfico** y **"Acción sugerida"**.

### 6.2 `suggested_actions.yaml`

Por finding: `control_id`, `severity`, `metric`, `source`, `narrative` (texto legible) y `suggested` (acción con prefijo `[Seguimiento]`/`[Hoy]`/`[Urgente]`/`[Positivo]`).

En rutina matinal: bloque **## Alertas** con una fila por cliente afectado y ruta al HTML. Para resumir en chat, usar el **formato de presentación de la sección 0 del `SKILL.md`**.
