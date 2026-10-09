// Frontend reference model. All stored monetary amounts are integer paise.
export const TODAY = '2026-10-09';
export const inr = (paise) => new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', minimumFractionDigits: 0, maximumFractionDigits: 2 }).format(paise / 100);
export const dateAt = (days) => { const d = new Date(`${TODAY}T12:00:00Z`); d.setUTCDate(d.getUTCDate() + days); return d.toISOString().slice(0, 10); };
export const daysBetween = (a, b) => Math.ceil((new Date(`${b}T12:00:00Z`) - new Date(`${a}T12:00:00Z`)) / 86400000);
export const emptyScenario = { foodReduction: 0, shopping: 0, purchase: 0, salaryDelay: 0, emergency: 0, savings: 0, goalChange: 0 };
export const bills = [{ name: 'Electricity', amount: 180000, day: 6 }, { name: 'Broadband', amount: 79900, day: 11 }, { name: 'Netflix', amount: 64900, day: 14 }, { name: 'Rent', amount: 900000, day: 24 }];
export function demoTransactions() {
  const rows = [];
  for (const month of ['08', '09', '10']) {
    const end = month === '10' ? 9 : 28;
    rows.push({ id: `${month}-salary`, date: `2026-${month}-01`, merchant: 'Acme Studio · Salary', amount: 3000000, direction: 'credit', category: 'Income', bank: 'Demo account' });
    rows.push({ id: `${month}-rent`, date: `2026-${month}-02`, merchant: 'UPI · Rent', amount: 900000, direction: 'debit', category: 'Housing', bank: 'Demo account' });
    for (let day = 3; day <= end; day += 3) rows.push({ id: `${month}-food-${day}`, date: `2026-${month}-${String(day).padStart(2, '0')}`, merchant: day % 2 ? 'Swiggy' : 'FreshMart', amount: 60000, direction: 'debit', category: 'Food', bank: 'Demo account' });
    rows.push({ id: `${month}-metro`, date: `2026-${month}-05`, merchant: 'Metro · UPI', amount: 180000, direction: 'debit', category: 'Transport', bank: 'Demo account' });
    if (month !== '10') rows.push({ id: `${month}-netflix`, date: `2026-${month}-23`, merchant: 'Netflix', amount: 64900, direction: 'debit', category: 'Subscriptions', bank: 'Demo account' });
  }
  rows.push({ id: 'fee', date: '2026-10-07', merchant: 'Account service fee', amount: 19900, direction: 'debit', category: 'Fees', bank: 'Demo account' });
  return rows.sort((a, b) => b.date.localeCompare(a.date));
}
export const initialState = () => ({ transactions: demoTransactions(), balance: 2485000, reserve: 500000, salary: 3000000, consent: false, connections: [], imports: [], decisions: {}, alerts: {}, goals: [{ id: 'emergency', name: 'Emergency cushion', target: 6000000, saved: 1800000, deadline: '2027-06-01', priority: 'High' }], theme: 'light' });
export function assumptions(state) {
  const history = state.transactions.filter(t => t.direction === 'debit' && t.date >= '2026-08-01' && t.date <= '2026-09-30');
  const food = history.filter(t => t.category === 'Food').reduce((s, t) => s + t.amount, 0);
  const transport = history.filter(t => t.category === 'Transport').reduce((s, t) => s + t.amount, 0);
  return { foodDaily: Math.round(food / 61), essentialDaily: Math.round(transport / 61), sampleDays: 61 };
}
export function forecast(state, scenario = emptyScenario, optimized = false, days = 30) {
  const { foodDaily, essentialDaily } = assumptions(state);
  let balance = state.balance;
  const foodCut = Math.min(100, Math.max(0, Number(scenario.foodReduction) || 0));
  const acceptedFood = optimized && state.decisions.food?.status === 'accepted' ? state.decisions.food.amount : 0;
  const acceptedSubscription = optimized && state.decisions.subscription?.status === 'accepted' ? state.decisions.subscription.amount : 0;
  const points = [{ date: TODAY, balance }];
  for (let day = 1; day <= days; day++) {
    balance -= Math.round(foodDaily * (1 - foodCut / 100)) + essentialDaily;
    const dailyReduction = Math.round(acceptedFood * day / 30) - Math.round(acceptedFood * (day - 1) / 30);
    balance += Math.min(dailyReduction, Math.round(foodDaily * (1 - foodCut / 100)));
    for (const bill of bills.filter(b => b.day === day)) balance -= Math.max(0, bill.amount - (bill.name === 'Netflix' ? acceptedSubscription : 0));
    if (day === 23 + Number(scenario.salaryDelay || 0)) balance += state.salary;
    if (day === 1) balance -= Math.round((Number(scenario.shopping || 0) + Number(scenario.purchase || 0) + Number(scenario.emergency || 0) + Number(scenario.savings || 0)) * 100);
    points.push({ date: dateAt(day), balance: Math.round(balance) });
  }
  return points;
}
export function metrics(state, scenario = emptyScenario, optimized = false) {
  const points = forecast(state, scenario, optimized);
  const low = Math.min(...points.map(p => p.balance));
  const payday = 23 + Number(scenario.salaryDelay || 0);
  const beforePay = forecast(state, scenario, optimized, Math.max(30, payday - 1)).filter((_, i) => i < payday);
  const safe = Math.max(0, Math.min(...beforePay.map(p => p.balance)) - state.reserve);
  const goalProgress = state.goals.length ? state.goals.reduce((s, g) => s + Math.min(1, g.saved / g.target), 0) / state.goals.length : 0;
  const a = assumptions(state);
  const components = { 'Positive cash flow': low >= 0 ? 25 : 0, 'Emergency buffer': Math.round(Math.min(1, Math.max(0, low) / Math.max(1, state.reserve)) * 25), 'Upcoming obligations': low >= state.reserve ? 20 : Math.round(Math.max(0, low) / Math.max(1, state.reserve) * 20), 'Spending consistency': Math.round(Math.max(0, 1 - Math.abs(a.foodDaily * 30 - 540000) / 540000) * 15), 'Goal progress': Math.round(goalProgress * 15) };
  return { points, end: points.at(-1).balance, low, safe, daily: Math.floor(safe / payday), capacity: Math.max(0, Math.min(safe, points.at(-1).balance - state.reserve)), score: Object.values(components).reduce((s, n) => s + n, 0), components, payday };
}
export function recommendations(state) {
  const a = assumptions(state);
  const foodImpact = Math.round(a.foodDaily * 30 * .2);
  const hasNetflix = state.transactions.some(t => t.merchant.toLowerCase().includes('netflix'));
  return [ ...(foodImpact > 0 ? [{ id: 'food', title: 'Make room in your everyday spending', issue: 'Food spending leaves less room for your savings goal.', amount: foodImpact, priority: 'Opportunity', action: 'Try a 20% smaller food budget', evidence: `${inr(a.foodDaily)} per day across the 61-day reference period × 30 days × 20% = ${inr(foodImpact)}.`, uncertainty: 'Assumes your recent food spending continues. The change is a proposed budget, not a guarantee.' }] : []), ...(hasNetflix ? [{ id: 'subscription', title: 'Give your subscriptions a second look', issue: 'Netflix appears in both August and September.', amount: 64900, priority: 'Review', action: 'Review the ₹649 monthly subscription', evidence: 'Two monthly Netflix payments of ₹649. One avoided payment could retain ₹649; 12 avoided payments could retain ₹7,788.', uncertainty: 'We cannot know whether you use this service. You must cancel it yourself before savings occur.' }] : []) ];
}
export function goalPlan(state, goal, scenario = emptyScenario, optimized = false) {
  const remaining = Math.max(0, goal.target + Number(scenario.goalChange || 0) * 100 - goal.saved);
  const months = Math.max(1, Math.ceil(daysBetween(TODAY, goal.deadline) / 30));
  const capacity = metrics(state, scenario, optimized).capacity;
  const totalWeight = state.goals.reduce((s, g) => s + (g.priority === 'High' ? 2 : 1), 0) || 1;
  const allocation = Math.floor(capacity * (goal.priority === 'High' ? 2 : 1) / totalWeight);
  return { remaining, required: Math.ceil(remaining / months), allocation, months: remaining === 0 ? 0 : allocation ? Math.ceil(remaining / allocation) : null, feasible: remaining === 0 || (goal.deadline >= TODAY && allocation * months >= remaining) };
}
export function categorize(merchant) {
  const m = merchant.toLowerCase();
  if (/salary|payroll/.test(m)) return 'Income';
  if (/swiggy|zomato|freshmart|food|grocery/.test(m)) return 'Food';
  if (/rent/.test(m)) return 'Housing';
  if (/metro|uber|transport/.test(m)) return 'Transport';
  if (/netflix|spotify/.test(m)) return 'Subscriptions';
  if (/fee|charge/.test(m)) return 'Fees';
  if (/electric|broadband|utility/.test(m)) return 'Bills';
  return 'Uncategorized';
}
export function normalize(row, bank = 'CSV') {
  const date = String(row.date || row.transactionDate || row.booked_on || '');
  const merchant = String(row.merchant || row.description || row.payee || '').trim();
  const raw = Number(row.amount ?? row.value ?? row.amount_paise / 100);
  const direction = row.direction || (row.type === 'CR' ? 'credit' : row.type === 'DR' ? 'debit' : row.flow === 'in' ? 'credit' : row.flow === 'out' ? 'debit' : '');
  if (!/^\d{4}-\d{2}-\d{2}$/.test(date) || Number.isNaN(Date.parse(date)) || new Date(`${date}T12:00:00Z`).toISOString().slice(0, 10) !== date || date > TODAY || !merchant || !Number.isFinite(raw) || raw <= 0 || !['debit', 'credit'].includes(direction) || raw > 1e9) throw new Error('Each row needs a valid past ISO date, merchant, positive INR amount and debit/credit direction. Demo date: 9 Oct 2026.');
  return { id: `${bank}-${date}-${merchant}-${Math.round(raw * 100)}-${direction}`, date, merchant, amount: Math.round(raw * 100), direction, category: categorize(merchant), bank };
}
export function mergeTransactions(existing, incoming) {
  const key = t => `${t.date}|${t.merchant.toLowerCase()}|${t.amount}|${t.direction}`;
  const seen = new Set(existing.map(key));
  let duplicates = 0;
  const added = incoming.filter(t => { if (seen.has(key(t))) { duplicates++; return false; } seen.add(key(t)); return true; });
  return { transactions: [...existing, ...added].sort((a, b) => b.date.localeCompare(a.date)), duplicates, count: added.length };
}
export function parseCSV(text) {
  // Handles quoted fields, escaped quotes, BOM, CRLF and commas in descriptions.
  const rows = []; let row = [], field = '', quoted = false;
  const source = text.replace(/^\uFEFF/, '').replace(/\r\n/g, '\n');
  for (let i = 0; i < source.length; i++) {
    const c = source[i];
    if (c === '"') { if (quoted && source[i + 1] === '"') { field += '"'; i++; } else quoted = !quoted; }
    else if (c === ',' && !quoted) { row.push(field.trim()); field = ''; }
    else if (c === '\n' && !quoted) { row.push(field.trim()); if (row.some(Boolean)) rows.push(row); row = []; field = ''; }
    else field += c;
  }
  if (quoted) throw new Error('Unclosed quote in CSV.');
  row.push(field.trim()); if (row.some(Boolean)) rows.push(row);
  const headers = rows.shift()?.map(h => h.toLowerCase());
  if (!headers || !['date', 'merchant', 'amount', 'direction'].every(h => headers.includes(h))) throw new Error('CSV headers must include date, merchant, amount, direction.');
  if (!rows.length) throw new Error('The CSV contains no transactions.');
  return rows.map((r, i) => { if (r.length !== headers.length) throw new Error(`CSV row ${i + 2} has the wrong number of fields.`); return normalize(Object.fromEntries(headers.map((h, n) => [h, r[n]]))); });
}
export const bankSamples = {
  'River Bank': [{ date: '2026-10-08', merchant: 'Zomato UPI', amount: 420, direction: 'debit' }],
  'Lotus Bank': [{ transactionDate: '2026-10-06', description: 'Spotify', value: 119, type: 'DR' }],
  'Summit Bank': [{ booked_on: '2026-10-04', payee: 'Uber UPI', amount_paise: 28000, flow: 'out' }],
};
export function alertsFor(state) {
  const m = metrics(state);
  const alerts = [{ id: 'bill', title: 'Electricity bill on 15 October', priority: 'Upcoming', reason: '₹1,800 is included in your forecast.', action: 'Keep this amount available before the bill date.' }];
  if (m.low < state.reserve) alerts.push({ id: 'buffer', title: 'Your buffer may run low', priority: 'High', reason: `Lowest projected balance: ${inr(m.low)}.`, action: 'Reduce optional spending or test a later purchase.' });
  if (state.transactions.some(t => t.category === 'Fees')) alerts.push({ id: 'fee', title: 'A fee worth checking', priority: 'Review', reason: 'A service fee appears in your transaction history.', action: 'Check the fee with your bank; recurrence is unknown.' });
  for (const goal of state.goals) if (!goalPlan(state, goal).feasible) alerts.push({ id: `goal-${goal.id}`, title: `${goal.name} needs a little more time`, priority: 'Review', reason: 'Estimated allocation is below the amount needed for the deadline.', action: 'Adjust the deadline or target on Savings Goals.' });
  return alerts.map(a => ({ ...a, timestamp: `${TODAY}T09:00:00+05:30` }));
}
