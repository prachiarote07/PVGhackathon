import { useState } from 'react';
import { isNative } from '../platform/native.js';
import { validateApiBaseUrl } from './config.js';
import { createApiClient } from './client.js';

export default function ConnectionPanel() {
  let endpoint = '', error = '';
  try { endpoint = validateApiBaseUrl(import.meta.env.VITE_API_BASE_URL, { native: isNative || import.meta.env.VITE_APP_TARGET === 'android', development: import.meta.env.DEV }); } catch (e) { error = e.message; }
  const [status, setStatus] = useState(''), [busy, setBusy] = useState(false);
  const check = async () => {
    setBusy(true); setStatus('Checking secure API connection…');
    try {
      const result = await createApiClient(endpoint).request('/health');
      if (!result || !['ok', 'healthy'].includes(result.status)) throw new Error('Health response did not confirm an available backend.');
      setStatus('Backend reachable. Sign in to open your database-backed account; the offline demo stays separate.');
    } catch (e) { setStatus(e.message); } finally { setBusy(false); }
  };
  return <section className="panel connection-panel"><h2>Backend connection</h2><p>{isNative ? 'Android app' : 'Website'} · offline demo financial data</p><p>{error || (endpoint ? `Configured API: ${endpoint}` : 'No API configured for the offline demo. Website accounts use the same-origin API; Android accounts require a configured HTTPS address.')}</p><p>Signed-in accounts use FastAPI, SQL persistence and Python analytics. This optional connection check sends only a health request.</p>{endpoint && !error && <button className="secondary" disabled={busy} onClick={check}>{busy ? 'Checking…' : 'Check backend connection'}</button>}<p role="status">{status}</p></section>;
}
