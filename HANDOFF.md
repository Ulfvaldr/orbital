# Orbital handoff

Canonical repository: `C:\Users\rvanb\Projects\orbital`

Run from the repository root:

    python server.py --port 8766

Open `http://127.0.0.1:8766/`.

Validation commands:

    python -m unittest discover -v
    python -m compileall -q server.py test_orbital.py
    git diff --check

The app reads `HERMES_KANBAN_DB` in SQLite read-only mode. It does not modify Hermes state. The next verifier should independently exercise `/`, `/api/fleet`, `/api/snapshot`, `/api/agents/<name>`, `/api/runs/<id>`, `/api/events/<id>`, and mutation rejection.

This task intentionally did not commit, merge, push, tag, publish, or modify the Hermes database. The directory was initialized as a local Git repository solely to provide a durable working tree and diff-check surface; it has no commit yet.
