# Morning anomalies — Fuentes de datos (sección 2)

> Fichero de referencia del skill `morning-anomalies`. Volver al índice: [SKILL.md](SKILL.md).
> Leer cuando haya que explicar **de dónde sale el dato** (sintético vs live) o cómo se resuelven GA4/GSC.

## 2. De dónde salen los datos (APIs y modo sintético)

### 2.1 Modo sintético (`--synthetic` o `--lab-root`)

No llama a APIs. Lee CSV bajo `demo-data/<client_id>/`:

| Fichero | Columnas típicas |
|---------|------------------|
| `ga4_daily.csv` | `date`, `page_path`, `sessions`, `conversions`, … |
| `gsc_page_daily.csv` | `date`, `page`, `clicks`, `impressions`, `position` |
| `gsc_query_daily.csv` | `date`, `query`, `clicks`, `impressions`, `position` |

Útil para desarrollo, tests y lab interno.

### 2.2 Modo live (`--no-synthetic`, producción)

Implementado en `scripts/anomaly_detection/fetch.py` (`load_live_bundle`). Lee `client.yaml` del cliente y descarga la ventana de 90 días hasta `D`.

**Google Analytics 4 (Data API)** — por `ga4_property_id` del `client.yaml`:

- **Informe:** `RunReport` con rango `[inicio_90d, fecha_informe]`.
- **Dimensiones:** `date`, `pagePath`. **Métricas:** `sessions`, `conversions`.
- **Paginación:** lotes hasta agotar filas. **Normalización:** `page_path` vía `scripts/common/page_path_normalize.py` para alinear con GSC.

**Google Search Console (Search Analytics API)** — por `gsc_site_url` del `client.yaml` (si falta, se infiere `sc-domain:` desde `email_domains`):

- **Sitio:** se resuelve contra `sites.list` para usar la propiedad verificada (URL-prefix o dominio). **Ojo:** si el token no tiene permiso sobre `sc-domain:`, fijar `gsc_site_url` con la URL-prefix correcta (p. ej. `https://www.cliente.com/`).
- **Totales de sitio:** dimensión **`date`** sola (`fetch_daily_traffic`) → clics/impresiones reales del sitio. **Crítico:** sumar filas `date+query` **infravalora** los clics (la API solo da las top queries por día, ~10-15% del total). Por eso los controles **sin grupo** usan el total por `date`.
- **Por página / por query (topics):** dimensiones `date`+`page` y `date`+`query` (`scripts/gsc_fetch.py`); el filtro del grupo monitorizado se aplica tras descargar, con las reglas del YAML.

**Comportamiento por control:**

- Control **con `collection_id`** → filtra el grupo y agrega (vista de topic/landings).
- Control **sin grupo** y fuente GSC → usa el **total de sitio** por `date` (cifras correctas a nivel dominio).

**Autenticación:** OAuth del flavour (`resources/secrets/`); comprobar con **llamar a** `test-auth` (Anexo A del `SKILL.md`).
