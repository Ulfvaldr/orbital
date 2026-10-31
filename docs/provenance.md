# Reconstruction provenance

The original Orbital implementation workspace was reported missing or not a Git working tree. Recovery reports identified a diagnostic probe containing `server.py`, `index.html`, and smoke tests, plus approved design, data-interaction, and acceptance documents in the Hermes task attachments.

This repository was reconstructed in the authorized canonical directory from those approved requirements and evidence. The probe was not treated as authoritative: the reconstruction adds deterministic active-task selection, explicit run/event/dependency read APIs, invalid-source semantics, and regression coverage. No Hermes database, task board, or other repository was modified.

Synthetic SQLite data exists only inside automated tests and is clearly test-local. The running app uses the configured real Hermes kanban database and labels source availability.
