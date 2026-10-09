import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react';
import tailwindcss from '@tailwindcss/vite';
import { validateApiBaseUrl } from './src/api/config.js';

export default defineConfig(({ mode, command }) => {
  const android = mode === 'android';
  const env = { ...loadEnv(mode, process.cwd(), 'VITE_'), ...process.env };
  const api = validateApiBaseUrl(env.VITE_API_BASE_URL, { native: android, development: command === 'serve' });
  const csp = android ? {
    name: 'moneyfy-native-security-policy',
    transformIndexHtml() {
      return [{ tag: 'meta', attrs: { 'http-equiv': 'Content-Security-Policy', content: `default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; font-src 'self'; connect-src 'self'${api ? ` ${new URL(api).origin}` : ''}; object-src 'none'; base-uri 'self'; form-action 'self'` }, injectTo: 'head-prepend' }];
    },
  } : null;
  return {
    plugins: [react(), tailwindcss(), csp].filter(Boolean),
    define: { 'import.meta.env.VITE_APP_TARGET': JSON.stringify(android ? 'android' : 'web') },
    server: { port: 5173, strictPort: true, proxy: { '/api': 'http://127.0.0.1:8000' } },
    preview: { proxy: { '/api': 'http://127.0.0.1:8000' } },
    build: { outDir: android ? 'dist-android' : 'dist', rollupOptions: { output: { manualChunks: { charts: ['recharts'] } } } },
  };
});
