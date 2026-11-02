import { useCallback, useEffect, useRef, useState } from 'react';
import useApi from '../../hooks/APIHandler';

const API = 'products/';
const unwrap = (response) => response?.data?.data ?? response?.data ?? null;
const rows = (payload) => Array.isArray(payload) ? payload : payload?.results || payload?.items || [];
const responseError = (response, fallback) => {
  const payload = response?.data;
  const detail = payload?.data?.detail || payload?.detail;
  if (typeof detail === 'string') return detail;
  return payload?.message || fallback;
};

/** Real API state for the shop operations console. No sample values are used
 * as a fallback; an unavailable endpoint stays visibly unavailable. */
export default function useShopControlCenter({ enabled = true, pollIntervalMs = 60000 } = {}) {
  const { callApi } = useApi();
  const callRef = useRef(callApi);
  callRef.current = callApi;
  const [insights, setInsights] = useState(null);
  const [jobs, setJobs] = useState([]);
  const [runs, setRuns] = useState([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState(null);
  const [jobsError, setJobsError] = useState(null);
  const [runsError, setRunsError] = useState(null);
  const [actionError, setActionError] = useState(null);
  const [pendingAction, setPendingAction] = useState(null);
  const [lastUpdatedAt, setLastUpdatedAt] = useState(null);
  const mounted = useRef(true);
  const inflight = useRef(false);
  const refreshQueued = useRef(false);
  const actionInFlight = useRef(false);
  const enabledRef = useRef(enabled);
  enabledRef.current = enabled;

  useEffect(() => {
    mounted.current = true;
    return () => { mounted.current = false; };
  }, []);

  const refresh = useCallback(async ({ background = false } = {}) => {
    if (!enabledRef.current) return;
    if (inflight.current) { refreshQueued.current = true; return; }
    inflight.current = true;
    if (mounted.current) {
      if (background) setRefreshing(true);
      else setLoading(true);
    }
    try {
      const [insightsResult, jobsResult, runsResult] = await Promise.allSettled([
        callRef.current({ url: `${API}admin/insights/?days=30`, silent: true, timeout: 25000 }),
        callRef.current({ url: `${API}admin/sync-jobs/`, silent: true, timeout: 25000 }),
        callRef.current({ url: `${API}admin/sync-runs/`, silent: true, timeout: 25000 }),
      ]);
      const insightsResponse = insightsResult.status === 'fulfilled' ? insightsResult.value : null;
      const jobsResponse = jobsResult.status === 'fulfilled' ? jobsResult.value : null;
      const runsResponse = runsResult.status === 'fulfilled' ? runsResult.value : null;
      const insightsPayload = insightsResponse?.status === 200 ? unwrap(insightsResponse) : null;
      const jobsPayload = jobsResponse?.status === 200 ? unwrap(jobsResponse) : null;
      const runsPayload = runsResponse?.status === 200 ? unwrap(runsResponse) : null;
      if (mounted.current) {
        if (insightsPayload) { setInsights(insightsPayload); setError(null); setLastUpdatedAt(new Date()); }
        else setError(new Error('Insights are unavailable. Retry to check the live source.'));
        if (jobsPayload) { setJobs(rows(jobsPayload)); setJobsError(null); }
        else setJobsError(new Error('Sync jobs are unavailable.'));
        if (runsPayload) { setRuns(rows(runsPayload)); setRunsError(null); }
        else setRunsError(new Error('Run history is unavailable.'));
      }
    } catch (requestError) {
      if (mounted.current) setError(requestError);
    } finally {
      inflight.current = false;
      if (mounted.current) {
        setLoading(false);
        setRefreshing(false);
        if (refreshQueued.current) { refreshQueued.current = false; refresh({ background: true }); }
      }
    }
  }, []);

  useEffect(() => {
    if (!enabled) {
      setLoading(false);
      return undefined;
    }
    refresh();
    const poll = () => {
      if (!document.hidden) refresh({ background: true });
    };
    const timer = pollIntervalMs > 0 ? window.setInterval(poll, pollIntervalMs) : null;
    document.addEventListener('visibilitychange', poll);
    return () => {
      if (timer !== null) window.clearInterval(timer);
      document.removeEventListener('visibilitychange', poll);
    };
  }, [enabled, pollIntervalMs, refresh]);

  const performJobAction = useCallback(async (job, action) => {
    if (!enabledRef.current || actionInFlight.current || !job?.id || !['run', 'pause', 'resume'].includes(action)) return false;
    actionInFlight.current = true;
    const key = `${job.id}:${action}`;
    setPendingAction(key);
    setActionError(null);
    try {
      const response = await callRef.current({
        url: `${API}admin/sync-jobs/${job.id}/${action}/`, method: 'POST', body: {},
        silent: true, rawError: true, timeout: 25000,
      });
      if (![200, 202, 204].includes(response?.status)) {
        throw new Error(responseError(response, `Could not ${action} this job.`));
      }
      // A run is only queued here. Its eventual outcome comes from the worker
      // and the next authoritative read; never optimistically mark it complete.
      await refresh({ background: true });
      return true;
    } catch (requestError) {
      if (mounted.current) setActionError(requestError);
      return false;
    } finally {
      actionInFlight.current = false;
      if (mounted.current) setPendingAction(null);
    }
  }, [refresh]);

  const saveJob = useCallback(async (job, id = null) => {
    if (!enabledRef.current || actionInFlight.current) return false;
    actionInFlight.current = true;
    setPendingAction(id ? `${id}:save` : 'create');
    setActionError(null);
    try {
      const response = await callRef.current({
        url: id ? `${API}admin/sync-jobs/${id}/` : `${API}admin/sync-jobs/`,
        method: id ? 'PATCH' : 'POST', body: job, silent: true, rawError: true, timeout: 25000,
      });
      if (![200, 201].includes(response?.status)) {
        throw new Error(responseError(response, 'Could not save this sync job.'));
      }
      await refresh({ background: true });
      return true;
    } catch (requestError) {
      if (mounted.current) setActionError(requestError);
      return false;
    } finally {
      actionInFlight.current = false;
      if (mounted.current) setPendingAction(null);
    }
  }, [refresh]);

  return {
    insights, jobs, runs, loading, refreshing, error, jobsError, runsError, actionError,
    pendingAction, lastUpdatedAt, refresh, performJobAction, saveJob,
  };
}
