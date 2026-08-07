// Where a sidebar click should actually take you.
//
// Top-level modules like Products, Orders, Inventory, Settings, Food and
// Custom Printing are seeded with NO module_url -- they are containers for
// their submenus (see accounts/management/commands/seed_admin_modules.py).
// The old handler navigated only for items with no submenus, so clicking any
// of those six expanded a list and changed nothing else, which reads as a dead
// button: the page stays put and the console just shows the menus reloading.
//
// A container now falls through to its first navigable child, which is what a
// user means by "open Products".

/** The first submenu (depth-first) that actually has a URL, or null. */
export function firstNavigableChild(item) {
  const submenus = item?.submenus || [];
  for (const child of submenus) {
    if (child?.module_url) return child;
    const deeper = firstNavigableChild(child);
    if (deeper) return deeper;
  }
  return null;
}

/**
 * The menu item a click should activate, or null when there is genuinely
 * nowhere to go (a container whose children all lack URLs).
 *
 * Returns the item itself when it has its own URL -- a container with BOTH a
 * URL and children must open its own page rather than skip to a child.
 */
export function resolveMenuTarget(item) {
  if (!item) return null;
  if (item.module_url) return item;
  return firstNavigableChild(item);
}

/**
 * Admin routes are mounted under /admin (see App.js), but module_url is seeded
 * without that prefix. Idempotent so an already-prefixed URL is left alone.
 */
export function toAdminPath(moduleUrl) {
  if (!moduleUrl) return null;
  return moduleUrl.startsWith('/admin') ? moduleUrl : `/admin${moduleUrl}`;
}

/** True when clicking this item should also toggle its submenu list. */
export function isExpandable(item) {
  return !!(item?.submenus && item.submenus.length > 0);
}
