# Orbital v0.1.0 project status

Status: v0.1.0 read-only MVP, locally validated.

Canonical path: `C:\Users\rvanb\Projects\orbital`

Implemented:

- Standard-library loopback server and static dark Fleet Overview UI.
- Fixed Odin/Bao/Brokkr/Veritas roster with multi-assignment summaries.
- Deterministic current-task derivation: active task only; completed-only history yields `null`.
- Read-only task, run, event, and dependency/handoff endpoints.
- Honest unavailable-source and unavailable-telemetry states.
- Explicit HTTP 501 rejection for all mutation methods.
- Regression tests for current-task selection, assignments, dependencies, timeline, invalid source, serving, and write rejection.

Not implemented by design: orchestration controls, task editing, n8n integration, cost/token fabrication, authentication, remote deployment, and replay/re-execution.

Release focus: data correctness, operational visibility, read-only safety, and reliable local operation. Visual polish, deeper telemetry, and orchestration controls remain future work. See `docs/provenance.md` for the implementation boundary and source-of-truth notes.
