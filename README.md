# Orbital v0.1.0

Orbital is the local, read-only observation surface for the Hermes Lean Agent Team. Hermes remains the system that runs agents and owns kanban state; Orbital is a companion viewer that reads that state so a human can inspect agent status, current work, recent requests, and basic system indicators.

**v0.1.0 is an early, locally validated MVP.** It is useful for inspecting a local Hermes kanban database, but it is not an orchestration console or a production operations platform.

## Current MVP scope

The MVP serves:

- a dark mission-control Fleet Overview UI at `/`;
- an outliner and fleet tiles for the supported Hermes agents;
- a read-only Agent Inspector for each supported agent;
- a Latest Requests section populated from recorded Hermes task data when available;
- simple System Indicators that distinguish available, unavailable, and not-connected data instead of fabricating metrics;
- JSON read APIs for smoke checks and simple integrations.

Supported Hermes agents in this MVP:

- Odin — orchestrator
- Bao — researcher
- Brokkr — implementer
- Veritas — reviewer

## Read-only boundary

Orbital is observational only.

It reads the Hermes kanban SQLite database using SQLite read-only mode. The application does not include controls or API handlers to:

- create, assign, edit, rerun, approve, block, or complete tasks;
- mutate the Hermes database;
- trigger Hermes agents;
- change Hermes profile configuration;
- alter n8n workflows or any external automation.

HTTP write methods (`POST`, `PUT`, `PATCH`, and `DELETE`) return `501 Orbital is read-only`.

## Architecture and data sources

`server.py` is a standard-library HTTP server and SQLite adapter. `index.html` is the static browser UI. The read model queries the local Hermes SQLite tables `tasks`, `task_links`, `task_runs`, and `task_events` when they exist. Optional columns and missing tables are handled defensively; no production fixture data is injected. The UI polls the read APIs every 15 seconds, but it remains a point-in-time view of whatever the selected database contains.

## Requirements

- Python 3.11 or newer.
- Access to a Hermes kanban database with the expected kanban tables.
- No Python package installation is required for the current MVP; it uses the Python standard library only.

## Start locally

From this repository directory:

    python server.py --port 8766

Then open:

    http://127.0.0.1:8766/

The server binds to `127.0.0.1` and serves the durable `index.html` from this repository directory.

By default Orbital reads:

    ~/AppData/Local/hermes/kanban.db

To inspect another Hermes kanban database, set `HERMES_KANBAN_DB` before starting the server. In a POSIX shell:

    HERMES_KANBAN_DB=C:/path/to/kanban.db python server.py --port 8766

In Windows Command Prompt:

    set HERMES_KANBAN_DB=C:\path\to\kanban.db && python server.py --port 8766

## API endpoints

- `GET /` or `GET /index.html` — Fleet Overview UI.
- `GET /api/fleet` — supported agents, current and historical assignment counts/lists, truthful current task, context, dependency links, latest run pointer, and the database source path.
- `GET /api/snapshot` — agent snapshot plus recent tasks and task events where those tables are available.
- `GET /api/agents/Odin`, `/api/agents/Bao`, `/api/agents/Brokkr`, `/api/agents/Veritas` — read-only detail for one supported agent.
- `GET /api/agents/<unknown>` — an unavailable read-only object; this does not create or modify anything.

## What data Orbital reads

Orbital reads only local Hermes kanban data from SQLite tables when they exist:

- `tasks` for task id, title, status, assignee, project/project_id, priority, and timestamps;
- `task_links` for authoritative `parent_id` → `child_id` relationships (the live Hermes schema);
- `task_runs` for recent run metadata associated with tasks;
- `task_events` for recent activity shown in the Latest Requests area.

The server selects only columns that exist in the database, so older or partial schemas degrade rather than crashing when optional columns are missing. `current_task` is derived from the newest task in an active status, not simply the newest row. Completed-only history remains historical, while `current_task` is `null` for an idle agent. Assignment counts distinguish current and historical work; project context comes from Hermes project fields; dependency direction comes from `task_links.parent_id` → `child_id`.

## Missing, stale, or unavailable data

Orbital must be truthful when telemetry is incomplete:

- If the database cannot be opened, a table is missing, or a query fails, the affected collection is returned as empty rather than fabricated.
- If an agent has no current work, `current_task` is `null` and the UI shows `No current task (idle)`.
- `assignment_count` and `current_assignment_count` count only current statuses (`running`, `in_progress`, `blocked`, `review`, `validating`, `ready`, `scheduled`). `total_assignment_count` includes historical rows, and `historical_assignment_count` reports the remainder.
- Every assignment carries `assignment_class` (`current` or `historical`) and a `context` object. Project metadata comes only from Hermes `project`/`project_id`; absent metadata is shown as `Unscoped`. Parent context comes from live `task_links.parent_id`/`child_id`.
- Dependencies preserve the authoritative parent-to-child direction and are scoped to links touching that agent's assignment IDs; missing links produce no fabricated relationship.
- Completed or stale historical tasks are not promoted to `current_task` just because they are the most recent rows.
- If an agent has assignments but none are current, the agent may appear idle while still showing assignment history/counts.
- Cost/token metrics and n8n status are unavailable/not connected in v0.1.0. Orbital does not estimate or fabricate them. A missing database, missing table, failed query, or stale Hermes writer produces empty or unavailable states instead of invented activity.

## Verify

Run the smoke tests:

    python -m unittest discover -v

Useful manual smoke check:

    python server.py --port 8766
    # in another shell:
    curl http://127.0.0.1:8766/api/fleet

Read-only behavior can be checked by sending a write method to any API route and confirming a `501` response.

If this directory is a valid Git worktree, also run:

    git diff --check

## Limitations

- Local-only, loopback server; not hardened for internet-facing use.
- No authentication or multi-user access control.
- No write/orchestration controls of any kind.
- No n8n integration in the MVP.
- No historical replay, advanced analytics, alerting, or multi-instance federation.
- The current UI is a compact MVP, not a complete operations platform.
- Runtime truthfulness depends on the selected Hermes kanban database being present and current.

See `CHANGELOG.md` for the v0.1.0 release scope and `docs/architecture.md` for implementation boundaries.