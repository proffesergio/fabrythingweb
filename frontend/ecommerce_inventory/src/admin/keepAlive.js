import { useEffect } from 'react';
import config from '../utils/config';

// Keeps the (free-tier, sleep-prone) backend warm while an admin or shopper
// tab is open: a cheap public GET every ~9 minutes, well under Render's
// ~15-minute idle sleep. Visibility-guarded so background tabs cost nothing,
// fully silent (no toasts, no state) so it can mount anywhere safe.
export default function useKeepAlive(enabled = true, intervalMs = 9 * 60 * 1000) {
  useEffect(() => {
    if (!enabled) return undefined;
    let timer = 0;
    const ping = () => {
      if (typeof document !== 'undefined' && document.visibilityState !== 'visible') return;
      fetch(`${config.API_URL}health/`, { method: 'GET' }).catch(() => {});
    };
    ping();
    timer = setInterval(ping, intervalMs);
    document.addEventListener('visibilitychange', ping);
    return () => {
      clearInterval(timer);
      document.removeEventListener('visibilitychange', ping);
    };
  }, [enabled, intervalMs]);
}
