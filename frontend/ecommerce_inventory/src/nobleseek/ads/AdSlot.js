import React, { useEffect, useRef, useState } from 'react';
import { useLocation } from 'react-router-dom';
import { loadAdSense, shouldSuppressAds, useAdConfig } from './adsConfig';

// Policy-safe lazy ad unit. Renders <ins class="adsbygoogle"> only when
// visible (IntersectionObserver), pushes once, never re-pushes. Hides
// itself on no-ad routes and when slot id is missing (so local dev with
// no AdSense IDs shows a subtle placeholder instead of breaking layout).
export default function AdSlot({ slot, format = 'auto', layout, style, label = 'Advertisement', minHeight = 90 }) {
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
  }, []);

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
  if (!slot) {
    if (process.env.NODE_ENV === 'production') return null;
    return (
      <div ref={ref} style={{ ...style, minHeight, border: '1px dashed #cbd5e1', borderRadius: 8, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#94a3b8', fontSize: 12, background: '#f8fafc', margin: '16px 0' }}>
        AdSlot placeholder — set slot id in Admin → NobleSeek → Ads
      </div>
    );
  }
  return (
    <div ref={ref} style={{ margin: '20px 0', textAlign: 'center', minHeight, ...style }} aria-label={label}>
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
    </div>
  );
}
