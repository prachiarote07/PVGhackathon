"""Signals derived from account transactions; no automatic financial actions."""
from collections import defaultdict
from statistics import median
import hashlib

def signals(state, analysis):
    output = []
    def add(id, title, reason, action, priority='Review'):
        output.append({'id': id, 'title': title, 'reason': reason, 'action': action, 'priority': priority, 'timestamp': state['asOf'] + 'T09:00:00+05:30'})
    if analysis['baseline']['low'] < state['reserve']:
        add('buffer', 'Your projected buffer may run low', f"Lowest projected balance is ₹{analysis['baseline']['low'] / 100:,.2f}.", 'Review discretionary spending or adjust a planned purchase.', 'High')
    for b in analysis['assumptions']['bills']:
        if 0 < b['day'] <= 14: add('bill-' + b['id'], b['name'] + ' is approaching', f"₹{b['amount'] / 100:,.2f} due {b['dueDate']}; {b['source']}.", 'Keep the amount available before the due date.', 'Upcoming')
    groups = defaultdict(list)
    exact = defaultdict(list)
    for t in state['transactions']:
        if t['direction'] != 'debit': continue
        groups[t['merchant'].lower()].append(t)
        exact[(t['date'], t['merchant'].lower(), t['amount'])].append(t)
    for key, rows in exact.items():
        if len(rows) > 1: add('duplicate-' + hashlib.sha256(str(key).encode()).hexdigest()[:12], 'Possible duplicate payment', f"{rows[0]['merchant']}: {len(rows)} matching charges on {key[0]}.", 'Review the statement. Matching payments can be legitimate.')
    for merchant, rows in groups.items():
        rows.sort(key=lambda t: t['date'])
        if len(rows) >= 4:
            usual = median(t['amount'] for t in rows[:-1])
            if usual > 0 and rows[-1]['amount'] > usual * 2:
                add('unusual-' + rows[-1]['id'], 'Unusual merchant amount', f"{rows[-1]['merchant']}: latest charge ₹{rows[-1]['amount'] / 100:,.2f} exceeds twice the earlier median ₹{usual / 100:,.2f}.", 'Check whether this was an intended purchase.')
    for b in analysis['assumptions']['recurring']:
        if b['category'] == 'Bills' and b['amount'] > b['previous'] * 1.2:
            add('rising-' + b['id'], b['name'] + ' has increased', f"Latest charge rose from ₹{b['previous'] / 100:,.2f} to ₹{b['amount'] / 100:,.2f}.", 'Review usage and the bill; no future annual increase is assumed.')
    fees = [t for t in state['transactions'] if t['category'] == 'Fees' and t['direction'] == 'debit']
    if fees: add('fees', 'Fees worth checking', f"Recorded fees total ₹{sum(t['amount'] for t in fees) / 100:,.2f}.", 'Review the charges. Recurrence is unknown.')
    for goal in state['goals']:
        if not analysis['goals']['baseline'][goal['id']]['feasible']: add('goal-' + goal['id'], goal['name'] + ' needs an adjustment', 'The available allocation is below the deadline requirement.', 'Increase the deadline or reduce the target.')
    return output
