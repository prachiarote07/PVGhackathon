/** Shared by the Vite build and runtime. Native APIs must use trusted HTTPS. */
export function validateApiBaseUrl(value = '', { native = false, development = false } = {}) {
  const input = String(value).trim();
  if (!input) return '';
  let url;
  try { url = new URL(input); } catch { throw new Error('VITE_API_BASE_URL must be a complete HTTPS URL.'); }
  if (url.username || url.password || url.search || url.hash) throw new Error('API URL must not contain credentials, query parameters or a fragment.');
  const loopback = url.hostname === 'localhost' || url.hostname.endsWith('.localhost') || /^127\./.test(url.hostname) || ['[::1]', '0.0.0.0', '[::]'].includes(url.hostname);
  if (native && loopback) throw new Error('Android API URL cannot use localhost/loopback: use a reachable trusted HTTPS host. Emulator host access is 10.0.2.2, not localhost.');
  if (url.protocol !== 'https:' && !(development && !native && loopback && url.protocol === 'http:')) throw new Error('API communication requires HTTPS. HTTP is allowed only for local web development.');
  return url.href.replace(/\/+$/, '');
}
