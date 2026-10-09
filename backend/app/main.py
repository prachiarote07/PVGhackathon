import csv
import hashlib
import hmac
import importlib.util
import io
import json
import os
from pathlib import Path
import secrets
from threading import Lock
import time
import uuid
from contextlib import asynccontextmanager
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation

from fastapi import Depends, FastAPI, File, HTTPException, Request, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import create_engine, delete, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker
from pydantic import ValidationError
from .models import Base, User, LoginSession, Workspace, Signup, Credentials, FinancialState, WorkspaceUpdate, Scenario, CategoryUpdate, Confirmed, Transaction, NewSchedule, ManualTransaction, ScheduleStatus, OccurrenceAction, PatternAction
from .recurring_routes import install_recurring

ROOT = Path(__file__).resolve().parents[1]
def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
engine_module = load_module('moneyfy_analytics', ROOT.parent / 'analytics-engine' / 'engine.py')
signals_module = load_module('moneyfy_signals', ROOT.parent / 'alerts-integration' / 'signals.py')

def blank_state():
    today = date.today()
    payday = (today.replace(day=28) + timedelta(days=4)).replace(day=1)
    return FinancialState(asOf=today, nextPayday=payday).model_dump(mode='json')

def password_hash(password, salt=None):
    salt = salt or secrets.token_hex(16)
    try:
        digest = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt), n=16384, r=8, p=1, dklen=32, maxmem=64 * 1024 * 1024).hex()
    except (MemoryError, ValueError):
        raise HTTPException(503, 'Sign-in service is temporarily busy. Please try again shortly.')
    return f'{salt}:{digest}'

def normalize(row, bank, as_of):
    merchant = str(row.get('merchant') or row.get('description') or row.get('payee') or '').strip()
    raw_amount = row.get('amount', row.get('value'))
    if raw_amount is None and 'amount_paise' in row: raw_amount = Decimal(str(row['amount_paise'])) / 100
    try:
        amount = Decimal(str(raw_amount))
        if not amount.is_finite() or amount <= 0 or amount != amount.quantize(Decimal('.01')): raise ValueError('Amount must be positive with at most two decimal places')
    except (InvalidOperation, ValueError, TypeError): raise ValueError('Invalid positive INR amount')
    direction = row.get('direction') or {'CR': 'credit', 'DR': 'debit', 'in': 'credit', 'out': 'debit'}.get(row.get('type') or row.get('flow'))
    category = 'Uncategorized'
    for words, label in [('salary|payroll', 'Income'), ('swiggy|zomato|freshmart|food|grocery', 'Food'), ('rent', 'Housing'), ('metro|uber|transport', 'Transport'), ('netflix|spotify', 'Subscriptions'), ('fee|charge', 'Fees'), ('electric|broadband|utility', 'Bills')]:
        import re
        if re.search(words, merchant.lower()): category = label; break
    tx = Transaction(id=str(uuid.uuid4()), date=row.get('date') or row.get('transactionDate') or row.get('booked_on'), merchant=merchant, amount=int(amount * 100), direction=direction, category=category, bank=bank)
    if tx.date.isoformat() > as_of: raise ValueError('Transaction is later than the account balance date')
    return tx.model_dump(mode='json')

def create_app(database_url=None):
    url = database_url or os.getenv('DATABASE_URL')
    if not url:
        if os.getenv('MONEYFY_ENV') == 'production': raise RuntimeError('Set DATABASE_URL for production; SQLite fallback is development only')
        (ROOT / 'data').mkdir(exist_ok=True)
        url = 'sqlite:///' + (ROOT / 'data' / 'moneyfy.db').as_posix()
    engine = create_engine(url, connect_args={'check_same_thread': False} if url.startswith('sqlite:') else {}, pool_pre_ping=True)
    sessions = sessionmaker(engine, expire_on_commit=False)
    @asynccontextmanager
    async def lifespan(_app):
        Base.metadata.create_all(engine)
        yield
        engine.dispose()
    app = FastAPI(title='MoneyFy API', version='1.0.0', lifespan=lifespan)
    app.state.engine = engine
    app.state.sessions = sessions
    app.add_middleware(CORSMiddleware, allow_origins=os.getenv('CORS_ORIGINS', 'http://127.0.0.1:5173,http://localhost:5173,http://127.0.0.1:4173,https://localhost').split(','), allow_credentials=False, allow_methods=['GET', 'POST', 'PUT', 'PATCH', 'DELETE'], allow_headers=['Authorization', 'Content-Type'])
    @app.middleware('http')
    async def request_limits(request, call_next):
        if int(request.headers.get('content-length', '0') or 0) > 2_000_000:
            return JSONResponse({'detail': 'Request too large (2 MB maximum)'}, status_code=413)
        response = await call_next(request)
        response.headers['Cache-Control'] = 'no-store'
        response.headers['X-Content-Type-Options'] = 'nosniff'
        return response
    @app.exception_handler(RequestValidationError)
    async def validation_error(_request, exc):
        return JSONResponse({'detail': '; '.join(f"{'.'.join(str(p) for p in e['loc'])}: {e['msg']}" for e in exc.errors())}, status_code=422)
    def db():
        with sessions() as session: yield session
    bearer = HTTPBearer(auto_error=False)
    def current_user(auth: HTTPAuthorizationCredentials = Depends(bearer), session: Session = Depends(db)):
        if not auth: raise HTTPException(401, 'Sign in to continue', headers={'WWW-Authenticate': 'Bearer'})
        record = session.get(LoginSession, hashlib.sha256(auth.credentials.encode()).hexdigest())
        if not record or record.expires <= int(time.time()): raise HTTPException(401, 'Session expired. Please sign in again.', headers={'WWW-Authenticate': 'Bearer'})
        user = session.get(User, record.user_id)
        if not user: raise HTTPException(401, 'Account unavailable')
        return user
    def public_user(user): return {'id': user.id, 'name': user.name, 'email': user.email}
    def issue(user, session):
        token = secrets.token_urlsafe(32)
        session.add(LoginSession(token_hash=hashlib.sha256(token.encode()).hexdigest(), user_id=user.id, expires=int(time.time()) + 86400))
        session.execute(delete(LoginSession).where(LoginSession.expires < int(time.time())))
        session.commit()
        return {'token': token, 'user': public_user(user), 'expiresIn': 86400}
    attempts, lock = {}, Lock()
    def rate_limit(request, email):
        key = (request.client.host if request.client else 'unknown', email)
        now = time.monotonic()
        with lock:
            for k in list(attempts):
                if now - attempts[k][-1] > 300: del attempts[k]
            history = [t for t in attempts.get(key, []) if now - t < 300]
            if len(history) >= 15: raise HTTPException(429, 'Too many sign-in attempts. Try again in five minutes.')
            attempts[key] = history + [now]
    @app.get('/api/v1/health')
    def health(session: Session = Depends(db)):
        session.execute(select(1))
        return {'status': 'ok', 'database': engine.dialect.name, 'mode': 'sqlite-development-fallback' if engine.dialect.name == 'sqlite' else 'postgresql'}
    @app.post('/api/v1/auth/signup', status_code=201)
    def signup(data: Signup, request: Request, session: Session = Depends(db)):
        rate_limit(request, data.email)
        user = User(id=str(uuid.uuid4()), email=data.email, name=data.name, password_hash=password_hash(data.password))
        session.add(user)
        try:
            session.flush()
            session.add(Workspace(user_id=user.id, version=1, data=blank_state()))
            session.commit()
        except IntegrityError:
            session.rollback()
            raise HTTPException(409, 'An account with this email already exists. Sign in instead.')
        return issue(user, session)
    @app.post('/api/v1/auth/login')
    def login(data: Credentials, request: Request, session: Session = Depends(db)):
        rate_limit(request, data.email)
        user = session.scalar(select(User).where(User.email == data.email))
        expected = user.password_hash if user else password_hash('dummy-password-for-timing')
        actual = password_hash(data.password, expected.split(':')[0])
        if not user or not hmac.compare_digest(expected, actual): raise HTTPException(401, 'Email or password is incorrect')
        return issue(user, session)
    @app.get('/api/v1/auth/me')
    def me(user=Depends(current_user)): return public_user(user)
    @app.post('/api/v1/auth/logout')
    def logout(auth: HTTPAuthorizationCredentials = Depends(bearer), user=Depends(current_user), session: Session = Depends(db)):
        session.execute(delete(LoginSession).where(LoginSession.token_hash == hashlib.sha256(auth.credentials.encode()).hexdigest()))
        session.commit()
        return {'status': 'signed-out'}
    def response(workspace): return {'state': FinancialState.model_validate(workspace.data).model_dump(mode='json'), 'version': workspace.version, 'database': engine.dialect.name}
    def save(user_id, version, data, session):
        try:
            data = FinancialState.model_validate(data).model_dump(mode='json')
        except ValidationError as error:
            raise HTTPException(422, '; '.join(e['msg'] for e in error.errors()))
        result = session.execute(update(Workspace).where(Workspace.user_id == user_id, Workspace.version == version).values(data=data, version=version + 1))
        if result.rowcount != 1:
            session.rollback()
            raise HTTPException(409, 'This workspace changed in another session. Reload before editing again.')
        session.commit()
        session.expire_all()
        return response(session.get(Workspace, user_id))
    @app.get('/api/v1/workspace')
    def workspace(user=Depends(current_user), session: Session = Depends(db)):
        return response(session.get(Workspace, user.id))
    @app.put('/api/v1/workspace')
    def put_workspace(data: WorkspaceUpdate, user=Depends(current_user), session: Session = Depends(db)):
        old = session.get(Workspace, user.id).data
        state = data.state.model_dump(mode='json')
        for field in ['schedules', 'occurrences', 'patternDecisions']:
            if state[field] != old.get(field, [] if field == 'schedules' else {}):
                raise HTTPException(400, 'Use the recurring transaction controls to change schedules and payment status')
        if not state['consent'] and any(t['id'] not in {r['id'] for r in old['transactions']} for t in state['transactions']): raise HTTPException(403, 'Import consent is required to add transactions')
        for key, decision in state['decisions'].items():
            if decision['status'] == 'accepted' and old['decisions'].get(key) != decision and not data.confirmed: raise HTTPException(400, 'Confirm proposed financial actions before accepting')
        return save(user.id, data.version, state, session)
    install_recurring(app, db, current_user, save, engine_module.recurrence)
    @app.post('/api/v1/analysis')
    def analysis(scenario: Scenario, user=Depends(current_user), session: Session = Depends(db)):
        workspace = session.get(Workspace, user.id)
        result = engine_module.analyze(workspace.data, scenario.model_dump())
        result['alerts'] = signals_module.signals(workspace.data, result)
        result['version'] = workspace.version
        return result
    @app.patch('/api/v1/transactions/{transaction_id}/category')
    def category(transaction_id: str, body: CategoryUpdate, user=Depends(current_user), session: Session = Depends(db)):
        state = json.loads(json.dumps(session.get(Workspace, user.id).data))
        tx = next((t for t in state['transactions'] if t['id'] == transaction_id), None)
        if not tx: raise HTTPException(404, 'Transaction not found')
        tx['category'] = body.category
        return save(user.id, body.version, state, session)
    def ingest(user, rows, label, session):
        workspace = session.get(Workspace, user.id)
        state = FinancialState.model_validate(workspace.data).model_dump(mode='json')
        if not state['consent']: raise HTTPException(403, 'Enable import consent before importing')
        if len(rows) > 5000: raise HTTPException(422, 'Maximum 5000 rows')
        try: normalized = [normalize(row, label, state['asOf']) for row in rows]
        except (ValueError, TypeError) as error: raise HTTPException(422, 'Invalid statement row: ' + str(error).split('\n')[0])
        key = lambda t: (t['date'], t['merchant'].lower(), t['amount'], t['direction'])
        seen = {key(t) for t in state['transactions']}
        added = []
        replaced = 0
        for tx in normalized:
            if key(tx) not in seen:
                # A bank record may replace a manually recorded payment, but only with one unambiguous exact-amount match.
                candidates = []
                day = date.fromisoformat(tx['date'])
                for occurrence in engine_module.recurrence.expand(state, day-timedelta(days=3), day+timedelta(days=3)):
                    previous = next((t for t in state['transactions'] if t['id'] == occurrence.get('transactionId')), None)
                    if occurrence['status'] == 'paid' and previous and previous['bank'] == 'Manual payment' and previous['amount'] == tx['amount'] and engine_module.recurrence.matches(tx, occurrence):
                        candidates.append(previous)
                if len(candidates) == 1:
                    previous = candidates[0]
                    seen.discard(key(previous))
                    previous.update({**tx, 'id': previous['id']})
                    seen.add(key(previous))
                    replaced += 1
                else:
                    added.append(tx); seen.add(key(tx))
        if len(state['transactions']) + len(added) > 5000: raise HTTPException(422, 'Workspace maximum is 5000 transactions')
        state['transactions'] = sorted(state['transactions'] + added, key=lambda t: t['date'], reverse=True)
        engine_module.recurrence.reconcile(state)
        state['imports'] = (state['imports'] + [{'id': str(uuid.uuid4()), 'label': label, 'count': len(added), 'duplicates': len(rows) - len(added) - replaced, 'at': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}])[-200:]
        if label != 'CSV statement': state['connections'] = list(dict.fromkeys(state['connections'] + [label]))
        output = save(user.id, workspace.version, state, session)
        return dict(output, added=len(added), duplicates=len(rows) - len(added) - replaced, replaced=replaced, raw=rows[0] if rows else None, normalized=normalized[0] if normalized else None)
    @app.post('/api/v1/imports/csv')
    async def import_csv(file: UploadFile = File(...), user=Depends(current_user), session: Session = Depends(db)):
        content = await file.read(1_000_001)
        if len(content) > 1_000_000: raise HTTPException(413, 'Choose a CSV smaller than 1 MB')
        try:
            reader = csv.DictReader(io.StringIO(content.decode('utf-8-sig')), strict=True)
            if not {'date', 'merchant', 'amount', 'direction'}.issubset(reader.fieldnames or []): raise ValueError('Required headers: date, merchant, amount, direction')
            rows = list(reader)
            if not rows or any(None in row or any(v is None for v in row.values()) for row in rows): raise ValueError('Empty or malformed CSV')
        except (UnicodeError, csv.Error, ValueError) as error: raise HTTPException(422, str(error))
        return ingest(user, rows, 'CSV statement', session)
    banks = json.loads((ROOT.parent / 'demo-data' / 'banks.json').read_text())
    @app.get('/api/v1/banks/{bank_id}/raw')
    def bank_raw(bank_id: str, user=Depends(current_user), session: Session = Depends(db)):
        name = {'river': 'River Bank', 'lotus': 'Lotus Bank', 'summit': 'Summit Bank'}.get(bank_id)
        if not name: raise HTTPException(404, 'Unknown fictional bank')
        return banks[name]
    @app.post('/api/v1/banks/{bank_id}/connect')
    def bank_connect(bank_id: str, user=Depends(current_user), session: Session = Depends(db)):
        name = {'river': 'River Bank', 'lotus': 'Lotus Bank', 'summit': 'Summit Bank'}.get(bank_id)
        if not name: raise HTTPException(404, 'Unknown fictional bank')
        return ingest(user, banks[name], name, session)
    @app.post('/api/v1/privacy/delete')
    def clear(body: Confirmed, user=Depends(current_user), session: Session = Depends(db)):
        workspace = session.get(Workspace, user.id)
        return save(user.id, workspace.version, blank_state(), session)
    @app.post('/api/v1/privacy/reset')
    def reset(body: Confirmed, user=Depends(current_user), session: Session = Depends(db)):
        state = blank_state()
        txs = json.loads((ROOT.parent / 'demo-data' / 'transactions.json').read_text())
        state.update(transactions=txs, asOf='2026-10-09', nextPayday='2026-11-01', balance=2485000, salary=3000000, reserve=500000)
        workspace = session.get(Workspace, user.id)
        return save(user.id, workspace.version, state, session)
    return app

app = create_app()
