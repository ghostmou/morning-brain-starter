# Morning anomalies — Detección y gravedad (secciones 1 y 4)

> Fichero de referencia del skill `morning-anomalies`. Volver al índice: [SKILL.md](SKILL.md).
> Leer cuando haya que explicar **por qué saltó** un control, cómo funciona el algoritmo o cómo se clasifica la severidad.

## 1. Cómo se detecta

### 1.1 Fecha que se evalúa

- Se analiza **un solo día**: la **fecha del informe** (`--date`, o `today` en rutina matinal).
- Ese día es el candidato a “día anómalo”; todo el histórico anterior sirve solo de referencia.

### 1.2 Ventana temporal de datos

| Concepto | Duración | Uso |
|----------|----------|-----|
| **Serie para detección** | **90 días** hasta la fecha del informe (inclusive) | Filas diarias GA4/GSC que alimentan cada control |
| **Baseline móvil** | **28 días** estrictamente **anteriores** al día del informe | Media y desviación típica (z-score) |
| **Mismo día de la semana** | **2 semanas** previas (mismo weekday, sin incluir el día del informe) | Refuerzo de estacionalidad semanal; se promedia con la baseline de 28 días |
| **Historial mínimo** | Al menos **7 días** con datos antes del informe | Si no hay, el control **no** genera finding (evita ruido al arrancar) |

Ejemplo: informe `2026-06-02` → datos desde ~`2026-03-05` hasta `2026-06-02`; la comparación del 2 junio usa marzo–mayo y los dos martes/lunes previos según corresponda.

### 1.3 Qué es un “control” y un “grupo monitorizado”

**Grupo monitorizado** = criterio para decir “estas filas cuentan juntas”. No es una carpeta ni un informe aparte: es la **definición de qué URLs o qué búsquedas** entran en la misma serie diaria antes de detectar.

Ejemplos (negocio B2B, alquiler de maquinaria industrial):

- Grupo de **búsquedas** GSC: queries de alquiler de excavadora, retroexcavadora, grúa, etc.
- Grupo de **páginas** GA4/GSC: URLs bajo `/alquiler/` (landings de categoría o ficha de máquina).

Configuración en `anomaly_controls.yaml` (por cliente):

- **`query_collections`**: grupos sobre dimensión **`query`** (GSC).
- **`page_collections`**: grupos sobre **`page`** (GSC) o **`page_path`** (GA4).
- **`controls`**: cada uno enlaza un grupo (`collection_id`) y define **qué métrica** dispara la alerta.

**Ejemplo integrado** (`context/clients/<client_id>/anomaly_controls.yaml` o lab):

```yaml
# --- Grupos monitorizados (definen QUÉ filas entran) ---
# Caso: renta B2B de maquinaria industrial (excavadoras, grúas, plataformas…)

query_collections:
  - id: topic_alquiler_maquinaria        # id que referenciará un control GSC query
    label: "Alquiler maquinaria (queries)"
    match_mode: any                      # any = basta un filtro; all = deben cumplirse todos
    filters:
      - type: contains
        value: "alquiler excavadora"
      - type: contains
        value: "alquiler retroexcavadora"
      - type: contains
        value: "alquiler grúa"
      - type: contains
        value: "alquiler maquinaria construcción"

page_collections:
  - id: landings_alquiler
    label: "Landings alquiler"
    match_mode: any
    filters:
      - type: contains
        value: "/alquiler/"              # page_path GA4 o URL GSC page

# --- Controles (definen QUÉ métrica vigilar sobre cada grupo) ---

controls:
  - id: GA4_ALQUILER_01                  # id del finding en HTML (finding-GA4_ALQUILER_01)
    source: ga4                          # ga4 | gsc_page | gsc_query
    collection_id: landings_alquiler     # enlace al grupo page_collections
    metrics: [sessions, conversions]     # métricas a agregar por día (suma)
    primary_metric: conversions          # p. ej. solicitudes de presupuesto / lead
    label: "GA4 landings alquiler"

  - id: GSC_TOPIC_ALQUILER_01
    source: gsc_query
    collection_id: topic_alquiler_maquinaria
    metrics: [clicks, impressions, position]
    primary_metric: clicks
    label: "Visibilidad topic alquiler maquinaria"
```

**Lectura del ejemplo:** `GA4_ALQUILER_01` suma cada día `sessions` y `conversions` de páginas bajo `/alquiler/` y evalúa si `conversions` en `D` es anómala (caída de leads en landings de alquiler). `GSC_TOPIC_ALQUILER_01` agrega clicks de búsquedas del topic de alquiler industrial y vigila si la visibilidad orgánica del cluster cae.

**Vista de sitio completo (sin grupo):** un control **sin `collection_id`** vigila el agregado de **todo el cliente** (no un topic). Útil como "alarma general". Para GSC usa el total real por `date` (ver `anomalies-data-sources.md` §2.2). Ejemplo:

```yaml
controls:
  - id: GSC_SITE_CLICKS_01
    source: gsc_query
    metrics: [clicks, impressions, position]
    primary_metric: clicks            # con impressions en metrics → CTR + gráfico doble eje
    label: "GSC clicks sitio (total)"
  - id: GA4_SITE_CONVERSIONS_01
    source: ga4
    metrics: [sessions, conversions]
    primary_metric: conversions
    label: "GA4 conversiones sitio (total)"
```

Nota: con vista de sitio, `gsc_query` y `gsc_page` sobre `clicks` dan el **mismo total**; basta uno para clics de sitio.

Filtros v1 (combinables con `match_mode: any | all`):

| Tipo | Comportamiento |
|------|----------------|
| `contains` | Subcadena (sin distinguir mayúsculas) |
| `starts_with` / `ends_with` | Prefijo / sufijo |
| `regex` | Patrón compilable (validado al cargar YAML) |

**Fuentes de control (`source`):**

| source | Datos | Dimensión filtrada |
|--------|--------|-------------------|
| `ga4` | `ga4_daily.csv` o API GA4 | `page_path` |
| `gsc_page` | `gsc_page_daily.csv` o API GSC | `page` (URL) |
| `gsc_query` | `gsc_query_daily.csv` o API GSC | `query` |

### 1.4 Agregación (antes de detectar)

Por control, paso a paso:

1. Cargar todas las filas de la fuente en la ventana de 90 días.
2. **Acotar el conjunto:**
   - Si el control tiene `collection_id` → **quedarse solo** con filas del grupo monitorizado (filtros del YAML).
   - Si **no** tiene grupo y la fuente es GSC → usar el **total de sitio** por `date` (no la suma de top queries, que infravalora; ver `anomalies-data-sources.md` §2.2).
3. **Sumar por `date`** las métricas listadas en el control (`metrics`).
4. Quedarse con la **`primary_metric`** (p. ej. `clicks`, `conversions`) como serie univariada: `fecha → valor`. Si la `primary_metric` es `clicks` y `impressions` está en `metrics`, se guarda también la serie de impresiones como **acompañante** (para CTR y gráfico de doble eje).

### 1.5 Algoritmo de detección (por serie)

**Nombre (documentación y código):** **z-score con baseline híbrida** — en el repo: *hybrid rolling z-score + same-weekday baseline* (`scripts/anomaly_detection/detect.py`).

**Idea en una frase:** comparar el valor del día del informe con lo “normal” reciente (28 días) y con el mismo día de la semana (2 semanas), y marcar alerta solo si la desviación es grande en unidades de dispersión (z) o en porcentaje (Δ%).

**Base matemática (resumida):**

| Símbolo | Significado |
|---------|-------------|
| `D` | Fecha del informe |
| `V` | Valor de la métrica primaria en `D` |
| `μ₂₈` | Media de los valores en los 28 días estrictamente anteriores a `D` |
| `σ₂₈` | Desviación típica poblacional (`pstdev`) de esos 28 días |
| `μ_wd` | Media de valores del **mismo weekday** que `D` en las 2 semanas previas (sin incluir `D`) |

**Baseline combinada:**

- `μ = (μ₂₈ + μ_wd) / 2` cuando existen ambas; si solo hay una, se usa esa.
- `σ = σ₂₈`; si `σ = 0`, se intenta `σ` desde los días weekday; si sigue en 0 → **sin alerta**.

**Estadístico principal:**

- **z-score:** `z = (V − μ) / σ`
- **Desviación relativa:** `Δ% = (V − μ) / μ × 100` (si `μ ≠ 0`)

**Regla de alerta:** umbrales en `z` y `Δ%` (sección 4, abajo); no es un test de hipótesis formal (no hay p-value), es un **filtro operativo** para priorizar revisión humana.

**Pasos operativos** (misma lógica que el código):

1. Calcular `μ₂₈` y `σ₂₈` con los **28 días** anteriores a `D`.
2. Calcular `μ_wd` con el **mismo weekday** en las **2 semanas** previas (si existen).
3. Combinar en `μ` y calcular `z` y `Δ%` como arriba.
4. Clasificar severidad según dirección de la métrica (caída vs subida de `position`).
5. Si `σ = 0` o histórico inferior a 7 días → **no hay alerta**.

**Métricas donde “más alto = peor”:** `position`, `avg_position` (subida = posible problema).  
**Resto** (`clicks`, `impressions`, `sessions`, `conversions`, …): **más bajo = peor**.

**Pseudocódigo** (espejo de `evaluate_series`, para razonar sin abrir el código):

```text
si V no existe en serie:                  -> sin alerta
si días con datos antes de D < 7:          -> sin alerta
μ28, σ28 = media/pstdev(28 días previos)
μwd      = media(mismo weekday, 2 semanas previas)
μ = promedio(μ28, μwd) si ambos; si no, el que exista
σ = σ28; si σ==0: σ = pstdev(días weekday)
si σ == 0:                                 -> sin alerta
z   = (V - μ) / σ
Δ%  = (V - μ) / μ * 100
sev = clasificar(z, Δ%, dirección de la métrica)   # sección 4
si sev is None:                            -> sin alerta
si no:                                     -> finding(sev, z, Δ%, V, μ, ...)
```

**Ejemplo numérico (caída de clicks):** μ ≈ 100, σ ≈ 8, V = 41 → `z = (41−100)/8 ≈ −7,4`, `Δ% = −59 %`. Ambos cruzan el umbral más alto de impacto negativo (z ≤ −3,5 o Δ% ≤ −50). Resultado: finding `terrorifico`. (Si en vez de caer, la métrica subiera con la misma magnitud, el finding sería `muy_alto` en la escala positiva.)

### 1.6 Cuándo **no** se genera alerta

- Menos de 7 días de histórico antes de `D`.
- Desviación nula (todos los días iguales).
- La señal no alcanza ningún umbral de la tabla de gravedad (sección 4, abajo).
- Grupo monitorizado vacío tras filtros (control silencioso).

---

## 4. Cómo se clasifica la gravedad

Todo **finding** es una **desviación**: el signo decide si va a la escala **negativa** (perjudica al negocio) o **positiva** (lo favorece). Misma magnitud de umbrales en ambos sentidos. La etiqueta va en HTML, YAML y resumen matinal.

**Concepto clave (evita la confusión histórica):** las etiquetas **no** significan "buena/mala noticia"; son **niveles de intensidad** dentro de cada polaridad. Una caída de conversiones es `leve/serio/terrorifico` (nunca "bueno"); una subida real de clics es `mejora_leve/alto/muy_alto`.

**Polaridad:** se normaliza el signo para que "adverso" sea siempre positivo internamente. En métricas donde **bajar es malo** (clicks, conversions, sessions, impressions, …) la caída es negativa y la subida es positiva. En `position` / `avg_position` es al revés (subir de posición = peor → negativo; bajar = mejor → positivo).

### Escala de **impacto negativo** (desviación adversa)

| Nivel | Condición (cualquiera que se cumpla) | Lectura operativa |
|-------|--------------------------------------|-------------------|
| **leve** | \|z\| ≥ 1,5 **o** \|Δ%\| ≥ 15 % | Desviación leve; vigilar |
| **serio** | \|z\| ≥ 2,0 **o** \|Δ%\| ≥ 25 % | Revisar hoy con checklist |
| **terrorifico** | \|z\| ≥ 3,5 **o** \|Δ%\| ≥ 50 % | Prioridad inmediata |

### Escala de **señal positiva** (desviación favorable)

| Nivel | Condición (cualquiera que se cumpla) | Lectura operativa |
|-------|--------------------------------------|-------------------|
| **mejora_leve** | \|z\| ≥ 1,5 **o** \|Δ%\| ≥ 15 % | Mejora leve; anotar causa |
| **alto** | \|z\| ≥ 2,0 **o** \|Δ%\| ≥ 25 % | Mejora clara; identificar palanca |
| **muy_alto** | \|z\| ≥ 3,5 **o** \|Δ%\| ≥ 50 % | Salto fuerte; validar que es real y capitalizar |

**Validaciones extra (suben un nivel dentro de su escala):** divergencia CTR (clics ↓ con impresiones ↑ y CTR desplomado) y tendencia descendente progresiva (≥3 días). Definidas en `finding_context.py`.

**Severidad máxima del cliente:** la **peor** de sus findings, con prioridad a la escala negativa (`terrorifico` > `serio` > `leve`; los positivos solo encabezan si no hay ningún negativo). Es la que se destaca en `summary.md` y en el bloque **## Alertas** del morning. En el HTML los findings se ordenan de peor a mejor.

**Validación CTR y tendencia (`finding_context.py`):** además de clasificar, el sistema enriquece cada finding con:

- **Narrativa legible** (`narrative`): día, valor vs referencia esperada, ventana consultada, **semana vs. semana anterior**, **trayectoria** de los últimos días y, en clics GSC, **impresiones del día y CTR**.
- **Subida de nivel** cuando se cumple un patrón de riesgo: **divergencia CTR** (clics ↓ con impresiones ↑ y CTR desplomado) o **caída progresiva** (≥3 días). Una caída del 24% con ese patrón pasa de `leve` a `serio`.

**Gráfico por finding (`chart_timeseries.py`):** SVG con:

- **Serie primaria** (azul, eje izquierdo) de la métrica del control.
- **Línea de referencia** discontinua en el valor esperado (baseline híbrida).
- **Segunda serie** (morado, eje derecho) cuando hay acompañante — en clics GSC, las **impresiones**: enseña a simple vista el patrón "clics ↓ / impresiones ↑".
- **Punto del día evaluado** coloreado por polaridad: **rojo** si es impacto negativo, **verde** si es señal positiva.
