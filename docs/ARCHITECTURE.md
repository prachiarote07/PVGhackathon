# MoneyFy architecture

React/Vite provides the shared website and Capacitor Android interface. The default offline demo uses browser localStorage and the preserved JavaScript reference model. Signed-in mode uses FastAPI account endpoints, SQLAlchemy persistence and the Python analytics/signals modules; failures do not switch account data to synthetic values.

Users and sessions are separate SQL tables. Each user owns one validated JSON workspace containing transactions, balances, dates, bills, goals, preferences and decisions. This aggregate preserves the existing interface and enables atomic optimistic version checks. It is not a normalized accounting ledger. SQLAlchemy supports PostgreSQL via Psycopg; only SQLite persistence was executed locally.

The browser keeps its opaque bearer token in sessionStorage, never passwords. The server keeps only a token hash and expiry. Account edits serialize through a save queue. Visible errors, retry/reload controls and version conflicts prevent silent replacement of newer data. Server analysis follows successful saves. Financial imports require consent and account ownership.

Python forecasts derive spending rates and recurring costs from saved history and explicit inputs. The supplied balance is a snapshot, so imports do not debit it again. Scenario amounts are hypothetical; accepted recommendations change the proposed plan only. Goal allocations share available capacity. All monetary persistence uses integer paise.

Android packages dist-android; website builds dist. Native communication requires an explicit trusted HTTPS API URL, exact CORS origins, no cleartext or mixed content, and INTERNET permission only. Capacitor localhost is the bundled app origin, not the backend. Native Back/file sharing requires device verification after SDK setup.

See README and backend/README for startup, docs/openapi.json for implemented contracts, and TEST_RESULTS for verification limits. The older api-contract.openapi.json is an unimplemented historical design proposal and must not be used as the current API reference.

## Recurring payments and public homepage

Confirmed schedules, occurrence exceptions and pattern decisions extend the existing per-user JSON workspace with backwards-compatible defaults. Separate authenticated endpoints protect changes; paid occurrences must link to distinct actual records. Calendar expansion is pure and lazy. Python forecasts use confirmed schedules; uncertain patterns only suggest tracking. See RECURRING_TRANSACTIONS.md. PublicHome is informational; account data requires authentication and the offline demo requires an explicit selection.
