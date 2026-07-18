# Fabrything Food Delivery — Marketplace Design (v1.1.0)

**Date:** 2026-07-18
**Status:** Approved roadmap; Phase 1 detailed design for implementation.
**Author:** Design captured via brainstorming with the product owner.

---

## 1. Mission & context

Fabrything is an existing e-commerce platform (Django REST backend on Render, React/MUI
frontend on Vercel/`fabrything.com`, Neon Postgres). We are adding a **Food Delivery**
vertical as a **multi-restaurant marketplace**.

**Mission constraint (drives every design choice):** this launches for a **local
community area in rural Bangladesh** — the goal is to bring online food delivery to
rural people. This means:

- **Low-bandwidth first:** lightweight pages, aggressive image compression/lazy-loading,
  minimal JS on customer + rider screens, tolerate flaky connectivity.
- **COD-first:** cash on delivery is the default and must work end-to-end before online
  payment. Online payment (SSLCommerz) is added later; keys/hosting come from the owner.
- **Phone-centric identity:** rural users identify by phone number; sign-in/checkout must
  work with a phone number, not require email.
- **Bangla localization:** UI must support Bangla (bn) alongside English (en). Currency is
  BDT (৳), already used across the store.
- **Constrained service area:** delivery is offered only inside defined local zones, not
  nationwide. Ordering outside a serviceable zone is blocked with a clear message.

## 2. Locked-in decisions

| Decision | Choice |
|---|---|
| App boundary | New Django `food` app; **shared** customer accounts, admin shell, and site (`fabrything.com/food`). |
| Vendor model | **Multi-restaurant marketplace** — restaurants onboard, own their menus, receive payouts minus commission. |
| Payments | **COD** now; **online (SSLCommerz/bKash)** later (owner supplies merchant keys). Tips: cash or online. |
| Rider client (v1) | Web dashboard with a `Rider` role + browser Geolocation. Native app = future. |
| Roles | Existing: Super Admin, Admin, Supplier, Customer, Staff. **Add: `Restaurant`, `Rider`.** |
| Hosting | GPS/live tracking (Phase 6) requires paid hosting or a 3rd-party realtime service; owner will upgrade. Until then, Phase 6 uses a polling fallback. |

## 3. Roles & permissions

Add two role choices to `accounts.Users.role`: `Restaurant`, `Rider`.

- **Customer** — reuses existing customer auth; can order food.
- **Restaurant (Vendor)** — owns exactly one `Restaurant`; manages only their own menu,
  hours, availability, and views their own orders/payouts. Scoped by `owner` FK.
- **Rider** — sees only tasks assigned to them; updates task status; broadcasts location.
- **Admin / Super Admin** — full control across all restaurants, foods, orders, riders,
  dispatch, payouts via the unified admin console.

Admin-panel screens register as `accounts.Modules` (seeded via a new
`seed_food_modules` management command) and are gated by the existing
`UserPermissions` + `ModuleUrls` + `PermissionMiddleware` machinery. Vendor and Rider
dashboards are **not** admin modules; they are role-scoped API endpoints with their own
frontend routes, authorized in the view layer (not the admin permission middleware).

## 4. Phased roadmap

| Phase | Scope | Definition of done |
|---|---|---|
| **0 — Foundations** | `food` app; `Restaurant` + `Rider` roles; admin nav entry; animated "Food" header link (entry only) | App installed, migrations apply, roles selectable, Food menu visible |
| **1 — Restaurant & menu catalog** | `Restaurant`, `RestaurantHours`, `DeliveryZone`, `FoodCategory`, `FoodItem`, `FoodItemOptionGroup`, `FoodItemOption`; admin onboarding/approval; **vendor dashboard** to manage own menu | Admin can approve restaurants; a vendor can build a full menu; public read API returns menus |
| **2 — Customer ordering** | Animated Food menu → browse restaurants → menu → **food cart** (separate from clothing) → checkout (address, zone check, delivery fee, ETA); `FoodOrder` lifecycle; **COD** | A customer in a serviced zone can place a COD food order |
| **3 — Online payments** | SSLCommerz integration, payment records, webhooks, reconciliation, online tips | Cashless checkout works alongside COD |
| **4 — Rider management** | `Rider` accounts (unique ID, vehicle, availability), delivery counts, **tips ledger**, earnings; admin manages riders; rider mobile dashboard | Riders exist, see assigned work, accrue counts/tips |
| **5 — Dispatch / tasks** | `DeliveryTask` (order→restaurant pickup→rider→customer dropoff); manual assign (auto later); accept/pickup/deliver lifecycle; tips on completion | An order can be assigned and driven to "delivered" |
| **6 — Live GPS tracking** | Rider broadcasts location (Geolocation); customer "track my order" + admin fleet map (Leaflet + OpenStreetMap). Realtime transport chosen here (polling until paid hosting) | Customer/admin see live rider position |
| **7 — Unified admin console** | One console: products/categories (existing) + restaurants, foods, orders, riders, dispatch, **payouts/commissions**. Grows across phases, finalized here | Single control center for the whole platform |

**Build order:** 0 → 1 → 2 → 3 → 4 → 5 → 6, with 7 growing incrementally.

## 5. Cross-cutting concerns

- **Money:** all amounts in BDT, stored as `DecimalField(max_digits=10, decimal_places=2)`
  (match existing catalog). Commission stored per-restaurant as a percentage; payout =
  item subtotal − commission. Delivery fee and tips are **not** part of restaurant payout.
- **Geo / zones:** `DeliveryZone` = named area with a serviceable check. v1 uses a simple
  model — a zone has a center point (lat/lng) + radius (km), or a list of area/upazila
  names; a restaurant serves one or more zones and a customer address maps to a zone.
  Full polygon/routing is deferred. Lat/lng stored as `DecimalField`, no PostGIS (keeps
  Neon/Render simple).
- **Localization:** persist `name`/`description` with a Bangla counterpart
  (`name_bn`, `description_bn`) on catalog models; frontend picks language from user
  preference (existing `Users.language`). Fall back to English when Bangla is empty.
- **Images:** reuse the existing media/upload pattern; store compressed derivatives;
  serve `loading="lazy"`; cap dimensions on upload.
- **Design system:** reuse MUI theme, `APIHandler` hook, `renderResponse`,
  `CustomPageNumberPagination`, react-hook-form patterns. Follow existing
  `storefront/` and `pages/` conventions so the new module reads like the current code.

---

## 6. Phase 1 — Restaurant & menu catalog (detailed design)

Phase 1 delivers the marketplace's supply side: restaurants and their menus, managed by
both admins (onboarding/approval/oversight) and vendors (their own menu), plus a
public read API the customer app (Phase 2) will consume. No cart/checkout yet.

### 6.1 Data models (`food/models.py`)

All models use an `AutoField` PK and `created_at`/`updated_at` timestamps to match the
codebase. FK fields follow the existing `_id` suffix convention where the current code
does (e.g. `category_id`).

**`Restaurant`**
- `owner` → `accounts.Users` (role `Restaurant`), one-to-one, nullable until claimed.
- `name`, `name_bn`, `slug` (unique), `description`, `description_bn`.
- `logo` (image), `cover_image` (image), `cuisine_type` (char/tags).
- `phone` (contact), `address`, `pickup_lat`, `pickup_lng` (Decimal).
- `commission_percentage` (Decimal, default e.g. 15.00) — admin-set.
- `base_delivery_fee` (Decimal), `avg_prep_minutes` (int), `min_order_amount` (Decimal).
- `status`: `PENDING` (submitted, awaiting admin approval) → `ACTIVE` / `SUSPENDED` / `REJECTED`.
- `is_open` (manual open/closed toggle by vendor), computed availability also honors hours.

**`RestaurantHours`**
- `restaurant` FK, `weekday` (0–6), `open_time`, `close_time`, `is_closed` (whole day).

**`DeliveryZone`**
- `name`, `name_bn`, `center_lat`, `center_lng` (Decimal), `radius_km` (Decimal),
  `is_active`. (v1 serviceability = point-in-radius.)

**`RestaurantZone`** (M2M through)
- `restaurant` FK, `zone` FK, optional per-zone `delivery_fee` override.

**`FoodCategory`**
- `restaurant` FK (categories are per-restaurant), `name`, `name_bn`, `display_order`,
  `is_active`.

**`FoodItem`**
- `restaurant` FK, `category_id` FK → `FoodCategory`.
- `name`, `name_bn`, `slug`, `description`, `description_bn`, `image`.
- `price` (Decimal), `discount_price` (Decimal, nullable).
- `prep_minutes` (int, nullable — falls back to restaurant avg).
- `is_available` (bool), `is_veg` (bool), `spice_level` (optional enum), `display_order`.

**`FoodItemOptionGroup`** (e.g. "Size", "Add-ons")
- `item` FK, `name`, `name_bn`, `min_select`, `max_select`, `is_required`.

**`FoodItemOption`** (e.g. "Large +৳50")
- `group` FK, `name`, `name_bn`, `price_delta` (Decimal, default 0), `is_default`,
  `display_order`.

**Indexes:** `Restaurant.slug`, `Restaurant.status`, `FoodItem(restaurant, is_available)`,
`FoodCategory(restaurant, display_order)`.

### 6.2 API surface

Base path `/api/food/`. Three audiences, authorized in the view layer:

**Public (AllowAny, read-only)** — consumed by Phase 2 customer app; safe to build now:
- `GET /api/food/restaurants/` — list `ACTIVE` restaurants; supports `?zone=`, `?search=`,
  `?cuisine=`, pagination. Serializer annotates open/closed and delivery fee.
- `GET /api/food/restaurants/<slug>/` — restaurant detail + categories + available items
  (nested), with option groups. **Annotate to avoid N+1** (same discipline as the
  storefront homepage fix — prefetch categories/items/options, no per-item queries).
- `GET /api/food/zones/` — active zones (for the storefront to check serviceability).

**Vendor (role `Restaurant`, scoped to `owner`)**:
- `GET/PATCH /api/food/vendor/restaurant/` — the caller's own restaurant profile + hours +
  `is_open` toggle (cannot change `commission_percentage` or `status`).
- CRUD `/api/food/vendor/categories/`, `/api/food/vendor/items/`,
  `/api/food/vendor/items/<id>/options/` — all filtered to the owner's restaurant; writes
  reject objects belonging to another restaurant (403).

**Admin (role Admin/Super Admin, via existing permission middleware + modules)**:
- CRUD `/api/food/admin/restaurants/` incl. `POST .../<id>/approve/`,
  `.../<id>/suspend/`, and setting `commission_percentage`.
- CRUD `/api/food/admin/zones/`.
- Read access to any restaurant's menu for oversight.

**Serializers** live in `food/serializers.py`, following `storefront/serializers.py`
conventions (ModelSerializer + method fields that read annotations, localized `name`
resolution helper).

### 6.3 Vendor onboarding & approval flow

1. Admin creates a `Restaurant` in `PENDING` and invites an owner, **or** a self-serve
   vendor signup creates a `Users(role=Restaurant)` + a `PENDING` `Restaurant`.
2. Vendor logs into the **vendor dashboard**, completes profile (logo, address, pickup
   pin, hours, zones) and builds the menu — all allowed while `PENDING`, but the
   restaurant is not publicly listed.
3. Admin reviews and `approve`s → status `ACTIVE` → appears in public list.
4. Admin may `SUSPEND`/`REJECT` with a reason; suspended restaurants are hidden from
   public list but retain their data.

### 6.4 Frontend (React/MUI)

**Admin console (under `src/pages/food/`, registered as Modules):**
- `Restaurants` list (approve/suspend, set commission) + detail.
- `Delivery Zones` CRUD.
- Read-only menu viewer per restaurant.
- Register via `seed_food_modules` under a new top-level **"Food"** admin menu group,
  following the `seed_admin_modules` pattern (parent "Food" → children).

**Vendor dashboard (new route group `src/vendor/`, role-gated):**
- Restaurant profile + hours + open/closed toggle.
- Menu builder: categories, items (with images, price, availability), option groups.
- Uses `APIHandler`, react-hook-form, MUI — mobile-friendly and light for low bandwidth.

**Storefront (Phase 1 slice only):**
- Add the **animated highlighted "Food" entry** to the storefront header (the eye-catching
  menu item requested). In Phase 1 it links to a simple "Food — coming to your area"
  placeholder / restaurant list stub; full browse/order is Phase 2. Animation via the
  existing `framer-motion` dependency, kept subtle and cheap to render.

### 6.5 Reuse & conventions
- Money, pagination, response envelope, JWT auth, image upload — reuse existing helpers.
- Match `Products`/`Categories` admin CRUD page structure for the food admin pages.
- No PostGIS; geo math (point-in-radius) done in Python/ORM with plain Decimal lat/lng.

### 6.6 Testing strategy
- **Model tests:** serviceability (point-in-radius), open/closed from hours, payout/
  commission math, slug uniqueness.
- **API tests:** public list hides non-ACTIVE; vendor cannot read/write another
  restaurant's objects (403); admin approve transitions status; N+1 guard — assert the
  restaurant-detail endpoint issues a bounded query count (mirrors the storefront fix).
- **Frontend:** vendor menu-builder happy path; admin approve flow; header Food link
  renders and animates.

### 6.7 Phase 1 acceptance criteria (Definition of Done)
1. Migrations apply cleanly on Postgres; `seed_food_modules` registers the Food admin menu.
2. Admin can onboard a restaurant, set commission, and approve it to `ACTIVE`.
3. A `Restaurant`-role user can log into the vendor dashboard and build a complete menu
   (categories → items → options) with images, scoped strictly to their own restaurant.
4. Public read API returns only `ACTIVE` restaurants and their available menus, with
   bounded query counts (no N+1) and localized (bn/en) names.
5. The animated "Food" entry appears in the storefront header.
6. Tests for the above pass.

---

## 7. Open questions / deferred
- Exact SSLCommerz product (bKash direct vs SSLCommerz aggregator) — decided in Phase 3.
- Auto-dispatch algorithm (nearest available rider) — Phase 5; manual assignment first.
- Realtime transport for GPS (polling vs WebSockets vs Pusher/Ably) — Phase 6, gated on
  hosting upgrade.
- Whether vendor self-serve signup is open or invite-only at launch — default invite-only;
  revisit before Phase 1 ships.
