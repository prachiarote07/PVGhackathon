# MoneyFy FastAPI backend

Run from the repository root using the README commands. `start.ps1` binds only 127.0.0.1:8000. The frontend development proxy handles local requests. API docs: http://127.0.0.1:8000/docs.

## Database configuration

With DATABASE_URL unset, the explicit development fallback is disk-backed `backend/data/moneyfy.db` (SQLite). Health reports this mode. Users, hashed sessions and versioned per-user workspace JSON are persisted. Files and secrets are ignored by Git.

For PostgreSQL, install/start PostgreSQL or use the optional compose service (Docker required):

```powershell
$env:MONEYFY_POSTGRES_PASSWORD = '<your-local-password>'
docker compose up -d
$env:DATABASE_URL = 'postgresql+psycopg://moneyfy:<URL-encoded-password>@127.0.0.1:5432/moneyfy'
./backend/start.ps1
```

Environment variables must be set in the backend terminal. `.env.example` documents settings; the service does not automatically load dotenv files. Tables are created on startup. Switching databases does not migrate existing SQLite data. PostgreSQL was not available for verification; do not call it tested. Production sets MONEYFY_ENV=production and requires an explicit DATABASE_URL. Add reviewed schema migrations before production evolution.

Set CORS_ORIGINS to a comma-separated exact allowlist for deployed clients; defaults include local Vite origins and Capacitor https://localhost. Terminate trusted TLS at a reviewed proxy. Android requires a reachable HTTPS endpoint. Never expose the development server directly as a production deployment.

## API and behavior

`/api/v1` includes auth/signup, auth/login, auth/me, auth/logout, workspace, analysis, imports/csv, banks/{id}/raw, banks/{id}/connect, transactions/{id}/category, privacy/delete and privacy/reset. See generated `docs/openapi.json` or live `/docs` for methods and bodies.

Passwords use salted scrypt; only hashes of random 24-hour bearer session tokens are stored. Logout revokes the session. Financial endpoints enforce account ownership. Workspace writes require a version and return 409 for stale changes. Import requires consent; recommendation acceptance/deletion requires confirmation. Privacy deletion clears financial workspace data but retains authentication.

Amounts are integer paise internally. CSV values use positive INR amounts with at most two decimal places and debit/credit direction. Future transactions are rejected relative to the supplied balance date. Entire invalid CSV imports fail atomically.

Tests: `backend/.venv/Scripts/python.exe -m pytest backend/tests -q` from the repository root. Verified with temporary SQLite databases, including persistence after app recreation. Rate limiting is single-process, not production distributed protection. Email verification, recovery, MFA and account removal are pending.

Recurring endpoints: GET/POST `/api/v1/recurring`, PATCH `/api/v1/recurring/{schedule_id}`, POST `/api/v1/recurring/suggestions/{pattern_id}`, POST `/api/v1/recurring/occurrences/{occurrence_id}` and POST `/api/v1/transactions` for explicit manual entry. Reads take `month=YYYY-MM`; mutations use workspace versions. New JSON fields have compatible defaults for existing saved accounts. See `docs/RECURRING_TRANSACTIONS.md`.
