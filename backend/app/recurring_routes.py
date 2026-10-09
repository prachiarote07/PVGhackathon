"""Account-owned recurring schedules and explicit payment actions."""
from datetime import date, timedelta
import uuid
from fastapi import Depends, HTTPException, Query
from sqlalchemy.orm import Session
from .models import Workspace, FinancialState, Schedule, NewSchedule, ManualTransaction, ScheduleStatus, OccurrenceAction, PatternAction


def install_recurring(app, db, current_user, save, recurrence):
    def load(user, session):
        workspace = session.get(Workspace, user.id)
        return FinancialState.model_validate(workspace.data).model_dump(mode='json'), workspace.version

    def add_schedule(state, data):
        schedule = Schedule(**data, id=str(uuid.uuid4())).model_dump(mode='json')
        if any(recurrence.key(s['name']) == recurrence.key(schedule['name']) and s['direction'] == schedule['direction'] for s in state['schedules']):
            raise HTTPException(409, 'This merchant already has a schedule. Use its existing controls.')
        if len(state['schedules']) >= 100: raise HTTPException(422, 'Maximum 100 schedules')
        state['schedules'].append(schedule)
        recurrence.reconcile(state)
        return schedule

    @app.get('/api/v1/recurring')
    def overview(month: str = Query(pattern=r'^(20\d{2}|2100)-(0[1-9]|1[0-2])$'), user=Depends(current_user), session: Session=Depends(db)):
        state, version = load(user, session)
        return dict(recurrence.month_view(state, month), version=version)

    @app.post('/api/v1/recurring', status_code=201)
    def create(body: NewSchedule, user=Depends(current_user), session: Session=Depends(db)):
        state, _ = load(user, session)
        add_schedule(state, body.schedule.model_dump(mode='json'))
        return save(user.id, body.version, state, session)

    @app.patch('/api/v1/recurring/{schedule_id}')
    def toggle(schedule_id: str, body: ScheduleStatus, user=Depends(current_user), session: Session=Depends(db)):
        state, _ = load(user, session)
        schedule = next((s for s in state['schedules'] if s['id'] == schedule_id), None)
        if not schedule: raise HTTPException(404, 'Schedule not found')
        schedule['active'] = body.active
        recurrence.reconcile(state)
        return save(user.id, body.version, state, session)

    @app.post('/api/v1/transactions', status_code=201)
    def manual(body: ManualTransaction, user=Depends(current_user), session: Session=Depends(db)):
        state, _ = load(user, session)
        tx = body.transaction.model_dump(mode='json')
        tx.update(id=str(uuid.uuid4()), bank='Manual payment')
        if tx['date'] > min(state['asOf'], date.today().isoformat()): raise HTTPException(422, 'Actual payments cannot be after today or your balance date. Update the balance snapshot first, or add a future schedule instead.')
        if len(state['transactions']) >= 5000: raise HTTPException(422, 'Maximum 5000 transactions')
        if any(all(t[k] == tx[k] for k in ['date','merchant','amount','direction']) for t in state['transactions']): raise HTTPException(409, 'An identical transaction is already recorded')
        state['transactions'].append(tx)
        if body.schedule:
            if not body.confirmed: raise HTTPException(400, 'Confirm recurring tracking first')
            schedule_data = body.schedule.model_dump(mode='json')
            if not recurrence.matches(tx, dict(schedule_data, dueDate=schedule_data['expectedDate'])): raise HTTPException(422, 'The first recurring payment must match this transaction')
            add_schedule(state, schedule_data)
        recurrence.reconcile(state)
        state['transactions'].sort(key=lambda t:t['date'], reverse=True)
        return save(user.id, body.version, state, session)

    @app.post('/api/v1/recurring/suggestions/{pattern_id}')
    def suggestion(pattern_id: str, body: PatternAction, user=Depends(current_user), session: Session=Depends(db)):
        state, _ = load(user, session)
        pattern = next((p for p in recurrence.patterns(state) if p['id'] == pattern_id), None)
        if not pattern: raise HTTPException(404, 'Suggestion is no longer available. Refresh to see current suggestions.')
        if body.status == 'accepted':
            if not body.confirmed: raise HTTPException(400, 'Confirm before tracking this pattern')
            fields = ['name','amount','category','direction','frequency','variable','startDate','expectedDate']
            add_schedule(state, {k:pattern[k] for k in fields})
        state['patternDecisions'][pattern_id] = {'status':body.status, 'fingerprint':pattern['fingerprint'], 'remindOn':(date.today()+timedelta(days=30)).isoformat() if body.status == 'later' else None}
        return save(user.id, body.version, state, session)

    @app.post('/api/v1/recurring/occurrences/{occurrence_id}')
    def action(occurrence_id: str, body: OccurrenceAction, user=Depends(current_user), session: Session=Depends(db)):
        state, _ = load(user, session)
        try: nominal = date.fromisoformat(occurrence_id.rsplit('@',1)[1])
        except (ValueError, IndexError): raise HTTPException(404, 'Payment occurrence not found')
        event = state['occurrences'].get(occurrence_id, {})
        effective = date.fromisoformat(event.get('postponedTo') or nominal.isoformat())
        occurrence = next((o for o in recurrence.expand(state, effective, effective) if o['id'] == occurrence_id), None)
        if not occurrence: raise HTTPException(404, 'Payment occurrence not found')
        if occurrence['status'] == 'paid': raise HTTPException(409, 'This payment is already linked to an actual transaction')
        if not occurrence['active']: raise HTTPException(409, 'Resume this schedule before changing a payment')
        if body.status == 'paid':
            if body.transactionId:
                tx = next((t for t in state['transactions'] if t['id'] == body.transactionId), None)
                if not tx or tx['direction'] != occurrence['direction']: raise HTTPException(422, 'Choose a recorded transaction with the same direction')
                if any(e.get('transactionId') == tx['id'] for e in state['occurrences'].values()): raise HTTPException(409, 'This transaction is already linked')
            else:
                if not body.paymentDate or not body.amount: raise HTTPException(422, 'Payment date and actual amount are required')
                if body.paymentDate.isoformat() > min(state['asOf'],date.today().isoformat()): raise HTTPException(422, 'Payment date cannot be after today or your balance date')
                if len(state['transactions']) >= 5000: raise HTTPException(422, 'Maximum 5000 transactions')
                tx = {'id':str(uuid.uuid4()), 'merchant':occurrence['name'], 'amount':body.amount, 'date':body.paymentDate.isoformat(), 'direction':occurrence['direction'], 'category':occurrence['category'], 'bank':'Manual payment'}
                if any(recurrence.matches(t, occurrence) for t in state['transactions']): raise HTTPException(409, 'A possible payment already exists. Link a recorded transaction instead.')
                state['transactions'].append(tx)
            state['occurrences'][occurrence_id] = {**event, 'status':'paid', 'transactionId':tx['id']}
        elif body.status == 'postponed':
            if not body.postponedTo or body.postponedTo <= effective or body.postponedTo.year > 2100: raise HTTPException(422, 'Choose a later date, no later than year 2100')
            state['occurrences'][occurrence_id] = {'status':'postponed', 'postponedTo':body.postponedTo.isoformat()}
        elif body.status == 'skipped':
            state['occurrences'][occurrence_id] = {**event, 'status':'skipped'}
        else:
            state['occurrences'].pop(occurrence_id, None)
            recurrence.reconcile(state)
        return save(user.id, body.version, state, session)
