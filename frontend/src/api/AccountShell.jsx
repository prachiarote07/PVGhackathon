import { useEffect, useMemo, useState } from 'react';
import { createApiClient } from './client.js';
import { validateApiBaseUrl } from './config.js';
import { isNative } from '../platform/native.js';
import App from '../App.jsx';
import PublicHome from '../PublicHome.jsx';

const KEY = 'moneyfy.session.v1';
function readSession() { try { return JSON.parse(sessionStorage.getItem(KEY)); } catch { return null; } }
function endpoint() {
  const configured = import.meta.env.VITE_API_BASE_URL;
  const native = isNative || import.meta.env.VITE_APP_TARGET === 'android';
  if (configured) return validateApiBaseUrl(configured, { native, development: import.meta.env.DEV });
  return native ? '' : '/api/v1';
}
export default function AccountShell() {
  const [session, setSession] = useState(readSession), [data, setData] = useState(null), [mode, setMode] = useState(() => sessionStorage.getItem('moneyfy.demo.open') === 'yes' ? 'demo' : 'public'), [form, setForm] = useState('login'), [error, setError] = useState(''), [busy, setBusy] = useState(false);
  let base = '', configError = ''; try { base = endpoint(); } catch (e) { configError = e.message; }
  const client = useMemo(() => createApiClient(base, globalThis.fetch, session?.token || ''), [base, session?.token]);
  useEffect(() => {
    if (!session) return;
    let active = true;
    setMode('loading');
    Promise.all([client.request('/auth/me'), client.request('/workspace'), client.request('/analysis', { method: 'POST', body: {} })]).then(([user, workspace, analysis]) => {
      if (active) { setData({ ...workspace, analysis, user }); setMode('account'); setError(''); }
    }).catch(e => { if (active) { setError(e.message); setMode('auth'); if (e.status === 401) { sessionStorage.removeItem(KEY); setSession(null); } } });
    return () => { active = false; };
  }, [client, session]);
  const logout = async () => {
    setBusy(true);
    try { await client.request('/auth/logout', { method: 'POST' }); }
    catch (e) { if (e.status !== 401) { setError(`Could not revoke the server session: ${e.message}`); setBusy(false); return; } }
    sessionStorage.removeItem(KEY); sessionStorage.removeItem('moneyfy.demo.open'); setSession(null); setData(null); setForm('login'); setMode('auth'); setBusy(false);
  };
  const authenticate = async e => {
    e.preventDefault(); setError(''); setBusy(true);
    const values = Object.fromEntries(new FormData(e.currentTarget));
    try {
      const next = await createApiClient(base).request(`/auth/${form}`, { method: 'POST', body: values });
      sessionStorage.setItem(KEY, JSON.stringify(next)); setSession(next);
    } catch (e) { setError(e.message); } finally { setBusy(false); }
  };
  if (mode === 'account' && data) return <><App key={session.user.id} account={data.user} accountData={data} api={client} onLogout={logout}/>{error && <div className="toast" role="alert">{error}<button onClick={() => setError('')}>Dismiss</button></div>}</>;
  if (mode === 'public' && !session) return <PublicHome onSignIn={() => {setMode('auth');setError('');}} onDemo={() => {sessionStorage.setItem('moneyfy.demo.open','yes');setMode('demo');}}/>;
  if (mode === 'demo' && !session) return <App key="offline-demo" onSignIn={() => { setMode('auth'); setError(''); }}/>;
  return <div className="auth-shell" data-theme="light"><section className="auth-brand"><span className="brand-icon">₹</span><h1>MoneyFy</h1><p>Your Moves, Made Smarter.</p><p>Your account. Your data. A clearer picture of tomorrow.</p></section><section className="panel auth-panel"><h2>{mode === 'loading' ? 'Opening your workspace…' : form === 'login' ? 'Welcome back' : 'Create your MoneyFy account'}</h2><p className="muted">Accounts save to the connected database. The offline demo remains separate.</p>{(error || configError) && <p className="warning" role="alert">{error || configError}</p>}{mode !== 'loading' && <form onSubmit={authenticate}>{form === 'signup' && <label>Your name<input name="name" required maxLength="80" autoComplete="name"/></label>}<label>Email<input name="email" type="email" required maxLength="254" autoComplete="email"/></label><label>Password<input name="password" type="password" required minLength="10" maxLength="128" autoComplete={form === 'login' ? 'current-password' : 'new-password'}/></label><p className="muted">Use at least 10 characters. No bank password is needed.</p><button className="primary full" disabled={busy || !base || !!configError}>{busy ? 'Please wait…' : form === 'login' ? 'Sign in' : 'Create account'}</button><button type="button" className="text-button" onClick={() => { setForm(form === 'login' ? 'signup' : 'login'); setError(''); }}>{form === 'login' ? 'New here? Create an account' : 'Already registered? Sign in'}</button></form>}{!base && <p className="warning">This Android build has no backend address. Configure a reachable HTTPS API and rebuild, or explore the offline demo.</p>}<button className="secondary full" onClick={() => { if (session) { setError('Sign out successfully before switching to the offline demo.'); return; } sessionStorage.setItem('moneyfy.demo.open','yes'); setMode('demo'); }}>Explore offline demo</button></section></div>;
}
