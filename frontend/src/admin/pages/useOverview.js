import { useCallback, useEffect, useRef, useState } from 'react';
import useApi from '../../hooks/APIHandler';
import { readSnap, writeSnap } from '../snap';

export default function useOverview(apiUrl, cacheKey) {
  const { callApi } = useApi();
  const callRef = useRef(callApi);
  callRef.current = callApi;
  const [days, setDays] = useState(14);
  const [revision, setRevision] = useState(0);
  const [data, setData] = useState(() => readSnap(`${cacheKey}:14`));
  const [loading, setLoading] = useState(true);
  const [failed, setFailed] = useState(false);
  const [errorMessage, setErrorMessage] = useState(null);
  const [lastUpdatedAt, setLastUpdatedAt] = useState(null);

  useEffect(() => {
    let current = true;
    const snapshotKey = `${cacheKey}:${days}`;
    setData(readSnap(snapshotKey));
    setLoading(true);
    setFailed(false);
    setErrorMessage(null);
    setLastUpdatedAt(null);
    const load = async () => {
      try {
        const response = await callRef.current({ url: `${apiUrl}?days=${days}`, silent: true, rawError: true, timeout: 25000 });
        if (!current) return;
        const payload = response?.status === 200 ? (response.data?.data ?? response.data) : null;
        if (payload) {
          setData(payload);
          writeSnap(snapshotKey, payload);
          setLastUpdatedAt(new Date());
        } else {
          setFailed(true);
          setErrorMessage(response?.status === 401 ? 'Your session expired. Sign in again to load this report.' : response?.status === 403 ? 'This account does not have access to this report.' : 'The report could not be loaded. Please retry.');
        }
      } catch {
        if (current) setFailed(true);
      } finally {
        if (current) setLoading(false);
      }
    };
    load();
    return () => { current = false; };
  }, [apiUrl, cacheKey, days, revision]);

  const retry = useCallback(() => setRevision((value) => value + 1), []);
  return { data, loading, failed, retry, days, setDays, lastUpdatedAt, errorMessage };
}
