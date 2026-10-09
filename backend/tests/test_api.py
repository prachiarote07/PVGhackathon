import json
from pathlib import Path
import sys

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.main import create_app, engine_module, signals_module
from app.models import User, LoginSession

@pytest.fixture
def client(tmp_path):
    app = create_app('sqlite:///' + (tmp_path / 'test.db').as_posix())
    with TestClient(app) as c: yield c

def register(c, email='aarav@example.com'):
    response = c.post('/api/v1/auth/signup', json={'name': 'Aarav', 'email': email, 'password': 'Long-test-password-2026'})
    assert response.status_code == 201, response.text
    return {'Authorization': 'Bearer ' + response.json()['token']}

def change(c, headers, **values):
    workspace = c.get('/api/v1/workspace', headers=headers).json()
    workspace['state'].update(values)
    response = c.put('/api/v1/workspace', headers=headers, json={'state': workspace['state'], 'version': workspace['version'], 'confirmed': True})
    assert response.status_code == 200, response.text
    return response.json()

def test_auth_isolation_password_hash_and_revocation(client):
    first = register(client)
    second = register(client, 'another@example.com')
    assert client.get('/api/v1/workspace').status_code == 401
    change(client, first, balance=1234500)
    assert client.get('/api/v1/workspace', headers=second).json()['state']['balance'] == 0
    with client.app.state.sessions() as db:
        user = db.scalar(select(User).where(User.email == 'aarav@example.com'))
        assert 'Long-test-password' not in user.password_hash
        token = first['Authorization'].split()[1]
        assert db.get(LoginSession, token) is None
    assert client.post('/api/v1/auth/login', json={'email': 'aarav@example.com', 'password': 'incorrect-password'}).status_code == 401
    assert client.post('/api/v1/auth/login', json={'email': 'AARAV@example.com', 'password': 'Long-test-password-2026'}).status_code == 200
    assert client.post('/api/v1/auth/logout', headers=first).status_code == 200
    assert client.get('/api/v1/workspace', headers=first).status_code == 401

def test_csv_consent_normalization_category_and_atomic_validation(client):
    h = register(client)
    csv = b'date,merchant,amount,direction\n2026-10-08,"Unknown, Shop",125.50,debit'
    assert client.post('/api/v1/imports/csv', headers=h, files={'file': ('test.csv', csv)}).status_code == 403
    change(client, h, consent=True, asOf='2026-10-09', nextPayday='2026-11-01')
    result = client.post('/api/v1/imports/csv', headers=h, files={'file': ('test.csv', csv)})
    assert result.status_code == 200, result.text
    data = result.json()
    assert data['added'] == 1 and data['normalized']['amount'] == 12550
    tx = data['state']['transactions'][0]
    assert tx['category'] == 'Uncategorized'
    update = client.patch(f"/api/v1/transactions/{tx['id']}/category", headers=h, json={'category': 'Food', 'version': data['version']})
    assert update.status_code == 200
    assert update.json()['state']['transactions'][0]['category'] == 'Food'
    assert client.post('/api/v1/imports/csv', headers=h, files={'file': ('test.csv', csv)}).json()['duplicates'] == 1
    bad = csv + b'\n2026-10-08,Bad,-5,debit'
    assert client.post('/api/v1/imports/csv', headers=h, files={'file': ('test.csv', bad)}).status_code == 422
    assert len(client.get('/api/v1/workspace', headers=h).json()['state']['transactions']) == 1
    other = register(client, 'other@example.com')
    assert client.patch(f"/api/v1/transactions/{tx['id']}/category", headers=other, json={'category': 'Food', 'version': 1}).status_code == 404

def test_version_conflicts_approval_validation_and_privacy(client):
    h = register(client)
    saved = change(client, h, balance=100000)
    assert client.put('/api/v1/workspace', headers=h, json={'state': saved['state'], 'version': 1}).status_code == 409
    saved['state']['decisions'] = {'food': {'status': 'accepted', 'amount': 100}}
    assert client.put('/api/v1/workspace', headers=h, json={'state': saved['state'], 'version': saved['version']}).status_code == 400
    assert client.post('/api/v1/privacy/delete', headers=h, json={'confirmed': False}).status_code == 422
    assert client.post('/api/v1/privacy/reset', headers=h, json={'confirmed': True}).status_code == 200
    assert client.post('/api/v1/analysis', headers=h, json={}).status_code == 200
    cleared = client.post('/api/v1/privacy/delete', headers=h, json={'confirmed': True}).json()
    assert cleared['state']['transactions'] == [] and cleared['state']['balance'] == 0
    assert client.get('/api/v1/auth/me', headers=h).status_code == 200

def test_sqlite_persists_across_service_restart(tmp_path):
    url = 'sqlite:///' + (tmp_path / 'persistent.db').as_posix()
    with TestClient(create_app(url)) as first:
        headers = register(first)
        change(first, headers, balance=654321)
    with TestClient(create_app(url)) as second:
        assert second.get('/api/v1/workspace', headers=headers).json()['state']['balance'] == 654321

def test_all_banks_and_validation_errors_hide_passwords(client):
    h = register(client)
    change(client, h, consent=True, asOf='2026-10-09', nextPayday='2026-11-01')
    for bank in ['river', 'lotus', 'summit']:
        assert client.get(f'/api/v1/banks/{bank}/raw', headers=h).status_code == 200
        assert client.post(f'/api/v1/banks/{bank}/connect', headers=h).json()['added'] == 1
    assert client.post('/api/v1/auth/signup', json={'email':'wrong', 'name':'a', 'password':'secret'}).status_code == 422
    assert 'secret' not in client.post('/api/v1/auth/signup', json={'email':'wrong', 'name':'a', 'password':'secret'}).text

def test_account_data_drives_analytics_and_simulations(client):
    h = register(client)
    change(client, h, asOf='2026-10-09', nextPayday='2026-11-01', balance=1000000, reserve=200000, salary=3000000, bills=[{'id':'power','name':'Power','dueDate':'2026-10-15','amount':180000}])
    base = client.post('/api/v1/analysis', headers=h, json={}).json()
    assert base['baseline']['end'] == 3820000
    emergency = client.post('/api/v1/analysis', headers=h, json={'emergency':1000}).json()
    assert base['baseline']['end'] - emergency['simulated']['end'] == 100000
    delayed = client.post('/api/v1/analysis', headers=h, json={'salaryDelay':10}).json()
    assert delayed['simulated']['end'] == 820000
    assert 0 <= base['baseline']['score'] <= 100
    assert client.post('/api/v1/analysis', headers=h, json={'foodReduction':101}).status_code == 422
    assert client.get('/api/v1/workspace', headers=h).json()['state']['balance'] == 1000000

def test_recurring_leaks_and_shared_goal_capacity(client):
    h = register(client)
    client.post('/api/v1/privacy/reset', headers=h, json={'confirmed':True})
    overview = client.get('/api/v1/recurring?month=2026-10', headers=h).json()
    for pattern in overview['suggestions']:
        version = client.get('/api/v1/workspace', headers=h).json()['version']
        response = client.post('/api/v1/recurring/suggestions/' + pattern['id'], headers=h, json={'version':version,'status':'accepted','confirmed':True})
        assert response.status_code == 200, response.text
    data = client.post('/api/v1/analysis', headers=h, json={}).json()
    rec = next(r for r in data['recommendations'] if 'Netflix' in r['title'])
    before = data['baseline']['end']
    change(client, h, decisions={rec['id']:{'status':'accepted','amount':rec['amount']}})
    after = client.post('/api/v1/analysis', headers=h, json={}).json()
    assert after['optimized']['end'] - before == 64900
    change(client, h, goals=[{'id':str(i),'name':'Goal '+str(i),'target':10000000,'saved':0,'deadline':'2027-01-01','priority':'High' if i == 0 else 'Normal'} for i in range(2)])
    result = client.post('/api/v1/analysis', headers=h, json={}).json()
    assert sum(g['allocation'] for g in result['goals']['baseline'].values()) <= result['baseline']['capacity']
    assert any(a['id'].startswith('goal-') for a in result['alerts'])
