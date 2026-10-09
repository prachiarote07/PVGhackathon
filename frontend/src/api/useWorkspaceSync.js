import { useEffect, useRef, useState } from 'react';

/** Serial, versioned saves. A failed save blocks later writes until user retries. */
export function useWorkspaceSync(state, scenario, accountData, api, setState) {
  const [analysis, setAnalysis] = useState(accountData?.analysis || null);
  const [status, setStatus] = useState(accountData ? 'Saved to database' : 'Offline demo');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const version = useRef(accountData?.version);
  const committed = useRef(accountData?.state);
  const latest = useRef({ state, scenario }); latest.current = { state, scenario };
  const chain = useRef(Promise.resolve());
  const blocked = useRef(false);
  const alive = useRef(true);
  useEffect(() => { alive.current = true; return () => { alive.current = false; }; }, []);
  const execute = async () => {
    if (!api || blocked.current || !alive.current) return;
    const snapshot = latest.current;
    try {
      if (snapshot.state !== committed.current) {
        setStatus('Saving changes…');
        const result = await api.request('/workspace', { method: 'PUT', body: { state: snapshot.state, version: version.current, confirmed: true } });
        version.current = result.version; committed.current = snapshot.state;
      }
      const result = await api.request('/analysis', { method: 'POST', body: snapshot.scenario });
      if (alive.current && snapshot === latest.current) { setAnalysis(result); setStatus('Saved to database'); }
      else if (alive.current && snapshot.state === latest.current.state && JSON.stringify(snapshot.scenario) === JSON.stringify(latest.current.scenario)) { setAnalysis(result); setStatus('Saved to database'); }
    } catch (e) { if (alive.current) { blocked.current = true; setError(e.message); setStatus('Changes not saved'); } }
  };
  useEffect(() => {
    if (!api) return;
    setStatus(state === committed.current ? 'Updating calculations…' : 'Saving changes…');
    const timer = setTimeout(() => { chain.current = chain.current.then(execute); }, 250);
    return () => clearTimeout(timer);
  }, [state, scenario, api]);
  useEffect(() => {
    if (!api) return;
    const beforeUnload = e => { if (latest.current.state !== committed.current) { e.preventDefault(); e.returnValue = ''; } };
    window.addEventListener('beforeunload', beforeUnload);
    return () => window.removeEventListener('beforeunload', beforeUnload);
  }, [api]);
  const action = async (path, options) => {
    if (blocked.current) throw new Error('Resolve the save error before continuing.');
    setBusy(true);
    let output;
    const run = async () => {
      await execute();
      if (blocked.current) throw new Error('Changes have not been saved.');
      output = await api.request(path, { ...options, body: options.body instanceof FormData ? options.body : { ...options.body, version: options.withVersion ? version.current : undefined } });
      version.current = output.version; committed.current = output.state; setState(output.state);
      const result = await api.request('/analysis', { method: 'POST', body: latest.current.scenario });
      setAnalysis(result); setStatus('Saved to database');
    };
    const work = chain.current.then(run); chain.current = work.catch(() => {});
    try { await work; } finally { if (alive.current) setBusy(false); }
    return output;
  };
  return { analysis, status, error, busy, action, dirty: state !== committed.current, retry: () => { blocked.current = false; setError(''); chain.current = chain.current.then(execute); } };
}
