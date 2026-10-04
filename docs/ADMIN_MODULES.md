# Modular Admin — Shop / Food / News

One admin shell, three businesses. A top switcher (Shop / Food / News)
swaps the sidebar menu, landing dashboard, brand mark, and analytics.
Shared items (Dashboard, Settings, Live Chat, Traffic & Analytics) appear
in every module under a Shared group.

## Routes (all existing paths preserved)

- `/admin` → redirects to the last-used module home
- `/admin/shop`, `/admin/food`, `/admin/news` → per-module overview dashboards
- `/admin/home` → legacy generic dashboard (still linked from Shared)
- Every `/admin/manage/*` page keeps its exact path; the switcher follows
  the route (food/* → Food, nobleseek → News, other manage/* → Shop) and
  shared pages (users, analytics, chat, home) keep the current module.

## Menus — backend-driven

`accounts.Modules.module` tags each menu (`shop`/`food`/`news`/`shared`,
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

## Keep-alive (free-tier sleep)

Render sleeps the backend after ~15 min idle, which used to mean every
dashboard load paid a 30–60s cold start. Two layers now:

1. `useKeepAlive()` (`src/admin/keepAlive.js`) pings public
   `GET /api/health/` every 9 minutes — mounted in the admin Layout and
   the app root, visibility-guarded (background tabs cost nothing),
   fully silent. Keeps the service warm while anyone has a tab open.
2. For true 24/7 warmth with zero visitors, add an external monitor
   (e.g. UptimeRobot free, 5-min interval) on
   `https://<api>/api/health/` — frontend pings can't cover idle nights.

## Files

- Frontend: `src/admin/modules/` (registry, context, switcher, sidebar,
  bell, index redirect), `src/admin/widgets.jsx`, `src/admin/pages/`
  (`ShopOverview`, `FoodOverview`, `NewsOverview`, `useOverview`),
  `src/admin/keepAlive.js`, `src/admin/snap.js`
- Backend: `analytics/views_overview.py`, `nobleseek` overview view,
  `Modules.module` + seeder tags
