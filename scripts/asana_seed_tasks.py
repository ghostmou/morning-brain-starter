"""
Crear en Asana tareas de demo por cliente, basadas en las bitácoras.
Añade tareas (algunas completadas, otras pendientes) a los proyectos Acme, MCR,
Mao-Kwikowski, Rocinante y Tycho. Si no existen, intenta crearlos (puede fallar
en workspaces tipo organización; en ese caso créalos a mano en Asana).

Uso: desde la raíz del proyecto, .venv/bin/python scripts/asana_seed_tasks.py
"""

import json
import os
import urllib.error
import urllib.request
from datetime import datetime, timedelta
from typing import Optional
from pathlib import Path

_project_root = Path(__file__).resolve().parent.parent
if str(_project_root) not in os.sys.path:
    os.sys.path.insert(0, str(_project_root))

from scripts.credentials import load_env

load_env()

# Proyectos por cliente (nombre exacto en Asana)
CLIENT_PROJECT_NAMES = ["Acme", "MCR", "Mao-Kwikowski", "Rocinante", "Tycho"]

# Tareas por cliente: lista de {"name": str, "due_on": "YYYY-MM-DD"|None, "completed": bool}
# Fechas en rango 2025-2026 (completadas en el pasado reciente, pendientes por venir).
# Basadas en context/clients/<client>/bitacora.md
TASKS_BY_CLIENT = {
    "Acme": [
        {"name": "Renovación contrato marco suministros – firmado 12/11", "due_on": "2025-11-12", "completed": True,
         "notes": "Contrato marco 2 años con compras; condiciones comerciales actualizadas. Firmado por ambas partes el 12/11. Archivo en legal."},
        {"name": "Enviar muestras y fichas técnicas aleaciones a Tycho", "due_on": "2025-11-25", "completed": True,
         "notes": "Tras presentación del catálogo de aleaciones y sellantes (11/11). Tycho y otros del cinturón interesados. Enviado en plazo."},
        {"name": "Cierre incidencia retraso envío Luna (envío parcial)", "due_on": "2025-12-03", "completed": True,
         "notes": "Retraso 2 semanas Luna→Tycho por congestión en puerto orbital. Envío parcial urgente aceptado; resto llegó 03/12. Incidencia cerrada."},
        {"name": "Certificados formación protocolos exportación", "due_on": "2025-12-05", "completed": True,
         "notes": "Formación interna sobre nuevos protocolos Tierra–espacio (normativa actualizada). Asistencia completa; certificados registrados."},
        {"name": "Seguimiento oferta Tycho – recordar en enero", "due_on": "2026-01-10", "completed": True,
         "notes": "Primera reunión formal contrato a largo plazo (26/11); ellos comparan con otros proveedores. Recordatorio enviado en enero."},
        {"name": "Confirmación por escrito extensión oferta Tycho hasta 31/01", "due_on": "2026-01-15", "completed": True,
         "notes": "Llamada 14/01: piden extensión de validez de la oferta. Concedida hasta 31/01. Confirmación por escrito enviada."},
        {"name": "Revisión incidencias Q4 – plan de mejora", "due_on": "2026-01-28", "completed": True,
         "notes": "Una crítica (retraso Luna–Tycho), dos menores. Plan de mejora: reserva de capacidad con partner Luna. Revisar en Q2."},
        {"name": "Cerrar negociación Tycho – confirmación antes 10/02", "due_on": "2026-02-10", "completed": False,
         "notes": "Tycho debe confirmar aprobación interna antes del 10/02. Si dan el sí, preparar borrador de contrato marco (volumen y precios ya acordados en principio). Contacto: equipo compras Tycho."},
        {"name": "Firma contrato partner logístico Luna", "due_on": "2026-02-15", "completed": False,
         "notes": "Contrato con nuevo partner logístico en Luna para prueba piloto Q1 (dos envíos). Condiciones ya acordadas; legal está cerrando el texto. Coordinar firma con su representante."},
        {"name": "Redacción contrato Tycho si confirman oferta", "due_on": "2026-02-20", "completed": False,
         "notes": "Solo iniciar cuando Tycho confirme. Usar plantilla contrato marco suministros; ajustar anexos con volúmenes y plazos de la oferta extendida. Revisión legal antes de enviar."},
    ],
    "MCR": [
        {"name": "Firma marco MCRN – borrador nuestra parte enviado", "due_on": "2025-11-08", "completed": True,
         "notes": "Renovación marco colaboración soporte técnico y suministros (3 años, revisión anual). Borrador firmado por nuestra parte; pendiente firma MCRN."},
        {"name": "Entregar certificados formación seguridad (antes 30/11)", "due_on": "2025-11-28", "completed": True,
         "notes": "Sesión 14/11 con equipo seguridad MCRN: protocolos de acceso y clasificación. Formación obligatoria; certificados entregados en plazo."},
        {"name": "Enviar matriz requisitos traza Nave 7", "due_on": "2025-12-02", "completed": True,
         "notes": "Kick-off técnico Nave 7 con Tycho (21/11). Especificaciones MCRN navegación y armamento. Matriz enviada según acuerdo."},
        {"name": "Informe lecciones aprendidas ejercicio conjunto", "due_on": "2025-12-12", "completed": True,
         "notes": "Ejercicio coordinación MCRN–Tycho (28/11). Comunicaciones, tiempos de respuesta, cadenas de mando. Informe entregado."},
        {"name": "Revisión presupuesto Q1 – stock seguridad ampliado", "due_on": "2025-12-10", "completed": True,
         "notes": "Reunión compras 05/12: volumen Q1, previsión envíos desde Marte. Dos partidas con posible retraso; mitigación con stock ampliado."},
        {"name": "Documentación interoperabilidad naves civiles (Roci)", "due_on": "2026-01-10", "completed": True,
         "notes": "Consulta formal uso de interfaces estándar con naves civiles. Documentación y condiciones de uso enviadas; en revisión por su legal."},
        {"name": "Alinear plan comunicación con Tycho (post reunión 15/01)", "due_on": "2026-01-22", "completed": True,
         "notes": "Revisión estratégica 2026 (15/01): prioridades Nave 7, interoperabilidad, formación cruzada. Plan de comunicación alineado."},
        {"name": "Seguimiento envío componentes Nave 7 (1ª semana feb)", "due_on": "2026-02-07", "completed": True,
         "notes": "Coordinación logística 22/01: envío componentes Marte→Tycho. Ventana de lanzamiento y cadena de custodia; envío programado 1ª semana feb."},
        {"name": "Cerrar no conformidades auditoría Nave 7 (antes 15/02)", "due_on": "2026-02-15", "completed": False,
         "notes": "Auditoría de calidad 29/01 detectó 2 no conformidades menores en documentación y procesos. Plan de cierre enviado; seguir con las acciones y evidencias. Coordinar con responsable calidad MCRN."},
        {"name": "Seguimiento briefing operación conjunta cinturón", "due_on": "2026-02-25", "completed": False,
         "notes": "Briefing preliminar del 04/02 (clasificado). Solo alcance alto nivel; sin compromiso formal. Mantener contacto con enlace MCRN para próximos pasos. No incluir en comunicaciones externas."},
    ],
    "Mao-Kwikowski": [
        {"name": "Actualizar plan Proyecto Proteus – validación fin de año", "due_on": "2025-11-20", "completed": True,
         "notes": "Sesión técnica 14/11: retraso 2 semanas en pruebas por restricciones de laboratorio. Nuevo hito validación antes fin de año; plan actualizado."},
        {"name": "Formación confidencialidad 12 personas (certificados 15/12)", "due_on": "2025-12-15", "completed": True,
         "notes": "Reunión compliance 21/11: protocolos de confidencialidad y control de accesos. 12 personas; certificados en carpeta compartida."},
        {"name": "Cierre acciones post-incidente seguridad diciembre", "due_on": "2026-01-25", "completed": True,
         "notes": "Incidencia seguridad 11/12 contenida; sin fuga de datos clasificados. Revisión de accesos y parches. Todas las acciones cerradas."},
        {"name": "Coordinación con MCR – especificaciones técnicas", "due_on": "2026-01-23", "completed": True,
         "notes": "Reunión confidencial con enlace MCR: componentes especializados. Solo especificaciones técnicas y plazos; sin compromiso comercial."},
        {"name": "Comunicar decisión go Proteus a dirección", "due_on": "2026-02-10", "completed": False,
         "notes": "Reunión go/no-go 06/02: decisión go con condiciones (seguimiento quincenal, revisión en marzo). Redactar resumen ejecutivo para dirección y actualizar plan del proyecto con hitos acordados."},
        {"name": "Seguimiento quincenal Proteus – revisión en marzo", "due_on": "2026-03-15", "completed": False,
         "notes": "Condición del go: revisión quincenal de avance y riesgos. Próxima revisión formal con dirección en marzo. Preparar métricas y estado de los tres criterios de validación."},
        {"name": "Auditoría externa seguridad (20/02)", "due_on": "2026-02-20", "completed": False,
         "notes": "Auditoría externa post-incidente de diciembre, confirmada para 20/02. Tener listos informes de cierre de acciones, parches y revisión de accesos. Contacto: equipo compliance."},
        {"name": "Evaluación proveedor alternativo suministros", "due_on": "2026-02-28", "completed": False,
         "notes": "Proveedor actual con retrasos recurrentes; opción en Luna en evaluación desde Q4. Cerrar informe de comparativa (precio, plazos, calidad) y recomendación antes de fin de febrero."},
    ],
    "Rocinante": [
        {"name": "Enviar checklist pre-mantenimiento Roci", "due_on": "2025-11-15", "completed": True,
         "notes": "Kick-off con Holden y equipo (12/11): revisión trimestral propulsión y soporte vital, ventana 24/7. Checklist enviado según acuerdo."},
        {"name": "Cierre reparación reactor secundario (dique Tycho)", "due_on": "2025-11-22", "completed": True,
         "notes": "Incidencia 18/11: fluctuaciones reactor en ruta Ceres–Tycho. Desvío a Tycho; reparación completada 22/11. Roci operativa."},
        {"name": "Informe técnico y certificación post-mantenimiento Tycho", "due_on": "2025-12-05", "completed": True,
         "notes": "Sesión en Tycho 25/11 (Fred Johnson presente). Mejoras aplicadas, certificación de nave. Informe firmado y garantías actualizadas."},
        {"name": "Oferta formal ampliación SLA (EVA + armamento) antes fin de año", "due_on": "2025-12-20", "completed": True,
         "notes": "Revisión costes y SLA 09/12: todo en margen. Solicitud ampliación EVA y armamento. Oferta formal enviada antes de fin de año."},
        {"name": "Formación protocolos emergencia tripulación – material a bordo", "due_on": "2025-12-16", "completed": True,
         "notes": "Sesión con Amos y equipo: simulacros contención y botiquín de emergencia. Material dejado a bordo. Feedback muy positivo; refresco en 6 meses."},
        {"name": "Mantenimiento programado Tycho – certificado navegabilidad", "due_on": "2026-01-15", "completed": True,
         "notes": "Reunión in situ 13/01. Roci en dique; revisión drive y sistemas. Sin hallazgos críticos. Certificado de navegabilidad renovado."},
        {"name": "Enviar documentación interoperabilidad sistemas MCR", "due_on": "2026-01-28", "completed": True,
         "notes": "Consulta 27/01: compatibilidad con equipos MCR en operación conjunta. Documentación de interfaces estándar enviada; pendiente su respuesta."},
        {"name": "Recordar oferta ampliada SLA a Rocinante (17/02)", "due_on": "2026-02-17", "completed": False,
         "notes": "Oferta EVA + armamento presentada 03/02; dieron dos semanas para validar con Holden y cerrar presupuesto. Llamar o escribir el 17/02 para recordar y cerrar si ya tienen decisión."},
        {"name": "Seguimiento respuesta compatibilidad MCRN", "due_on": "2026-02-24", "completed": False,
         "notes": "Documentación de interfaces estándar enviada 27/01 (interoperabilidad con sistemas MCR en operación conjunta). Pendiente de respuesta de su parte. Recordar si no contestan esta semana."},
    ],
    "Tycho": [
        {"name": "Actualizar Gantt y comunicar retraso a subcontratas", "due_on": "2025-11-15", "completed": True,
         "notes": "Reunión estratégica OPA 08/11: retraso 2 semanas envío desde Luna; impacto asumido. Gantt actualizado y subcontratas informadas."},
        {"name": "Enviar manual y fecha curso formación aduanas muelle 12", "due_on": "2025-11-25", "completed": True,
         "notes": "Coordinación 15/11 con jefes de muelle: nuevos protocolos inspección cargamentos desde Tierra. Manual y fecha del curso enviados."},
        {"name": "Coordinación llegada Roci – dique 3 (salida 24/11)", "due_on": "2025-11-22", "completed": True,
         "notes": "Roci para mantenimiento post-incidencia. Dique 3 y turno de ingeniería asignados. Todo según lo previsto; salida 24/11 sin incidencias."},
        {"name": "Acta kick-off Nave 7 y plan de comunicación", "due_on": "2025-12-05", "completed": True,
         "notes": "Kick-off formal 29/11 con equipos Tycho y enlace MCR. Alcance, hitos y confidencialidad. Acta y plan de comunicación entregados."},
        {"name": "Confirmar llegada materiales críticos antes 20/12", "due_on": "2025-12-20", "completed": True,
         "notes": "Revisión suministros 06/12: dos partidas en umbral mínimo; pedidos de emergencia cursados. Llegada confirmada antes del 20."},
        {"name": "Revisión inspecciones preventivas sector 7 (Q1)", "due_on": "2026-01-15", "completed": True,
         "notes": "Incidente menor 13/12: fuga contenida en sector 7. Revisión de inspecciones preventivas adelantada a Q1. Hecho."},
        {"name": "Revisión Q1 – calendario Nave 7 integración motores", "due_on": "2026-01-17", "completed": True,
         "notes": "Revisión 10/01: Nave 7 en fase de estructura; hito integración motores en febrero. Posible deslizamiento 1 semana; mitigación en curso."},
        {"name": "Formación OPA – nueva tanda seguridad y muelle", "due_on": "2026-01-20", "completed": True,
         "notes": "Nueva tanda formación personal OPA (seguridad y protocolos de muelle). Asistencia correcta; feedback para más simulacros prácticos."},
        {"name": "Inspección diques 1–4 – presupuesto reservado", "due_on": "2026-01-31", "completed": True,
         "notes": "Inspección programada mantenimiento. Diques 1 y 2 en buen estado; 3 y 4 requieren trabajos menores en Q2. Presupuesto reservado."},
        {"name": "Decisión suministros Acme (antes 31/01)", "due_on": "2026-01-31", "completed": False,
         "notes": "Reunión 24/01 con Acme; oferta recibida para contrato a largo plazo. Comparativa con otros proveedores en curso. Recordar fecha límite 31/01 y pedir prórroga corta si la necesitan."},
        {"name": "Enviar recordatorio escala Roci (marzo) a Rocinante Corp", "due_on": "2026-02-12", "completed": False,
         "notes": "Ventana de escala Roci en marzo ya confirmada; dique y servicios asignados. Enviar recordatorio a Rocinante Corp con fecha exacta y checklist de lo que necesitan para la parada."},
        {"name": "Trabajos menores diques 3 y 4 en Q2", "due_on": "2026-04-15", "completed": False,
         "notes": "Inspección 31/01: diques 1 y 2 OK; 3 y 4 requieren trabajos menores. Presupuesto reservado. Planificar ventanas de mantenimiento en Q2 sin afectar tráfico programado (coordinar con operaciones)."},
    ],
}

# Tareas extra para hoy (demo The Expanse): (nombre_proyecto, {name, notes}).
# due_on se fija en main() a la fecha del día en que se ejecuta el script.
EXTRA_TASKS_TODAY = [
    ("Rocinante", {"name": "Revisar checklist de mantenimiento PDCs antes de salida", "notes": "Verificar que todos los Point Defense Cannons pasen el test de calibración. Amos suele hacer la revisión final; confirmar con él que no hay anomalías en el último informe."}),
    ("Rocinante", {"name": "Confirmar ventana de lanzamiento con torre Tycho", "notes": "Coordinar con control de tráfico de Tycho la ventana asignada a la Roci. Evitar solapamiento con llegada de convoy desde Ceres."}),
    ("Rocinante", {"name": "Actualizar certificación de soporte vital tras inspección", "notes": "La inspección en dique ha detectado un sensor de CO2 en el límite. Sustituir y volver a certificar antes de próximo despliegue."}),
    ("Rocinante", {"name": "Coordinar entrega de repuestos EVA con almacén Tycho", "notes": "Pedido de piezas para trajes EVA (sellos y baterías) pendiente. Confirmar llegada y que estén en el muelle antes de salida."}),
    ("Rocinante", {"name": "Verificar calibración de sensores de navegación", "notes": "Alex dejó anotado un desvío menor en el array de navegación. Ejecutar secuencia de calibración estándar y documentar resultado."}),
    ("Rocinante", {"name": "Enviar informe de estado del reactor a Fred Johnson", "notes": "Resumen post-mantenimiento: reactor principal y secundario OK. Incluir certificado de Tycho y próxima ventana de revisión."}),
    ("Rocinante", {"name": "Programar simulacro de contención con tripulación", "notes": "Simulacro de brecha o despresurización. Fijar fecha con Holden y Naomi; preparar checklist y roles según protocolo OPA."}),
    ("Tycho", {"name": "Confirmar reserva de dique 3 para Roci (ventana marzo)", "notes": "Rocinante tiene ventana de escala en marzo. Verificar que dique 3 sigue asignado y enviar recordatorio a Rocinante Corp con checklist de servicios."}),
    ("Tycho", {"name": "Revisar protocolos de inspección sector 7", "notes": "Tras el incidente de fuga en sector 7, las inspecciones preventivas se adelantaron. Revisar que los protocolos actualizados estén en el manual."}),
    ("Tycho", {"name": "Enviar acta de reunión Nave 7 a enlace MCR", "notes": "Acta del último kick-off de integración motores. Incluir hitos y responsabilidades; clasificación según acuerdo con MCRN."}),
    ("Tycho", {"name": "Verificar llegada de materiales críticos para integración", "notes": "Dos partidas de componentes para Nave 7 en tránsito desde Marte. Comprobar ETA y que almacén tenga espacio y cadena de custodia lista."}),
    ("Tycho", {"name": "Coordinar nueva tanda de formación OPA seguridad y muelle", "notes": "Siguiente grupo de personal OPA para formación en protocolos de seguridad y muelle. Fijar fechas y aula; incluir simulacros prácticos."}),
    ("Tycho", {"name": "Actualizar Gantt de integración motores Nave 7", "notes": "Posible deslizamiento de una semana en el hito de integración. Actualizar Gantt y comunicar a MCR si se confirma el retraso."}),
    ("Tycho", {"name": "Preparar briefing preliminar operación conjunta cinturón", "notes": "Material para el briefing de alto nivel (clasificado). Solo alcance y objetivos; sin compromisos formales. Coordinar con enlace MCRN."}),
    ("MCR", {"name": "Cerrar no conformidades de auditoría Nave 7 (documentación)", "notes": "Auditoría de calidad detectó 2 no conformidades menores en documentación. Completar las acciones del plan de cierre y adjuntar evidencias."}),
    ("MCR", {"name": "Enviar matriz de requisitos actualizada a Tycho", "notes": "Matriz de requisitos técnicos Nave 7 tras última revisión de navegación y armamento. Asegurar que Tycho tiene la versión vigente."}),
    ("MCR", {"name": "Verificar cadena de custodia del envío de componentes", "notes": "Envío Marte–Tycho programado. Confirmar que cada eslabón de la cadena de custodia está documentado y que no hay huecos."}),
    ("MCR", {"name": "Documentar lecciones aprendidas del ejercicio conjunto", "notes": "Ejercicio de coordinación MCRN–Tycho: comunicaciones, tiempos de respuesta, cadenas de mando. Redactar sección de lecciones aprendidas para el informe."}),
    ("MCR", {"name": "Coordinar fecha del briefing clasificado con enlace MCRN", "notes": "Briefing preliminar operación cinturón. Acordar fecha y asistencia; recordar que el contenido es solo alcance alto nivel, sin compromiso formal."}),
    ("MCR", {"name": "Validar especificaciones de interoperabilidad con Roci", "notes": "Consulta sobre interfaces estándar con naves civiles (Rocinante). Revisar que las especificaciones enviadas cubren el caso de uso de operación conjunta."}),
    ("MCR", {"name": "Preparar informe de estado para comando MCRN", "notes": "Resumen ejecutivo: Nave 7, envío de componentes, auditoría y no conformidades. Formato y periodicidad según procedimiento interno."}),
    ("Mao-Kwikowski", {"name": "Comunicar decisión go Proteus a dirección", "notes": "Redactar resumen ejecutivo del go/no-go: decisión go con condiciones, seguimiento quincenal y revisión en marzo. Enviar a dirección."}),
    ("Mao-Kwikowski", {"name": "Preparar documentación para auditoría de seguridad 20/02", "notes": "Auditoría externa post-incidente diciembre. Tener listos informes de cierre de acciones, parches aplicados y revisión de accesos."}),
    ("Mao-Kwikowski", {"name": "Actualizar plan Proteus con hitos y revisión en marzo", "notes": "Incorporar al plan del proyecto los hitos acordados en el go y la fecha de revisión formal con dirección en marzo. Actualizar Gantt."}),
    ("Mao-Kwikowski", {"name": "Coordinar con compliance pre-auditoría 20/02", "notes": "Reunión interna con equipo de compliance para repasar alcance de la auditoría externa y asegurar que toda la documentación está accesible."}),
    ("Mao-Kwikowski", {"name": "Evaluar propuesta de proveedor alternativo (Luna)", "notes": "Proveedor actual con retrasos recurrentes. Cerrar informe de comparativa (precio, plazos, calidad) con la opción en Luna y recomendación."}),
    ("Mao-Kwikowski", {"name": "Enviar resumen ejecutivo go/no-go Proteus a dirección", "notes": "Resumen breve con decisión, condiciones (seguimiento quincenal, revisión marzo) y próximos pasos. Incluir referencia a los tres criterios de validación."}),
    ("Acme", {"name": "Cerrar negociación Tycho – confirmación antes del 10/02", "notes": "Tycho debe confirmar aprobación interna. Si confirman, preparar borrador de contrato marco con volúmenes y precios ya acordados. Contacto: equipo compras Tycho."}),
    ("Acme", {"name": "Preparar borrador de contrato con partner logístico Luna", "notes": "Contrato para prueba piloto Q1 (dos envíos). Legal está cerrando el texto; coordinar con el representante del partner la fecha de firma."}),
    ("Acme", {"name": "Redactar anexos del contrato Tycho (volúmenes y plazos)", "notes": "Cuando Tycho confirme la oferta, usar plantilla de contrato marco y ajustar anexos con los volúmenes y plazos de la oferta extendida. Revisión legal antes de enviar."}),
    ("Acme", {"name": "Enviar recordatorio a compras Tycho sobre fecha límite", "notes": "Recordar cortésmente la fecha límite de confirmación (10/02) y ofrecer una prórroga muy corta si la necesitan para aprobación interna."}),
    ("Acme", {"name": "Verificar condiciones comerciales de la oferta extendida", "notes": "Revisar que las condiciones de la oferta extendida hasta 31/01 siguen vigentes y no hay cambios en precios ni plazos antes de cerrar con Tycho."}),
    ("Acme", {"name": "Coordinar firma de contrato con representante Luna", "notes": "Una vez legal cierre el texto del contrato con el partner logístico en Luna, acordar fecha y lugar de firma (presencial o remoto según procedimiento)."}),
    ("Acme", {"name": "Actualizar plantilla de contrato marco para Tycho", "notes": "Asegurar que la plantilla de contrato marco de suministros incluye las cláusulas acordadas en las últimas negociaciones con Tycho (normativa Tierra–espacio)."}),
]


def _api(method: str, url: str, token: str, data: dict = None) -> dict:
    headers = {"Authorization": "Bearer " + token, "Content-Type": "application/json"}
    body = json.dumps(data).encode("utf-8") if data else None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        err_body = e.read().decode() if e.fp else ""
        try:
            err_json = json.loads(err_body)
            msg = err_json.get("errors", [{}])[0].get("message", err_body)
        except Exception:
            msg = err_body
        raise RuntimeError(f"Asana API {e.code}: {msg}") from e


def get_workspace_gid(token: str, for_seed: bool = False) -> str:
    if for_seed:
        gid = os.getenv("ASANA_SEED_WORKSPACE_GID", "").strip()
        if gid:
            return gid
    workspace_gid = os.getenv("ASANA_WORKSPACE_GID", "").strip()
    if workspace_gid:
        return workspace_gid
    data = _api("GET", "https://app.asana.com/api/1.0/workspaces", token)
    workspaces = data.get("data", [])
    if not workspaces:
        raise SystemExit("No hay workspaces en la cuenta.")
    return workspaces[0]["gid"]


def _find_project_for_client(client_name: str, projects: list) -> Optional[str]:
    """Devuelve el GID del proyecto que corresponde a este cliente (nombre exacto o variante)."""
    by_name = {p["name"]: p["gid"] for p in projects}
    if client_name in by_name:
        return by_name[client_name]
    client_lower = client_name.lower()
    for p in projects:
        name = p["name"]
        if name.lower() == client_lower:
            return p["gid"]
        if name.lower().startswith(client_lower) or client_lower in name.lower():
            return p["gid"]
    # Variantes conocidas: MCR -> MCR-COM, Rocinante -> Rocinante-Corp, etc.
    for p in projects:
        n = p["name"].upper().replace("-", " ").replace("_", " ")
        c = client_name.upper().replace("-", " ").replace("_", " ")
        if c in n or n.startswith(c):
            return p["gid"]
    return None


def list_teams(token: str, workspace_gid: str) -> list:
    url = "https://app.asana.com/api/1.0/workspaces/" + workspace_gid + "/teams"
    data = _api("GET", url, token)
    return data.get("data", [])


def list_projects(token: str, workspace_gid: str) -> list:
    url = (
        "https://app.asana.com/api/1.0/workspaces/" + workspace_gid + "/projects?"
        "opt_fields=name,gid&archived=false"
    )
    data = _api("GET", url, token)
    return data.get("data", [])


def create_project(token: str, workspace_gid: str, name: str, team_gid: str = None) -> dict:
    """Crea un proyecto en el workspace. Si el workspace es organización, team_gid es obligatorio."""
    url = "https://app.asana.com/api/1.0/workspaces/" + workspace_gid + "/projects"
    payload = {"name": name}
    if team_gid:
        payload["team"] = team_gid
    body = {"data": payload}
    data = _api("POST", url, token, body)
    return data["data"]


def get_current_user_gid(token: str) -> str:
    data = _api("GET", "https://app.asana.com/api/1.0/users/me", token)
    return data["data"]["gid"]


def get_tasks_for_project(token: str, project_gid: str) -> list:
    url = (
        "https://app.asana.com/api/1.0/projects/" + project_gid + "/tasks?"
        "opt_fields=name,gid,due_on,completed,assignee"
    )
    data = _api("GET", url, token)
    return data.get("data", [])


def update_task(
    token: str,
    task_gid: str,
    due_on: str = None,
    completed: bool = None,
    assignee_gid: str = None,
    notes: str = None,
) -> dict:
    payload = {"data": {}}
    if due_on is not None:
        payload["data"]["due_on"] = due_on
    if completed is not None:
        payload["data"]["completed"] = completed
    if assignee_gid is not None:
        payload["data"]["assignee"] = assignee_gid
    if notes is not None:
        payload["data"]["notes"] = notes
    if not payload["data"]:
        return {}
    data = _api("PUT", "https://app.asana.com/api/1.0/tasks/" + task_gid, token, payload)
    return data["data"]


def create_task(
    token: str,
    workspace_gid: str,
    project_gid: str,
    name: str,
    due_on: str = None,
    completed: bool = False,
    assignee_gid: str = None,
    notes: str = None,
) -> dict:
    payload = {
        "data": {
            "name": name,
            "workspace": workspace_gid,
            "projects": [project_gid],
            "completed": completed,
        }
    }
    if due_on:
        payload["data"]["due_on"] = due_on
    if assignee_gid:
        payload["data"]["assignee"] = assignee_gid
    if notes:
        payload["data"]["notes"] = notes
    data = _api("POST", "https://app.asana.com/api/1.0/tasks", token, payload)
    return data["data"]


def main():
    token = os.getenv("ASANA_ACCESS_TOKEN", "").strip()
    if not token:
        print("ASANA_ACCESS_TOKEN no configurado. Configura Asana en resources/secrets/.env")
        return

    user_gid = get_current_user_gid(token)
    workspace_gid = get_workspace_gid(token, for_seed=True)
    projects = list_projects(token, workspace_gid)
    name_to_gid = {p["name"]: p["gid"] for p in projects}

    client_to_gid = {}
    for client_name in CLIENT_PROJECT_NAMES:
        gid = _find_project_for_client(client_name, projects)
        if gid:
            client_to_gid[client_name] = gid

    if not client_to_gid:
        print("No se encontró ningún proyecto que coincida con:", ", ".join(CLIENT_PROJECT_NAMES))
        print("Proyectos en el workspace:", ", ".join(sorted(name_to_gid.keys())[:20]) + ("..." if len(name_to_gid) > 20 else ""))
        print("Tip: usa ASANA_SEED_WORKSPACE_GID en .env para otro workspace (ej. Demo).")
        return

    if len(client_to_gid) < len(CLIENT_PROJECT_NAMES):
        missing = [c for c in CLIENT_PROJECT_NAMES if c not in client_to_gid]
        print("Proyectos encontrados para:", ", ".join(client_to_gid.keys()))
        print("Sin proyecto para:", ", ".join(missing))
        print()

    teams = list_teams(token, workspace_gid)
    team_gid = os.getenv("ASANA_TEAM_GID", "").strip() or (teams[0]["gid"] if teams else None)

    for client_name in CLIENT_PROJECT_NAMES:
        if client_name not in client_to_gid:
            try:
                print("Creando proyecto:", client_name, "...", end=" ")
                proj = create_project(token, workspace_gid, client_name, team_gid=team_gid)
                client_to_gid[client_name] = proj["gid"]
                print("OK")
            except RuntimeError as e:
                print("falló.")
                print("  ", str(e))
                if not team_gid and teams:
                    print("  Prueba definiendo ASANA_TEAM_GID con el GID de un team donde seas miembro (ej. en la URL del team en Asana).")
                print("  O crea el proyecto «" + client_name + "» manualmente en Asana y vuelve a ejecutar.")
                continue
        project_gid = client_to_gid[client_name]
        project_label = next((p["name"] for p in projects if p["gid"] == project_gid), client_name)
        print("Proyecto:", client_name, "→", project_label)

        tasks = TASKS_BY_CLIENT.get(client_name, [])
        if not tasks:
            continue
        existing_tasks = {task["name"]: task for task in get_tasks_for_project(token, project_gid)}
        for t in tasks:
            name = t["name"]
            due_on = t.get("due_on")
            completed = t.get("completed", False)
            estado = "✓ completada" if completed else "pendiente"
            notes = t.get("notes")
            if name in existing_tasks:
                update_task(
                    token,
                    existing_tasks[name]["gid"],
                    due_on=due_on,
                    completed=completed,
                    assignee_gid=user_gid,
                    notes=notes,
                )
                print("  [actualizada]", estado, "|", name[:60] + ("..." if len(name) > 60 else ""))
            else:
                create_task(
                    token,
                    workspace_gid,
                    project_gid,
                    name=name,
                    due_on=due_on,
                    completed=completed,
                    assignee_gid=user_gid,
                    notes=notes,
                )
                print("  [nueva]", estado, "|", name[:60] + ("..." if len(name) > 60 else ""))

    # Tareas extra para hoy (demo The Expanse)
    today_str = datetime.utcnow().strftime("%Y-%m-%d")
    print("\n--- Tareas extra para hoy (" + today_str + ") ---")
    created_extra = 0
    for project_name, t in EXTRA_TASKS_TODAY:
        if project_name not in client_to_gid:
            continue
        project_gid = client_to_gid[project_name]
        name = t["name"]
        notes = t.get("notes")
        existing_tasks = {task["name"]: task for task in get_tasks_for_project(token, project_gid)}
        if name in existing_tasks:
            update_task(
                token,
                existing_tasks[name]["gid"],
                due_on=today_str,
                completed=False,
                assignee_gid=user_gid,
                notes=notes,
            )
            print("  [actualizada] pendiente |", name[:60] + ("..." if len(name) > 60 else ""))
        else:
            create_task(
                token,
                workspace_gid,
                project_gid,
                name=name,
                due_on=today_str,
                completed=False,
                assignee_gid=user_gid,
                notes=notes,
            )
            print("  [nueva] pendiente |", name[:60] + ("..." if len(name) > 60 else ""))
            created_extra += 1
    print("\nListo. Tareas de demo actualizadas o creadas. Tareas extra para hoy:", len(EXTRA_TASKS_TODAY), "(" + str(created_extra) + " nuevas).")


if __name__ == "__main__":
    main()
