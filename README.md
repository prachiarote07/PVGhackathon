# MoneyFy — Your Moves, Made Smarter.

The existing React/Vite application now connects to FastAPI, SQLAlchemy and Python financial analytics. The website and Capacitor Android shell share the same interface, rotating coin introduction and financial features. No commits or pushes were made.

## Run locally

Requires Python 3.11+ (tested with 3.14), Node 22.12+ and npm. From the repository root in PowerShell:

```powershell
python -m venv backend/.venv
backend/.venv/Scripts/python.exe -m pip install -r backend/requirements.lock.txt
./backend/start.ps1
```

In a second terminal:

```powershell
cd frontend
npm ci
npm run dev
```

Open http://127.0.0.1:5173. Choose **Sign in / Create account**. New accounts start empty. In Privacy Center set balance, salary, reserve, balance date and next payday; permit imports before uploading statements. Transactions supports manual categories. `demo-data/` contains synthetic examples. Sample dates must not exceed the chosen balance date.

Without DATABASE_URL the backend explicitly uses persisted SQLite at `backend/data/moneyfy.db`. This is the verified local configuration, not PostgreSQL. See [backend setup](backend/README.md) for PostgreSQL configuration. The offline synthetic demo remains separate; it is never silently substituted for account data.

## Implemented

- Signup, login, logout, password hashing, expiring sessions and account isolation.
- Dashboard and 7/15/30-day forecasts from saved transactions, supplied balance, confirmed recurring payments, bills and payday.
- Manual transactions with weekly/monthly/yearly/custom recurrence, paid/skipped/postponed occurrences, bank matching, and month/year navigation.
- History-based recurrence suggestions require confirmation; declined patterns are remembered and reminders can be snoozed.
- CSV imports, three fictional-bank adapters, duplicate exclusion and persisted manual categorization.
- Money Autopilot with evidence, confirmation, modify/reject/undo; What-If Simulator.
- Savings goals, explainable recommendations, financial health score, alerts and money-leak signals.
- Privacy consent, export, confirmed financial-data deletion and explicit sample reset. Deletion retains the login account.
- Refreshed white/teal interface, left desktop sidebar, mobile navigation, touch charts/sliders and How It Works. The public homepage contains no personal financial figures; the synthetic demo is an explicit separate choice.

## Android APK

The Android app name is **MoneyFy**, package `com.moneyfy.app`. Install JDK 21, Android Studio or standalone tools, SDK Platform 36, Build-Tools 35.0.0 and platform-tools; configure JAVA_HOME / ANDROID_HOME and accept SDK licenses.

```powershell
cd frontend
npm run android:doctor
npm run android:apk
```

After a successful build the APK is `frontend/android/app/build/outputs/apk/debug/app-debug.apk`. Install from `frontend/` with `adb install -r android/app/build/outputs/apk/debug/app-debug.apk`.

**No APK has been generated on this laptop:** compatible JDK 21 and Android SDK prerequisites are missing. Native installation and plugins remain unverified. [Android guide](docs/ANDROID.md) covers setup and device checks.

Android account access requires `VITE_API_BASE_URL=https://YOUR-ACTUAL-API-HOST/api/v1` in `frontend/.env.android.local`, then sync/rebuild. Phone localhost is not the laptop. Trusted HTTPS is required; cleartext and mixed content are disabled. Without an API URL the packaged offline demo works. Web development proxies `/api` to port 8000; a deployed website needs an equivalent HTTPS reverse proxy or explicit HTTPS API URL. Build website fallback with `npm run build` (dist); Android uses dist-android.

## Verify

Start the backend before browser account tests. From the root:

```powershell
backend/.venv/Scripts/python.exe -m pytest backend/tests -q
cd frontend
npm test
npm run build
npm run test:e2e
npm run android:sync
npm run test:android-web
```

Browser tests require installed Google Chrome. See [test results](docs/TEST_RESULTS.md), [resumption audit](docs/RESUME_AUDIT.md), [architecture](docs/ARCHITECTURE.md), and [feature status](docs/FEATURE_CHECKLIST.md). The running API serves `/docs`; [OpenAPI](docs/openapi.json) describes implemented endpoints. The older `api-contract.openapi.json` is historical planning material.

See [the recurring-payment guide](docs/RECURRING_TRANSACTIONS.md) for calendar rules, payment matching, suggestion decisions and month progression.

## Limits and team workflow

Forecasts use deterministic rules, not trained AI. Balance is a supplied snapshot; historical imports do not double-count against it. Recurring patterns are suggested from history; only confirmed schedules and explicit bills enter forecasts. Expected payments stay separate from actual records. Forecasts and scores are estimates. No money moves and bank adapters are fictional.

SQLite persistence is tested; PostgreSQL configuration is provided but execution is unverified. Real banking, Excel imports, deployment/TLS, email verification/password recovery/MFA, production migrations and distributed rate limiting remain unfinished. Session tokens live in sessionStorage; storage is not encrypted by this app. Use synthetic hackathon data.

Existing repository/history and team ownership are preserved. See [TEAM_ROLES.md](TEAM_ROLES.md) and [CONTRIBUTING.md](CONTRIBUTING.md). Team review and explicit approval are required before committing or pushing.
