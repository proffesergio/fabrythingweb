// Guest order registry: guests have no account, so the order codes they
// placed live here — surviving browser restarts via localStorage. The phone
// stays attached (the track endpoint needs code + phone), and a manual
// code+phone entry covers cleared storage / incognito / new devices.

const KEY = 'food_guest_orders';
const MAX = 20;
const TTL_MS = 30 * 24 * 3600 * 1000; // 30 days

export function readGuestOrders() {
  try {
    const raw = JSON.parse(localStorage.getItem(KEY) || '[]');
    if (!Array.isArray(raw)) return [];
    const fresh = raw.filter((o) => o && o.code && (!o.at || Date.now() - o.at < TTL_MS));
    if (fresh.length !== raw.length) {
      try { localStorage.setItem(KEY, JSON.stringify(fresh)); } catch { /* ignore */ }
    }
    return fresh;
  } catch { return []; }
}

export function recordGuestOrder({ code, phone, restaurant, total }) {
  if (!code) return;
  try {
    const list = readGuestOrders().filter((o) => o.code !== code);
    list.unshift({
      code, phone: phone || '',
      restaurant: restaurant || '', total: total ?? null, at: Date.now(),
    });
    localStorage.setItem(KEY, JSON.stringify(list.slice(0, MAX)));
  } catch { /* ignore */ }
}

export function removeGuestOrder(code) {
  try {
    localStorage.setItem(KEY, JSON.stringify(readGuestOrders().filter((o) => o.code !== code)));
  } catch { /* ignore */ }
}
