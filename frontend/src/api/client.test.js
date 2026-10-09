import test from 'node:test';
import assert from 'node:assert/strict';
import { createApiClient } from './client.js';
test('API client uses configured base, no credentials and no redirects', async () => {
  let request;
  const client = createApiClient('https://api.example.com/api/v1', async (url, options) => { request = { url, options }; return Response.json({ status: 'ok' }); });
  assert.deepEqual(await client.request('/health'), { status: 'ok' });
  assert.equal(request.url, 'https://api.example.com/api/v1/health');
  assert.equal(request.options.redirect, 'error'); assert.equal(request.options.credentials, 'omit');
});
test('API failures do not silently substitute demo data', async () => {
  await assert.rejects(createApiClient('').request('/health'), /No backend/);
  await assert.rejects(createApiClient('https://api.example.com', async () => new Response('no', { status: 503 })).request('/health'), /503/);
  await assert.rejects(createApiClient('https://api.example.com', async () => new Response('<html>oops</html>')).request('/health'), /JSON/);
  await assert.rejects(createApiClient('https://api.example.com').request('//evil.example'), /Invalid API path/);
});
test('API timeout is reported to the user', async () => {
  const client = createApiClient('https://api.example.com', (_url, { signal }) => new Promise((_resolve, reject) => signal.addEventListener('abort', () => reject(new DOMException('Aborted', 'AbortError')))));
  await assert.rejects(client.request('/health', { timeoutMs: 5 }), /timed out/);
});

test('Monthly queries and encoded payment identifiers stay on the configured API', async () => {
  const urls = [];
  const client = createApiClient('https://api.example.com/api/v1', async url => { urls.push(url); return Response.json({}); });
  await client.request('/recurring?month=2027-01');
  await client.request('/recurring/occurrences/schedule%402026-10-05', { method: 'POST', body: { status: 'skipped' } });
  assert.deepEqual(urls, ['https://api.example.com/api/v1/recurring?month=2027-01', 'https://api.example.com/api/v1/recurring/occurrences/schedule%402026-10-05']);
  for (const path of ['https://other.example', '//other.example', '/recurring#fragment', '/bad%zz']) await assert.rejects(client.request(path), /Invalid API path/);
});
