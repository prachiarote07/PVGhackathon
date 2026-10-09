# Confirmed recurring transactions

MoneyFy extends the existing account workspace, FastAPI service and Python analytics. No separate application or ledger was created. Existing workspace JSON loads with empty schedule fields by default; existing transactions and settings are preserved.

## Using the feature

Sign in, open Transactions, and choose **Add transaction** for an actual payment or **Add recurring schedule** for a future commitment. Manual entries ask whether the payment repeats weekly, monthly, yearly, at a custom interval, or only once. Provide a starting date, first expected payment, optional end date and fixed/variable amount. Saving a schedule explicitly confirms tracking.

Dashboard and Transactions have Previous Month, Current Month, Next Month and a month/year picker. Expected occurrences are calculated on demand, including future years, without creating fake transaction rows. An open current-month view advances when the calendar month changes; a manually selected historical month stays selected. The balance forecast remains clearly anchored to the supplied balance snapshot, not the selected browsing month.

Monthly plans show actual income/expenses separately from expected income/expenses. Planned expenses equal actual spending plus unpaid expected expenses. Variable amounts remain estimates. Imported history does not change the supplied account balance.

Each expected occurrence can be marked paid/received, skipped or postponed. Recording payment requires an actual amount and date no later than today or the balance snapshot. Alternatively, explicitly link a recorded transaction. Paid occurrences link to one ledger record. Postponing changes just that occurrence, even across months; skipping does not change later payments. Skipped payments can be restored. Schedules can be paused/resumed.

## Calendar rules

- Weekly: every seven days from the first expected payment.
- Monthly: the original day of month, clamped to the last day in shorter months. January 31 becomes February 28 and then March 31; it does not drift to March 28.
- Yearly: the original month/day, with February 29 clamped in non-leap years and restored in leap years.
- Custom: every 1–365 days, weeks, months or years. End dates are inclusive.
- Supported schedule/browsing dates: 2000–2100. Generated views do not mutate stored data.

## Suggestions and matching

History detection requires distinct recorded dates and consistent gaps: at least two monthly/yearly payments or three weekly payments. Very irregular amounts and stale patterns are excluded. Suggestions display supporting dates and amounts and never create schedules without confirmation.

**Not Recurring** remembers the decision. Another occurrence at a similar price does not prompt again. A cadence change or a median amount change greater than 25% can resurface a pattern. **Remind Me Later** snoozes for 30 calendar days. Confirmed or paused merchant schedules suppress duplicate suggestions.

Automatic matching requires the same normalized merchant and direction, a date within three days, and the same amount for fixed payments. Variable payments permit a 30% amount tolerance (minimum ₹1). Exactly one transaction and one occurrence must match. Ambiguous payments remain unlinked for explicit review.

A bank import can replace a matching manually recorded payment when its amount matches exactly, preserving the occurrence link rather than adding a second expense. Exact duplicate imports are skipped. These are conservative rules, not bank-provided payment identifiers; review ambiguous matches and legitimate identical payments.

## Integration and limitations

Confirmed expected debits feed upcoming bills, alerts and forecasts. Confirmed scheduled income feeds projections; an active Income schedule replaces the supplied salary assumption to avoid double crediting. Tracked everyday-category merchants are excluded from average daily spending so a schedule is not counted twice. Matching one-off bills yield to confirmed recurrence.

Unconfirmed history patterns remain suggestions and evidence for recommendations; they no longer create forecast obligations automatically. Existing paid/imported transactions remain actual records. No real banking action, payment execution, notification service or background task is implied.

Schedules, occurrence exceptions and pattern decisions persist in the existing versioned per-user database workspace. API ownership checks and optimistic version checks apply. Privacy financial-data deletion/reset clears these fields. PostgreSQL configuration is retained; local runtime verification uses SQLite. No APK/device execution is implied by browser checks.

The supplied request ended mid-sentence in the month-progression section. All complete requirements before that point were implemented; no unseen requirements were inferred.
