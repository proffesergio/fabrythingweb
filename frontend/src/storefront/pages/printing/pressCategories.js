// ColorLifePrint-style catalog taxonomy for the web-to-press storefront.
// NAV drives the top category bar; STRIP drives the "Products Categories"
// carousel. Keys match printing.PrintShowcaseItem categories on the backend,
// so admin uploads appear in the right tile automatically.

export const PRESS_NAV = [
  { label: 'Business Cards', category: 'business-cards' },
  { label: 'Flyers & Brochures', category: 'flyers-brochures' },
  { label: 'Office & Packaging', category: 'office-packaging' },
  { label: 'Stickers & Labels', category: 'stickers-labels' },
  { label: 'Signage & Outdoor Branding', category: 'signage-outdoor', badge: 'OFFER' },
  { label: 'Promotional Products', category: 'promotional' },
  { label: 'Urgent Print', category: null },
  { label: 'Design Support', category: null, badge: 'FREE' },
];

export const PRESS_STRIP = [
  { key: 'box-packaging', title: 'Box & Packaging' },
  { key: 'brochures-catalogues', title: 'Brochures & Catalogues' },
  { key: 'business-cards', title: 'Business Cards' },
  { key: 'corporate-stationery', title: 'Corporate Stationery' },
  { key: 'flags-display', title: 'Flags & Outdoor Display' },
  { key: 'flyers-leaflets', title: 'Flyers & Leaflets' },
  { key: 'flyers-brochures', title: 'Flyers & Brochures' },
  { key: 'large-format', title: 'Large Format Printing' },
  { key: 'letterheads', title: 'Letterheads' },
  { key: 'stickers-labels', title: 'Stickers & Labels' },
  { key: 'posters', title: 'Posters' },
  { key: 'promotional', title: 'Promotional Products' },
];

export const PRESS_BADGES = ['', 'HOT', 'NEW', 'OFFER'];

export function categoryTitle(key) {
  return (PRESS_STRIP.find((c) => c.key === key) || {}).title || key || '—';
}

const WISHLIST_KEY = 'press_wishlist';

export function readWishlist() {
  try {
    return new Set(JSON.parse(localStorage.getItem(WISHLIST_KEY) || '[]'));
  } catch {
    return new Set();
  }
}

export function toggleWishlist(id) {
  const set = readWishlist();
  if (set.has(id)) set.delete(id);
  else set.add(id);
  try {
    localStorage.setItem(WISHLIST_KEY, JSON.stringify([...set]));
  } catch { /* private mode */ }
  return set;
}
