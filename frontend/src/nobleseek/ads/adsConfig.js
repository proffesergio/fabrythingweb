import { useEffect, useState } from 'react';
import axios from 'axios';
import config from '../../utils/config';

let cached = null;
let inflight = null;

// Public ad density flags + slot ids. Cached in-memory + localStorage so
// news detail renders instantly even on cold backend.
export function useAdConfig() {
  const [adConfig, setAdConfig] = useState(() => {
    try { return JSON.parse(localStorage.getItem('ns_adconfig') || 'null'); } catch { return null; }
  });
  useEffect(() => {
    let live = true;
    async function load() {
      if (cached) { if (live) setAdConfig(cached); return; }
      if (!inflight) {
        inflight = axios.get(`${config.API_URL}store/nobleseek/ad-config/`)
          .then(r => r?.data?.data || r?.data)
          .catch(() => null)
          .finally(() => {});
      }
      const data = await inflight;
      inflight = null;
      if (data) {
        cached = data;
        try { localStorage.setItem('ns_adconfig', JSON.stringify(data)); } catch {}
        if (live) setAdConfig(data);
      }
    }
    load();
    return () => { live = false; };
  }, []);
  return adConfig || {};
}

const NO_AD_PATHS = ['/cart', '/checkout', '/account', '/auth/', '/admin', '/rider', '/vendor'];

// True when ads must be suppressed (shop checkout funnel + backoffice).
export function shouldSuppressAds(pathname = '') {
  return NO_AD_PATHS.some(p => pathname === p || pathname.startsWith(p));
}

let adsenseLoading = null;
export function loadAdSense(client) {
  if (typeof document === 'undefined') return Promise.resolve(false);
  if (document.querySelector('script[data-ns-adsense]')) return Promise.resolve(true);
  const id = (client || process.env.REACT_APP_ADSENSE_CLIENT || '').trim();
  if (!id || id.includes('REACT_APP') || !id.startsWith('ca-pub-')) return Promise.resolve(false);
  if (!adsenseLoading) {
    adsenseLoading = new Promise((resolve) => {
      const s = document.createElement('script');
      s.async = true;
      s.setAttribute('data-ns-adsense', '1');
      s.src = `https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=${encodeURIComponent(id)}`;
      s.crossOrigin = 'anonymous';
      s.onload = () => resolve(true);
      s.onerror = () => resolve(false);
      document.head.appendChild(s);
    });
  }
  return adsenseLoading;
}
