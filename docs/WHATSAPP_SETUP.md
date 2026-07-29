# WhatsApp order alerts — setup instructions

Branch `feat/whatsapp-alerts`. Ships **fully built and fully tested but dormant** —
it sends nothing until you paste real credentials into Render's environment
variables. Nothing in this system can hit the network in tests; 23 new tests
cover the dormant and configured paths (23 new, 518 total, all green).

## What it does

1. **New store order → WhatsApp to you (the admin).** Fires the moment a
   customer places a Cash-on-Delivery order on the storefront.
2. **New food delivery offer → WhatsApp to the rider.** Fires whenever the
   existing auto-dispatch (`food/services_dispatch.py`) offers a CONFIRMED
   order to a rider — same offer, just also sent over WhatsApp now, so a
   rider doesn't have to have the dashboard open to see it.
3. **No rider available → WhatsApp to you (the admin).** Fires when a food
   order has been offered around and nobody could be found (or nobody is
   online at all) — this used to sit silently in the admin queue.

None of this touches or changes the existing auto-assignment logic in
`services_dispatch.py` — the alerts are attached to it, not built on top of it.

## 1. Environment variables (Render → your service → Environment)

Set these three when you have Meta Business verification done and a WhatsApp
Business app created:

| Variable | Example | Notes |
| --- | --- | --- |
| `WHATSAPP_ACCESS_TOKEN` | `EAAG...` | The permanent (System User) access token from Meta Business Manager. **Never commit this or paste it into a chat/log.** |
| `WHATSAPP_PHONE_NUMBER_ID` | `109876543210123` | From the Cloud API dashboard for your business phone number — not the phone number itself. |
| `WHATSAPP_API_VERSION` | `v20.0` | Optional. Defaults to `v20.0` if unset. |

The system is dormant — `send_whatsapp()` returns `False` and does nothing —
until **both** `WHATSAPP_ACCESS_TOKEN` and `WHATSAPP_PHONE_NUMBER_ID` are set.
Nothing else needs to change; no redeploy-required code path depends on them
being present at build time.

## 2. Where the phone *numbers* go (not env vars — admin panel)

Unlike the credentials above, destination numbers are not secrets, so they're
editable from the Django admin without a redeploy:

- **Your (admin) WhatsApp number** — Django admin → Core → Store
  configurations → the one row → `Whatsapp admin number`. Use international
  format, digits only, no leading `+` (e.g. `8801700000000`). This number
  receives both the "new store order" alert and the "no rider available"
  fallback alert.
- **Each rider's WhatsApp number** — Django admin (or the existing admin
  panel Riders screen) → the rider's `Phone` field. This field already
  existed on `Rider` and was already editable — no migration was needed for
  it. Same international format.

If either number is blank, that alert is silently skipped (logged at info
level) — it will never error or affect the order/dispatch flow.

## 3. Templates to create in Meta Business Manager

Meta requires an **approved template** for any business-initiated message
(which all three of these are — you're messaging first, not replying within a
customer's 24h session window). Create these three templates under
**Meta Business Manager → WhatsApp Manager → Message Templates**, category
**Utility**, before setting the env vars — messages will fail (and show up as
failed in the admin log, see below) until each template is approved.

### Template 1 — `store_new_order_admin`
- **Language:** English (`en`)
- **Category:** Utility
- **Body:**
  ```
  New store order {{1}}
  Customer: {{2}} ({{3}})
  Items: {{4}}
  Total: {{5}}
  ```
- **Parameters (in order):** order number, customer name, customer phone,
  item count, total (with currency, e.g. "550.00 BDT").

### Template 2 — `food_rider_delivery_offer`
- **Language:** English (`en`)
- **Category:** Utility
- **Body:**
  ```
  New delivery offer!
  Pickup: {{1}}
  Deliver to: {{2}}
  Your pay: {{3}}
  Open the rider app to accept — offers expire in 60 seconds.
  ```
- **Parameters (in order):** pickup restaurant name, delivery area
  (village/zone name, or the raw address if neither is known), rider's pay
  for this order (`FoodOrder.rider_base_pay`, no currency symbol prefixed —
  add one in the template text if you want, e.g. `৳{{3}}`).

### Template 3 — `food_no_rider_available_admin`
- **Language:** English (`en`)
- **Category:** Utility
- **Body:**
  ```
  No rider available for order {{1}} from {{2}} to {{3}}.
  Please assign a rider manually.
  ```
- **Parameters (in order):** order code, restaurant name, delivery area.

If you rename any of these in Meta, update the matching constant in code:
`STORE_ORDER_ADMIN_TEMPLATE` in `orders/services.py`, and
`RIDER_OFFER_TEMPLATE` / `NO_RIDER_ADMIN_TEMPLATE` in
`food/services_dispatch.py`.

## 4. How to verify alerts are firing once credentials are in

1. Place a small test order on the storefront (or a food order that gets
   auto-offered to a rider).
2. Django admin → Core → **Whatsapp alert logs**. Every attempt is recorded
   here — recipient, kind, related order, success/failure, and the error
   text if it failed. This table stays empty while the integration is
   dormant; a row appearing here means a real API call was made. **This is
   the single place to check "is this actually working" — a WhatsApp
   message that silently never sent is the most likely failure mode**, and
   this table is what makes that visible instead of silent.
3. A `success=False` row with an error mentioning the template name usually
   means the template isn't approved yet, or the recipient number isn't
   verified in Meta's test mode (numbers must be added to your app's allowed
   testers until the app goes through Business verification for
   general messaging).

## Design notes for the next engineer

- **`core/whatsapp.py`** is the only module that talks to the network. It is
  deliberately dumb: build a template payload, POST it, log the attempt,
  never raise. `is_configured()` gates everything.
- **`core.models.WhatsAppAlertLog`** — one row per real attempt (rows are
  only written when the provider is configured AND a destination number is
  known; a dormant/no-op call writes nothing, since that's the expected
  steady state, not a failure).
- **Deferred send.** `send_whatsapp_on_commit()` wraps
  `transaction.on_commit`, mirroring the existing pattern in
  `food/services.py:notify()` for Expo push — both storefront order
  placement and the rider offer/accept cycle run inside
  `@transaction.atomic` blocks that sometimes hold `select_for_update()` row
  locks, so a slow/hanging WhatsApp POST must never run before commit.
- **Why the admin number lives in `StoreConfiguration` and not an env var:**
  it's not a secret, and per the task's own framing it should be editable
  without a redeploy. `DeliveryPricing.get_solo()` in `food/` was the
  precedent for this "cached singleton row" pattern (see `core/models.py`);
  I put the field on the existing `core.StoreConfiguration` singleton rather
  than inventing a new one, since it's already the general cross-app config
  row and is used by both the storefront and (via `food/services_dispatch.py`)
  the food admin fallback alert.
- **Rider phone reuse.** `Rider.phone` already existed and was already
  writable through `RiderSerializer` / `AdminRiderViewSet` — no model change
  or migration was needed for it, only for `StoreConfiguration` and the new
  `WhatsAppAlertLog` model (`core/migrations/0003_...py`).
- **No-rider-alert de-dupe.** `offer_order()` runs on every rider poll (via
  `sweep_offers`) and via the `sweep_delivery_offers` cron backstop, so a
  persistently rider-less order would otherwise re-alert the admin every few
  seconds. `_alert_admin_no_rider_available()` checks
  `WhatsAppAlertLog` for a prior **successful** alert for that order and
  skips if one exists — it keeps retrying on a failure (e.g. template not
  yet approved) but stops once one attempt actually succeeds. This wasn't
  explicitly asked for but was necessary to avoid spamming your WhatsApp
  (and burning API quota) once the pool of riders runs dry.

## Files touched

- `backend/EcommerceInventory/core/whatsapp.py` — new, the provider.
- `backend/EcommerceInventory/core/models.py` — `WhatsAppAlertLog` model,
  `StoreConfiguration.whatsapp_admin_number` field.
- `backend/EcommerceInventory/core/migrations/0003_storeconfiguration_whatsapp_admin_number_and_more.py` — new.
- `backend/EcommerceInventory/core/admin.py` — registers `WhatsAppAlertLog`
  (read-only list) and shows the admin number on `StoreConfiguration`.
- `backend/EcommerceInventory/orders/services.py` — `place_cod_order` sends
  the store-order-admin alert on commit.
- `backend/EcommerceInventory/food/services_dispatch.py` — `offer_order`
  sends the rider alert on a successful offer and the admin fallback alert
  when no rider is found.
- Tests: `core/test_whatsapp.py`, `storefront/test_whatsapp_alerts.py`,
  `food/tests/test_whatsapp_alerts.py`.
