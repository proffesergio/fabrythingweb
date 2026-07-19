# Fabrything Food — Customer Delivery UI + COD Ordering (Phase 2)

**Date:** 2026-07-19
**Status:** Approved design; ready for implementation planning.
**Builds on:** `docs/superpowers/specs/2026-07-18-food-delivery-marketplace-design.md` (Phases 0–1 shipped).

---

## 1. Goal

Deliver the customer-facing side of the Food Delivery vertical: selecting **Food** in the
header switches the whole UI into a dedicated, immersive food-delivery app at `/food/*`,
where a customer can browse restaurants, build a food cart, and place a **Cash-on-Delivery
(COD)** order end-to-end. A minimal fulfillment hook lets restaurants/admin advance an
order to "delivered" so the loop is testable.

## 2. Revised constraints (supersede the v1.1 low-bandwidth stance)

| Topic | Decision (this phase) |
|---|---|
| Look & feel | **Immersive**, modern dark food-app aesthetic. Bandwidth is NOT a constraint. |
| Responsiveness | **Mobile-browser responsive** is the priority target. |
| App boundary | `/food/*` is a **fully separate themed app**: own theme + layout, outside the storefront wrapper. Clothing storefront untouched. |
| Cart | **Independent** food cart (own Redux slice + localStorage key). **One restaurant per cart.** |
| Checkout auth | **Guest COD**: name + phone + address, no login required. Prefill if logged in. |
| Location | **Zone dropdown is primary/authoritative**; optional "use my location" map pin resolves to a zone via point-in-radius. |
| Payment | **COD only** this phase (online = later phase). Tips: cash only. |
| Money / i18n | BDT (৳); bn/en toggle in the food header; localized names with English fallback. |

## 3. Architecture

### 3.1 Frontend boundary
- New route tree `/food/*` mounted **outside** `StorefrontWrapper` in `src/App.js`.
- `src/food/theme.js` — dark immersive MUI theme (separate from storefront theme).
- `src/food/layout/FoodLayout.js` — own header (logo, location selector, search, cart badge,
  bn/en toggle, "← Fabrything store" link back), `<Outlet/>`, footer.
- Pages under `src/food/pages/`. Reuse `APIHandler`, response envelope, pagination, MUI.
- The storefront header's animated **Food** link points to `/food` (replaces the coming-soon
  route). `FoodComingSoon` is retired.

### 3.2 Independent cart
- `src/food/redux/foodCartSlice.js` (or matching existing redux conventions), persisted to
  `localStorage` key `food_cart`, wired into the existing store.
- Cart shape: `{ restaurantId, restaurantSlug, restaurantName, items: [{ itemId, name, price,
  qty, selectedOptions: [{groupId, optionId, name, priceDelta}], lineTotal }], tip }`.
- **One-restaurant guard:** adding an item from a different `restaurantId` prompts to clear
  and start a new order.
- Client totals are for display only; the **server recomputes** authoritative totals at order time.

## 4. Customer screens (mobile-first)

1. **Food Home** `/food` — hero with location selector + search; cuisine category chips;
   restaurant grid filtered by selected zone; card badges: open/closed, ETA, delivery fee,
   rating. Empty state when the chosen area has no serviceable restaurants.
2. **Restaurant detail** `/food/restaurant/:slug` — cover image, info bar (hours/open state,
   min order, delivery fee, ETA), category-sectioned menu, dish cards. A dish with option
   groups opens an **item modal** (required/optional groups honoring min/max select, qty)
   before add-to-cart.
3. **Cart** `/food/cart` — line items, qty edit/remove, options summary, subtotal, delivery
   fee, min-order warning, optional tip, "proceed to checkout".
4. **Checkout** `/food/checkout` — guest form (name, phone, address) + **zone dropdown** and
   optional "use my location" pin; recompute delivery fee + ETA; COD confirmation; place order.
5. **Order confirmation / track** `/food/order/:code` — status timeline
   (Placed → Confirmed → Preparing → On the way → Delivered), order + restaurant summary,
   order code; **polls** for status changes.
6. **My orders** `/food/orders` — logged-in customer history; guests look up by order code + phone.

## 5. Backend (new for Phase 2)

### 5.1 Models (`food/models.py`)
**`FoodOrder`**
- `customer` → `accounts.Users`, nullable (guest orders).
- `guest_name`, `guest_phone`, `delivery_address` (text).
- `restaurant` FK, `zone` FK (resolved serviceable zone).
- `order_code` (unique, human-friendly, e.g. `FD-XXXXXX`).
- `status`: `PLACED | CONFIRMED | PREPARING | OUT_FOR_DELIVERY | DELIVERED | CANCELLED`.
- Money (Decimal 10,2): `subtotal`, `delivery_fee`, `tip`, `total`.
- `payment_method`: `COD` (only value this phase); `payment_status`: `PENDING | COLLECTED`.
- `created_at`, `updated_at`.

**`FoodOrderItem`**
- `order` FK, `item` FK (nullable-on-delete to preserve history), snapshots:
  `item_name`, `unit_price`, `qty`, `selected_options` (JSON snapshot: name + price_delta),
  `line_total`.

**Status transitions** enforced server-side; illegal transitions rejected.

### 5.2 Customer/public APIs (`/api/food/`)
- `POST /api/food/orders/` — place order (guest or auth). Server:
  1. loads restaurant + items fresh; rejects unavailable items / closed restaurant / below
     min-order; validates all option selections against the item's option groups.
  2. resolves zone: explicit zone id, or map pin → point-in-radius; rejects if the restaurant
     does not serve that zone.
  3. **recomputes** subtotal, delivery fee (per-zone override else restaurant base), tip, total
     — never trusts client amounts.
  4. creates `FoodOrder` + items, returns `order_code`.
- `GET /api/food/orders/<order_code>/?phone=` — track. Guests must supply the matching phone;
  auth customers can read their own without phone.
- `GET /api/food/orders/` — auth customer order history.
- Browse reuses existing public restaurant/zone read endpoints (Phase 1).
- ETA = restaurant `avg_prep_minutes` + fixed delivery buffer (constant this phase).

### 5.3 Minimal fulfillment (so COD is end-to-end)
- `GET /api/food/vendor/orders/` — owner-scoped list of the vendor's restaurant orders.
- `PATCH /api/food/vendor/orders/<id>/status/` — advance status along the legal chain;
  owner-scoped.
- Admin can list/read all food orders and update status (reuses admin auth + a food-orders
  admin screen stub; the **full GoMeal-style admin redesign is a separate later spec**).

## 6. Out of scope (explicitly deferred to later specs)
- Full GoMeal-style unified admin dashboard + order-management redesign (workstream 2).
- Rider accounts, dispatch/tasks, live GPS (Phases 4–6).
- Online payments / SSLCommerz (Phase 3).
- OTP verification of guest phone (later hardening).

## 7. Parallel small task — ecommerce products not showing in admin
Separate from the Food work: diagnose why admin **Manage Products** is empty despite the
`seed_bd_store` / `seed_clothing_data` / `seed_demo` commands. Most likely a tenant/owner
mismatch (seeded products attached to a different `domain_user`/tenant than the logged-in
admin, or the list query filtering by the request user). Fix the root cause, run the
appropriate seed, and verify products appear in the admin list. Committed separately.

## 8. Testing strategy (TDD)
**Backend (write tests first):**
- Order placement: server-side total recompute (client-sent totals ignored); below-min-order
  rejected; closed restaurant rejected; unavailable item rejected; invalid option selection
  rejected; non-serviceable zone rejected; one-restaurant enforcement (items from a single
  restaurant only).
- Guest track: correct phone returns order; wrong/missing phone is denied; auth customer reads
  own order.
- Status transitions: legal advance succeeds; illegal jump/backward rejected; vendor scoped to
  own restaurant (cross-restaurant 403).
- `order_code` uniqueness.

**Frontend:**
- Add-to-cart with option selection builds correct line + total.
- One-restaurant guard prompts on cross-restaurant add.
- Checkout blocks a non-serviceable zone; COD happy path posts and routes to confirmation.
- Order confirmation renders status timeline from API.

## 9. Definition of done
1. Selecting **Food** switches into the themed `/food` app (separate theme/layout), responsive
   on mobile browsers.
2. A guest can browse restaurants in a serviceable zone, build a single-restaurant cart, and
   place a COD order; server-computed totals are authoritative.
3. Order confirmation/track shows live status; guests can look up by code + phone.
4. A vendor (and admin) can advance that order through to `DELIVERED`.
5. Ecommerce admin **Manage Products** shows seeded products.
6. All new tests pass.
