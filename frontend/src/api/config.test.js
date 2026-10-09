import test from 'node:test';
import assert from 'node:assert/strict';
import { validateApiBaseUrl } from './config.js';
test('Android permits explicit offline mode and trusted HTTPS host URLs', () => {
  assert.equal(validateApiBaseUrl('', { native: true }), '');
  assert.equal(validateApiBaseUrl('https://api.example.com/api/v1/', { native: true }), 'https://api.example.com/api/v1');
  assert.equal(validateApiBaseUrl('https://10.0.2.2:8443/api/v1', { native: true }), 'https://10.0.2.2:8443/api/v1');
});
test('Android rejects phone-local addresses, HTTP and embedded credentials', () => {
  for (const value of ['https://localhost:8000/api', 'https://127.0.0.1/api', 'https://[::1]/api', 'http://10.0.2.2:8000/api', 'http://192.168.1.5:8000/api', 'https://user:secret@example.com/api', 'https://api.example.com/?token=secret', '/api']) assert.throws(() => validateApiBaseUrl(value, { native: true, development: true }));
});
test('Web development allows only loopback HTTP; production requires HTTPS', () => {
  assert.equal(validateApiBaseUrl('http://127.0.0.1:8000/api/v1', { development: true }), 'http://127.0.0.1:8000/api/v1');
  assert.throws(() => validateApiBaseUrl('http://127.0.0.1:8000/api/v1'));
  assert.throws(() => validateApiBaseUrl('http://example.com/api', { development: true }));
});
