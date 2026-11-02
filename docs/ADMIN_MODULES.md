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
