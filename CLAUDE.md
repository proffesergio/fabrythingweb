# Fabrything — project map

Read this before exploring. It exists so a fresh session does not have to
re-derive the layout with Glob/Grep. If something here contradicts the code,
the code wins — fix this file in the same commit.

**Exploration budget.** In order, cheapest first — stop as soon as you can act:
1. This file. The layout, the API surface and the traps below are current.
2. A targeted `Grep` for a **symbol** (`grep -rn "domain_user_id\.id"`), not a
   concept. One grep across the repo beats opening five files to compare them.
3. Run the tests (~200, ~5s) — they answer "is the code broken?" far more cheaply
   than reading the code does, and they tell you *which* layer to open.
4. Only then `Read`, and read the *one* file the evidence pointed at.

Do not open a file to confirm something already written here, do not read a
module "for context" before you have a specific question, and do not spawn a
subagent for work that is a grep and two reads. `graphify-out/` and the
code-review-graph MCP are stale (see the note at the end) — prefer grep.

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

## Diagnosing a production 500 — do this FIRST

A blank `Server Error (500)` page from `fabrythingweb.onrender.com` carries no
traceback (`DEBUG=False`). Do **not** start grepping views. Cost of the wrong
order here has been measured in whole sessions.

1. **`curl https://fabrythingweb.onrender.com/api/health/`** (`core.views.HealthView`).
   It reports `pending_migrations` and answers 503 when the schema lags the code.
   *A schema that lags the deployed code is the single most common cause of a
   cluster of unrelated 500s* — it has happened twice.
2. **Does the failure set share a table?** Group the failing URLs by the model
   they touch before suspecting any view. `rider/me` + `rider/orders` +
   `rider/earnings` + `admin/riders` + `admin/dashboard` all failing at once is
   not five bugs, it is one missing column on `food_rider`.
3. **Run the suite before reading code**: `DJANGO_SETTINGS_MODULE=config.settings.test
   python manage.py test`. ~200 tests, ~5s. **Green suite + broken prod ⇒ the bug
   is environmental, not in the code** — stop reading views and go look at the
   database or the deploy.
4. Only then read source, and only the views for the *shared* model from step 2.

**Query the live DB directly** instead of guessing (read-only is safe):

```bash
# neonctl is authenticated; the MCP server may be bound to the WRONG Neon org
# (it saw only the "neWell" org, which does not contain this project).
export DBURL="$(npx -y neonctl connection-string --project-id crimson-wind-60301476)"
python -c "import os,psycopg; ..."   # psycopg3 — psycopg2 is NOT installed
```

Neon project `fabrything` = `crimson-wind-60301476`, org `org-restless-field-32561692`,
**one branch only** (`production`) — so there is no "migrated the wrong branch"
explanation to chase. Useful probes: `SELECT app,name FROM django_migrations`,
and `information_schema.columns` for the suspect table.

**`render.yaml` describes a service named `fabrything-api`, but the live host is
`fabrythingweb.onrender.com`** — the running service was created by hand, so its
Build Command is whatever the dashboard says and **may not be `./build.sh`**.
That is why migrations can be missing even though `build.sh` runs `migrate` under
`set -o errexit`. Never conclude "migrations ran because build.sh runs them".

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
- **`accounts.Users.domain_user_id` is nullable and is dereferenced everywhere.**
  ~25 call sites did `request.user.domain_user_id.id`, which is an
  `AttributeError` — a blank 500 — whenever it is NULL. `Users.save()` now
  self-assigns it after the INSERT (it used to only self-heal on UPDATE, so every
  account made by `create_user()` — i.e. every admin-created rider and vendor —
  was born NULL), and `accounts/0003_backfill_domain_user_id` repairs old rows.
  **Always write `user.domain_user_id_id`, never `user.domain_user_id.id`.**
- **Each audience has its OWN login route.** `/admin/auth` (admin),
  `/rider/login` (rider, `rider/RiderLogin.js`), `/auth/login` (customer +
  vendor). `utils/ProtectedRoute.js` picks the target from the path prefix.
  The customer page defaults its post-login redirect to `/`, so routing a rider
  through it silently dumps them on the storefront homepage — that was the
  reported "login bounces to fabrything.com". `utils/roleHome.js` is the single
  table mapping role → landing page; use it rather than a fresh `if role ===`.
- **Login redirect is role-blind in the admin panel.** `pages/Auth.js` sends every
  successful login to `/admin/home`. Non-admin roles land on an empty dashboard.
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
`zones/`, `delivery-quote/`, `partner/apply/`; customer `orders/`, `orders/<order_code>/`; vendor `vendor/restaurant/`,
`vendor/orders/…` + router `vendor/{categories,items,coupons}`; admin
`admin/dashboard/`, `admin/orders/…`, `admin/orders/<pk>/assign/`,
`admin/payments/`, `admin/settlements/{,summary/,bulk/,<pk>/leg/}`,
`admin/zone-tree/`, `admin/menu/copy/`, `admin/rider-cash/{,<pk>/deposit/}`,
`admin/partner/{applications/,<pk>/decision/}` + router
`admin/{restaurants,zones,villages,categories,items,option-groups,options,coupons,riders}`;
rider `rider/{me,availability,heartbeat,orders,earnings,offer,orders/<pk>/status}`; plus
`coupons/validate/`, `notifications/`, `loyalty/`.

## food/ module

24 models in `food/models.py`: `DeliveryZone`, `DeliveryPricing`, `Village`, `Restaurant`,
`RestaurantHours`, `RestaurantZone`, `FoodCategory`, `FoodItem`,
`FoodItemOptionGroup`, `FoodItemOption`, `Coupon`, `FoodOrder`, `FoodOrderItem`,
`PaymentTransaction`, `OrderSettlement`, `Rider`, `RiderEarning`, `Notification`,
`LoyaltyAccount`, `LoyaltyLedger`, `RiderCashDeposit`, `DeliveryOffer` (all inherit `TimeStamped`).

Views are split by audience, not by model:
`views_public` · `views_vendor` · `views_partner` · `views_admin` · `views_admin_menu` ·
`views_admin_dashboard` · `views_orders` · `views_settlement` (settlements +
zone/village admin) · `views_food_ext` (coupons, riders, dispatch,
notifications, loyalty, payments). Serializers mirror the same split
(`serializers_admin_menu.py`, `serializers_orders.py`, `serializers_write.py`, …).
Business logic in `services.py` / `services_admin.py` / `services_settlement.py` /
`services_partner.py` / `services_cash.py` / `services_dispatch.py`; money rates
in `pricing.py`; geography in `geo.py`.

`FoodOrder` has a forward-only state machine (`ALLOWED_TRANSITIONS`):
PLACED → CONFIRMED → PREPARING → OUT_FOR_DELIVERY → DELIVERED, CANCELLED
reachable from any non-terminal state. Money is snapshotted at creation.

`transition_to()` is the **single choke point** for status changes — rider,
vendor and admin views all route through it. Reaching DELIVERED calls
`services_settlement.settle_order()` there, so the ledger can't be bypassed by
adding another endpoint.

### Pricing (`food/pricing.py`) — the two money rules

**All money rates live in `food/pricing.py` and the `DeliveryPricing` singleton
row** (`DeliveryPricing.get_solo()`, admin-tunable without a deploy). Nothing
reads them at settlement time — every figure is snapshotted onto the order at
checkout, so a rate change never moves existing books.

1. **Commission is `max(min_commission_amount, food_net × commission_percentage%)`**,
   capped at `food_net`. A flat 12% loses money on a ৳150 rural basket; the ৳25
   floor carries it. The cap exists because a ৳25 floor on a ৳20 order would
   otherwise make `restaurant_payout` negative.
2. **Delivery is priced by distance** from the restaurant's `pickup_lat/lng` to
   the customer's pin → village centre → zone centre (in that order;
   `distance_source` records which was used). `fee = clamp(base + per_km ×
   max(0, distance − free_km))`, rounded **up** to the nearest ৳5.

`FoodOrder.distance_km` and `FoodOrder.rider_base_pay` are the snapshots;
`OrderSettlement.commission_floor` snapshots the floor alongside the rate.

**The platform can never lose money on a delivery.** `_apply_margin_backstop`
caps rider pay at `fee − platform_min_margin`. This is structural — a
misconfigured rate in the admin panel caps the *rider*, it cannot create a loss.
`max_delivery_km` (12 km) refuses the long orders where that cap would be unfair
to the rider rather than letting it bite. `per_km_fee` must stay **above**
`rider_per_km` or longer deliveries earn less; a test pins it.

`RestaurantZone.delivery_fee` is still honoured as an explicit per-zone override
(a promo rate) and outranks the formula. **The zone decides *whether* we
deliver; the pin decides *what it costs*** — so checkout sends both, and
`GET api/food/delivery-quote/` prices with the same function the order endpoint
uses, so the quote can never disagree with the charge.

### Partner self-signup

`POST api/food/partner/apply/` (public) creates `Users(role='Restaurant')` +
`Restaurant(status=PENDING)` in one `transaction.atomic` — the orphan-login trap
again. PENDING is the whole approval gate: `PublicRestaurantListView` already
filters to ACTIVE, so an unapproved restaurant is invisible for free, while the
owner can sign in and build a menu. Re-applying **updates** the first
application rather than minting a second login (a typo would otherwise strand
the applicant on the unique-username constraint). Admin approves at
`/admin/manage/food/partners`, which is where commission terms are set.

### Rider cash (`food/services_cash.py`)

On COD the platform's money is physically in a rider's pocket between delivery
and deposit. **`cash_in_hand` is derived (collections − deposits), never
stored** — a balance column would drift from the ledger on any missed write.
`RiderCashDeposit` records money coming back and settles the `rider_cash` legs
it fully covers, oldest first (a partly-covered leg is left PENDING).

The real protection is the ceiling: `pick_rider_for` skips riders over
`DeliveryPricing.rider_cash_ceiling` **for COD orders only** — they keep getting
prepaid work. If every rider is over the line the order falls through to the
admin queue, because an unassigned order is a visible problem and an unbounded
cash position is not.

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
(property) mirrors the dispatch filter in `services_dispatch.dispatchable_riders()`
— `is_available` is the rider's own switch, `is_online` is the heartbeat. Both
must hold to be dispatchable.

### Dispatch: the offer/accept cycle (`services_dispatch.py`)

A CONFIRMED order is **offered** to the nearest eligible rider, not silently
assigned. `offer_order(order)` is the single engine and is idempotent — already
assigned → no-op; live offer out → returns it (never double-offers); else offers
the next untried rider; no rider left → None, and the order waits in the admin
queue. `maybe_auto_assign_rider` is an alias for it, called on CONFIRMED.

`DeliveryOffer` (state OFFERED/ACCEPTED/REJECTED/EXPIRED, 60s TTL) is the record.
**Invariant, enforced in code not schema: at most one OFFERED offer per order.**
A rider gets **one shot per order** — a decline/expire excludes them from the
re-offer, so the cascade always moves to someone new rather than looping.

- Rider side: `GET/POST api/food/rider/offer/` (accept/decline). Accept locks
  the order and re-checks `rider_id`, so a rider can never grab an order an admin
  just gave away — that returns 409.
- Admin override: `assign_rider` (behind `admin/orders/<pk>/assign/`) sets the
  rider directly and **closes any live offer**, or a second rider could accept.
- **No job runner, so expiry is lazy.** `sweep_offers()` expires timed-out
  offers and cascades every stuck order; it runs on *every* `rider/offer/` GET
  (so online riders keep the whole cycle moving) and via the
  `sweep_delivery_offers` management command for a cron backstop — needed for
  when the offered rider closed their tab and stopped polling.

**Rider pay is the distance snapshot, everywhere.** `FoodOrder.rider_base_pay`
(set at checkout by `pricing.delivery_quote`) is what the offer card shows, what
`RiderEarning` books on DELIVERED, and what `services_settlement._base_pay_for`
settles — all three read the same field, so a rider's dashboard total can't drift
from the ledger. Orders placed before distance pricing (snapshot 0) fall back to
the flat `RIDER_BASE_PAY`/`DEFAULT_RIDER_BASE_PAY`.

Riders have **no self-serve signup or password reset**. An admin creates the
login alongside the rider and can set a password via
`POST admin/riders/<pk>/reset-password/`. `RiderSerializer` exposes `username`
so the admin panel can hand over working credentials.

Riders sign in at **`/rider/login`** (`rider/RiderLogin.js`), which posts to the
role-agnostic `store/auth/login/` and rejects any non-`Rider` role client-side.
It is login-only by design — `/auth/signup` creates `Customer` accounts, so a
rider who "signs up" there gets a customer account that can never open `/rider`
(prod really had one: user `riderbills`, role `Customer`). Adding a signup tab
means building the admin-approval flow first.

When that happens the username/email is stuck — `prune_orphan_logins` won't help,
because it only prunes `Rider`/`Restaurant` roles. Use `release_login`
(`accounts/management/commands/`), which refuses admins, accounts already owning a
Rider/Restaurant, and anything with order history, and prints the exact cascade
before acting. On Render (free plan, no Shell) set `RELEASE_LOGIN=<username>` in
the dashboard, deploy once, then **remove the variable** — same opt-in pattern as
`PRUNE_ORPHAN_LOGINS`.

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
- **A form offering options the service layer rejects.** Checkout listed all 13
  zones from `food/zones/` while `place_food_cod_order` only accepted the
  restaurant's own — every order for a restaurant nobody had assigned zones to
  died on a 400 whose message never reached the screen, because `callApi`
  returns `null` on non-2xx *and* the handler read `res.data.data` (the error
  envelope key is `errors`). Any dropdown feeding a validated endpoint must be
  sourced from the same rule the endpoint enforces.

### Delivery-zone serviceability

`food.services.served_zones(restaurant)` is the **single definition** of where a
restaurant delivers. **No `RestaurantZone` rows means "unconfigured", not
"delivers nowhere"** — it falls back to every active zone, so a freshly
onboarded restaurant is orderable instead of 400-ing every checkout. Assigning
even one zone flips it back to an explicit allow-list.

Three places must agree with it, and tests pin all three:
- `_resolve_zone` (checkout validation),
- `PublicRestaurantListView` — the zone filter and the `delivers_to_zone`
  annotation both special-case the unzoned restaurant,
- `RestaurantDetailSerializer.served_zone_ids` — **`null` means "every zone"**,
  which is also what the checkout client treats as "still loading". Returning
  null rather than enumerating keeps the detail endpoint at 5 queries
  (`test_detail_is_query_bounded`); `zones` is prefetched in `_detail_prefetch`
  for exactly that reason, so that helper returns a *tuple* of prefetches.

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

## Brand assets

Two brands, and they **never appear on the same screen**:

| Surface | Brand |
| --- | --- |
| Storefront header/drawer/footer, `/auth/login`, `/admin/auth`, admin shell | Fabrything |
| `/food/*` header, vendor panel, rider dashboard + `/rider/login`, and admin pages under `/admin/manage/food/*` | Fabrything Food |

Everything goes through **`components/BrandLogo.js`** — the only file that maps
brand + variant + canvas to a filename. Never hardcode a logo path in a
component; add the case there instead.

```jsx
<BrandLogo brand="food" variant="horizontal" mode={isDark ? 'dark' : 'light'} height={28} />
```

- **`mode` is the canvas the logo sits ON, not the theme name.** The storefront
  footer is dark in both themes, so it passes `mode="dark"` while the site is in
  light mode. Get this wrong and the logo is *invisible*, not broken — the
  artwork is monochrome-on-transparent, so there is no missing-image icon to
  notice. `BrandLogo.test.js` pins every combination.
- The food files are named `-vertical-`, the Fabrything ones `-stacked-`.
  `BrandLogo` absorbs that; callers always say `variant="stacked"`.
- The admin shell picks its brand from
  `location.pathname.startsWith('/admin/manage/food')` (`layout/layout.js`), so a
  new food admin page is branded automatically — but a food page mounted outside
  that prefix will silently show the store logo.
- `themes.js` used to carry `logo:{rectangle,square}` in all 12 variants. It was
  **dead config that nothing read**, pointing at deleted files; it is gone. Don't
  reintroduce per-theme logo paths — `BrandLogo` owns this.
- Favicons are polarity-split via `media="(prefers-color-scheme: …)"` in
  `public/index.html`, with `favicon.ico` as the fallback. `logo192/512.png` are
  opaque (white ground) because a transparent PWA icon renders as a black square
  on some Android launchers.

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

**`FoodGalaxy` is the food pages' actual background.** It is `position: fixed;
inset: 0` behind every `/food/*` route, so *its* base colour — not
`palette.background.default` — is what the customer sees. It hardcoded the light
canvas, which in dark mode put warm off-white text on a near-white sheet: the
menu category headings vanished while text inside Cards stayed readable, because
Cards paint their own `background.paper`. It now reads `foodTokens(mode)`. The
symptom to recognise: **text disappears only where it sits directly on the page
background**, never inside a card.

## Commands

```bash
# Is prod healthy? (schema vs. deployed code) — always the first move on a 500
curl https://fabrythingweb.onrender.com/api/health/

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
python manage.py release_login <user|email> # dry run; --apply frees the name for reuse
python manage.py sweep_delivery_offers       # expire timed-out offers + re-offer (cron backstop)

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
