import React, { useEffect, useRef, useState } from 'react';
import { useLocation } from 'react-router-dom';
import { loadAdSense, shouldSuppressAds, useAdConfig } from './adsConfig';

// Policy-safe lazy ad unit. Renders <ins class="adsbygoogle"> only when
// visible (IntersectionObserver), pushes once, never re-pushes. Hides
// itself on no-ad routes and when slot id is missing (so local dev with
// no AdSense IDs shows a subtle placeholder instead of breaking layout).
export default function AdSlot({ slot, format = 'auto', layout, style, label = 'Advertisement', minHeight = 90, placement }) {
  const ref = useRef(null);
  const [visible, setVisible] = useState(false);
  const [pushed, setPushed] = useState(false);
  const location = useLocation();
  const adConfig = useAdConfig();
  const client = adConfig.adsense_client || process.env.REACT_APP_ADSENSE_CLIENT || '';

  useEffect(() => {
    const el = ref.current;
    if (!el) return undefined;
    if (!('IntersectionObserver' in window)) { setVisible(true); return undefined; }
    const io = new IntersectionObserver((entries) => {
      if (entries.some(e => e.isIntersecting)) { setVisible(true); io.disconnect(); }
    }, { rootMargin: '400px 0px' });
    io.observe(el);
    return () => io.disconnect();
  }, [slot, client, placement]);

  useEffect(() => {
    if (!visible || pushed || !slot || shouldSuppressAds(location.pathname)) return;
    let cancelled = false;
    loadAdSense(client).then((ok) => {
      if (!ok || cancelled) return;
      try {
        (window.adsbygoogle = window.adsbygoogle || []).push({});
        if (!cancelled) setPushed(true);
      } catch { /* AdSense throws when slot misconfigured — keep page alive */ }
    });
    return () => { cancelled = true; };
  }, [visible, pushed, slot, client, location.pathname]);

  if (shouldSuppressAds(location.pathname)) return null;
  const reservedStyle = {
    margin: '24px auto', textAlign: 'center', minHeight,
    width: '100%', maxWidth: placement === 'sidebar' ? 300 : placement === 'leaderboard' ? 970 : undefined,
    background: '#f4f4f4', overflow: 'hidden', ...style,
  };
  // Keep newspaper ad geometry stable without showing setup instructions or fake ads.
  if (!slot || !client) {
    if (!placement) return null;
    return (
      <aside ref={ref} aria-label={label} data-ad-placement={placement} style={{ ...reservedStyle, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <span style={{ fontSize: 10, color: '#767676', letterSpacing: '0.1em', textTransform: 'uppercase' }}>{label}</span>
      </aside>
    );
  }
  return (
    <aside ref={ref} data-ad-placement={placement} style={reservedStyle} aria-label={label}>
      <div style={{ fontSize: 10, letterSpacing: '0.12em', textTransform: 'uppercase', color: '#94a3b8', marginBottom: 4 }}>{label}</div>
      {visible && (
        <ins
          className="adsbygoogle"
          style={{ display: 'block', minHeight }}
          data-ad-client={client}
          data-ad-slot={slot}
          data-ad-format={format}
          {...(layout ? { 'data-ad-layout': layout } : {})}
          data-full-width-responsive="true"
        />
      )}
    </aside>
  );
}
