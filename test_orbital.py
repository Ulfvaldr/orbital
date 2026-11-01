import json
import os
import sqlite3
import tempfile
import threading
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import server

class OrbitalReadOnlyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        cls.tmp.close()
        cls.db = cls.tmp.name
        with sqlite3.connect(cls.db) as db:
            db.executescript("""
              create table tasks (id text primary key, title text, status text, assignee text, project text, updated_at text);
              create table task_runs (id text primary key, task_id text, outcome text, started_at text);
              create table task_events (id text primary key, run_id text, task_id text, kind text, summary text, created_at text);
              create table task_links (parent_id text, child_id text);
              insert into tasks values ('done-odin','Old done','done','Odin','p','2026-01-01');
              insert into tasks values ('ready-odin','Current assignment','ready','Odin','p','2026-02-01');
              insert into tasks values ('review-bao','Review assignment','review','Bao','p','2026-02-02');
              insert into tasks values ('done-bao','History','done','Bao','p','2026-01-01');
              insert into tasks values ('done-veritas','Completed review','done','Veritas','p','2026-03-01');
              insert into task_runs values ('run-1','ready-odin','running','2026-02-01');
              insert into task_events values ('event-1','run-1','ready-odin','handoff','Waiting on Bao','2026-02-01');
              insert into task_links values ('ready-odin','review-bao');
              insert into task_links values ('unrelated-a','unrelated-b');
            """)
        cls.old_db = os.environ.get("HERMES_KANBAN_DB")
        os.environ["HERMES_KANBAN_DB"] = cls.db
        cls.httpd = server.ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
        cls.httpd.daemon_threads = True
        cls.httpd.block_on_close = False
        cls.thread = threading.Thread(target=cls.httpd.serve_forever, daemon=True); cls.thread.start()
        cls.base = "http://127.0.0.1:%d" % cls.httpd.server_address[1]

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown(); cls.thread.join(timeout=2); cls.httpd.server_close()
        try:
            os.unlink(cls.db)
        except PermissionError:
            pass
        if cls.old_db is None: os.environ.pop("HERMES_KANBAN_DB", None)
        else: os.environ["HERMES_KANBAN_DB"] = cls.old_db

    def get(self, path):
        with urlopen(self.base + path) as response: return response.status, json.load(response)

    def test_ui_and_fixed_roster(self):
        html = urlopen(self.base + "/").read().decode()
        for marker in ("Fleet Overview", "Agent Inspector", "Latest Requests", "System Indicators"):
            self.assertIn(marker, html)
        status, data = self.get("/api/fleet")
        self.assertEqual(status, 200); self.assertEqual([a["name"] for a in data["agents"]], server.AGENTS); self.assertTrue(data["read_only"])

    def test_current_task_completed_only_is_null_and_active_wins(self):
        fleet = self.get("/api/fleet")[1]["agents"]
        odin = next(a for a in fleet if a["name"] == "Odin")
        bao = next(a for a in fleet if a["name"] == "Bao")
        self.assertEqual(odin["current_task"]["id"], "ready-odin")
        self.assertEqual(bao["current_task"]["id"], "review-bao")
        self.assertIsNone(next(a for a in fleet if a["name"] == "Brokkr")["current_task"])
        self.assertIsNone(next(a for a in fleet if a["name"] == "Veritas")["current_task"])

    def test_current_task_ignores_stale_done_work_and_preserves_multiple_assignments(self):
        fleet = self.get("/api/fleet")[1]["agents"]
        odin = next(a for a in fleet if a["name"] == "Odin")
        veritas = next(a for a in fleet if a["name"] == "Veritas")
        self.assertEqual(odin["assignment_count"], 1)
        self.assertEqual(odin["current_assignment_count"], 1)
        self.assertEqual(odin["historical_assignment_count"], 1)
        self.assertEqual(odin["historical_assignments"][0]["assignment_class"], "historical")
        self.assertEqual(odin["current_task"]["status"], "ready")
        self.assertIsNone(veritas["current_task"])
        self.assertEqual(veritas["assignment_count"], 0)
        self.assertEqual(veritas["historical_assignment_count"], 1)

    def test_assignments_dependencies_timeline_and_write_rejection(self):
        odin = self.get("/api/agents/Odin")[1]
        self.assertEqual(odin["assignment_count"], 1)
        self.assertEqual(odin["dependencies"][0]["parent_task_id"], "ready-odin")
        self.assertEqual(odin["dependencies"][0]["child_task_id"], "review-bao")
        self.assertEqual(odin["dependencies"][0]["direction"], "parent_to_child")
        self.assertEqual(odin["assignments"][0]["context"]["project"], "p")
        self.assertEqual(len(odin["dependencies"]), 1)
        timeline = self.get("/api/runs/run-1")[1]
        self.assertEqual(timeline["events"][0]["id"], "event-1"); self.assertTrue(timeline["read_only"])
        with self.assertRaises(HTTPError) as error: urlopen(Request(self.base + "/api/fleet", method="POST"))
        self.assertEqual(error.exception.code, 501)

    def test_failed_state_has_distinct_static_ui_contract(self):
        with open(os.path.join(server.ROOT, "index.html"), encoding="utf-8") as page:
            html = page.read()
        self.assertIn(".failed{background:#f87171}", html)
        self.assertNotIn(".failed{background:var(--teal)}", html)
        self.assertIn("a.state==='running'?'pulse':''", html)
        self.assertIn("<span class=\"dot ${a.state}\">", html)
        self.assertIn("<button class=\"agent ${a.state==='running'?'pulse':''}\"", html)

    def test_missing_database_degrades_without_fabrication(self):
        old = os.environ["HERMES_KANBAN_DB"]; os.environ["HERMES_KANBAN_DB"] = self.db + ".missing"
        try:
            data = self.get("/api/fleet")[1]
            self.assertEqual(len(data["agents"]), 4); self.assertEqual(data["agents"][0]["assignment_count"], 0); self.assertEqual(data["agents"][0]["source_status"], "unavailable")
        finally: os.environ["HERMES_KANBAN_DB"] = old



class OrbitalHeartbeatTests(unittest.TestCase):

    def test_heartbeat_freshness(self):
        import time
        import server

        now = int(time.time())

        cases = [
            ("fresh", "running", now - 30),
            ("stale", "running", now - 600),
            ("unavailable", "running", None),
            ("not_applicable", "completed", now - 600),
        ]

        for expected, status, heartbeat in cases:
            with self.subTest(expected=expected):
                task = {"id": "heartbeat-test", "status": status}

                if heartbeat is not None:
                    task["last_heartbeat_at"] = heartbeat

                result = server._activity_metadata([task], [])

                self.assertEqual(
                    result["heartbeat_status"],
                    expected
                )

if __name__ == "__main__": unittest.main(verbosity=2)
