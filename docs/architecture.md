# Orbital architecture

Orbital v0.2.0 is a local, read-only web application and companion viewer for Hermes. Hermes owns execution and kanban state. `server.py` is a standard-library HTTP server and SQLite adapter; `index.html` is the static browser UI; `test_orbital.py` exercises the derived model and HTTP contract.

Data source and safety:

- `HERMES_KANBAN_DB` selects the source; the default is `~/AppData/Local/hermes/kanban.db`.
- SQLite opens with `mode=ro`; known tables are queried only after column discovery.
- Supported tables are `tasks`, `task_runs`, `task_events`, and `task_links`.
- Missing tables, invalid paths, and unavailable databases return empty collections plus explicit source status; no fixture data is injected into production responses.
- `POST`, `PUT`, `PATCH`, and `DELETE` return HTTP 501.

Derived model:

- Four fixed profiles are shown: Odin, Bao, Brokkr, and Veritas.
- Assignments remain separate from derived state and can contain multiple tasks/projects.
- `current_task` is the newest task in an active status (`running`, `blocked`, `review`, `validating`, `in_progress`, `ready`, or `scheduled`). Completed-only history returns `null`.
- State is derived from current task and latest run: running, blocked, review, failed, or idle.
- Links from `task_links` are exposed as dependencies/handoffs, and run/event endpoints provide read-only timelines.

UI baseline:

The shell preserves the dark mission-control layout: top status bar, left outliner, central orbital fleet overview, right Agent Inspector, Latest Requests/live activity, System Indicators, restrained yellow/teal accents, and responsive cards. There are no operational mutation controls.


## Analytics architecture

### Usage analytics

- `usage.py` provides read-only usage aggregation.
- `stats.html` provides interactive usage visualizations.
- `/api/usage` exposes usage analytics.
- Reporting includes API calls, token consumption, estimated costs,
  and agent/model/provider breakdowns.
- Missing or unclassified cost records are handled explicitly.
- Estimated costs are not authoritative billing totals.

### Operations analytics

- `operations.py` aggregates recorded task outcomes.
- `operations.html` provides the Agent Operations dashboard.
- `/api/operations` exposes operational analytics.
- Timeline windows support 7, 14, and 30 days.
- Completion timelines use recorded UTC completion dates.
- Missing completion dates are never fabricated.
- Workload summaries distinguish completed, failed,
  active/pending, and other tasks.

### Application boundaries

- All three dashboards remain read-only.
- Hermes retains ownership of execution and task state.
- No additional Python dependencies are required.
- No external API calls are required for dashboard rendering.
- Authentication and remote deployment remain outside release scope.

### Automated validation

- `test_orbital.py`: core functionality and read-only behavior.
- `test_usage.py`: usage aggregation and cost classification.
- `test_operations.py`: task outcomes and timeline accuracy.
- Release validation: 22 automated tests passed.
