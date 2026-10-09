# Python financial intelligence

`engine.py` is called by authenticated FastAPI analysis requests. It uses saved transactions, explicit account dates, opening balance, salary, reserve, scheduled bills, goals and confirmed decisions. Integer paise and decimal half-up rounding avoid floating-point money drift.

Daily rates use up to 60 days of supplied history. History suggests possible recurring patterns. Only confirmed schedules and explicit one-off bills enter forecasts. Matching confirmed schedules replace one-off estimates. recurring.py owns calendar expansion, matching, month totals and suggestion decisions. Projections show 30 days and extend calculations through delayed payday for safe-to-spend. Scenarios are temporary. Priority goals share a single capacity budget. Scores disclose their components. No trained model or bank transfer is claimed.

Regression checks live in `backend/tests/`. The frontend offline demo retains its separate reference engine; signed-in account calculations use this Python module.
