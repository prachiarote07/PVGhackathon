# MoneyFy contribution responsibilities

One workspace, four members, one existing repository: https://github.com/prachiarote07/PVGhackathon.git

| Checkpoint | Reviewer / module owner | Scope |
| --- | --- | --- |
| 1 | Yadnesha | `frontend/`: React UI, all pages, charts, responsive layout, local demo reference model and frontend tests |
| 2 | Prachi | `backend/`: FastAPI, Pydantic, SQLAlchemy, Psycopg, PostgreSQL, simulated bank REST endpoints, ingestion and persistence |
| 3 | Nirali | `analytics-engine/`: authoritative forecasts, scoring, goal allocation, simulation and explainable recommendations |
| 4 | Mansi | `alerts-integration/`, `tests/`: leak detection, alerts, integration and final verification |

Shared root documentation, contracts and demo fixtures are prepared for review at checkpoint 1. Ownership of their commit must be explicitly approved. Module responsibility is not a claim of authorship: the initial code is Codex-assisted work prepared for each member to review and improve.

Current boundary: checkpoint 1 is prepared; later implementations have not begun. Nothing is staged, committed or pushed by Codex. Each member must review their files, authorize the exact commit scope and authenticate their own GitHub account before their individual commit and push. Do not change author identity or invent co-author entries to simulate contributions.

Mentor-requested Android adaptation extends checkpoint 1: Yadnesha reviews the shared mobile UI, Capacitor shell and native Android project; Prachi reviews the planned secure API/CORS boundary; Mansi owns emulator/device verification after SDK setup. The full-stack module plan remains unchanged. Android source and shared docs still require explicit commit/push approval.
