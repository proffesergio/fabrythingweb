// Versioned localStorage cache for GET responses (stale-while-revalidate).
//
// Bump CACHE_VERSION whenever a response shape changes or you need every client
// to drop its cached copies on the next load — old-version entries are ignored
// by readCache, so a stale cache can never permanently hide new data.
// v2: restaurant responses gained is_open_now, next_open, opening_hours and
// served_zone_ids. A v1 entry would render "Open now" from the old
// master-switch field, and would let a closed restaurant's menu reach the bag.
export const CACHE_VERSION = "v2";
const PREFIX = `swr:${CACHE_VERSION}:`;

export function cacheKey(url, params) {
    const p = params && Object.keys(params).length ? JSON.stringify(params) : "";
    return `${PREFIX}${url}${p ? "?" + p : ""}`;
}

export function readCache(key) {
    try {
        const raw = localStorage.getItem(key);
        if (!raw) return null;
        const parsed = JSON.parse(raw);
        if (!parsed || parsed.v !== CACHE_VERSION) return null;
        return parsed; // { v, ts, data }
    } catch {
        return null;
    }
}

export function writeCache(key, data) {
    try {
        localStorage.setItem(key, JSON.stringify({ v: CACHE_VERSION, ts: Date.now(), data }));
    } catch {
        // localStorage full or unavailable (private mode) — caching is best-effort.
    }
}

export function isFresh(entry, ttlMs) {
    if (!entry || !ttlMs) return false;
    return Date.now() - entry.ts < ttlMs;
}
