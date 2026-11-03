# Modular Admin — Shop / Food / News / Custom Printing

One admin shell, four businesses. The top switcher selects the business's
Control Center, permission-filtered sidebar, brand mark and analytics.
The dark Control Center theme is the default; other theme choices remain available.
Shared management tools appear in every module under a Shared group.

## Routes (all existing paths preserved)

- `/admin` → redirects to the last-used module home
- `/admin/shop`, `/admin/food`, `/admin/news`, `/admin/print` → Control Centers
- Each center has Operations and searchable Management tools tabs. Shop also has
  Automation & insights and Business report tabs, preserving the prior dashboards.
- `/admin/shop/control-center` → `/admin/shop?tab=automation` (legacy link)
- `/admin/home` → last-used permitted module; the legacy generic dashboard is
  preserved in Shop's Business report tab.
- Every `/admin/manage/*` page keeps its exact path; the switcher follows
  the route (food/* → Food, nobleseek → News, other manage/* → Shop) and
  shared pages (users, analytics, chat, home) keep the current module.

## Menus — backend-driven

`accounts.Modules.module` tags each menu (`shop`/`food`/`news`/`print`/`shared`,
children inherit the parent; migration `0005`). `seed_admin_modules`
writes the tags on every deploy via `MODULE_OF`. `getMenus/` already
permission-filters, so a user only ever sees modules they are granted.
Frontends with no tags (stale cache, old tests) render unfiltered —
the UI never blanks.

Frontend mirror: `src/admin/modules/registry.js` (brand map + pure
helpers `moduleForPath`, `visibleModules`, `splitItems`,
`filterMenuItems` — covered by `registry.test.js`).

## Overview APIs (staff-only, `?days=14|30`)

- `GET /api/store/analytics/admin/shop-overview/` — revenue/orders/AOV,
  14–30d series, top products, recent orders, alerts (pending verification,
  low/out-of-stock). Canceled/returned orders excluded from money.
- `GET /api/store/analytics/admin/food-overview/` — GMV/orders, active
  restaurants, online riders (heartbeat presence), top restaurants, recent
  orders, alerts (unconfirmed, pending partners, cash to collect).
- `GET /api/store/nobleseek/admin/overview/` — desk KPIs, publishing
  activity series, top stories by views, alerts (review queue, scheduled,
  trends inbox, empty sections).
- `GET /api/store/analytics/admin/notifications/` — `{shop, food, news,
  total}` pending-count rollup for the topbar bell.
- Non-platform roles get **403** by design (domain sub-accounts stay on
  their tenant pages, never platform-wide numbers).

Tests: `analytics/test_overview.py` (incl. seed-tag test),
`nobleseek/tests.py::NobleSeekOverviewTests`.

## Keep-alive (retired)

The backend now runs on Vercel Functions (`https://fabrythingapi.vercel.app`)
instead of Render's sleep-prone free tier, so the Render keep-alive workaround
was removed from the app and the GitHub Actions cron was deleted. Vercel
Functions scale on demand; no warm-up pings are needed.

## Files

- Frontend: `src/admin/modules/` (registry, context, switcher, sidebar,
  bell, index redirect), `src/admin/widgets.jsx`, `src/admin/pages/`
  (`ShopOverview`, `FoodOverview`, `NewsOverview`, `useOverview`),
  `src/admin/snap.js`
- Backend: `analytics/views_overview.py`, `nobleseek` overview view,
  `Modules.module` + seeder tags

## Access and cached reports

The admin shell requires an authenticated administrative role. API permissions
remain authoritative: middleware rejects unauthorized requests before executing
views, and platform-wide Food actions exclude tenant administrators. Explicit
"Skip Permission" URLs remain supported by the module URL editor.

Menu/report caches are scoped to the signed-in user. Report snapshots expire
after 15 minutes and use separate date-range keys. Date changes ignore outdated
responses; failed requests expose retry controls. Logout reloads the application
to clear the previous user's in-memory state.
