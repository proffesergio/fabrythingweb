// Central analytics helper: GA4 (gtag.js) + Google Tag Manager (dataLayer)
// + Meta Pixel passthrough + first-party event ingest to our own backend.
//
// Design notes:
// - The gtag/GTM <script> tags live in public/index.html. This module only
//   *sends* — it never injects scripts, so ad-blockers failing to load gtag
//   just make every helper below a silent no-op (all calls are guarded).
// - Same hostname guard as the Meta Pixel in index.html: localhost, 127.0.0.1
//   and *.vercel.app preview builds never send to the real properties.
//   Backend ingest follows the same rule, otherwise dev traffic pollutes the
//   admin Traffic panel.
// - Consent Mode v2: defaults to granted (Bangladesh has no opt-in cookie law
//   and AdSense/GA4 expect measurement). Call denyConsent() to flip to denied
//   — the choice persists in localStorage.

import config from './config';

const GA_ID = process.env.REACT_APP_GA4_MEASUREMENT_ID || 'G-S32TZJZCLV';
const INGEST_URL = `${config.API_URL}store/analytics/ingest/`;
const SID_KEY = 'fab_analytics_sid';
const CONSENT_KEY = 'fab_analytics_consent';

function prodHost() {
  try {
    const h = window.location.hostname;
    if (h === 'localhost' || h === '127.0.0.1') return false;
    if (h.endsWith('.vercel.app')) return false;
    return true;
  } catch {
    return false;
  }
}

/** True when a tracking call may leave the browser. */
export function isTrackingEnabled() {
  if (typeof window === 'undefined') return false;
  if (!prodHost()) return false;
  try {
    if (localStorage.getItem(CONSENT_KEY) === 'denied') return false;
  } catch {
    /* private mode — track nothing rather than throw */
    return false;
  }
  return true;
}

export function grantConsent() {
  try {
    localStorage.setItem(CONSENT_KEY, 'granted');
    window.gtag?.('consent', 'update', {
      ad_storage: 'granted',
      ad_user_data: 'granted',
      ad_personalization: 'granted',
      analytics_storage: 'granted',
    });
  } catch { /* noop */ }
}

export function denyConsent() {
  try {
    localStorage.setItem(CONSENT_KEY, 'denied');
    window.gtag?.('consent', 'update', {
      ad_storage: 'denied',
      ad_user_data: 'denied',
      ad_personalization: 'denied',
      analytics_storage: 'denied',
    });
  } catch { /* noop */ }
}

function getSessionId() {
  try {
    let sid = localStorage.getItem(SID_KEY);
    if (!sid) {
      sid = `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 10)}`;
      localStorage.setItem(SID_KEY, sid);
    }
    return sid;
  } catch {
    return 'unknown';
  }
}

/** SPA pageview: push to GA4 directly AND to the GTM dataLayer. */
export function trackPageview(path) {
  const pagePath = path || window.location.pathname + window.location.search;
  if (!isTrackingEnabled()) return;
  try {
    window.gtag?.('event', 'page_view', {
      page_path: pagePath,
      page_location: window.location.href,
      send_to: GA_ID,
    });
    window.dataLayer = window.dataLayer || [];
    window.dataLayer.push({ event: 'pageview', page_path: pagePath });
  } catch { /* noop */ }
  ingest('page_view', { path: pagePath });
}

/**
 * Generic event: GA4 + GTM dataLayer + Meta Pixel (for the standard
 * e-commerce events Meta understands) + backend ingest.
 */
export function trackEvent(name, params = {}) {
  if (!isTrackingEnabled()) return;
  try {
    window.gtag?.('event', name, params);
    window.dataLayer = window.dataLayer || [];
    window.dataLayer.push({ event: name, ...params });
    // Meta Pixel understands a subset — map GA4 names to Pixel ones.
    const pixelMap = {
      view_item: ['ViewContent', { content_ids: params.items?.map((i) => i.item_id), content_type: 'product' }],
      add_to_cart: ['AddToCart', { content_ids: params.items?.map((i) => i.item_id), value: params.value, currency: params.currency || 'BDT' }],
      begin_checkout: ['InitiateCheckout', { value: params.value, currency: params.currency || 'BDT' }],
      purchase: ['Purchase', { value: params.value, currency: params.currency || 'BDT' }],
    };
    const mapped = pixelMap[name];
    if (mapped && window.fbq) window.fbq('track', mapped[0], mapped[1]);
  } catch { /* noop */ }
  ingest(name, params);
}

// ── GA4 e-commerce helpers (BDT amounts) ──────────────────────────────

export function trackViewItem({ id, name, price }) {
  trackEvent('view_item', {
    currency: 'BDT',
    value: Number(price) || 0,
    items: [{ item_id: String(id), item_name: name, price: Number(price) || 0 }],
  });
}

export function trackAddToCart({ id, name, price, quantity = 1 }) {
  trackEvent('add_to_cart', {
    currency: 'BDT',
    value: (Number(price) || 0) * quantity,
    items: [{ item_id: String(id), item_name: name, price: Number(price) || 0, quantity }],
  });
}

export function trackBeginCheckout({ value, numItems }) {
  trackEvent('begin_checkout', { currency: 'BDT', value: Number(value) || 0, num_items: numItems });
}

export function trackPurchase({ orderNumber, value, numItems }) {
  trackEvent('purchase', {
    currency: 'BDT',
    transaction_id: orderNumber,
    value: Number(value) || 0,
    num_items: numItems,
  });
}

/** web-vitals callback — forwards Core Web Vitals to GA4 as events. */
export function sendToAnalytics({ name, delta, value, id }) {
  if (!isTrackingEnabled()) return;
  try {
    window.gtag?.('event', name, {
      event_category: 'Web Vitals',
      event_label: id,
      // GA4 event params must be numbers/strings — delta in ms.
      value: Math.round(name === 'CLS' ? delta * 1000 : delta),
      non_interaction: true,
    });
  } catch { /* noop */ }
}

// ── First-party ingest (powers the admin Traffic panel) ───────────────
// Fire-and-forget by design: keepalive so it survives page unloads, and it
// must NEVER throw into the shopping flow or delay navigation.

function ingest(event, params = {}) {
  try {
    const body = JSON.stringify({
      event,
      path: window.location.pathname,
      session_id: getSessionId(),
      params: safeParams(params),
    });
    if (navigator.sendBeacon) {
      const blob = new Blob([body], { type: 'application/json' });
      navigator.sendBeacon(INGEST_URL, blob);
    } else {
      // No credentials: ingest is AllowAny + throttled, so cookies add
      // nothing but a CORS preflight failure mode (Allow-Credentials).
      fetch(INGEST_URL, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body,
        keepalive: true,
        credentials: 'omit',
      }).catch(() => {});
    }
  } catch { /* noop */ }
}

// Params may contain product objects — cap size so a beacon stays small.
function safeParams(params) {
  try {
    const s = JSON.stringify(params);
    return s.length > 2000 ? JSON.parse(s.slice(0, 2000)) : params;
  } catch {
    return {};
  }
}
