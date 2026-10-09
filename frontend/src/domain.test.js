import test from 'node:test';
import assert from 'node:assert/strict';
import { initialState, metrics, forecast, emptyScenario, goalPlan, parseCSV, normalize, mergeTransactions, bankSamples, recommendations, inr } from './domain.js';
test('Forecast counts salary once, each bill once and uses integer paise', () => {
  const s = initialState(); s.transactions = [];
  const points = forecast(s);
  assert.equal(points[22].balance, s.balance - 180000 - 79900 - 64900);
  assert.equal(points[23].balance, points[22].balance + s.salary);
  assert.equal(points[24].balance, points[23].balance - 900000);
  assert.ok(points.every(p => Number.isInteger(p.balance)));
});
test('Emergency and delayed salary affect forecast without mutating history', () => {
  const s = initialState(); const before = JSON.stringify(s);
  const base = metrics(s); const emergency = metrics(s, { ...emptyScenario, emergency: 10000 });
  assert.equal(base.end - emergency.end, 1000000);
  assert.equal(metrics(s, { ...emptyScenario, salaryDelay: 10 }).end, base.end - s.salary);
  assert.equal(JSON.stringify(s), before);
});
test('Savings constraints preserve emergency reserve and shared goal capacity', () => {
  const s = initialState(); s.balance = 10000;
  assert.equal(metrics(s).safe, 0); assert.equal(goalPlan(s, s.goals[0]).allocation, 0);
  const healthy = initialState(); healthy.goals.push({ ...healthy.goals[0], id: 'second', priority: 'Normal' });
  assert.ok(healthy.goals.reduce((n, g) => n + goalPlan(healthy, g).allocation, 0) <= metrics(healthy).capacity);
});
test('Approved plans improve only optimized forecast; rejected plans do nothing', () => {
  const s = initialState(); const base = metrics(s).end;
  s.decisions.subscription = { status: 'accepted', amount: 64900 };
  assert.equal(metrics(s).end, base); assert.equal(metrics(s, emptyScenario, true).end - base, 64900);
  s.decisions.subscription.status = 'rejected'; assert.equal(metrics(s, emptyScenario, true).end, base);
  assert.ok(recommendations(s).every(r => r.amount > 0));
});
test('All three bank schemas normalize and exact duplicates are excluded', () => {
  const rows = Object.entries(bankSamples).flatMap(([name, rows]) => rows.map(r => normalize(r, name)));
  assert.equal(rows.length, 3); assert.equal(rows[2].amount, 28000);
  assert.equal(mergeTransactions(rows, rows).duplicates, 3);
});
test('CSV supports quoted merchants, rejects invalid dates, amounts and malformed rows', () => {
  const rows = parseCSV('date,merchant,amount,direction\r\n2026-10-08,"Cafe, Pune",125.50,debit');
  assert.equal(rows[0].amount, 12550); assert.equal(rows[0].category, 'Uncategorized');
  for (const date of ['2026-02-30', '2026-13-01', 'tomorrow']) assert.throws(() => normalize({ date, merchant: 'Shop', amount: 12, direction: 'debit' }));
  assert.throws(() => parseCSV('date,merchant,amount,direction\n2026-10-08,Shop,-12,debit'));
  assert.throws(() => parseCSV('date,merchant,amount,direction\n2026-10-08,Shop,12,debit,extra'));
});
test('Health score stays between 0 and 100, budgets never negative', () => {
  for (const balance of [0, 10000, 2485000, 100000000]) { const m = metrics({ ...initialState(), balance }); assert.ok(m.score >= 0 && m.score <= 100); assert.ok(m.safe >= 0 && m.daily >= 0); }
});
test('Safe-to-spend includes spending after day 30 before a delayed payday', () => {
  const s = initialState();
  const delayed = metrics(s, { ...emptyScenario, salaryDelay: 15 });
  const extended = forecast(s, { ...emptyScenario, salaryDelay: 15 }, false, 37);
  assert.equal(delayed.safe, Math.max(0, Math.min(...extended.map(p => p.balance)) - s.reserve));
  assert.equal(delayed.points.length, 31);
});
test('Display preserves paise and proposed food reduction totals the exact approved amount', () => {
  assert.equal(inr(12550), '₹125.5');
  const s = initialState(); s.decisions.food = { status: 'accepted', amount: 100001 };
  assert.equal(metrics(s, emptyScenario, true).end - metrics(s).end, 100001);
});
