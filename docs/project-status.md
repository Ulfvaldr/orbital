# Orbital v0.2.0 Project Status

Updated: 2026-11-26

## Status

Implementation complete and locally validated. Release publication pending.

Orbital is a local, read-only AI agent observability platform for the Hermes Lean Agent Team.

## Implemented

- Fleet Overview and Agent Inspector.
- Four-agent roster: Odin, Bao, Brokkr, and Veritas.
- Fleet health and heartbeat monitoring.
- Current and historical task assignments.
- Task dependencies, execution records, and event history.
- Interactive usage and token analytics.
- Estimated API costs and model/provider breakdowns.
- Agent Operations dashboard.
- Task outcome timelines and workload visualization.
- Agent task ledger and completion metrics.
- Read-only SQLite access.
- HTTP 501 rejection of mutation methods.
- Truthful unavailable and missing-data states.

## Validation

- 22 of 22 automated regression tests passed.
- Python syntax validation passed.
- Git whitespace validation passed.
- Preliminary credential and sensitive filename checks passed.
- All three dashboards visually validated.
- SVG timeline rendering corrected.
- Fleet analytics navigation corrected.

## Architecture

- Python standard-library server.
- Static HTML, CSS, and JavaScript.
- Local SQLite data sources.
- Loopback-only network access.
- No additional package installation or frontend build required.

## Known limitations

- No authentication or multi-user access control.
- No remote deployment support.
- No agent orchestration or task mutation controls.
- No n8n integration.
- No automated alerting or historical replay.
- Estimated costs are not authoritative billing totals.
- Data freshness depends on Hermes.

## Release

Version: v0.2.0
Branch: main
Repository: https://github.com/Ulfvaldr/orbital

## Future development

- Expanded telemetry and reporting.
- Cost-efficiency benchmarking.
- Optional automation integrations.
- Additional observability capabilities.

Future features are outside the v0.2.0 release scope.
