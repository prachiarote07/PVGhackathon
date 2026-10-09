from datetime import date, timedelta
from fastapi.testclient import TestClient
from app.main import create_app, engine_module
from test_api import register, change


def version(c,h): return c.get('/api/v1/workspace',headers=h).json()['version']
def schedule(c,h,**changes):
    fields={'name':'Rent','amount':800000,'category':'Housing','direction':'debit','frequency':'monthly','startDate':'2026-10-05','expectedDate':'2026-10-05','variable':False}
    fields.update(changes)
    response=c.post('/api/v1/recurring',headers=h,json={'version':version(c,h),'confirmed':True,'schedule':fields})
    assert response.status_code==201,response.text
    return response.json()['state']['schedules'][-1]
def overview(c,h,month='2026-10'):
    response=c.get('/api/v1/recurring',headers=h,params={'month':month})
    assert response.status_code==200,response.text
    return response.json()
def occurrence_action(c,h,oid,status,**values):
    return c.post('/api/v1/recurring/occurrences/'+oid,headers=h,json={'version':version(c,h),'confirmed':True,'status':status,**values})
def setup(c):
    h=register(c)
    change(c,h,asOf='2026-10-09',nextPayday='2026-11-01',balance=2000000,consent=True)
    return h

def test_calendar_clamping_leap_year_custom_and_end_dates(client):
    h=setup(client)
    schedule(client,h,startDate='2026-01-31',expectedDate='2026-01-31')
    assert overview(client,h,'2026-02')['occurrences'][0]['dueDate']=='2026-02-28'
    assert overview(client,h,'2026-03')['occurrences'][0]['dueDate']=='2026-03-31'
    assert overview(client,h,'2027-01')['occurrences'][0]['dueDate']=='2027-01-31'
    schedule(client,h,name='Annual',frequency='yearly',startDate='2024-02-29',expectedDate='2024-02-29')
    assert next(o for o in overview(client,h,'2028-02')['occurrences'] if o['name']=='Annual')['dueDate']=='2028-02-29'
    schedule(client,h,name='Every two weeks',frequency='custom',interval=2,unit='weeks',endDate='2026-11-02')
    dates=[o['dueDate'] for o in overview(client,h)['occurrences'] if o['name']=='Every two weeks']
    assert dates==['2026-10-05','2026-10-19']
    assert [o['dueDate'] for o in overview(client,h,'2026-11')['occurrences'] if o['name']=='Every two weeks']==['2026-11-02']
    assert not [o for o in overview(client,h,'2026-12')['occurrences'] if o['name']=='Every two weeks']

def test_actual_and_expected_stay_separate_skip_postpone_restore(client):
    h=setup(client);s=schedule(client,h)
    data=overview(client,h);o=data['occurrences'][0]
    assert data['totals']['actualExpenses']==0 and data['totals']['expectedExpenses']==800000
    assert client.get('/api/v1/workspace',headers=h).json()['state']['transactions']==[]
    assert occurrence_action(client,h,o['id'],'postponed',postponedTo='2026-11-03').status_code==200
    assert overview(client,h)['occurrences']==[]
    november=overview(client,h,'2026-11')['occurrences'];assert len(november)==2
    assert [o['dueDate'] for o in november]==['2026-11-03','2026-11-05']
    assert occurrence_action(client,h,o['id'],'skipped').status_code==200
    assert overview(client,h,'2026-11')['totals']['expectedExpenses']==800000
    assert occurrence_action(client,h,o['id'],'expected').status_code==200
    assert overview(client,h)['occurrences'][0]['dueDate']=='2026-10-05'
    assert client.patch('/api/v1/recurring/'+s['id'],headers=h,json={'version':version(client,h),'active':False}).status_code==200
    assert overview(client,h,'2026-12')['occurrences']==[]

def test_paid_is_single_ledger_entry_and_bank_reimport_deduplicates(client):
    h=setup(client);schedule(client,h)
    o=overview(client,h)['occurrences'][0]
    assert occurrence_action(client,h,o['id'],'paid',paymentDate='2026-11-05',amount=800000).status_code==422
    paid=occurrence_action(client,h,o['id'],'paid',paymentDate='2026-10-05',amount=800000)
    assert paid.status_code==200,paid.text
    assert len(paid.json()['state']['transactions'])==1
    assert occurrence_action(client,h,o['id'],'paid',paymentDate='2026-10-05',amount=800000).status_code==409
    # Posted bank date differs by one day; it replaces the manually recorded payment.
    csv=b'date,merchant,amount,direction\n2026-10-06,Rent,8000,debit'
    response=client.post('/api/v1/imports/csv',headers=h,files={'file':('rent.csv',csv)})
    assert response.status_code==200,response.text
    assert len(response.json()['state']['transactions'])==1
    assert response.json()['state']['transactions'][0]['bank']=='CSV statement'
    data=overview(client,h)
    assert data['totals']['actualExpenses']==800000 and data['totals']['expectedExpenses']==0
    assert data['occurrences'][0]['transactionId']==response.json()['state']['transactions'][0]['id']
    assert client.post('/api/v1/imports/csv',headers=h,files={'file':('rent.csv',csv)}).json()['added']==0
    assert overview(client,h,'2026-11')['occurrences'][0]['status']=='expected'

def test_import_matches_variable_and_leaves_ambiguous_payments_for_review(client):
    h=setup(client);schedule(client,h,name='Power',category='Bills',amount=120000,variable=True)
    csv=b'date,merchant,amount,direction\n2026-10-06,Power,1300,debit'
    result=client.post('/api/v1/imports/csv',headers=h,files={'file':('power.csv',csv)})
    assert result.status_code==200,result.text
    assert overview(client,h)['occurrences'][0]['actualAmount']==130000
    schedule(client,h,name='Gym',category='Health',amount=100000)
    csv=b'date,merchant,amount,direction\n2026-10-04,Gym,1000,debit\n2026-10-06,Gym,1000,debit'
    assert client.post('/api/v1/imports/csv',headers=h,files={'file':('gym.csv',csv)}).status_code==200
    o=next(o for o in overview(client,h)['occurrences'] if o['name']=='Gym')
    assert o['status']=='expected'
    tx=next(t for t in client.get('/api/v1/workspace',headers=h).json()['state']['transactions'] if t['merchant']=='Gym')
    assert occurrence_action(client,h,o['id'],'paid',transactionId=tx['id']).status_code==200

def test_suggestions_require_confirmation_remember_decisions_and_material_change(client):
    h=setup(client)
    def tx(i,day,amount=19900): return {'id':str(i),'date':day,'merchant':'Netflix','amount':amount,'category':'Subscriptions','direction':'debit','bank':'CSV'}
    rows=[tx(1,'2026-08-05'),tx(2,'2026-09-05')]
    change(client,h,transactions=rows)
    p=overview(client,h)['suggestions'][0]
    assert client.get('/api/v1/workspace',headers=h).json()['state']['schedules']==[]
    assert client.post('/api/v1/analysis',headers=h,json={}).json()['assumptions']['bills']==[]
    path='/api/v1/recurring/suggestions/'+p['id']
    assert client.post(path,headers=h,json={'version':version(client,h),'status':'accepted'}).status_code==400
    assert client.post(path,headers=h,json={'version':version(client,h),'status':'declined'}).status_code==200
    assert overview(client,h)['suggestions']==[]
    # Same price and an additional month do not erase a decline.
    rows.append(tx(3,'2026-10-05'));change(client,h,transactions=rows)
    assert overview(client,h)['suggestions']==[]
    # Material price change >25%, not a tiny fluctuation, can prompt again.
    rows=[tx(1,'2026-08-05',29900),tx(2,'2026-09-05',29900),tx(3,'2026-10-05',29900)]
    change(client,h,transactions=rows)
    p=overview(client,h)['suggestions'][0]
    assert client.post(path,headers=h,json={'version':version(client,h),'status':'accepted','confirmed':True}).status_code==200
    assert overview(client,h)['suggestions']==[]
    assert overview(client,h)['occurrences'][0]['status']=='paid'
    assert overview(client,h,'2026-11')['totals']['expectedExpenses']==29900

def test_snooze_uses_calendar_time_and_resurfaces_after_thirty_days(client):
    h=setup(client)
    rows=[{'id':str(i),'date':day,'merchant':'Internet','amount':69900,'category':'Bills','direction':'debit','bank':'CSV'} for i,day in enumerate(['2026-08-05','2026-09-05'])]
    change(client,h,transactions=rows)
    p=overview(client,h)['suggestions'][0]
    assert client.post('/api/v1/recurring/suggestions/'+p['id'],headers=h,json={'version':version(client,h),'status':'later'}).status_code==200
    state=client.get('/api/v1/workspace',headers=h).json()['state']
    assert not engine_module.recurrence.patterns(state,date.today()+timedelta(days=29))
    assert engine_module.recurrence.patterns(state,date.today()+timedelta(days=30))

def test_manual_transaction_and_schedule_saved_atomically_with_owner_and_version_checks(client):
    h=setup(client)
    tx={'id':'client-id','merchant':'Rent','amount':800000,'date':'2026-10-05','direction':'debit','category':'Housing','bank':'Manual'}
    s={'name':'Rent','amount':800000,'category':'Housing','startDate':'2026-10-05','expectedDate':'2026-10-05'}
    body={'version':version(client,h),'transaction':tx,'schedule':s,'confirmed':False}
    assert client.post('/api/v1/transactions',headers=h,json=body).status_code==400
    assert client.get('/api/v1/workspace',headers=h).json()['state']['transactions']==[]
    body['confirmed']=True
    result=client.post('/api/v1/transactions',headers=h,json=body)
    assert result.status_code==201,result.text
    assert overview(client,h)['occurrences'][0]['status']=='paid'
    sid=result.json()['state']['schedules'][0]['id']
    other=register(client,'other@example.com')
    assert client.patch('/api/v1/recurring/'+sid,headers=other,json={'version':1,'active':False}).status_code==404
    assert client.patch('/api/v1/recurring/'+sid,headers=h,json={'version':1,'active':False}).status_code==409
    current=client.get('/api/v1/workspace',headers=h).json();current['state']['occurrences']={}
    assert client.put('/api/v1/workspace',headers=h,json={'version':current['version'],'state':current['state'],'confirmed':True}).status_code==400

def test_confirmed_income_replaces_salary_estimate_and_scheduled_health_is_not_daily_spending(client):
    h=setup(client)
    change(client,h,salary=3000000,nextPayday='2026-11-01')
    schedule(client,h,name='Payroll',category='Income',direction='credit',amount=3000000,startDate='2026-11-01',expectedDate='2026-11-01')
    schedule(client,h,name='Gym',category='Health',amount=100000,startDate='2026-10-15',expectedDate='2026-10-15')
    change(client,h,transactions=[{'id':'gym','date':'2026-09-15','merchant':'Gym','amount':100000,'direction':'debit','category':'Health','bank':'CSV'}])
    result=client.post('/api/v1/analysis',headers=h,json={}).json()
    assert result['baseline']['end']==4900000  # One income credit and one gym charge.
    assert result['assumptions']['essentialDaily']==0
    assert overview(client,h,'2026-11')['totals']['expectedIncome']==3000000

def test_recurring_persists_after_restart_and_delete_clears_schedules(tmp_path):
    url='sqlite:///'+(tmp_path/'recurring.db').as_posix()
    with TestClient(create_app(url)) as c:
        h=setup(c);schedule(c,h)
        o=overview(c,h)['occurrences'][0]
        assert occurrence_action(c,h,o['id'],'skipped').status_code==200
    with TestClient(create_app(url)) as c:
        assert overview(c,h)['occurrences'][0]['status']=='skipped'
        assert overview(c,h,'2027-02')['occurrences'][0]['status']=='expected'
        assert c.post('/api/v1/privacy/delete',headers=h,json={'confirmed':True}).status_code==200
        assert overview(c,h)['occurrences']==[]
        assert c.get('/api/v1/workspace',headers=h).json()['state']['schedules']==[]
