# Morning anomalies — Responder preguntas en chat (sección 8)

> Fichero de referencia del skill `morning-anomalies`. Volver al índice: [SKILL.md](SKILL.md).
> Leer cuando el usuario pregunte por un informe ya generado: qué artefactos leer y cómo responder sin recalcular.

## 8. Preguntas en chat sobre lo detectado

Tras un run (o con informes ya generados), el usuario puede preguntar por un cliente, control o severidad. El agente responde **leyendo artefactos**, no re-ejecutando detección salvo que lo pidan explícitamente.

### 8.1 Fuentes que debes leer (en este orden)

1. **`output/anomalies/<fecha>/summary.md`** — qué clientes alertaron y severidad máxima.
2. **`output/anomalies/<fecha>/<client_id>.html`** — findings, gráfico, contexto compartido (bitácora, core updates, digest si aparece).
3. **`output/anomalies/<fecha>/<client_id>-suggested_actions.yaml`** — propuesta por control y severidad.
4. **`output/anomalies/<fecha>/run.meta.json`** — `digest_skipped`, modo synthetic/live, lista de `control_id` con finding.
5. **Contexto vivo del cliente** (si hace falta más detalle): `context/clients/<client_id>/bitacora.md` (o lab), `anomaly_controls.yaml` (qué grupo y métrica es cada control).

Si la fecha no está clara, usar la del último run citado por el usuario o la de `run.meta.json`.

### 8.2 Plantilla de respuesta (corta y precisa)

Usar el **formato de presentación de la sección 0 del `SKILL.md`** (titular → tabla con rango/trayectoria → lectura de consultor). Por finding, los datos vienen ya servidos en el campo `narrative` del YAML/HTML; no recalcular.

Mínimos por finding:

1. **Qué:** label del control + métrica + fecha (`D`).
2. **Cuánto:** valor `V`, **referencia esperada** `μ`, `Δ%`, `z`, **semana vs. anterior** y, en clics GSC, **impresiones + CTR**. Severidad con su escala (negativa `leve`/`serio`/`terrorifico` o positiva `mejora_leve`/`alto`/`muy_alto`).
3. **Contexto:** una viñeta de bitácora, un core update en ventana, digest **solo si** no está `digest_skipped`.
4. **Qué haría el sistema:** resumir la línea `suggested` del YAML (plantillas de `anomalies-reporting.md` §5.2; sin humo).

Si **no** hay finding para ese control: decirlo explícito (“el algoritmo no cruzó umbral ese día”) y no dramatizar.

### 8.3 Cómo relacionar con cada tipo de contexto

| Pregunta típica | Dónde mirar | Cómo responder |
|-----------------|-------------|----------------|
| “¿Por qué saltó GA4_CAT_01?” | Sección `finding-GA4_CAT_01` en HTML + YAML | Nombre del algoritmo (`anomalies-detection.md` §1.5), cifras z/Δ%, luego bitácora (deploy, tracking) |
| “¿Puede ser un core update?” | Bloque core updates en HTML + CSV | Citar `date` + `title` si cae en ventana −21/+3 días; si no hay filas, decir “ninguno en ventana” |
| “¿Qué pusimos nosotros?” | Bitácora ±7 días | Citar línea con fecha; si vacío, “sin entradas en ventana” |
| “¿Qué dice el sector?” | Solo si digest **no** skipped | Resumir 1 fragmento del HTML; si `digest_skipped: true`, decir que **este repo/run no incluye digest** (normal en starter) |
| “¿Es grave?” | Severidad del finding + máxima en `summary.md` | Mapa de gravedad (`anomalies-detection.md` §4) + acciones (`anomalies-reporting.md` §5): cuándo actuar (seguimiento / hoy / urgente) |
| “¿Qué grupo es el topic de alquiler?” | `anomaly_controls.yaml` del cliente | Listar filtros del `query_collections` / `page_collections`; no inventar queries |

### 8.4 Reglas del agente al responder

- **No** recalcular z a mano salvo para explicar; las cifras oficiales son las del informe.
- **No** mezclar clientes: un `client_id` por hilo de respuesta salvo comparación explícita.
- Si el contexto (bitácora, festivo anotado, core update) **explica** la señal, decirlo y bajar tono de urgencia aunque la severidad siga siendo alta (la etiqueta no cambia retroactivamente).
- Si falta el informe, proponer **una** acción: ejecutar el run del Anexo A (`SKILL.md`) con la fecha y ruta correctas.
- Tono: castellano directo, técnico cuando haga falta; nombre del algoritmo: **“z-score con baseline híbrida (28 días + mismo día de la semana)”**.
