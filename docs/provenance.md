# Release provenance

Orbital v0.1.0 is the canonical local read-only observability application in this repository. Its implementation boundary is defined by the checked-in server, static UI, tests, and documentation; Hermes remains the authority for agent execution and kanban state.

The application reads the configured Hermes kanban SQLite database and derives display state without writing to Hermes. Deterministic active-task selection, explicit run/event/dependency read APIs, invalid-source semantics, and regression coverage are part of the v0.1.0 implementation. No Hermes database, task board, or other external system is modified.

Synthetic SQLite data exists only inside automated tests and is clearly test-local. The running app uses the configured real Hermes kanban database and labels source availability.
