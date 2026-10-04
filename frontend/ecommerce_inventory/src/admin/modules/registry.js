// Module registry for the modular admin shell.
//
// Menus themselves stay backend-driven (Modules table → getMenus → redux),
// so permissions keep working with zero duplication. This registry only maps
// each business to its brand, home dashboard, overview API and drill targets,
// plus the pure helpers that slice backend menus per active module.

export const SHARED = 'shared';

export const MODULES = {
  shop: {
    id: 'shop',
    label: 'Fabrything Shop',
    short: 'Shop',
    icon: 'Storefront',
    color: '#E85D4A',
    home: '/admin/shop',
    overviewApi: 'store/analytics/admin/shop-overview/',
    searchTarget: '/admin/manage/product',
  },
  food: {
    id: 'food',
    label: 'Fabrything Food',
    short: 'Food',
    icon: 'Restaurant',
    color: '#2E7D32',
    home: '/admin/food',
    overviewApi: 'store/analytics/admin/food-overview/',
    searchTarget: '/admin/manage/food/orders',
  },
  news: {
    id: 'news',
    label: 'NobleSeek News',
    short: 'News',
    icon: 'Newspaper',
    color: '#F2631F',
    home: '/admin/news',
    overviewApi: 'store/nobleseek/admin/overview/',
    searchTarget: '/admin/manage/nobleseek',
  },
};

export const MODULE_ORDER = ['shop', 'food', 'news'];
export const NOTIFICATIONS_API = 'store/analytics/admin/notifications/';

/** Which module a route belongs to. Shared pages return null (keep current). */
const SHARED_PATHS = ['/admin/home', '/admin/form', '/admin/create',
  '/admin/manage/users', '/admin/manage/moduleurls',
  '/admin/manage/analytics', '/admin/manage/chat'];
export function moduleForPath(pathname = '') {
  if (pathname === '/admin/shop') return 'shop';
  if (pathname === '/admin/food') return 'food';
  if (pathname === '/admin/news') return 'news';
  if (pathname.startsWith('/admin/manage/food')) return 'food';
  if (pathname.startsWith('/admin/manage/nobleseek')) return 'news';
  if (SHARED_PATHS.some((p) => pathname === p || pathname.startsWith(`${p}/`))) return null;
  if (pathname.startsWith('/admin/')) return 'shop';
  return null;
}

/** Module ids the user can see, from granted menu tags. Legacy (untagged) or
 *  empty menus → all modules, so an un-reseeded backend never blanks the UI. */
export function visibleModules(items) {
  const tags = new Set();
  const walk = (list) => (list || []).forEach((it) => {
    if (it && it.module && MODULES[it.module]) tags.add(it.module);
    walk(it && it.submenus);
  });
  walk(items);
  if (!items || items.length === 0 || tags.size === 0) return [...MODULE_ORDER];
  return MODULE_ORDER.filter((m) => tags.has(m));
}

/** Split top-level menus into the active module's items + shared group.
 *  Untagged items on a tagged backend are treated as shared (safe default);
 *  on a fully untagged backend everything stays visible (legacy mode). */
export function splitItems(items, module) {
  const mine = [];
  const shared = [];
  if (!items || items.length === 0) return { mine, shared };
  const hasTags = items.some((it) => it && it.module);
  items.forEach((it) => {
    if (!hasTags) { mine.push(it); return; }
    const tag = it.module || SHARED;
    if (tag === module) mine.push(it);
    else if (tag === SHARED) shared.push(it);
  });
  return { mine, shared };
}

/** Sidebar quick-find: keep an item when it or any descendant matches. */
export function filterMenuItems(items, query) {
  const q = String(query || '').trim().toLowerCase();
  if (!q) return items || [];
  const hit = (it) => (it.module_name || '').toLowerCase().includes(q)
    || (it.submenus || []).some(hit);
  return (items || []).filter(hit);
}
