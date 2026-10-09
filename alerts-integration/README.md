# MoneyFy signals and integration

`signals.py` derives low-reserve, upcoming-bill, duplicate, unusually large merchant payment, rising recurring bill, fee and goal-feasibility signals from account state and Python analysis. These are explainable rules, not trained anomaly detection.

FastAPI orchestrates signals, analytics and account persistence. The existing React client consumes `/api/v1/analysis` and displays its results. Three fictional bank adapters expose synthetic fixture ingestion; no real banking integration or automated money movement exists. Regression checks live in `backend/tests/`.
