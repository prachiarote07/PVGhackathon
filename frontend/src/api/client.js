export function createApiClient(baseUrl, fetcher = globalThis.fetch, token = '') {
  return {
    async request(path, { method = 'GET', body, timeoutMs = 10000 } = {}) {
      if (!baseUrl) throw new Error('No backend configured. MoneyFy is running the local demo.');
      if (!/^\/(?:[a-zA-Z0-9/_-]|%[0-9a-fA-F]{2})*(?:\?[a-zA-Z0-9_=&%-]+)?$/.test(path) || path.startsWith('//')) throw new Error('Invalid API path.');
      const controller = new AbortController();
      const timer = setTimeout(() => controller.abort(), timeoutMs);
      try {
        const response = await fetcher(`${baseUrl}${path}`, {
          method, signal: controller.signal, redirect: 'error', credentials: 'omit',
          headers: { Accept: 'application/json', ...(token ? { Authorization: `Bearer ${token}` } : {}), ...(body === undefined || body instanceof FormData ? {} : { 'Content-Type': 'application/json' }) },
          ...(body === undefined ? {} : { body: body instanceof FormData ? body : JSON.stringify(body) }),
        });
        if (!response.ok) {
          let detail; try { detail = (await response.json()).detail; } catch {}
          const error = new Error(typeof detail === 'string' ? detail : `API request failed (HTTP ${response.status}).`);
          error.status = response.status;
          throw error;
        }
        if (!response.headers.get('content-type')?.includes('application/json')) throw new Error('Backend did not return JSON. Check the API endpoint.');
        return await response.json();
      } catch (error) {
        if (error.name === 'AbortError') throw new Error('Backend connection timed out. Check your connection and API address.');
        if (error instanceof TypeError) throw new Error('Cannot reach the backend. Check HTTPS, device network access and backend CORS settings.');
        throw error;
      } finally { clearTimeout(timer); }
    },
  };
}
