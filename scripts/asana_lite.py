"""
Listar tareas de hoy (Asana). Opcional: solo se usa si ASANA_ACCESS_TOKEN está definido.
Ordenación por día de la semana según config/asana_order.yaml (addon: context/addons/asana-order-by-day.md).
Incluye: mover tareas pendientes de ayer a hoy (--move-yesterday-to-today).
"""

import argparse
import os
from datetime import datetime, timedelta
from pathlib import Path

_project_root = Path(__file__).resolve().parent.parent
if str(_project_root) not in os.sys.path:
    os.sys.path.insert(0, str(_project_root))

from scripts.credentials import load_env

load_env()


def _load_order_config() -> dict:
    path = _project_root / "config" / "asana_order.yaml"
    if not path.exists():
        return {}
    import yaml
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return {k: [str(x).strip() for x in v] for k, v in data.items() if isinstance(v, list)}


def _sort_tasks_by_day(tasks: list, order_config: dict) -> list:
    if not order_config or not tasks:
        return tasks
    weekday = datetime.utcnow().strftime("%A")  # Monday, Tuesday, ...
    priorities = order_config.get(weekday) or []
    prio_map = {p.lower(): i for i, p in enumerate(priorities)}

    def key(t):
        proj = (t.get("project_name") or "").strip().lower()
        idx = prio_map.get(proj)
        if idx is None:
            for p, i in prio_map.items():
                if p in proj or proj in p:
                    return (i, t.get("name", ""))
            return (999, t.get("name", ""))
        return (idx, t.get("name", ""))

    return sorted(tasks, key=key)


def add_task_to_project(task_gid: str, project_gid: str, section_gid: str = None) -> bool:
    """Añade la tarea al proyecto (y opcionalmente a la sección indicada). Requiere scope tasks:write."""
    token = os.getenv("ASANA_ACCESS_TOKEN")
    if not token or not task_gid or not project_gid:
        return False
    try:
        import urllib.request
        import json
        data = {"project": project_gid}
        if section_gid:
            data["section"] = section_gid
        payload = json.dumps({"data": data}).encode("utf-8")
        req = urllib.request.Request(
            "https://app.asana.com/api/1.0/tasks/" + task_gid + "/addProject",
            data=payload,
            method="POST",
            headers={
                "Authorization": "Bearer " + token,
                "Content-Type": "application/json",
            },
        )
        with urllib.request.urlopen(req) as r:
            r.read()
        return True
    except Exception:
        return False


def add_task_to_section(task_gid: str, section_gid: str) -> bool:
    """Añade la tarea a la sección indicada (p. ej. Today). La tarea debe estar en el proyecto de esa sección. Requiere tasks:write."""
    token = os.getenv("ASANA_ACCESS_TOKEN")
    if not token or not task_gid or not section_gid:
        return False
    try:
        import urllib.request
        import json
        payload = json.dumps({"data": {"task": task_gid}}).encode("utf-8")
        req = urllib.request.Request(
            "https://app.asana.com/api/1.0/sections/" + section_gid + "/addTask",
            data=payload,
            method="POST",
            headers={
                "Authorization": "Bearer " + token,
                "Content-Type": "application/json",
            },
        )
        with urllib.request.urlopen(req) as r:
            r.read()
        return True
    except Exception:
        return False


def _get_sections_for_project(token: str, project_gid: str) -> list:
    """Lista las secciones del proyecto. Devuelve [{"gid": ..., "name": ...}, ...]."""
    try:
        import urllib.request
        import json
        url = "https://app.asana.com/api/1.0/projects/" + project_gid + "/sections?opt_fields=name,gid"
        req = urllib.request.Request(url, headers={"Authorization": "Bearer " + token})
        with urllib.request.urlopen(req) as r:
            data = json.loads(r.read().decode())
        return data.get("data", [])
    except Exception:
        return []


def _resolve_today_section_gid(token: str, project_gid: str) -> str:
    """Devuelve el GID de la sección 'Today' en el proyecto: env ASANA_TODAY_SECTION_GID o búsqueda por nombre."""
    section_gid = os.getenv("ASANA_TODAY_SECTION_GID", "").strip()
    if section_gid:
        return section_gid
    sections = _get_sections_for_project(token, project_gid)
    for s in sections:
        if (s.get("name") or "").strip().lower() == "today":
            return s.get("gid") or ""
    return ""


def get_tasks_today() -> list:
    """Lista de tareas asignadas al usuario actual con due_date = hoy.
    Si ASANA_INBOX_PROJECT_GID está definido, asegura que todas las tareas de hoy
    estén en ese proyecto (My tasks) antes de ordenar y listar.
    Usa ASANA_WORKSPACE_GID y config/asana_order.yaml para el orden.
    """
    token = os.getenv("ASANA_ACCESS_TOKEN")
    if not token or not token.strip():
        return []

    try:
        import urllib.request
        import json
        today = datetime.utcnow().strftime("%Y-%m-%d")
        req = urllib.request.Request(
            "https://app.asana.com/api/1.0/users/me",
            headers={"Authorization": "Bearer " + token},
        )
        with urllib.request.urlopen(req) as r:
            me = json.loads(r.read().decode())
        user_gid = me["data"]["gid"]

        workspace_gid = os.getenv("ASANA_WORKSPACE_GID", "").strip()
        if not workspace_gid:
            req = urllib.request.Request(
                "https://app.asana.com/api/1.0/workspaces",
                headers={"Authorization": "Bearer " + token},
            )
            with urllib.request.urlopen(req) as r:
                ws = json.loads(r.read().decode())
            workspaces = ws.get("data", [])
            if not workspaces:
                return []
            workspace_gid = workspaces[0]["gid"]

        inbox_project_gid = os.getenv("ASANA_INBOX_PROJECT_GID", "").strip()
        today_section_gid = ""
        if inbox_project_gid:
            today_section_gid = _resolve_today_section_gid(token, inbox_project_gid)

        opt_fields = "name,due_on,assignee,projects,completed,gid"
        url = (
            "https://app.asana.com/api/1.0/tasks?"
            "assignee=" + user_gid + "&workspace=" + workspace_gid +
            "&completed_since=now&opt_fields=" + opt_fields
        )
        req = urllib.request.Request(url, headers={"Authorization": "Bearer " + token})
        with urllib.request.urlopen(req) as r:
            data = json.loads(r.read().decode())

        out = []
        for t in data.get("data", []):
            if t.get("due_on") != today:
                continue
            assignee = t.get("assignee")
            assignee_gid = assignee.get("gid") if isinstance(assignee, dict) else assignee
            if assignee_gid != user_gid:
                continue
            projects = t.get("projects") or []
            project_gids = [p.get("gid") for p in projects if p.get("gid")]
            # Añadir al proyecto (y a la sección Today si existe) o mover a Today si ya está en el proyecto
            if inbox_project_gid:
                if inbox_project_gid not in project_gids:
                    add_task_to_project(
                        t.get("gid"),
                        inbox_project_gid,
                        section_gid=today_section_gid or None,
                    )
                elif today_section_gid:
                    add_task_to_section(t.get("gid"), today_section_gid)
            project_name = projects[0].get("name", "") if projects else ""
            out.append({
                "name": t.get("name", ""),
                "due_on": t.get("due_on"),
                "project_name": project_name,
                "completed": t.get("completed", False),
            })
        order_config = _load_order_config()
        return _sort_tasks_by_day(out, order_config)
    except Exception:
        return []


def _get_user_and_workspace(token: str):
    """Devuelve (user_gid, workspace_gid) o (None, None) si falla."""
    try:
        import urllib.request
        import json
        req = urllib.request.Request(
            "https://app.asana.com/api/1.0/users/me",
            headers={"Authorization": "Bearer " + token},
        )
        with urllib.request.urlopen(req) as r:
            me = json.loads(r.read().decode())
        user_gid = me["data"]["gid"]
        workspace_gid = os.getenv("ASANA_WORKSPACE_GID", "").strip()
        if not workspace_gid:
            req = urllib.request.Request(
                "https://app.asana.com/api/1.0/workspaces",
                headers={"Authorization": "Bearer " + token},
            )
            with urllib.request.urlopen(req) as r:
                ws = json.loads(r.read().decode())
            workspaces = ws.get("data", [])
            if not workspaces:
                return None, None
            workspace_gid = workspaces[0]["gid"]
        return user_gid, workspace_gid
    except Exception:
        return None, None


def get_tasks_due_on(date_iso: str) -> list:
    """Tareas asignadas al usuario con due_on = date_iso y no completadas. Incluye gid para poder actualizarlas."""
    token = os.getenv("ASANA_ACCESS_TOKEN")
    if not token or not token.strip():
        return []
    user_gid, workspace_gid = _get_user_and_workspace(token)
    if not user_gid or not workspace_gid:
        return []
    try:
        import urllib.request
        import json
        project_gid = os.getenv("ASANA_INBOX_PROJECT_GID", "").strip()
        opt_fields = "name,due_on,assignee,projects,completed,gid"
        if project_gid:
            url = (
                "https://app.asana.com/api/1.0/projects/" + project_gid + "/tasks?"
                "opt_fields=" + opt_fields
            )
        else:
            url = (
                "https://app.asana.com/api/1.0/tasks?"
                "assignee=" + user_gid + "&workspace=" + workspace_gid +
                "&completed_since=now&opt_fields=" + opt_fields
            )
        req = urllib.request.Request(url, headers={"Authorization": "Bearer " + token})
        with urllib.request.urlopen(req) as r:
            data = json.loads(r.read().decode())
        out = []
        for t in data.get("data", []):
            if t.get("due_on") != date_iso:
                continue
            if t.get("completed"):
                continue
            if project_gid:
                assignee = t.get("assignee")
                assignee_gid = assignee.get("gid") if isinstance(assignee, dict) else assignee
                if assignee_gid != user_gid:
                    continue
            out.append({
                "gid": t.get("gid"),
                "name": t.get("name", ""),
                "due_on": t.get("due_on"),
            })
        return out
    except Exception:
        return []


def update_task_due(task_gid: str, due_on: str) -> bool:
    """Actualiza la fecha de vencimiento de una tarea. Requiere scope de escritura."""
    token = os.getenv("ASANA_ACCESS_TOKEN")
    if not token or not task_gid or not due_on:
        return False
    try:
        import urllib.request
        import json
        payload = json.dumps({"data": {"due_on": due_on}}).encode("utf-8")
        req = urllib.request.Request(
            "https://app.asana.com/api/1.0/tasks/" + task_gid,
            data=payload,
            method="PUT",
            headers={
                "Authorization": "Bearer " + token,
                "Content-Type": "application/json",
            },
        )
        with urllib.request.urlopen(req) as r:
            r.read()
        return True
    except Exception:
        return False


def move_yesterday_to_today() -> int:
    """Mueve las tareas pendientes con fecha de ayer a hoy. Devuelve el número de tareas actualizadas."""
    yesterday = (datetime.utcnow() - timedelta(days=1)).strftime("%Y-%m-%d")
    today = datetime.utcnow().strftime("%Y-%m-%d")
    tasks = get_tasks_due_on(yesterday)
    moved = 0
    for t in tasks:
        gid = t.get("gid")
        if gid and update_task_due(gid, today):
            moved += 1
    return moved


def _strip_html(html: str) -> str:
    """Quita etiquetas HTML y normaliza espacios."""
    if not html or not isinstance(html, str):
        return ""
    import re
    text = re.sub(r"<[^>]+>", " ", html)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def get_tasks_completed_on(date_iso: str) -> list:
    """
    Tareas asignadas al usuario que fueron completadas el día date_iso (YYYY-MM-DD).
    Devuelve lista de dict con: name, project_name, date_iso, notes (descripción en texto plano).
    """
    token = os.getenv("ASANA_ACCESS_TOKEN")
    if not token or not token.strip():
        return []
    user_gid, workspace_gid = _get_user_and_workspace(token)
    if not user_gid or not workspace_gid:
        return []
    try:
        import urllib.request
        import json
        # completed_since: tareas incompletas o completadas desde ese momento
        since = date_iso + "T00:00:00.000Z"
        opt_fields = "name,completed_at,completed,projects.name,notes"
        url = (
            "https://app.asana.com/api/1.0/tasks?"
            "assignee=" + user_gid + "&workspace=" + workspace_gid +
            "&completed_since=" + since + "&opt_fields=" + opt_fields
        )
        req = urllib.request.Request(url, headers={"Authorization": "Bearer " + token})
        with urllib.request.urlopen(req) as r:
            data = json.loads(r.read().decode())
        out = []
        for t in data.get("data", []):
            if not t.get("completed"):
                continue
            completed_at = t.get("completed_at") or ""
            if completed_at[:10] != date_iso:
                continue
            # La petición ya filtra por assignee=user_gid; por si acaso comprobamos
            assignee = t.get("assignee")
            if assignee is not None:
                aid = assignee.get("gid") if isinstance(assignee, dict) else assignee
                if aid != user_gid:
                    continue
            projects = t.get("projects") or []
            project_name = projects[0].get("name", "") if projects else ""
            notes = t.get("notes") or ""
            out.append({
                "name": t.get("name", ""),
                "project_name": project_name,
                "date_iso": date_iso,
                "notes": _strip_html(notes),
            })
        return out
    except Exception:
        return []


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Tareas de hoy (Asana). Opciones: mover ayer→hoy, tareas realizadas→bitácora.")
    parser.add_argument(
        "--move-yesterday-to-today",
        action="store_true",
        help="Mover tareas con fecha de ayer (pendientes) a hoy.",
    )
    parser.add_argument(
        "--completed-yesterday-to-bitacora",
        action="store_true",
        help="Recoger tareas realizadas ayer, leer descripción e incorporar a bitácora del cliente.",
    )
    args = parser.parse_args()

    load_env()
    if args.move_yesterday_to_today:
        n = move_yesterday_to_today()
        print("Tareas movidas de ayer a hoy:", n)
    elif args.completed_yesterday_to_bitacora:
        from scripts import bitacora_append
        yesterday = (datetime.utcnow() - timedelta(days=1)).strftime("%Y-%m-%d")
        entries = get_tasks_completed_on(yesterday)
        added = bitacora_append.process_completed_tasks(entries)
        print("Tareas realizadas ayer → bitácora:", len(added), "entrada(s) añadida(s).")
    else:
        tasks = get_tasks_today()
        print("Tareas hoy:", len(tasks))
        for t in tasks:
            print(" ", t["name"])
