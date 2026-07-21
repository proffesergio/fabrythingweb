# Food module: menu validation, rider dashboard, menu management

Date: 2026-07-21
Status: approved, ready for planning

Three defects/gaps reported against the live food-delivery module:

1. Creating a menu item with tags and the newer scheduling fields fails with
   "Validation Error".
2. Rider accounts are created successfully but the rider sees an empty page
   after logging in — no assigned orders, no customer info, no delivery
   location, no navigation aid.
3. Admin Menu Management lacks image handling and has no way to reuse one
   restaurant's menu when onboarding another.

Each part below is independently shippable and can be reviewed on its own.

---

## Part 1 — Menu item "Validation Error"

### Problem

`EnvelopeModelViewSetMixin.create` / `.update` (`food/views_vendor.py`) return
`serializer.errors` in the envelope's `data` but set `message` to the constant
string `"Validation error"`. `FoodMenuManager.saveItem` only surfaces `message`
via a toast, so the field that actually failed is never shown to the admin and
never reaches the logs. The reported symptom is therefore a *visibility*
failure wrapping an unknown underlying validation failure.

### Design

**Stage 1 — make the error visible (ships regardless of root cause).**

On a 400 from `food/admin/items/`, `FoodMenuManager` reads the per-field error
map from `res.data.data` and:

- sets `error` + `helperText` on the corresponding `TextField` in the item
  dialog, so the failing input is highlighted in place;
- shows a toast summarising the failing fields, e.g.
  `Couldn't save: image — Enter a valid URL`;
- keeps the dialog open with the admin's input intact.

Errors not tied to a rendered field (e.g. `non_field_errors`) render as an
alert at the top of the dialog.

**Stage 2 — fix the underlying rejection.** Characterisation tests are written
first against `POST /api/food/admin/items/`, one per suspected cause, to
establish which actually fail before any serializer change:

| Suspect | Why it would reject |
| --- | --- |
| `image` | `URLField`; any value that is not a full `http(s)://` URL is rejected. A filename or a bare domain fails. |
| `available_from` / `available_to` | Sent as `""` when unset. The frontend deletes those keys entirely, which also makes the values **unclearable on edit**. |
| `discount_price`, `prep_minutes` | Same `""`-vs-`null` problem. |
| `category_id` | FK literally named `category_id`; the list response and the dialog must agree on pk-int vs object. |
| `tags`, `available_days` | `JSONField(default=list)`; must accept a list and reject a stringified list. |

**Stage 3 — harden `AdminItemSerializer`** (`food/serializers_admin_menu.py`):

- coerce `""` to `None` for `discount_price`, `prep_minutes`, `available_from`,
  `available_to` before validation;
- accept explicit `null` on PATCH to clear those fields, and stop the frontend
  from deleting the keys — send `null` instead, so clearing works;
- validate `tags` against the curated key list
  (`spicy`, `new`, `popular`, `bestseller`, `veg`) and `available_days` against
  ints 0–6, returning a readable message rather than a raw JSON schema error.

### Acceptance

- An item created with tags, a spice level, a schedule window and weekday
  restrictions saves successfully.
- Submitting a deliberately invalid field shows that field's error inline.
- Clearing a previously-set discount price or schedule window persists as null.

---

## Part 2 — Rider dashboard, dispatch and live tracking

### Root cause of the blank page

`pages/Auth.js` navigates every successful login to `/admin/home` with no role
branch. A user with `role == "Rider"` lands on the admin dashboard, which
renders no modules for that role — "a dashboard page and nothing else". The
existing `RiderDashboard` at `/rider` is never reached.

### Design

#### 2a. Routing

- `Auth.js` branches on the authenticated user's role: `Rider` → `/rider`,
  `Restaurant` → the vendor panel, everyone else → `/admin/home` as today.
- `/admin/home` redirects a `Rider` to `/rider`, so a stale bookmark or a
  direct URL still lands correctly.

#### 2b. Presence: what "online" means without a native app

The rider dashboard is the rider's app — a web page on their phone. Presence is
derived, not declared:

- New `Rider` fields: `current_lat`, `current_lng` (`DecimalField(9,6)`,
  nullable), `last_seen_at` (`DateTimeField`, nullable). One migration.
- `POST /api/food/rider/heartbeat/` accepts `{lat, lng}` and updates all three.
- The dashboard's **Online** switch starts a `navigator.geolocation.watchPosition`
  and posts a heartbeat every ~20 seconds while the tab is open; flipping it off
  stops the watch and sets `is_available = False`.
- A rider is **dispatchable** iff `is_available` **and**
  `last_seen_at >= now - 3 minutes` **and** a location is present. Closing the
  tab or losing signal drops them out of dispatch automatically without any
  explicit "go offline" action.

Battery and privacy: location is only collected while the rider is Online, is
stored as a single current position (no history trail), and the dashboard states
this above the toggle in English and Bangla.

#### 2c. Auto-assignment

When an order transitions to `CONFIRMED`, a service picks a rider:

1. nearest dispatchable rider to the restaurant's `pickup_lat/lng` by haversine;
2. if the restaurant has no pickup coordinates, the dispatchable rider who has
   been idle longest (fewest active orders, then oldest `last_seen_at`) —
   riders are not associated with zones in the current model, so there is no
   zone filter to apply;
3. otherwise leave `rider` null for manual assignment.

Assignment notifies the rider (`Notification`) and the customer, reusing the
existing `notify` helper. Admin assignment in `ManageFoodOrders` remains and
overrides an auto-assignment. Assignment is idempotent: an order that already
has a rider is never reassigned automatically.

#### 2d. Richer order payload

`RiderOrdersView` currently serialises with `FoodOrderSerializer`, which already
carries `items`, `delivery_lat/lng`, `guest_phone` and `delivery_address`. A
rider-specific serializer adds:

- restaurant `pickup_lat`, `pickup_lng`, `phone` and `address` (needed for the
  pickup leg and the call button);
- per-item selected options/add-ons and the order note;
- `cash_to_collect` — the total when `payment_method` is COD and payment is
  unpaid, else zero.

#### 2e. Dashboard UI

Rebuilt `rider/RiderDashboard.js`, split into focused components rather than one
growing file: `RiderHeader` (profile, online toggle), `DeliveryCard`,
`DeliveryMap`, `EarningsPanel`.

Per assigned delivery:

- **Pickup list** — every item with quantity, chosen options/add-ons, and the
  order note, so the rider can verify the bag at the restaurant.
- **Call buttons** — `tel:` links for the customer and the restaurant.
- **Map (Leaflet, already a dependency)** — rider marker (pulsing), restaurant
  pin, customer pin, and a dashed polyline for the *active leg*: rider →
  restaurant before pickup, restaurant → customer after.
- **Heading check** — live haversine distance to the current target that ticks
  down, a bearing arrow, and an amber "You're moving away from the drop-off"
  banner when distance increases across three consecutive heartbeats.
- **Open in Google Maps** — a maps URL for real turn-by-turn navigation. We
  deliberately do **not** run a routing engine (OSRM or similar): a straight-line
  polyline plus the nav handoff delivers the "am I heading the right way" signal
  with no external service dependency, no API key, and no rate limit.
- **Status advance** — the existing picked-up / delivered buttons, kept.

Earnings panel: today's earnings, lifetime total, completed-delivery history
with per-order payout, and total cash to collect across active COD orders.
Served by a new `GET /api/food/rider/earnings/`.

### Acceptance

- A rider logging in lands on `/rider`, not the admin dashboard.
- With the Online toggle on, `last_seen_at` and coordinates update roughly every
  20 seconds; toggling off stops updates and removes the rider from dispatch.
- Confirming an order with a dispatchable rider nearby assigns it automatically
  and notifies both parties.
- An assigned delivery shows items, both phone numbers, both map legs, and a
  distance that decreases as the rider approaches.
- Marking delivered records a `RiderEarning` and moves the order into history.

---

## Part 3 — Menu Management: images and menu copying

### Design

#### 3a. Images

- A file-upload button in the item dialog posts to the existing
  `POST /api/uploads/` (`core.views.FileUploadViewInS3` — S3 when AWS keys are
  configured, local `MEDIA_ROOT` otherwise) and stores the returned URL in
  `FoodItem.image`. No model change; the field stays a `URLField`.
- The URL paste field is kept for externally hosted photos.
- Live preview in the dialog and a thumbnail on every item row in the list, with
  a neutral placeholder for items that have no photo.

#### 3b. Copying a menu

One transactional endpoint, `POST /api/food/admin/menu/copy/`, gated by
`IsPlatformAdmin`, accepting either shape:

```
{ "source_restaurant": 1, "target_restaurant": 2 }                 # whole menu
{ "source_restaurant": 1, "target_restaurant": 2,
  "item_ids": [10, 11], "target_category": 7 }                     # selection
```

Copy semantics:

- Categories are matched to the target by **name**; a match merges, no match
  creates. Items are matched within their target category by name; a match is
  **skipped**. Re-running a copy is therefore safe and idempotent.
- Option groups and their options are copied for each newly created item.
- Slugs are regenerated with the existing `_unique_item_slug` against the target
  restaurant, satisfying the `(restaurant, slug)` unique constraint.
- Images, prices, tags, spice level and schedule fields carry over as-is.
- The whole operation runs in `transaction.atomic`, so a failure part-way leaves
  the target restaurant untouched.
- The response reports counts: categories created/merged, items copied/skipped,
  options copied.

A `?dry_run=true` variant returns those same counts without writing, which the
UI uses for the confirmation preview.

#### 3c. Admin UI

- **Copy full menu**: a "Copy menu from…" action on the Menu Management screen
  — pick the source restaurant, see the dry-run preview ("12 items will be
  copied, 3 skipped as duplicates"), confirm.
- **Copy selected items**: a checkbox on each item row and a "Copy N items to…"
  bar that asks for the target restaurant and target category.

### Acceptance

- Uploading a photo attaches it to the item and the thumbnail appears in the
  list.
- Copying a full menu into an empty restaurant reproduces every category, item
  and option group.
- Running the same copy a second time reports everything skipped and creates no
  duplicates.
- A copy that fails part-way leaves the target restaurant unchanged.

---

## Testing

Backend, in `food/tests/` alongside the existing 20 test modules, run with
`python manage.py test food`:

- `test_admin_menu.py` — extended with the item-validation characterisation
  cases and the `""` → null coercion.
- new `test_menu_copy.py` — full copy, selective copy, idempotent re-run,
  slug collisions, atomic rollback.
- new `test_rider_dispatch.py` — dispatchability window, nearest-rider choice,
  fallbacks, idempotent assignment.
- extended rider API tests — heartbeat, enriched order payload, earnings.

Frontend, with `npm test` (jest + RTL, tests beside sources):

- `FoodMenuManager.test.js` — inline field errors on a 400, thumbnail rendering,
  copy dialog preview.
- new `RiderDashboard.test.js` — role redirect, heartbeat lifecycle tied to the
  toggle, delivery card contents, moving-away warning. Geolocation is mocked.

## Out of scope

- Real road routing / turn-by-turn inside the app (handed off to Google Maps).
- Customer-visible live rider tracking. The `Rider` location fields added here
  make it possible later, but no public endpoint exposes them in this work.
- Rider location history or trails.
- Installable PWA packaging for the rider dashboard.
- Any change to vendor-side menu management (`VendorMenu.js`).
