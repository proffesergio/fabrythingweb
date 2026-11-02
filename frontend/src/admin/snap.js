export function readSnap(key) {
  try {
    const raw = JSON.parse(localStorage.getItem(key) || 'null');
    return raw && raw.data !== undefined ? raw.data : null;
  } catch { return null; }
}

export function writeSnap(key, data) {
  try { localStorage.setItem(key, JSON.stringify({ at: Date.now(), data })); } catch { /* private mode */ }
}
