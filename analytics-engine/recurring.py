"""Confirmed recurrence: pure calendar expansion, conservative matching and suggestions.

Expected occurrences are views, never ledger entries. All changes are explicit API actions.
"""
from calendar import monthrange
from collections import defaultdict
from datetime import date, timedelta
from statistics import median
import hashlib
import re


def key(name):
    return re.sub(r'[^a-z0-9]', '', name.lower())


def cadence(schedule):
    return {'weekly': (1, 'weeks'), 'monthly': (1, 'months'), 'yearly': (1, 'years')}.get(schedule['frequency'], (schedule['interval'], schedule['unit']))


def due_at(schedule, index):
    anchor = date.fromisoformat(schedule['expectedDate'])
    interval, unit = cadence(schedule)
    n = interval * index
    if unit in ('days', 'weeks'):
        return anchor + timedelta(days=n * (7 if unit == 'weeks' else 1))
    months = anchor.year * 12 + anchor.month - 1 + n * (12 if unit == 'years' else 1)
    year, zero_month = divmod(months, 12)
    return date(year, zero_month + 1, min(anchor.day, monthrange(year, zero_month + 1)[1]))


def nominal_dates(schedule, start, end):
    anchor = date.fromisoformat(schedule['expectedDate'])
    limit = min(end, date.fromisoformat(schedule['endDate']) if schedule.get('endDate') else end)
    interval, unit = cadence(schedule)
    distance = (start - anchor).days // (interval * (7 if unit == 'weeks' else 1)) if unit in ('days', 'weeks') else ((start.year-anchor.year)*12+start.month-anchor.month) // (interval*(12 if unit == 'years' else 1))
    index = max(0, distance - 1)
    while True:
        try: due = due_at(schedule, index)
        except (ValueError, OverflowError): return
        if due > limit: return
        if due >= start: yield due
        index += 1


def expand(state, start, end):
    result = []
    for schedule in state.get('schedules', []):
        dates = set(nominal_dates(schedule, start, end))
        # Include postponed payments moved in from another month, without changing their identity.
        prefix = schedule['id'] + '@'
        for occurrence_id, event in state.get('occurrences', {}).items():
            if occurrence_id.startswith(prefix) and event.get('postponedTo'):
                if start <= date.fromisoformat(event['postponedTo']) <= end:
                    dates.add(date.fromisoformat(occurrence_id[len(prefix):]))
        for nominal in sorted(dates):
            occurrence_id = prefix + nominal.isoformat()
            event = state.get('occurrences', {}).get(occurrence_id, {})
            if not schedule['active'] and not event: continue
            due = date.fromisoformat(event.get('postponedTo') or nominal.isoformat())
            if not start <= due <= end: continue
            tx = next((t for t in state['transactions'] if t['id'] == event.get('transactionId')), None)
            result.append({'id': occurrence_id, 'scheduleId': schedule['id'], 'name': schedule['name'], 'amount': schedule['amount'], 'actualAmount': tx['amount'] if tx else None, 'direction': schedule['direction'], 'category': schedule['category'], 'variable': schedule['variable'], 'nominalDate': nominal.isoformat(), 'dueDate': due.isoformat(), 'status': event.get('status', 'expected'), 'transactionId': event.get('transactionId'), 'active': schedule['active']})
    return sorted(result, key=lambda row: (row['dueDate'], row['name'], row['id']))


def matches(tx, occurrence):
    tolerance = max(100, occurrence['amount'] * .3) if occurrence['variable'] else 0
    return (key(tx['merchant']) == key(occurrence['name']) and tx['direction'] == occurrence['direction'] and abs(tx['amount'] - occurrence['amount']) <= tolerance and abs((date.fromisoformat(tx['date']) - date.fromisoformat(occurrence['dueDate'])).days) <= 3)


def reconcile(state):
    linked = {e.get('transactionId') for e in state.get('occurrences', {}).values() if e.get('status') == 'paid'}
    candidates = {}
    for tx in state['transactions']:
        if tx['id'] in linked: continue
        day = date.fromisoformat(tx['date'])
        rows = [o for o in expand(state, day-timedelta(days=3), day+timedelta(days=3)) if o['active'] and o['status'] in ('expected', 'postponed') and matches(tx, o)]
        if len(rows) == 1: candidates[tx['id']] = rows[0]
    counts = defaultdict(int)
    for row in candidates.values(): counts[row['id']] += 1
    for tx_id, row in candidates.items():
        if counts[row['id']] == 1:
            old = state['occurrences'].get(row['id'], {})
            state['occurrences'][row['id']] = {**old, 'status': 'paid', 'transactionId': tx_id}


def patterns(state, today=None):
    today = today or date.today()
    groups = defaultdict(list)
    tracked = {(key(s['name']), s['direction']) for s in state.get('schedules', [])}
    for tx in state['transactions']:
        groups[(key(tx['merchant']), tx['direction'])].append(tx)
    result = []
    for merchant, rows in groups.items():
        if merchant in tracked: continue
        # Same-day duplicate records are not recurrence evidence.
        unique = {t['date']: t for t in rows}
        rows = sorted(unique.values(), key=lambda t: t['date'])
        if len(rows) < 2: continue
        rows = rows[-8:]
        gaps = [(date.fromisoformat(b['date']) - date.fromisoformat(a['date'])).days for a,b in zip(rows, rows[1:])]
        frequency = 'weekly' if len(rows) >= 3 and all(5 <= n <= 9 for n in gaps) else 'monthly' if all(26 <= n <= 35 for n in gaps) else 'yearly' if all(360 <= n <= 370 for n in gaps) else None
        if not frequency: continue
        latest = rows[-1]
        if (date.fromisoformat(state['asOf']) - date.fromisoformat(latest['date'])).days > {'weekly':21, 'monthly':70, 'yearly':400}[frequency]: continue
        typical = int(median(t['amount'] for t in rows))
        if any(abs(t['amount']-typical) > typical * .5 for t in rows): continue
        pattern_id = hashlib.sha256('|'.join(merchant).encode()).hexdigest()[:20]
        fingerprint = f'{frequency}:{typical}'
        decision = state.get('patternDecisions', {}).get(pattern_id)
        if decision:
            old_frequency, old_amount = decision['fingerprint'].split(':')
            material = old_frequency != frequency or abs(typical-int(old_amount)) > int(old_amount)*.25
            if not material and (decision['status'] in ('accepted','declined') or (decision.get('remindOn') and today < date.fromisoformat(decision['remindOn']))): continue
        result.append({'id':pattern_id, 'fingerprint':fingerprint, 'name':latest['merchant'], 'amount':latest['amount'], 'category':latest['category'], 'direction':latest['direction'], 'frequency':frequency, 'variable':len({t['amount'] for t in rows}) > 1, 'startDate':rows[0]['date'], 'expectedDate':rows[0]['date'], 'evidenceCount':len(rows), 'evidenceDates':[t['date'] for t in rows]})
    return result


def month_view(state, month):
    first = date.fromisoformat(month + '-01')
    last = first.replace(day=monthrange(first.year, first.month)[1])
    occurrences = expand(state, first, last)
    actual = [t for t in state['transactions'] if t['date'][:7] == month]
    pending = [o for o in occurrences if o['active'] and o['status'] in ('expected','postponed')]
    totals = {name:sum(t['amount'] for t in actual if t['direction'] == direction) for name,direction in [('actualIncome','credit'),('actualExpenses','debit')]}
    totals.update({name:sum(o['amount'] for o in pending if o['direction'] == direction) for name,direction in [('expectedIncome','credit'),('expectedExpenses','debit')]})
    totals['plannedExpenses'] = totals['actualExpenses'] + totals['expectedExpenses']
    return {'month':month, 'occurrences':occurrences, 'totals':totals, 'suggestions':patterns(state)}
