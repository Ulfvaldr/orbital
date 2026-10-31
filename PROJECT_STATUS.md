# Orbital project status

Status: reconstructed read-only MVP, locally validated.

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

The original accepted Orbital workspace was not recoverable as a durable checkout. This implementation is a reconstruction from the approved specifications and probe evidence; see `docs/provenance.md`.
