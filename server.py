"""Read-only Orbital Fleet Overview server (Python standard library only)."""
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse, parse_qs, unquote
import argparse
import json
import os
import sqlite3
from usage import usage_payload
import time

ROOT = os.path.dirname(os.path.abspath(__file__))
AGENTS = ["Odin", "Bao", "Brokkr", "Veritas"]
ROLES = {"Odin": "orchestrator", "Bao": "researcher", "Brokkr": "implementer", "Veritas": "reviewer"}
COLORS = {"Odin": "#f2c14e", "Bao": "#55d6be", "Brokkr": "#60a5fa", "Veritas": "#c084fc"}
ACTIVE = {"running", "in_progress", "blocked", "review", "validating", "ready", "scheduled"}
RUNNING = {"running", "in_progress"}
REVIEW = {"review", "validating"}

def db_path():
    return os.environ.get("HERMES_KANBAN_DB", os.path.join(os.path.expanduser("~"), "AppData", "Local", "hermes", "kanban.db"))

def rows(table, limit=5000):
    """Read a known table in SQLite read-only mode, adapting to live columns."""
    if table not in {"tasks", "task_runs", "task_events", "task_links"}:
        return []
    db = None
    try:
        db = sqlite3.connect("file:" + db_path() + "?mode=ro", uri=True)
        db.row_factory = sqlite3.Row
        names = {row[1] for row in db.execute(f"pragma table_info({table})")}
        wanted = [name for name in (
            "id", "title", "body", "status", "assignee", "project", "project_id", "team", "priority",
            "created_at", "updated_at", "started_at", "completed_at", "ended_at", "last_heartbeat_at",
            "outcome", "summary", "error", "run_id", "task_id", "event_type", "kind",
            "payload", "source_task_id", "target_task_id", "link_type", "parent_id", "child_id",
        ) if name in names]
        if not wanted:
            return []
        return [dict(row) for row in db.execute(
            "select " + ",".join(wanted) + f" from {table} order by rowid desc limit ?", (limit,)
        )]
    except (OSError, sqlite3.Error):
        return []
    finally:
        if db is not None:
            db.close()

def _stamp(item):
    return str(item.get("updated_at") or item.get("started_at") or item.get("created_at") or item.get("completed_at") or "")

def _status(task):
    return str(task.get("status") or "unknown").lower()

def _current_task(assignments):
    current = [task for task in assignments if _status(task) in ACTIVE]
    return sorted(current, key=lambda task: (_stamp(task), str(task.get("id", ""))), reverse=True)[0] if current else None

def _run_for(task_ids, runs):
    matches = [run for run in runs if str(run.get("task_id", "")).lower() in task_ids]
    return sorted(matches, key=lambda run: (_stamp(run), str(run.get("id", ""))), reverse=True)[0] if matches else None

def _context(task, parent_by_child):
    project = task.get("project") or task.get("project_id")
    return {"project": project or "Unscoped", "parent_task_id": parent_by_child.get(str(task.get("id", ""))), "source": "tasks.project/project_id and task_links"}

def _link_view(link, task_ids):
    parent = link.get("parent_id") or link.get("source_task_id")
    child = link.get("child_id") or link.get("target_task_id")
    if not parent or not child or (str(parent).lower() not in task_ids and str(child).lower() not in task_ids): return None
    return {"id": link.get("id"), "parent_task_id": parent, "child_task_id": child, "direction": "parent_to_child", "link_type": link.get("link_type") or "dependency"}


# Monitoring metadata only. Does not alter task state.
HEARTBEAT_STALE_SECONDS = 120

def _unix_time(value):
    """Accept Hermes Unix-second timestamps; reject invalid values."""
    if value is None or isinstance(value, bool):
        return None
    try:
        number = float(value)
        if not (0 < number < 32503680000):
            return None
        return number
    except (TypeError, ValueError, OverflowError):
        return None

def _latest_timestamp(values):
    valid = [_unix_time(value) for value in values]
    valid = [value for value in valid if value is not None]
    return int(max(valid)) if valid else None

def _activity_metadata(assignments, runs):
    """Derive observation metadata without claiming agent liveness."""
    task_ids = {
        str(task.get("id", "")).lower()
        for task in assignments
    }
    related_runs = [
        run for run in runs
        if str(run.get("task_id", "")).lower() in task_ids
    ]

    activity = []
    for task in assignments:
        activity.extend(task.get(key) for key in (
            "created_at", "updated_at", "started_at",
            "completed_at", "last_heartbeat_at"
        ))
    for run in related_runs:
        activity.extend(run.get(key) for key in (
            "started_at", "ended_at", "last_heartbeat_at"
        ))

    active_tasks = [
        task for task in assignments
        if _status(task) in RUNNING
    ]
    active_ids = {
        str(task.get("id", "")).lower()
        for task in active_tasks
    }

    heartbeat_values = [
        task.get("last_heartbeat_at") for task in active_tasks
    ]
    heartbeat_values.extend(
        run.get("last_heartbeat_at")
        for run in related_runs
        if str(run.get("task_id", "")).lower() in active_ids
    )

    heartbeat = _latest_timestamp(heartbeat_values)
    last_activity = _latest_timestamp(activity)

    if not active_tasks:
        heartbeat_status = "not_applicable"
        heartbeat_age = None
        heartbeat = None
    elif heartbeat is None:
        heartbeat_status = "unavailable"
        heartbeat_age = None
    else:
        heartbeat_age = max(0, int(time.time() - heartbeat))
        heartbeat_status = (
            "fresh"
            if heartbeat <= time.time()
            and heartbeat_age <= HEARTBEAT_STALE_SECONDS
            else "stale"
        )

    return {
        "last_heartbeat_at": heartbeat,
        "heartbeat_age_seconds": heartbeat_age,
        "heartbeat_status": heartbeat_status,
        "last_activity_at": last_activity,
    }

def model():
    tasks, runs, links = rows("tasks"), rows("task_runs"), rows("task_links")
    parent_by_child = {str(link.get("child_id")): link.get("parent_id") for link in links if link.get("child_id") and link.get("parent_id")}
    result = []
    for name in AGENTS:
        assignments = [task for task in tasks if str(task.get("assignee", "")).lower() == name.lower()]
        current_assignments = [task for task in assignments if _status(task) in ACTIVE]
        ids = {str(task.get("id", "")).lower() for task in assignments}
        current = _current_task(assignments); latest = _run_for(ids, runs)
        task_status = _status(current) if current else ""; outcome = str((latest or {}).get("outcome", "")).lower()
        if task_status in RUNNING or outcome == "running": state = "running"
        elif task_status == "blocked" or outcome == "blocked": state = "blocked"
        elif task_status in REVIEW or outcome in {"review_requested", "changes_requested"}: state = "review"
        elif outcome in {"failed", "crashed", "timed_out", "gave_up"}: state = "failed"
        else: state = "idle"
        assignments_view = []
        for task in assignments:
            item = dict(task); item["assignment_class"] = "current" if _status(task) in ACTIVE else "historical"; item["context"] = _context(task, parent_by_child); assignments_view.append(item)
        deps = [_link_view(link, ids) for link in links]
        result.append({"name": name, "role": ROLES[name], "state": state, "color": COLORS[name], "assignments": assignments_view,
            "assignment_count": len(current_assignments), "total_assignment_count": len(assignments), "current_assignment_count": len(current_assignments), "historical_assignment_count": len(assignments)-len(current_assignments),
            "current_assignments": [x for x in assignments_view if x["assignment_class"] == "current"], "historical_assignments": [x for x in assignments_view if x["assignment_class"] == "historical"],
            **_activity_metadata(assignments, runs),
            "current_task": current, "latest_run": latest, "dependencies": [x for x in deps if x is not None], "telemetry": "local kanban.db (read-only)", "source_status": "available" if os.path.exists(db_path()) else "unavailable"})
    return result

def payload(path, period="all"):
    fleet = model()
    if path == "/api/usage":
        return usage_payload(period=period)
    if path == "/api/fleet":
        return {"agents": fleet, "read_only": True, "source": db_path()}
    if path == "/api/snapshot":
        return {"agents": fleet, "requests": rows("tasks", 12), "events": rows("task_events", 40), "dependencies": rows("task_links", 80), "read_only": True, "source": db_path()}
    if path.startswith("/api/agents/"):
        name = unquote(path.rsplit("/", 1)[-1]).lower()
        found = next((agent for agent in fleet if agent["name"].lower() == name), None)
        return found or {"name": path.rsplit("/", 1)[-1], "state": "unavailable", "assignments": [], "dependencies": [], "read_only": True, "source_status": "unknown agent"}
    if path.startswith("/api/runs/"):
        run_id = unquote(path.rsplit("/", 1)[-1])
        return {"run": next((row for row in rows("task_runs") if str(row.get("id")) == run_id), None), "events": [row for row in rows("task_events", 200) if str(row.get("run_id")) == run_id], "read_only": True}
    if path.startswith("/api/events/"):
        event_id = unquote(path.rsplit("/", 1)[-1])
        return {"event": next((row for row in rows("task_events") if str(row.get("id")) == event_id), None), "read_only": True}
    return None

class Handler(SimpleHTTPRequestHandler):
    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/api/usage":
            period = parse_qs(urlparse(self.path).query).get("range", ["all"])[0]
            if period not in ("today", "7d", "30d", "all"):
                self.send_error(400, "Invalid usage range")
                return
            data = payload(path, period=period)
        else:
            data = payload(path)
        if data is not None:
            raw = json.dumps(data, default=str).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers(); self.wfile.write(raw); return
        if path in ("/", "/index.html", "/stats.html"): return super().do_GET()
        self.send_error(404)
    def do_POST(self): self.send_error(501, "Orbital is read-only")
    do_PUT = do_POST; do_PATCH = do_POST; do_DELETE = do_POST
    def log_message(self, format, *args):
        return

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the read-only Orbital Fleet Overview")
    parser.add_argument("--port", type=int, default=8766)
    args = parser.parse_args()
    os.chdir(ROOT)
    print(f"Orbital Fleet Overview: http://127.0.0.1:{args.port}/ (read-only)", flush=True)
    ThreadingHTTPServer(("127.0.0.1", args.port), Handler).serve_forever()
