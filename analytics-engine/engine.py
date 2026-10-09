"""Deterministic, explainable money calculations from the saved account state.

All money is integer paise. No network, database, or financial action side effects.
"""
from calendar import monthrange
from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP
import hashlib
import math
import re
import importlib.util
from pathlib import Path

_spec = importlib.util.spec_from_file_location("moneyfy_recurrence", Path(__file__).with_name("recurring.py"))
recurrence = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(recurrence)

def rounded(value):
    return int(Decimal(str(value)).quantize(Decimal('1'), rounding=ROUND_HALF_UP))

def rupees(amount):
    return f'₹{amount / 100:,.2f}'

def merchant_key(value):
    return re.sub(r'[^a-z0-9]', '', value.lower().replace('upi', ''))

def next_month_day(as_of, day):
    year, month = as_of.year, as_of.month
    candidate = date(year, month, min(day, monthrange(year, month)[1]))
    if candidate <= as_of:
        month = month % 12 + 1
        year += month == 1
        candidate = date(year, month, min(day, monthrange(year, month)[1]))
    return candidate

def source_data(state):
    today = date.fromisoformat(state['asOf'])
    cutoff = today - timedelta(days=59)
    history = [t for t in state['transactions'] if cutoff <= date.fromisoformat(t['date']) <= today and t['direction'] == 'debit']
    span = max(1, min(60, (today - min([date.fromisoformat(t['date']) for t in history], default=today)).days + 1))
    tracked = {(merchant_key(s['name']), s['direction']) for s in state.get('schedules', [])}
    everyday = [t for t in history if t['category'] not in ['Housing', 'Bills', 'Subscriptions'] and (merchant_key(t['merchant']), t['direction']) not in tracked]
    food = sum(t['amount'] for t in everyday if t['category'] == 'Food')
    other = sum(t['amount'] for t in everyday if t['category'] != 'Food')
    groups = defaultdict(list)
    for t in state['transactions']:
        if t['direction'] == 'debit' and t['category'] in ['Housing', 'Bills', 'Subscriptions']:
            groups[merchant_key(t['merchant'])].append(t)
    explicit = [dict(b, day=(date.fromisoformat(b['dueDate']) - today).days, source='Scheduled by you') for b in state['bills'] if date.fromisoformat(b['dueDate']) > today]
    explicit_names = {merchant_key(b['name']) for b in explicit}
    recurring = []
    for key, rows in groups.items():
        rows.sort(key=lambda t: t['date'])
        latest = rows[-1]
        if len({t['date'][:7] for t in rows}) < 2 or (today - date.fromisoformat(latest['date'])).days > 62:
            continue
        due = next_month_day(today, date.fromisoformat(latest['date']).day)
        identifier = 'recurring-' + hashlib.sha256(key.encode()).hexdigest()[:12]
        recurring.append({'id': identifier, 'name': latest['merchant'], 'amount': latest['amount'], 'dueDate': due.isoformat(), 'day': (due - today).days, 'category': latest['category'], 'source': f'Estimated from {len(rows)} recorded charges', 'previous': rows[-2]['amount']})
    confirmed = [dict(o, day=(date.fromisoformat(o['dueDate'])-today).days, source='Confirmed recurring schedule') for o in recurrence.expand(state, today + timedelta(days=1), today + timedelta(days=150)) if o['active'] and o['status'] in ('expected', 'postponed')]
    # A matching confirmed schedule replaces a legacy one-off estimate, never adds twice.
    bills = [b for b in explicit if not any(merchant_key(b['name']) == merchant_key(o['name']) and abs((date.fromisoformat(b['dueDate'])-date.fromisoformat(o['dueDate'])).days) <= 3 for o in confirmed)] + [o for o in confirmed if o['direction'] == 'debit']
    weekly = [0] * max(1, math.ceil(span / 7))
    for t in everyday:
        bucket = min(len(weekly) - 1, (today - date.fromisoformat(t['date'])).days // 7)
        weekly[bucket] += t['amount']
    mean = sum(weekly) / len(weekly)
    variation = (sum(abs(x - mean) for x in weekly) / len(weekly) / mean) if mean else 1
    return {'foodDaily': rounded(food / span), 'essentialDaily': rounded(other / span), 'sampleDays': span, 'sampleCount': len(history), 'bills': sorted(bills, key=lambda b: b['day']), 'recurring': recurring, 'income': [o for o in confirmed if o['direction'] == 'credit'], 'hasSalarySchedule': any(s['active'] and s['direction'] == 'credit' and s['category'] == 'Income' for s in state.get('schedules', [])), 'consistency': rounded(max(0, 1 - variation) * 15)}

def recommend(state, data):
    food_impact = rounded(data['foodDaily'] * 30 * .2)
    recs = []
    if food_impact:
        recs.append({'id': 'food', 'title': 'Make room in everyday spending', 'issue': 'Your recorded food spending is an opportunity to review.', 'amount': food_impact, 'priority': 'Opportunity', 'action': 'Try a 20% smaller food budget', 'evidence': f"{rupees(data['foodDaily'])} per day across {data['sampleDays']} recorded calendar days × 30 × 20% = {rupees(food_impact)}.", 'uncertainty': 'Recent spending is assumed to continue. Missing history can understate or overstate this estimate.'})
    for bill in data['recurring']:
        if bill['category'] != 'Subscriptions': continue
        recs.append({'id': bill['id'], 'title': f"Review {bill['name']}", 'issue': 'This merchant has charges in at least two distinct months.', 'amount': bill['amount'], 'priority': 'Review', 'action': 'Review whether you still need this subscription', 'evidence': f"Latest charge {rupees(bill['amount'])}; if it repeats monthly, avoiding 12 future payments could retain {rupees(bill['amount'] * 12)}.", 'uncertainty': 'Monthly recurrence is inferred, not guaranteed. You must change the service yourself; accepting only updates a proposed plan.'})
    return recs

def projection(state, scenario, optimized, days, data, recs):
    today = date.fromisoformat(state['asOf'])
    payday = (date.fromisoformat(state['nextPayday']) - today).days + scenario.get('salaryDelay', 0)
    cuts = {}
    for rec in recs:
        decision = state['decisions'].get(rec['id'], {})
        if optimized and decision.get('status') == 'accepted': cuts[rec['id']] = min(decision['amount'], rec['amount'])
    daily_food = rounded(Decimal(data['foodDaily']) * (Decimal(1) - Decimal(str(scenario.get('foodReduction', 0))) / 100))
    balance = state['balance']
    scheduled = defaultdict(list)
    for bill in data['bills']:
        scheduled[bill['day']].append(bill)
    points = [{'date': state['asOf'], 'balance': balance}]
    for day in range(1, days + 1):
        balance -= daily_food + data['essentialDaily']
        food_cut = rounded(cuts.get('food', 0) * day / 30) - rounded(cuts.get('food', 0) * (day - 1) / 30)
        balance += min(daily_food, food_cut)
        for bill in scheduled[day]:
            rec_id = 'recurring-' + hashlib.sha256(merchant_key(bill['name']).encode()).hexdigest()[:12]
            balance -= max(0, bill['amount'] - cuts.get(rec_id, 0))
        for income in data.get('income', []):
            delay = scenario.get('salaryDelay', 0) if income['category'] == 'Income' else 0
            if day == income['day'] + delay: balance += income['amount']
        if day == payday and not data.get('hasSalarySchedule'): balance += state['salary']
        if day == 1: balance -= sum(rounded(Decimal(str(scenario.get(key, 0))) * 100) for key in ['shopping', 'purchase', 'emergency', 'savings'])
        points.append({'date': (today + timedelta(days=day)).isoformat(), 'balance': balance})
    return points, payday

def metrics(state, scenario=None, optimized=False, data=None, recs=None):
    scenario = scenario or {}
    data = data or source_data(state)
    recs = recs if recs is not None else recommend(state, data)
    payday = (date.fromisoformat(state['nextPayday']) - date.fromisoformat(state['asOf'])).days + scenario.get('salaryDelay', 0)
    all_points, _ = projection(state, scenario, optimized, max(30, payday - 1), data, recs)
    points = all_points[:31]
    low = min(p['balance'] for p in points)
    safe = max(0, min(p['balance'] for p in all_points[:payday]) - state['reserve'])
    progress = sum(min(1, g['saved'] / g['target']) for g in state['goals']) / max(1, len(state['goals']))
    coverage = min(1, max(0, low) / max(1, state['reserve']))
    components = {'Positive cash flow': 25 if low >= 0 else 0, 'Emergency buffer': rounded(coverage * 25), 'Upcoming obligations': rounded(coverage * 20), 'Spending consistency': data['consistency'], 'Goal progress': rounded(progress * 15)}
    return {'points': points, 'end': points[-1]['balance'], 'low': low, 'safe': safe, 'daily': safe // payday, 'capacity': max(0, min(safe, points[-1]['balance'] - state['reserve'])), 'score': sum(components.values()), 'components': components, 'payday': payday}

def goal_plan(state, goal, scenario, result):
    weight = 2 if goal['priority'] == 'High' else 1
    total = sum(2 if g['priority'] == 'High' else 1 for g in state['goals']) or 1
    # Additional savings is a one-time proposed contribution, shared by priority.
    contribution = rounded(scenario.get('savings', 0) * 100) * weight // total
    remaining = max(0, goal['target'] + rounded(scenario.get('goalChange', 0) * 100) - goal['saved'] - contribution)
    days = (date.fromisoformat(goal['deadline']) - date.fromisoformat(state['asOf'])).days
    months = max(1, math.ceil(days / 30))
    allocation = result['capacity'] * weight // total
    return {'remaining': remaining, 'required': math.ceil(remaining / months), 'allocation': allocation, 'months': 0 if remaining == 0 else math.ceil(remaining / allocation) if allocation else None, 'feasible': remaining == 0 or (days >= 0 and allocation * months >= remaining)}

def analyze(state, scenario=None):
    scenario = scenario or {}
    data = source_data(state)
    recs = recommend(state, data)
    baseline = metrics(state, {}, False, data, recs)
    optimized = metrics(state, {}, True, data, recs)
    simulated = metrics(state, scenario, False, data, recs)
    goal_sets = {name: {g['id']: goal_plan(state, g, scenario if name == 'simulated' else {}, result) for g in state['goals']} for name, result in [('baseline', baseline), ('optimized', optimized), ('simulated', simulated)]}
    return {'baseline': baseline, 'optimized': optimized, 'simulated': simulated, 'recommendations': recs, 'goals': goal_sets, 'assumptions': data, 'asOf': state['asOf']}
