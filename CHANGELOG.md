# Changelog

All notable Orbital releases are documented here.

## [0.2.0] - 2026-11-26

Expanded read-only AI agent observability and operational analytics.

### Added

- Fleet health and heartbeat monitoring.
- Compact Agent Inspector improvements.
- Interactive usage analytics dashboard.
- Input, output, cache, and reasoning token reporting.
- Estimated API cost reporting and cost classification.
- Agent, model, and provider usage breakdowns.
- Agent Operations dashboard.
- Task outcome timelines with 7, 14, and 30-day views.
- Agent workload visualization and task ledger.
- Resolved task completion metrics.

### Fixed

- SVG rendering in the operations timeline.
- Fleet cost/token indicator now links to usage analytics.
- Improved visual states and failed-task handling.

### Validation

- All 22 automated regression tests passed.
- Python syntax validation passed.
- Git whitespace validation passed.
- Preliminary credential and sensitive filename checks passed.
- All three dashboards visually verified against local Hermes data.

### Security and boundaries

- Local, read-only architecture preserved.
- HTTP mutation methods remain disabled.
- No authentication or remote deployment support.
- Missing telemetry is never fabricated.
- Estimated costs are not authoritative billing totals.


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
