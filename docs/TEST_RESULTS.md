# Verification — 10 October 2026: UI refresh and recurring transactions

| Final check | Result |
| --- | --- |
| Backend pytest | **18 passed**: original account/integration cases plus calendar clamping, leap years, custom/end dates, skip/postpone/restore, fixed/variable reconciliation, duplicate prevention, confirmation, remembered decisions, snooze, persistence, ownership and forecast integration |
| Frontend unit tests | **17 passed**, including month-query and encoded occurrence-ID requests |
| Website production build | **Passed**, output in frontend/dist |
| Web browser workflows | **5 passed (1.6m)**: full account flow, preserved demo functionality, mobile navigation, public homepage privacy, and recurring payments across months with reload persistence and CSV reconciliation |
| Capacitor Android asset build/sync | **Passed**, updated packaged assets and existing plugins synced |
| Packaged touch-browser checks | **2 passed (53.5s)**: touch sliders/charts, navigation, approvals, phone/landscape layouts and safe areas |
| Android prerequisite check | **Blocked**: selected Java 26 / unset JAVA_HOME and missing SDK Platform 36. Android Studio, Build-Tools 36.0.0 and adb are detected. No APK generated |
| Git whitespace check | Passed; no staged changes, commits, pushes or remote changes |

All **42 automated test cases** passed in the final runs. Backend tests use isolated SQLite databases; account browser tests use the running real FastAPI service. PostgreSQL and native device execution remain unverified. Browser tests do not execute native plugins or certify an APK.

Visual review included desktop public and recurring screens plus mobile recurring forms. Representative screenshots are in docs/previews/redesign-*.png. The public homepage has no balance, spending or health-score figures before login; the synthetic demo requires an explicit choice.

Earlier attempts exposed an API path validator that rejected month queries/encoded occurrence IDs; it was fixed and covered by a regression test. Laptop memory pressure also caused one password-hashing allocation error and one browser target crash. Final sequential runs passed without reducing password-hashing strength. A temporary resource failure now returns a retryable service error instead of a generic server exception.

See RECURRING_TRANSACTIONS.md for behaviors, boundaries and matching rules. Earlier results below are historical and do not supersede this checkpoint.

---

# Verification — 9 October 2026

## Executed successfully after integration

| Check | Result |
| --- | --- |
| Backend pytest | 9 passed: authentication/revocation, password hashing, ownership, atomic imports, categories, consent, optimistic conflicts, persistence after restart, actual-data analysis, recommendations, goals and alert rules |
| Frontend unit tests | 16 passed: reference financial model, CSV/adapters, URL policy, client errors/timeouts and Android Back decisions |
| Website production build | Passed; output frontend/dist |
| Browser end-to-end | 3 passed (36.8s): account signup/login, saved inputs, imports, manual categories, reload persistence, Python recommendations/simulations, deletion; existing demo pages and mobile navigation/theme |
| Android asset build/sync | Passed; output frontend/dist-android and copied native assets/plugins |
| Packaged touch-browser tests | 2 passed (23.0s): CSP, navigation, slider and chart taps, approvals, secondary pages, 360px screen, landscape and safe-area padding |
| Git whitespace check | git diff --check passed; existing remote/history retained; no staged changes, commits or pushes |

The account browser suite uses the running real FastAPI backend and persisted SQLite, not mocked financial responses. Backend tests use isolated SQLite databases. PostgreSQL is configured but was not executed. Synthetic test accounts were used.

The native asset suite runs Chrome with touch enabled; it is not an Android emulator and does not verify native plugin execution. An outdated connection-message assertion initially failed after copy changes; the assertion was updated and both tests passed on rerun.

## Android build blocked

`npm run android:apk` was attempted again and exited 1 at its prerequisite check, before Gradle compilation:

- Node 24.21.0 and bundled Gradle wrapper found.
- Android Studio and the SDK directory are now detected.
- Selected Java/compiler 26 is incompatible; JAVA_HOME is unset. Use JDK 21.
- SDK Platform 36, Build-Tools 35.0.0+ and platform-tools/adb are missing.

**No APK was generated.** Native compiler, device installation, instrumentation, Back behavior, file picker, save/share, lifecycle and actual system-bar handling remain unverified. Follow ANDROID.md and ANDROID_DEVICE_CHECKLIST.md after installing prerequisites.

## Remaining validation and deployment work

PostgreSQL runtime and migrations, deployed HTTPS/CORS connectivity, real Android account flows and production authentication hardening remain unverified. The frontend runtime audit earlier reported zero vulnerabilities; the full development audit reported three moderate findings through Capacitor CLI/xcode/uuid. No forced dependency overrides were applied. This is a hackathon implementation using deterministic financial estimates and fictional banking adapters.
