import { defineConfig } from '@playwright/test';
export default defineConfig({
  testDir: './e2e-native',
  outputDir: './test-results-native',
  workers: 1,
  timeout: 45000,
  use: { baseURL: 'http://127.0.0.1:4174', channel: 'chrome', headless: true, hasTouch: true, isMobile: true, viewport: { width: 390, height: 844 } },
  webServer: { command: 'npx vite preview --mode android --port 4174 --strictPort --host 127.0.0.1', url: 'http://127.0.0.1:4174', reuseExistingServer: false },
});
