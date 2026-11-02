# Rider Ecosystem — Future Releases Roadmap

**Date:** 2026-07-19
**Status:** Planned (not yet implemented). Deferred from the food admin panel round.
**Depends on:** Food Delivery Phases 1–2 (restaurants, menus, COD orders) + the Food Admin Panel.

This document captures the **rider (delivery partner) ecosystem** so it can be built in
later releases. It is intentionally separate from the current admin-panel work; nothing here
is implemented yet. Money is BDT (৳); reuse existing patterns (`renderResponse` envelope,
JWT auth, DecimalField money, `food.geo.haversine_km`).

## Vision

A rider is a delivery partner who accepts assigned food orders, picks them up from the
restaurant, delivers to the customer, earns per-delivery pay + tips, broadcasts live location
during active deliveries, and unlocks rewards for hitting targets. Riders primarily use a
**dedicated rider mobile app**; admins manage riders and dispatch from the web console.

## Phase R1 — Rider accounts & profiles

**Backend (`food` app):**
- `Rider` model: `user` (OneToOne → `Users` role `Rider`), `rider_code` (unique, e.g. `RD-XXXX`),
  `vehicle_type` (bike/cycle/foot), `vehicle_number`, `is_available` (online/offline toggle),
  `is_verified` (admin-approved), `current_lat`/`current_lng` (Decimal, last known), `zone` FKs
  (zones a rider serves), `rating` (Decimal), timestamps.
- `RiderStats` (or annotate): `total_deliveries`, `completed_today`, lifetime earnings.
- Admin CRUD `/api/food/admin/riders/` (create rider + owner login, verify, assign zones,
  activate/suspend), mirroring the admin restaurant onboarding pattern.
- Rider self endpoints `/api/food/rider/profile/`, `/api/food/rider/availability/` (toggle online).

**Admin UI:** "Riders" page under the Food menu — list, verify, assign zones, view stats.

## Phase R2 — Dispatch & delivery tasks

**Backend:**
- Extend `FoodOrder` with `rider` FK (nullable) + statuses already include `OUT_FOR_DELIVERY`.
- `DeliveryTask` model: `order` (OneToOne), `rider` FK, lifecycle
  `ASSIGNED → ACCEPTED → PICKED_UP → DELIVERED` (+ `REJECTED`/`REASSIGNED`), timestamps per step,
  `pickup_lat/lng` + `drop_lat/lng` snapshots.
- Admin dispatch: `POST /api/food/admin/orders/<id>/assign/` (manual assign to a rider);
  auto-assign (nearest available verified rider in the order's zone via `haversine_km`) is a
  later enhancement.
- Rider endpoints: `GET /api/food/rider/tasks/` (assigned queue), `POST .../accept/`,
  `.../pickup/`, `.../deliver/`.

**Admin UI:** dispatch board — unassigned orders → assign to available riders; live task states.

## Phase R3 — Earnings, delivery counts & tips ledger

**Backend:**
- `RiderEarning` ledger rows per completed delivery: `rider`, `task`/`order`, `base_pay`,
  `tip_amount` (from `FoodOrder.tip`), `bonus`, `payout_status` (PENDING/PAID), `created_at`.
- `delivery_count` increments on each `DELIVERED`. Daily/weekly/monthly aggregates.
- Tips: `FoodOrder.tip` already captured at checkout (cash or, later, online) → credited to the
  rider's ledger on delivery completion. Cash tips are collected in-hand (marked collected);
  online tips are paid out.
- Admin payout view: per-rider earnings, mark paid, export.

**Rider app:** earnings dashboard (today/week/total), tips, pending payouts, delivery history.

## Phase R4 — Live GPS tracking

**Backend/transport:**
- Rider app broadcasts location during active deliveries → `POST /api/food/rider/location/`
  (throttled) OR a realtime channel (WebSocket/Pusher/Ably) once paid hosting is available.
  Until then, **polling fallback**: store `current_lat/lng` on `Rider`; customer/admin poll.
- Customer "track my order" shows the rider moving toward them (map). Admin fleet map shows all
  active riders (Leaflet + OpenStreetMap tiles).

**Note:** live realtime requires paid hosting or a 3rd-party realtime service (owner to provision).
Ship polling first; upgrade transport later without changing the client contract.

## Phase R5 — Rewards & targets (gamification)

**Backend:**
- `RiderTarget` / `RiderReward`: targets like "complete N deliveries this week", "maintain ≥4.5
  rating", "X deliveries in peak hours" → unlock a `bonus` credited to the earnings ledger or a
  badge. Progress computed from `RiderEarning`/`DeliveryTask` aggregates.
- Admin defines targets (amount, window, criteria); riders see progress.

**Rider app:** targets & rewards screen with progress bars; badges; leaderboard (optional).

## Dedicated Rider Mobile App

- **Platform:** React Native (Expo) — a separate app in the repo (e.g. `mobile/rider/`) or its own
  repo, consuming the **existing REST API** via `fetch` with JWT (same tokens as the web).
- **Auth:** phone/username + password → JWT (reuse the existing token issuance); role must be `Rider`.
- **Core screens:** login, online/offline toggle, assigned task queue, task detail (accept →
  navigate → pickup → deliver), earnings & tips, targets/rewards, profile.
- **Location:** Expo Location for background/foreground GPS during active deliveries → posts to
  `/api/food/rider/location/` (polling) or realtime channel later.
- **Offline tolerance:** queue status updates when connectivity drops; retry on reconnect.
- **Build/dist:** EAS build; distribute via Play Store (Android-first for the local market).

## Build order

R1 (accounts) → R2 (dispatch) → R3 (earnings/tips) → R4 (live GPS, gated on hosting) → R5 (rewards).
The rider mobile app starts alongside R1 (login + availability + task queue) and grows each phase.

## Cross-cutting

- **Roles:** `Rider` already exists in `accounts.Users.role`.
- **Security:** rider endpoints scoped to `request.user` (own tasks/earnings only), mirroring the
  vendor owner-scoping discipline; admin endpoints gated by `IsPlatformAdmin`.
- **Money:** all ledger amounts DecimalField(10,2), BDT.
- **Testing:** TDD per phase — assignment scoping, status-transition legality, earnings math,
  tip crediting, target progress, location-update throttle.
