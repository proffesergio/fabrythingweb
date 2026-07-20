import { useState, useEffect, useCallback, useRef } from "react";
import axios from "axios";
import config from "../utils/config";
import { cacheKey, readCache, writeCache } from "./apiCache";

/**
 * Stale-while-revalidate GET hook.
 *
 * On mount it returns any cached copy instantly (no spinner), then fetches fresh
 * data in the background and swaps it in. If the network fails, the stale copy is
 * kept rather than wiped — so a cold/sleeping backend never blanks the page.
 *
 * Returns { data, loading, revalidating, error, refetch }.
 *  - data:         unwrapped response payload (res.data.data ?? res.data)
 *  - loading:      true only on the very first load with no cache
 *  - revalidating: true while a background refresh is in flight
 */
export default function useCachedApi(url, { params = {}, enabled = true } = {}) {
    const key = cacheKey(url, params);
    const initial = enabled ? readCache(key) : null;
    const [data, setData] = useState(initial ? initial.data : null);
    const [loading, setLoading] = useState(enabled && !initial);
    const [revalidating, setRevalidating] = useState(false);
    const [error, setError] = useState(null);
    const paramsRef = useRef(params);
    paramsRef.current = params;

    const fetchFresh = useCallback(async () => {
        setRevalidating(true);
        try {
            const headers = {};
            const token = localStorage.getItem("token");
            if (token) headers.Authorization = `Bearer ${token}`;
            const res = await axios.get(config.API_URL + url, { params: paramsRef.current, headers });
            const payload = res?.data?.data ?? res?.data;
            setData(payload);
            writeCache(cacheKey(url, paramsRef.current), payload);
            setError(null);
        } catch (e) {
            setError(e);
            // Intentionally keep any stale cached data on failure.
        } finally {
            setLoading(false);
            setRevalidating(false);
        }
    }, [url]);

    useEffect(() => {
        if (!enabled) return;
        const entry = readCache(key);
        if (entry) { setData(entry.data); setLoading(false); }
        fetchFresh();
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [key, enabled]);

    return { data, loading, revalidating, error, refetch: fetchFresh };
}
