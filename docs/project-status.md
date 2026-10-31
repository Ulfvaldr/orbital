# Orbital MVP Project Status

Updated: 2026-10-31

## Status summary

Orbital's read-only MVP has been reconstructed as a durable local Python/HTML Fleet Overview for Hermes kanban state. It is intentionally observational: it reads local kanban SQLite data and presents the supported Hermes agent roster without task mutation controls.

The implementation, documentation, deterministic stale-task regression, startup path, API smoke checks, and read-only boundary have now been validated in `C:/Users/rvanb/Projects/orbital`. The repository has no commits yet; human Git staging, commit, remote configuration, and push remain explicitly outside agent scope.

## Validation status from release-readiness checks

Verified against the durable Orbital source:

- `python server.py --port 8766` serves the app when run from the accessible source directory.
- `GET /`, `GET /api/fleet`, `GET /api/snapshot`, and supported agent detail endpoints return HTTP 200 in probe checks.
- The four supported agents are Odin, Bao, Brokkr, and Veritas.
- `/api/fleet` reports `read_only: true`.
- `POST`, `PUT`, `PATCH`, and `DELETE` requests to `/api/fleet` return HTTP 501.
- Full unittest smoke/regression suite passes, including deterministic stale-current-task coverage.

The final release-readiness run is recorded in the task handoff. It covers UI markers, all four agent endpoints, current-task truthfulness, multiple assignments, dependency/timeline reads, missing-source degradation, write-method rejection, startup/restart, and `git diff --check`.

## Key architecture decisions

- Local-first, loopback-only MVP served at `http://127.0.0.1:8766/` by default.
- Python standard library only for the MVP server; no package installation required.
- Static `index.html` implements the UI; no frontend build step required.
- Hermes kanban data is read from SQLite in read-only mode.
- The four-agent roster is fixed for the MVP: Odin, Bao, Brokkr, Veritas.
- `current_task` is derived only from active statuses; completed/stale tasks are not promoted to current work.
- Write methods are disabled with HTTP 501; Orbital does not mutate Hermes tasks or trigger agents.
- Missing or unavailable data degrades to empty/unavailable UI states instead of fabricated metrics.

## Known limitations and risks

Release closeout:

- No automated release blocker remains in the durable source tree.
- The repository is intentionally uncommitted and has no configured remote; a human must inspect and perform Git closeout.

Product limitations:

- Local read-only MVP only; no orchestration controls.
- No task editing, assignment, state changes, reruns, approvals, or agent triggering.
- No n8n workflow control.
- No authentication or remote/multi-user deployment support.
- No historical replay, advanced analytics, alerting, or federation.
- Cost/token telemetry is unavailable unless a future source is added.
- The UI refreshes from local SQLite reads; stale source data remains stale until Hermes updates the database.

## Likely next development phase

Before a human commit/push or release, inspect the uncommitted durable source tree and rerun the documented checks if desired.

Recommended next implementation work after repository restoration:

1. Stage and review the durable source tree.
2. Commit and configure the intended remote under human control.
3. Push only after reviewing the commit and repository identity.

Future product phases should remain out of the MVP docs until implemented. Candidate later phases include richer timeline/history views, broader telemetry, optional n8n/status integrations, and controlled orchestration workflows, but none of those are available in the current MVP.