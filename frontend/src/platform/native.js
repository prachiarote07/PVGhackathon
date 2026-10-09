import { Capacitor, SystemBars, SystemBarsStyle } from '@capacitor/core';
import { App } from '@capacitor/app';
import { Filesystem, Directory, Encoding } from '@capacitor/filesystem';
import { Share } from '@capacitor/share';
import { useEffect, useRef } from 'react';
import { backAction } from './back.js';

export const isNative = Capacitor.isNativePlatform();
export function useNativeShell({ theme, modal, mobile, page, closeModal, closeMenu, navigate, report }) {
  const latest = useRef(null);
  latest.current = { modal, mobile, page, closeModal, closeMenu, navigate, report };
  useEffect(() => {
    if (!isNative) return;
    document.documentElement.classList.add('native-app');
    let disposed = false, handle;
    App.addListener('backButton', ({ canGoBack }) => {
      // Recurring-payment forms own their dialogs outside App's legacy modal state.
      const dialog = document.querySelector('dialog[open]');
      if (dialog) { dialog.dispatchEvent(new Event('cancel', { cancelable: true })); return; }
      const s = latest.current;
      switch (backAction({ modalOpen: !!s.modal, menuOpen: s.mobile, page: s.page, canGoBack })) {
        case 'close-modal': s.closeModal(); break;
        case 'close-menu': s.closeMenu(); break;
        case 'history': window.history.back(); break;
        case 'home': s.navigate('Home'); break;
        case 'minimize': App.minimizeApp().catch(() => s.report('Use the system Home gesture to leave MoneyFy.')); break;
      }
    }).then(h => { if (disposed) h.remove(); else handle = h; }).catch(() => latest.current.report('Android back navigation could not be initialized. Use the app navigation.'));
    clearExportCache().catch(() => {});
    return () => { disposed = true; handle?.remove(); };
  }, []);
  useEffect(() => {
    if (isNative) SystemBars.setStyle({ style: theme === 'dark' ? SystemBarsStyle.Dark : SystemBarsStyle.Light }).catch(() => {});
  }, [theme]);
}

export async function clearExportCache() {
  if (!isNative) return;
  // Only this app's export directory; no broad storage permissions or shared files.
  try { await Filesystem.rmdir({ path: 'moneyfy-exports', directory: Directory.Cache, recursive: true }); } catch { /* No previous exports is normal. */ }
}

export async function exportText(text, name, type = 'text/csv') {
  if (isNative) {
    const result = await Filesystem.writeFile({ path: `moneyfy-exports/${name}`, directory: Directory.Cache, data: text, encoding: Encoding.UTF8, recursive: true });
    await Share.share({ title: 'MoneyFy export', dialogTitle: 'Save or share your MoneyFy file', files: [result.uri] });
    // Keep the cache file until next launch/deletion so receiving apps can finish reading it.
    return;
  }
  const url = URL.createObjectURL(new Blob([text], { type }));
  const anchor = document.createElement('a'); anchor.href = url; anchor.download = name; anchor.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
