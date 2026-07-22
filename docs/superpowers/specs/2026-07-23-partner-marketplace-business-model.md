# Partner Marketplace — Business Model & "Become a Partner"

**Date:** 2026-07-23
**Status:** Decided (owner-approved), not yet implemented.
**Depends on:** the shipped settlement ledger (`food/services_settlement.py`,
`OrderSettlement`), rider presence/heartbeat, `services_dispatch.available_riders()`.

This is the first document in the repo about the *commercial* model rather than
features. The plumbing for most of it already exists — what was missing was the
policy. Four decisions were taken; everything below follows from them.

## The four decisions

| # | Decision | Chosen |
| - | -------- | ------ |
| 1 | Restaurant fee | **Hybrid: `max(floor, commission%)`** |
| 2 | COD cash | **Rider deposits to platform daily; platform pays out** |
| 3 | Partner onboarding | **Self-signup → `PENDING` → admin approves** |
| 4 | Dispatch | **Platform rider pool, auto-offer to nearest online rider, admin override** |

## 1. Fee model — a floor under the percentage

A flat 15% breaks on rural basket sizes: ৳150 × 15% = ৳22.50, less than a
rider's base pay, so the platform loses money on exactly the orders it gets most
of. A pure flat fee gives up all upside on large orders. The floor fixes the
first without the second.

```
commission = max(restaurant.min_commission_amount, food_net × commission_rate%)
```

Starting policy (both per-restaurant columns, so partners can be negotiated
individually and promo rates are possible):

- `commission_percentage` — default **12.00** (down from 15, because the floor
  now carries the small orders)
- `min_commission_amount` — **new column**, default **25.00**

Everything downstream is unchanged: `compute_breakdown` keeps its invariant
`restaurant_payout + rider_payout + platform_revenue == order.total`, and
`OrderSettlement` must **snapshot the floor as well as the rate** — the existing
snapshot is the reason changing a rate never moves past books, and a
non-snapshotted floor would silently reintroduce that bug.

**Migration note.** Existing settlements must not move. The floor applies to
orders settled *after* it ships; `backfill_settlements` must not be re-run over
already-settled rows.

## 2. Cash — the rider is a courier of money, not a party to it

```
Customer  → Rider       cash, at the door (order.total)
Rider     → Platform    daily deposit of everything collected
Platform  → Restaurant  weekly, food_net − commission
Platform  → Rider       weekly, base pay + tips
```

The platform touches the money before anyone else, so commission is never
invoiced and never chased — the single biggest operational reason to prefer this
over "rider pays the restaurant at pickup".

What it costs: the platform carries float and rider-default risk. That risk is
managed by making the outstanding balance visible and bounded:

- **`RiderCashDeposit`** (new model): `rider`, `amount`, `collected_for` (the
  settlement legs it clears), `received_by` (admin), `received_at`, `note`.
- **`Rider.cash_in_hand`** — derived, not stored: sum of `rider_cash` legs still
  `PENDING`. Deriving it means it can never drift from the ledger.
- A **deposit ceiling**: a rider whose `cash_in_hand` exceeds a configurable
  limit stops being offered new COD orders (`available_riders()` gains the
  filter). This is the actual protection; everything else is reporting.
- Admin "Rider deposits" screen: who owes what, record a deposit, which legs it
  cleared.

The four existing `OrderSettlement.LEGS` already model this exactly — this work
adds the human workflow that moves `rider_cash` from `PENDING` to `PAID`, not a
new money model.

## 3. "Become a Partner" — self-signup behind an approval gate

`Restaurant.Status.PENDING` already exists and `PublicRestaurantListView`
already filters to `ACTIVE`, so an unapproved restaurant is invisible to
customers for free.

Flow:

1. Public form (`/food/partner`) → name, owner name, phone, email, zone,
   address, optional map pin.
2. One **`transaction.atomic`** block creates `Users(role='Restaurant')` +
   `Restaurant(status=PENDING)`. This is non-negotiable: creating the User
   before the thing it belongs to, without atomicity, is the exact trap that has
   bitten both rider and restaurant onboarding — a committed orphan `User` owns
   the username forever and every retry fails with "already exists", with no row
   in the admin panel to delete (see CLAUDE.md, and `prune_orphan_logins`).
3. Owner signs in at `/auth/login` (already role-agnostic) and lands on the
   vendor panel via `utils/roleHome.js`.
4. Vendor panel while `PENDING`: menu, hours and zones are editable; a
   persistent banner says "Awaiting approval — customers can't see you yet";
   order screens are empty by construction.
5. Admin verifies in `ManageRestaurants` → `ACTIVE`. Approval is the moment the
   commission terms are set.

**Guard:** the partner form must not become a back door to a `Restaurant`-role
account with no restaurant. One phone/email → one pending application; a second
submission updates the first rather than creating a second login.

## 4. Dispatch — auto-offer, admin override

Today every order waits for an admin to assign a rider by hand. That is the
throughput ceiling on the whole business.

```
order → CONFIRMED
  offer to nearest rider where is_available AND is_online AND cash_in_hand < ceiling
    accept        → assign, order proceeds
    reject/60s    → next rider
  no rider after the pool is exhausted → admin queue (today's manual screen)
```

- `available_riders()` already ranks by distance and already encodes
  `is_available AND is_online` — the dispatch loop is new, the eligibility rule
  is not.
- **`DeliveryOffer`** (new): `order`, `rider`, `offered_at`, `expires_at`,
  `state` (OFFERED/ACCEPTED/REJECTED/EXPIRED). Gives an audit trail and makes
  "why did nobody get this order?" answerable.
- Assignment still routes through `transition_to()` — it is the single choke
  point where `settle_order()` fires, and no dispatch path may bypass it.
- The rider dashboard gains an incoming-offer card with a countdown; it already
  polls, so no new transport is needed.

## Build order

1. **Fee floor** — `min_commission_amount`, snapshot it, update
   `compute_breakdown` + its invariant tests. Smallest change, immediate
   revenue effect, no UI.
2. **Become a Partner** — public form + atomic signup + PENDING vendor banner +
   admin approve. Unblocks growth without you doing data entry.
3. **Rider cash deposits** — model, admin screen, `cash_in_hand`, ceiling.
   Required before order volume makes float risk real.
4. **Auto-dispatch** — offers, rider accept/reject, admin fallback. Highest
   complexity; do it once volume actually justifies removing the manual step.

## Open questions (not yet decided)

- Rider base pay: flat per delivery, or distance-banded by zone?
- Delivery fee to the customer: currently per-zone — does it stay flat per zone
  once distance is known from the customer's pin?
- Payout day and minimum payout threshold for restaurants.
- Does the platform absorb any part of a coupon discount, or does the restaurant
  bear all of it (today: all of it — `food_net = subtotal − discount`)?
