import { jwtDecode } from 'jwt-decode';
import { getToken } from '../utils/authToken';

// Never reuse a previous operator's financial snapshot on a shared device.
function scopedKey(key) {
  try {
    const token = getToken();
    const user = token && jwtDecode(token);
    return user?.user_id ? `admin-snap:v2:${user.user_id}:${key}` : null;
  } catch { return null; }
}

export function readSnap(key) {
  try {
    const scoped = scopedKey(key);
    if (!scoped) return null;
    const raw = JSON.parse(localStorage.getItem(scoped) || 'null');
    return raw && Date.now() - raw.at < 15 * 60 * 1000 && raw.data !== undefined ? raw.data : null;
  } catch { return null; }
}

export function writeSnap(key, data) {
  try {
    const scoped = scopedKey(key);
    if (scoped) localStorage.setItem(scoped, JSON.stringify({ at: Date.now(), data }));
  } catch { /* private mode */ }
}
