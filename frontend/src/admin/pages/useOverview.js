import { useCallback, useEffect, useRef, useState } from 'react';
import useApi from '../../hooks/APIHandler';
import { readSnap, writeSnap } from '../snap';

// Shared loader for module overview dashboards: cached snapshot first (so a
// sleeping backend never means a dead dashboard), 25s fail-fast, explicit
// failed flag with retry. callApi identity changes every render, so it is
// routed through a ref — never into dependency arrays.
export default function useOverview(apiUrl, cacheKey) {
  const { callApi } = useApi();
  const ref = useRef(callApi);
  ref.current = callApi;
  const daysRef = useRef(14);
  const [days, setDaysState] = useState(14);
  const [data, setData] = useState(() => readSnap(cacheKey));
  const [loading, setLoading] = useState(false);
  const [failed, setFailed] = useState(false);
  const inflight = useRef(false);

  const load = useCallback(async () => {
    if (inflight.current) return;
    inflight.current = true;
    setLoading(true);
    setFailed(false);
    try {
      const r = await ref.current({
        url: `${apiUrl}?days=${daysRef.current}`,
        silent: true, timeout: 25000,
      });
      const payload = r?.status === 200 ? (r.data?.data ?? r.data) : null;
      if (payload) {
        setData(payload);
        writeSnap(cacheKey, payload);
      } else {
        setFailed(true);
      }
    } catch {
      setFailed(true);
    } finally {
      inflight.current = false;
      setLoading(false);
    }
  }, [apiUrl, cacheKey]);

  useEffect(() => { load(); }, [load]);

  const setDays = useCallback((d) => {
    daysRef.current = d;
    setDaysState(d);
    load();
  }, [load]);

  return { data, loading, failed, retry: load, days, setDays };
}
