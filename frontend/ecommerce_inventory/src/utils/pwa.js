// PWA helpers. The decision logic lives here as pure functions so it can be
// tested without a browser — the install banner has a lot of "should this even
// appear?" rules and getting them wrong means either nagging every customer on
// every page or never showing the prompt at all.

export const INSTALL_DISMISSED_KEY = 'fabrything.install_dismissed_at';
export const INSTALL_DELAY_MS = 20000;

/** True when the page is already running as an installed app. */
export function isStandalone(win = window) {
  return (
    win.matchMedia?.('(display-mode: standalone)')?.matches === true ||
    // iOS Safari predates display-mode and uses a non-standard flag.
    win.navigator?.standalone === true
  );
}

export function isIos(nav = navigator) {
  const ua = nav.userAgent || '';
  return (
    /iPad|iPhone|iPod/.test(ua) ||
    // iPadOS 13+ reports itself as a Mac; the touch points give it away.
    (/Macintosh/.test(ua) && (nav.maxTouchPoints || 0) > 1)
  );
}

/** iOS Safari never fires `beforeinstallprompt`, so the only way to install is
 *  the Share sheet — which means we have to tell the user how by hand. */
export function needsManualIosInstructions(nav = navigator, win = window) {
  return isIos(nav) && !isStandalone(win);
}

/** A dismissal is remembered for 30 days so the bar never becomes a nag. */
export function wasRecentlyDismissed(storage = localStorage, now = Date.now()) {
  try {
    const raw = storage.getItem(INSTALL_DISMISSED_KEY);
    if (!raw) return false;
    const at = Number(raw);
    if (!Number.isFinite(at)) return false;
    return now - at < 30 * 24 * 60 * 60 * 1000;
  } catch {
    // Private mode can throw on localStorage; treat it as "not dismissed"
    // rather than suppressing the prompt forever.
    return false;
  }
}

export function rememberDismissal(storage = localStorage, now = Date.now()) {
  try {
    storage.setItem(INSTALL_DISMISSED_KEY, String(now));
  } catch {
    /* nothing we can do, and it must not throw into the UI */
  }
}

/**
 * Whether the install bar may be shown.
 *
 * `promptEvent` is the captured `beforeinstallprompt`; on iOS there is never
 * one, so `iosManual` stands in for it. Everything else is a veto.
 */
export function shouldOfferInstall({
  promptEvent = null,
  iosManual = false,
  standalone = false,
  dismissed = false,
  elapsedMs = 0,
  delayMs = INSTALL_DELAY_MS,
} = {}) {
  if (standalone) return false;      // already installed
  if (dismissed) return false;       // they said no
  if (elapsedMs < delayMs) return false;  // let them see the shop first
  return !!promptEvent || iosManual;
}

/**
 * Register the service worker and report when a new version is waiting.
 *
 * Deliberately NOT registered in development: a service worker in front of the
 * dev server makes every change look like it did not apply.
 */
export function registerServiceWorker({ onUpdateReady } = {}) {
  if (process.env.NODE_ENV !== 'production') return Promise.resolve(null);
  if (!('serviceWorker' in navigator)) return Promise.resolve(null);

  return navigator.serviceWorker
    .register('/sw.js')
    .then((registration) => {
      registration.addEventListener('updatefound', () => {
        const installing = registration.installing;
        if (!installing) return;
        installing.addEventListener('statechange', () => {
          // `controller` is null on the very first install — that is not an
          // update, it is the initial registration, and prompting to refresh
          // then would be confusing.
          if (installing.state === 'installed' && navigator.serviceWorker.controller) {
            onUpdateReady?.(registration);
          }
        });
      });
      return registration;
    })
    .catch(() => null);
}

/** Activate the waiting worker and reload once it takes over. */
export function applyUpdate(registration, win = window) {
  const waiting = registration?.waiting;
  if (!waiting) {
    win.location.reload();
    return;
  }
  let reloaded = false;
  navigator.serviceWorker.addEventListener('controllerchange', () => {
    if (reloaded) return;   // Chrome can fire this more than once
    reloaded = true;
    win.location.reload();
  });
  waiting.postMessage('SKIP_WAITING');
}
