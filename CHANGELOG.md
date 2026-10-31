# Changelog

All notable Orbital releases are documented here.

## [0.1.0] — 2026-10-31

Initial release of the locally validated, read-only MVP.

### Included

- Dark Fleet Overview for the fixed Hermes roster: Odin, Bao, Brokkr, and Veritas.
- Read-only agent inspection, assignments, current-task derivation, project context, dependency links, and recent task/run/event data.
- SQLite read model sourced from the local Hermes kanban database, with support for `HERMES_KANBAN_DB` overrides.
- Truthful empty/unavailable states for missing databases, missing tables, partial schemas, unavailable cost/token telemetry, and unconnected n8n status.
- Explicit HTTP 501 rejection for mutation methods.
- Standard-library-only local startup; no dependency installation or frontend build step.

### Not included by design

Orbital does not edit tasks, assign work, trigger agents, approve or replay runs, control n8n, provide authentication, support remote or multi-user deployment, or claim production operations-platform maturity.
