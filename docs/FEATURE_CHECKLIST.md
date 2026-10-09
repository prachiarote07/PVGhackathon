# Feature status — 9 October 2026

| Feature | Current implementation | Remaining limits |
| --- | --- | --- |
| Signup/login | Password hashes, sessions, logout, owner checks | Recovery, verification, MFA |
| Dashboard | Saved-account Python metrics and charts | Forecast estimates depend on input quality |
| Transactions | CSV, sample banks, duplicates, manual categories | Real banks and Excel pending |
| Forecasting | 7/15/30-day views, inferred and explicit bills | Rule based, not trained AI |
| Money Autopilot | Evidence, confirmation, modify/reject/undo | Proposed plans; no fund movement |
| What-If | Account-based spending, delay and savings simulations | Assumptions shown; not advice guarantees |
| Savings goals | Persisted priorities and shared capacity | Repeats current capacity as estimate |
| Recommendations | Python rules with explanations | Limited rule set |
| Smart alerts / leaks | Fees, duplicates, unusual payments, rising bills, cash risk | No external notifications or ML |
| Financial health | Derived components and disclosed score | Heuristic score |
| Privacy | Consent, export, financial deletion, sample reset | Login retained; no app-level storage encryption |
| How It Works | Existing educational flow retained | Educational examples are synthetic |
| Mobile / Android | Responsive UI, touch controls, Capacitor shell | APK/device tests blocked by prerequisites |
| Database | Verified SQLite persistence; PostgreSQL configuration | PostgreSQL runtime/migrations unverified |

Read TEST_RESULTS.md for checks actually executed. No commit or push has been performed.

## 10 October update

Smart recurring transactions now support explicit confirmation, weekly/monthly/yearly/custom dates, fixed/variable estimates, optional ending dates, paid/skipped/postponed status, import reconciliation, persistence, remembered suggestions and month navigation. Manual transactions are supported. The white/teal UI refresh includes an informational public homepage, account screens, profile/settings and responsive forms. See RECURRING_TRANSACTIONS.md and the latest TEST_RESULTS entry.
