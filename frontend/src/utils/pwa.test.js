import {
  INSTALL_DELAY_MS,
  INSTALL_DISMISSED_KEY,
  isIos,
  isStandalone,
  needsManualIosInstructions,
  rememberDismissal,
  shouldOfferInstall,
  wasRecentlyDismissed,
} from './pwa';

const winWith = (standalone) => ({
  matchMedia: () => ({ matches: standalone }),
  navigator: {},
});

describe('standalone detection', () => {
  it('detects an installed app via display-mode', () => {
    expect(isStandalone(winWith(true))).toBe(true);
    expect(isStandalone(winWith(false))).toBe(false);
  });

  it('detects iOS installed apps, which predate display-mode', () => {
    expect(isStandalone({ matchMedia: () => ({ matches: false }), navigator: { standalone: true } })).toBe(true);
  });
});

describe('iOS detection', () => {
  it('recognises iPhone and iPad', () => {
    expect(isIos({ userAgent: 'iPhone' })).toBe(true);
    expect(isIos({ userAgent: 'iPad' })).toBe(true);
  });

  it('recognises iPadOS 13+, which reports itself as a Mac', () => {
    expect(isIos({ userAgent: 'Macintosh', maxTouchPoints: 5 })).toBe(true);
  });

  it('does not mistake a real Mac for an iPad', () => {
    expect(isIos({ userAgent: 'Macintosh', maxTouchPoints: 0 })).toBe(false);
  });

  it('asks for manual instructions only when iOS and not yet installed', () => {
    expect(needsManualIosInstructions({ userAgent: 'iPhone' }, winWith(false))).toBe(true);
    expect(needsManualIosInstructions({ userAgent: 'iPhone' }, winWith(true))).toBe(false);
    expect(needsManualIosInstructions({ userAgent: 'Linux' }, winWith(false))).toBe(false);
  });
});

describe('dismissal memory', () => {
  const store = () => {
    const m = new Map();
    return { getItem: (k) => (m.has(k) ? m.get(k) : null), setItem: (k, v) => m.set(k, v) };
  };

  it('remembers a dismissal for 30 days', () => {
    const s = store();
    rememberDismissal(s, 1000);
    expect(wasRecentlyDismissed(s, 1000 + 5000)).toBe(true);
  });

  it('forgets after 30 days so a returning customer sees it again', () => {
    const s = store();
    rememberDismissal(s, 0);
    expect(wasRecentlyDismissed(s, 31 * 24 * 60 * 60 * 1000)).toBe(false);
  });

  it('treats an unreadable store as "not dismissed" rather than hiding forever', () => {
    const throwing = { getItem: () => { throw new Error('private mode'); } };
    expect(wasRecentlyDismissed(throwing, 0)).toBe(false);
  });

  it('does not throw when the store refuses writes', () => {
    expect(() => rememberDismissal({ setItem: () => { throw new Error('quota'); } }, 0)).not.toThrow();
  });

  it('uses a namespaced key', () => {
    expect(INSTALL_DISMISSED_KEY).toContain('fabrything');
  });
});

describe('when to offer the install bar', () => {
  const ready = { promptEvent: {}, elapsedMs: INSTALL_DELAY_MS };

  it('offers once the browser is ready and the visitor has browsed a little', () => {
    expect(shouldOfferInstall(ready)).toBe(true);
  });

  it('stays quiet before the delay elapses', () => {
    // A banner on landing covers the shop before the customer has seen it.
    expect(shouldOfferInstall({ ...ready, elapsedMs: 1000 })).toBe(false);
  });

  it('never offers inside the installed app', () => {
    expect(shouldOfferInstall({ ...ready, standalone: true })).toBe(false);
  });

  it('never offers after a dismissal', () => {
    expect(shouldOfferInstall({ ...ready, dismissed: true })).toBe(false);
  });

  it('stays quiet when the browser never offered an install event', () => {
    // Desktop Firefox, in-app webviews, and anything already installed.
    expect(shouldOfferInstall({ ...ready, promptEvent: null })).toBe(false);
  });

  it('offers on iOS even though there is no install event', () => {
    expect(shouldOfferInstall({ promptEvent: null, iosManual: true, elapsedMs: INSTALL_DELAY_MS })).toBe(true);
  });

  it('iOS still respects standalone and dismissal', () => {
    expect(shouldOfferInstall({ iosManual: true, standalone: true, elapsedMs: INSTALL_DELAY_MS })).toBe(false);
    expect(shouldOfferInstall({ iosManual: true, dismissed: true, elapsedMs: INSTALL_DELAY_MS })).toBe(false);
  });
});
