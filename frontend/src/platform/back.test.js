import test from 'node:test';
import assert from 'node:assert/strict';
import { backAction } from './back.js';
test('Android back dismisses overlays first, then navigates, then minimizes at Home', () => {
  assert.equal(backAction({ modalOpen: true, menuOpen: true, page: 'Home' }), 'close-modal');
  assert.equal(backAction({ menuOpen: true, page: 'Home' }), 'close-menu');
  assert.equal(backAction({ page: 'Dashboard', canGoBack: true }), 'history');
  assert.equal(backAction({ page: 'Dashboard', canGoBack: false }), 'home');
  assert.equal(backAction({ page: 'Home', canGoBack: true }), 'minimize');
});
