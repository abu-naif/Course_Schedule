/* Installation is independent of the schedule UI and its external icon library. */
(() => {
  let deferredPrompt;
  const standalone = () => window.matchMedia('(display-mode: standalone)').matches || navigator.standalone;
  const panel = () => document.querySelector('.install-panel');
  const button = () => document.getElementById('installAppBtn');
  window.addEventListener('beforeinstallprompt', (event) => {
    event.preventDefault();
    deferredPrompt = event;
    if (button()) button().textContent = 'Install app';
  });
  window.addEventListener('appinstalled', () => {
    deferredPrompt = null;
    if (panel()) panel().hidden = true;
  });
  document.addEventListener('DOMContentLoaded', () => {
    if (standalone() && panel()) panel().hidden = true;
    button()?.addEventListener('click', async () => {
      if (deferredPrompt) {
        const prompt = deferredPrompt;
        deferredPrompt = null;
        await prompt.prompt();
        const { outcome } = await prompt.userChoice;
        if (outcome === 'accepted' && panel()) panel().hidden = true;
        return;
      }
      const instructions = document.getElementById('installInstructions');
      const ios = /iPad|iPhone|iPod/.test(navigator.userAgent) || (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1);
      instructions.textContent = ios
        ? 'On iPhone or iPad: open this page in Safari, tap Share, then Add to Home Screen and Add.'
        : 'Open your browser menu and choose Install app or Add to Home screen. On desktop, look for the install icon in the address bar. Use the HTTPS website address.';
      instructions.hidden = !instructions.hidden;
      button().setAttribute('aria-expanded', String(!instructions.hidden));
    });
  });
  if ('serviceWorker' in navigator && window.isSecureContext) {
    window.addEventListener('load', () => {
      navigator.serviceWorker.register('/sw.js').catch((error) => console.warn('Service worker registration failed:', error));
    });
  }
})();
