# Fabrything — project map

Read this before exploring. It exists so a fresh session does not have to
re-derive the layout with Glob/Grep. If something here contradicts the code,
the code wins — fix this file in the same commit.

## Stack & layout

Django 5 + DRF backend, Create-React-App (React 18 + MUI 5 + Redux Toolkit)
frontend, Postgres (Neon) in prod. Backend deploys to Render
(`https://fabrythingweb.onrender.com`), frontend to Vercel (fabrything.com).

```
backend/EcommerceInventory/     Django project (manage.py lives here)
  config/settings/{base,dev,prod,test}.py   dev is the manage.py default
  accounts/    custom User (roles), auth, dynamic-form controllers
  core/        helpers.py, middleware, S3/local file upload view
  catalog/ inventory/ purchasing/ orders/   original ERP/inventory domain
  storefront/  public e-commerce storefront API
  food/        food-delivery marketplace  ← most active area
frontend/ecommerce_inventory/src/
  pages/       admin panel (Auth.js, DynamicForm.js, food/, products/, users/…)
  food/        customer-facing food ordering (pages/, components/, redux/, context/)
  vendor/      restaurant-owner panel
  rider/       RiderDashboard.js
  storefront/  public shop
  hooks/       APIHandler.js (useApi → callApi), apiCache, useCachedApi
  utils/       config.js (API base), ProtectedRoute, VendorRoute, Helper
  layout/      shell + MUI theme
```

## Conventions that bite

- **Response envelope.** `core.helpers.renderResponse` returns `{data, message}`
  on 2xx but **a different shape on errors**: `{errors, field_errors, message}`,
  where `errors` is a flat list of messages and `field_errors` is the original
  `{field: [messages]}` map. Read `field_errors` to attribute an error to an
  input. `EnvelopeModelViewSetMixin` (`food/views_vendor.py`) wraps ModelViewSet
  and sends the literal message `"Validation error"` on a 400, so the `message`
  alone never identifies the offending field.
- **`callApi` swallows HTTP errors** — it returns `null` on any non-2xx unless
  the caller passes `rawError: true`, which returns the axios error response.
- **No default auth class.** `REST_FRAMEWORK` sets no
  `DEFAULT_AUTHENTICATION_CLASSES`; every authenticated view must declare
  `authentication_classes = [JWTAuthentication]` or `request.user` is anonymous
  despite a valid bearer token.
- **Roles** live on `accounts.User.role` (string, not a group): `Super Admin`,
  `Admin`, `Supplier`, `Customer`, `Staff`, `Restaurant`, `Rider`.
  Food permission classes: `IsRestaurantOwner`, `IsRider`, `IsPlatformAdmin`
  (`food/permissions.py`).
- **Login redirect is role-blind.** `pages/Auth.js` sends every successful login
  to `/admin/home`. Non-admin roles land on an empty admin dashboard.
- **Image fields are `URLField`, not `ImageField`** (`FoodItem.image`,
  `Restaurant.logo/cover_image`). Upload goes through
  `POST /api/uploads/` (`core/views.FileUploadViewInS3` — S3 when AWS keys are
  set, otherwise local `MEDIA_ROOT`) which returns a URL you then store.
- **`FoodItem.category_id` is a ForeignKey literally named `category_id`.**
  Not a raw id column. Serializers expose it as a pk int.
- Admin sidebar modules are DB-driven — a new admin page needs a module row
  seeded before it appears live (see `food/management/commands/seed_food_modules.py`).

## API surface

Root mounts (`config/urls.py`): `api/auth/`, `api/getForm/<model>/`,
`api/getMenus/`, `api/products/`, `api/inventory/`, `api/orders/`,
`api/uploads/`, `api/store/`, `api/food/`.

`api/food/` (`food/urls.py`) — public `restaurants/`, `restaurants/<slug>/`,
`zones/`; customer `orders/`, `orders/<order_code>/`; vendor `vendor/restaurant/`,
`vendor/orders/…` + router `vendor/{categories,items,coupons}`; admin
`admin/dashboard/`, `admin/orders/…`, `admin/orders/<pk>/assign/`,
`admin/payments/`, `admin/settlements/{,summary/,bulk/,<pk>/leg/}`,
`admin/zone-tree/`, `admin/menu/copy/` + router
`admin/{restaurants,zones,villages,categories,items,option-groups,options,coupons,riders}`;
rider `rider/{me,availability,heartbeat,orders,earnings,orders/<pk>/status}`; plus
`coupons/validate/`, `notifications/`, `loyalty/`.

## food/ module

20 models in `food/models.py`: `DeliveryZone`, `Village`, `Restaurant`,
`RestaurantHours`, `RestaurantZone`, `FoodCategory`, `FoodItem`,
`FoodItemOptionGroup`, `FoodItemOption`, `Coupon`, `FoodOrder`, `FoodOrderItem`,
`PaymentTransaction`, `OrderSettlement`, `Rider`, `RiderEarning`, `Notification`,
`LoyaltyAccount`, `LoyaltyLedger` (all inherit `TimeStamped`).

Views are split by audience, not by model:
`views_public` · `views_vendor` · `views_admin` · `views_admin_menu` ·
`views_admin_dashboard` · `views_orders` · `views_settlement` (settlements +
zone/village admin) · `views_food_ext` (coupons, riders, dispatch,
notifications, loyalty, payments). Serializers mirror the same split
(`serializers_admin_menu.py`, `serializers_orders.py`, `serializers_write.py`, …).
Business logic in `services.py` / `services_admin.py` / `services_settlement.py`;
geography in `geo.py`.

`FoodOrder` has a forward-only state machine (`ALLOWED_TRANSITIONS`):
PLACED → CONFIRMED → PREPARING → OUT_FOR_DELIVERY → DELIVERED, CANCELLED
reachable from any non-terminal state. Money is snapshotted at creation.

`transition_to()` is the **single choke point** for status changes — rider,
vendor and admin views all route through it. Reaching DELIVERED calls
`services_settlement.settle_order()` there, so the ledger can't be bypassed by
adding another endpoint.

### Settlement ledger (the Payments tab)

`OrderSettlement` is created per delivered order and **snapshots** the
commission rate and rider base pay, so changing `Restaurant.commission_percentage`
never moves past books. Derivation (`services_settlement.compute_breakdown`):

```
food_net          = subtotal - discount        # discount is borne by the restaurant
commission        = food_net * commission_rate%
restaurant_payout = food_net - commission
rider_payout      = rider_base_pay + tip       # base pay 0 when no rider
platform_revenue  = commission + delivery_fee - rider_base_pay
```

Invariant pinned by tests: `restaurant_payout + rider_payout + platform_revenue
== order.total`. Four independent legs settle on their own clocks —
`customer_payment`, `rider_cash`, `rider_payout`, `restaurant_payout` (see
`OrderSettlement.LEGS`); a leg is `NA` when there's no money in it (prepaid
order has no rider cash; unassigned order has no rider payout).

Delivery is scoped to Bancharampur: 13 unions (`DeliveryZone`) + 121 villages,
per-zone fees, Leaflet map picker. Zones and villages both carry `name` and
`name_bn`; **display rule is Bangla with English fallback** (`name_bn or name`)
— serializers expose this as `display_name`.

`seed_bancharampur` is **create-only**. It runs on every deploy, so an
`update_or_create` there silently reverted admin edits each release; it now only
fills a *blank* `name_bn` and leaves existing rows alone unless
`--force-update` is passed. `food/tests/test_seed_preserves_edits.py` pins this
— do not "simplify" it back to `update_or_create`.

Rider presence: `Rider.current_lat/current_lng/last_seen_at` are set by a
heartbeat the rider dashboard posts ~every 20s while Online. `Rider.is_online`
(property) mirrors the dispatch filter in `services_dispatch.available_riders()`
— `is_available` is the rider's own switch, `is_online` is the heartbeat. Both
must hold to be dispatchable. Orders still reach a rider only via manual admin
assignment in `ManageFoodOrders`.

Riders have **no self-serve signup or password reset**. An admin creates the
login alongside the rider and can set a password via
`POST admin/riders/<pk>/reset-password/`. `RiderSerializer` exposes `username`
so the admin panel can hand over working credentials.

### Traps that have bitten this module

- **Creating a User before the thing it belongs to.** Both rider and restaurant
  onboarding do this. Without `transaction.atomic`, a later failure commits the
  orphan `User`, which then owns the username forever and makes every retry fail
  with "A user with that email/username already exists" — with no row in the
  admin panel to delete. Both paths are atomic now; `prune_orphan_logins`
  (dry-run by default) cleans up accounts stranded before the fix.
- **Silent empty states hiding 500s.** `callApi` returns `null` on any non-2xx,
  so `res?.data?.data || []` renders a cheerful "No riders yet" when the API is
  actually failing. Pass `rawError: true` and show the error on any admin list
  that matters.
- **Two different list envelopes.** `EnvelopeModelViewSetMixin` returns a flat
  `{data: [...]}`; `CommonListAPIMixin.common_list_decorator` returns a *nested*
  `{data: {data: [...], totalPages, totalItems}}`. Reading the wrong one is what
  broke the admin Food Orders page (commit 45ee192). Check which mixin the view
  uses before parsing.
- **`get_queryset` must return a QuerySet, not a list.** `common_list_decorator`
  calls `.filter()`/`.order_by()` on it. `PublicRestaurantListView` therefore
  annotates distance with SQL math functions (`_haversine_expr`) instead of
  sorting in Python.

### Customer discovery (homepage rows + Browse page)

All three shapes are `GET api/food/restaurants/`:

| Row | Query |
| --- | --- |
| Nearest to your area | `?zone=&lat=&lng=&sort=distance` |
| Restaurants you may also like | `?zone=&sort=popular&exclude=<nearest ids>` |
| Browse Restaurants (`/food/restaurants`) | `?all=true&zone=` |

`sort=popular` counts **delivered** orders only. `all=true` stops `zone` from
filtering and instead annotates `delivers_to_zone`, so the Browse page can list
every restaurant and mark the un-orderable ones. `distance_km` is null when the
restaurant has no `pickup_lat/lng`; those sort last (`nulls_last=True`).
The homepage falls back to the zone centre when the customer has no dropped pin.

### Food theme (light/dark)

`getFoodTheme(mode)` builds from `FOOD` / `FOOD_DARK` tokens; `foodTokens(mode)`
exposes them for components needing a raw colour. `FoodThemeProvider`
(`food/context/FoodThemeContext.js`) owns the `ThemeProvider`, persists to
`localStorage.food_theme`, and follows the OS setting **only until** the user
picks explicitly. The toggle lives in the food header; the admin panel and
storefront are unaffected (the storefront has its own `sf_dark` mechanism).

Components must use palette slots (`divider`, `background.paper`, `primary.main`)
or an `sx` theme callback — importing `FOOD` directly pins them to light mode.
The few remaining direct `FOOD.*` imports (`RestaurantCard`, `RestaurantDetail`,
`FoodOrderTrack`) are semantic accents that read correctly on both canvases.

## Commands

```bash
# backend (from backend/EcommerceInventory, venv at .venv)
# Tests REQUIRE config.settings.test — it uses SQLite. The manage.py default is
# config.settings.dev, which points at a local Postgres that usually isn't running.
DJANGO_SETTINGS_MODULE=config.settings.test python manage.py test food
python manage.py migrate
python manage.py runserver

# Repair / maintenance (all idempotent; the first two run in build.sh)
python manage.py seed_bancharampur          # create-only; --force-update to overwrite
python manage.py backfill_settlements       # settlements for pre-ledger delivered orders
python manage.py prune_orphan_logins        # dry run; --apply to actually delete

# frontend (from frontend/ecommerce_inventory)
npm start        # CRA dev server
npm test         # react-scripts test (jest + RTL); tests sit beside sources
npm run build    # CI=false — see below
```

**The build is `CI=false react-scripts build`** (pinned in both `package.json`
and `vercel.json`). The repo carries many pre-existing lint warnings, and CRA
turns warnings into errors when `CI=true`, which Vercel sets by default — so a
plain `react-scripts build` fails while the real deploy succeeds. Verify with
`CI=false npx react-scripts build`; only treat *new* warnings in your own files
as something to fix.

Specs and design docs live in `docs/superpowers/specs/`.

<!-- code-review-graph MCP tools -->
## MCP Tools: code-review-graph

> **Status (2026-07-22).** Works on the **Linux** checkout at
> `/home/billsbro/Music/fabrythingweb` (the path `.mcp.json` hardcodes), where
> `list_graph_stats_tool` returns 714 nodes / 6704 edges over 133 files. It is
> **unavailable on the Windows clone** (`C:\Users\bhnbi\Music\SaaS\fabrythingweb`)
> because of that hardcoded path plus a missing `code_review_graph` in
> `backend/EcommerceInventory/.venv`.
>
> Two caveats even where it works: the graph was **last built 2026-07-16**, so
> everything from `52ca617` onward (riders, coupons, settlements, Bancharampur
> zones) is missing — run `build_or_update_graph_tool` before trusting it.
> And `embeddings_count` is 0, so `semantic_search_nodes` does nothing until
> `sentence-transformers` is installed. Structural queries (`query_graph`,
> `get_impact_radius`) work regardless.
>
> **Read the project map above first either way** — it is maintained by hand and
> is current.

**IMPORTANT: This project has a knowledge graph. ALWAYS use the
code-review-graph MCP tools BEFORE using Grep/Glob/Read to explore
the codebase.** The graph is faster, cheaper (fewer tokens), and gives
you structural context (callers, dependents, test coverage) that file
scanning cannot.

### When to use graph tools FIRST

- **Exploring code**: `semantic_search_nodes` or `query_graph` instead of Grep
- **Understanding impact**: `get_impact_radius` instead of manually tracing imports
- **Code review**: `detect_changes` + `get_review_context` instead of reading entire files
- **Finding relationships**: `query_graph` with callers_of/callees_of/imports_of/tests_for
- **Architecture questions**: `get_architecture_overview` + `list_communities`

Fall back to Grep/Glob/Read **only** when the graph doesn't cover what you need.

### Key Tools

| Tool | Use when |
| ------ | ---------- |
| `detect_changes` | Reviewing code changes — gives risk-scored analysis |
| `get_review_context` | Need source snippets for review — token-efficient |
| `get_impact_radius` | Understanding blast radius of a change |
| `get_affected_flows` | Finding which execution paths are impacted |
| `query_graph` | Tracing callers, callees, imports, tests, dependencies |
| `semantic_search_nodes` | Finding functions/classes by name or keyword |
| `get_architecture_overview` | Understanding high-level codebase structure |
| `refactor_tool` | Planning renames, finding dead code |

### Workflow

1. The graph auto-updates on file changes (via hooks).
2. Use `detect_changes` for code review.
3. Use `get_affected_flows` to understand impact.
4. Use `query_graph` pattern="tests_for" to check coverage.
