export function backAction({ modalOpen, menuOpen, page, canGoBack }) {
  if (modalOpen) return 'close-modal';
  if (menuOpen) return 'close-menu';
  if (page === 'Home') return 'minimize';
  return canGoBack ? 'history' : 'home';
}
