from test_api import register, change

def test_rising_utilities_unusual_amounts_and_duplicate_alerts(client):
    h = register(client)
    rows = []
    for i, (day, amount) in enumerate([('2026-08-15',100000),('2026-09-15',150000)]):
        rows.append({'id':f'b{i}','date':day,'merchant':'Power Company','amount':amount,'direction':'debit','category':'Bills','bank':'CSV'})
    for i, amount in enumerate([10000,12000,10000,50000]):
        rows.append({'id':f's{i}','date':f'2026-10-0{i+1}','merchant':'Shop','amount':amount,'direction':'debit','category':'Shopping','bank':'CSV'})
    rows.append({**rows[-1], 'id':'duplicate'})
    change(client, h, asOf='2026-10-09', nextPayday='2026-11-01', consent=True, transactions=rows)
    alerts = client.post('/api/v1/analysis', headers=h, json={}).json()['alerts']
    assert any(a['id'].startswith('rising-') for a in alerts)
    assert any(a['id'].startswith('unusual-') for a in alerts)
    assert any(a['id'].startswith('duplicate-') for a in alerts)

def test_late_payday_includes_repeated_monthly_obligations(client):
    h = register(client)
    rows = [{'id':str(i),'date':day,'merchant':'Rent','amount':100000,'direction':'debit','category':'Housing','bank':'CSV'} for i,day in enumerate(['2026-08-15','2026-09-15'])]
    change(client,h,asOf='2026-10-09',nextPayday='2026-12-01',consent=True,transactions=rows,balance=1000000,reserve=0)
    overview = client.get('/api/v1/recurring?month=2026-10', headers=h).json()
    for pattern in overview['suggestions']:
        version = client.get('/api/v1/workspace', headers=h).json()['version']
        response = client.post('/api/v1/recurring/suggestions/' + pattern['id'], headers=h, json={'version':version,'status':'accepted','confirmed':True})
        assert response.status_code == 200, response.text
    result = client.post('/api/v1/analysis', headers=h,json={}).json()
    assert result['baseline']['safe'] == 800000  # October and November rent before payday.
