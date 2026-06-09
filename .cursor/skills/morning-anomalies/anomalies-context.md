# Morning anomalies — Contexto compartido (sección 3)

> Fichero de referencia del skill `morning-anomalies`. Volver al índice: [SKILL.md](SKILL.md).
> Leer para interpretar (no detectar): bitácora, core updates, digest y festivos que acompañan a cada finding.

## 3. Cómo se recoge el contexto (interpretar, no detectar)

Todo esto va al bloque **“Contexto compartido”** del HTML (una vez por cliente).

### 3.1 Bitácora del cliente

- **Leer** `bitacora.md` en la raíz del cliente y, si existen, `projects/<id>/bitacora.md`.
- **Ventana:** líneas que contengan una fecha `YYYY-MM-DD` entre **±7 días** respecto a la fecha del informe.
- **Límite:** hasta **5** entradas (las más recientes primero).
- **Para qué sirve:** deploys, cambios de tracking, acuerdos con cliente, notas de “no hay festivo relevante”, etc.

### 3.2 Actualizaciones Google (Ranking)

- **Fuente:** `scripts/reporting/data/google_core_updates.csv` (mantenido con **llamar a** `sync-google-core-updates`).
- **Ventana en el informe:** desde **21 días antes** hasta **3 días después** de la fecha del informe.
- **Contenido:** filas `date, title` de incidentes/producto Ranking (core updates, spam updates, etc.).
- **Para qué sirve:** no atribuir a “nuestro bug” un movimiento que coincide con un rollout de Google.

### 3.3 Digest de noticias (opcional; depende del repo)

**Qué es:** fragmentos de un **digest editorial** opcional (resúmenes en Markdown por fecha), **no** datos del cliente. Aporta contexto de sector además de la bitácora y el CSV de Google.

**Por qué es opcional:**

- Solo entra en el informe si el **sistema del repo** expone un directorio de digests y el run pasa **`--news-digest-dir`**.
- Este proyecto puede usar `digest-fixture/` (ficción demo) con `--news-digest-dir digest-fixture`.
- Si no hay carpeta o no hay fichero para la fecha → `digest_skipped: true` y el informe sigue siendo válido con bitácora + core updates. No inventar digest.

**Comportamiento técnico:**

- **Entrada:** directorio con ficheros `YYYY-MM-DD.md` (**llamar a** `--news-digest-dir` en el run).
- Si el directorio no existe, está vacío o ningún párrafo coincide → `digest_skipped: true` en `run.meta.json` y nota en `summary.md`.
- **Heurística:** párrafos que mencionen (regex) *core update, GSC, Search Console, GA4, medición, ranking*, etc.; máximo **3** fragmentos de 500 caracteres.
- **Prioridad al interpretar:** bitácora del cliente y core updates **primero**; digest solo como matiz sectorial, nunca como prueba causal del cliente.

### 3.4 Festivos y estacionalidad (v1 manual)

El detector **no** resta festivos automáticamente. Antes de interpretar una caída:

- Comprobar calendario **nacional / autonómico / local** del mercado del cliente.
- Dejar constancia en **bitácora** o `festivos.md` bajo el cliente cuando la ventana esté “limpia”.
- Si hay festivo en la ventana, **mencionarlo en contexto** antes de escalar gravedad (criterio humano; integración automática = iteración posterior).
