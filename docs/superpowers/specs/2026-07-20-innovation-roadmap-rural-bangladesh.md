# Innovation Roadmap — Unique Features for Rural Bangladesh (2027)

**Date:** 2026-07-20
**Status:** Research-backed roadmap. Not implemented — pick items per future round.
**Context:** Fabrything = ecommerce + food-delivery platform for a local rural community in
Bangladesh. Goal: features that are genuinely useful *and* differentiated from traditional
platforms (Foodpanda, Daraz, Chaldal), matched to rural realities (weak connectivity, low
literacy, cash/MFS economy, community-oriented buying).

## Grounding trends (2026–2027)
- **Bangla QR** unified QR payments went live **1 July 2026** — one QR works across all
  banks + MFS (bKash, Nagad, Rocket). ([source](https://berndpulch.org/2026/07/16/bangladesh-goes-cashless-with-bangla-qr/))
- **MFS rural penetration**: Nagad 80M+ accounts, lower merchant fees, strong rural reach;
  bKash dominant. Digital payments displacing cash-on-delivery. ([source](https://futurestartup.com/2026/02/23/the-state-of-bangladeshs-digital-economy-at-the-beginning-of-2026/))
- **Food-delivery 2026+**: voice ordering, offline-first for rural/low-connectivity, AI
  predictive reordering, food+grocery hybrid (q-commerce), group/social ordering, eco
  packaging. ([source](https://digitalyieldgroup.com/blog/the-2026-food-drink-app-ecosystem-analysis-q-commerce-ai-and-the-new-era-of-digital-delivery/), [source](https://msmcoretech.com/blogs/top-food-delivery-app-trends))
- **BD e-commerce**: shift to digital wallets/QR, BNPL going mainstream, tech-driven
  last-mile in underserved areas. ([source](https://ecomezi.com/future-of-e-commerce-in-bangladesh/))

## Prioritized feature roadmap

### Tier 1 — highest impact, distinctly local
1. **Bangla QR + bKash/Nagad checkout** — add MFS/QR alongside COD (store *and* food).
   Payment records + webhooks + reconciliation. Biggest lever: moves beyond cash, timely
   with the July-2026 Bangla QR rollout. *(Backend payment app + checkout UI.)*
2. **Community group orders ("village cart")** — neighbors join one shared order to clear a
   restaurant's minimum and split the delivery fee; delivered to a single pickup point. A
   group leader opens a cart, others add items before a cutoff. Genuinely unique for rural
   density patterns. *(New group-order model + join-by-code UI + split billing.)*
3. **Offline-first PWA** — installable app, cached menus/catalog (builds on the
   stale-while-revalidate cache already added), and **queued orders** that sync when
   connectivity returns. Critical where data is intermittent. *(Service worker + outbox queue.)*

### Tier 2 — accessibility & retention
4. **Bangla voice ordering / voice search** — for low-literacy users ("আমার নিয়মিত অর্ডার").
   Web Speech API (bn-BD) → intent → cart. *(Voice UI + intent mapping.)*
5. **Agent-assisted ordering** — a local shopkeeper/agent role places orders on behalf of
   customers without smartphones (phone-in → agent enters), earning a small commission.
   *(New `Agent` role + assisted-checkout flow + commission ledger.)*
6. **SMS / IMO order status** — order updates over channels rural users actually use, no data
   needed. *(SMS gateway integration on order status transitions.)*
7. **Tiffin & daily-essentials subscriptions** — recurring daily meals (tiffin), milk, veg,
   with pause/skip. Big habitual demand in BD. *(Subscription model + scheduler + recurring COD/MFS.)*

### Tier 3 — supply & sustainability
8. **Farmer / local-producer sourcing** — hyperlocal fresh, farmer-to-consumer listings;
   supports the local economy. *(Producer role + fresh catalog + harvest-day scheduling.)*
9. **Eco / reusable packaging option + carbon-lite delivery batching** — batch nearby orders
   onto one rider trip; optional reusable-container deposit. *(Delivery batching in dispatch.)*
10. **MFS cashback loyalty** — points redeemable as bKash/Nagad cashback; referral rewards.
    *(Loyalty ledger + payout integration.)*

## Build sequencing
Payments (T1.1) unblocks loyalty/subscriptions; group orders (T1.2) and PWA offline (T1.3)
are independent and can run in parallel. Voice + agent-assisted (T2) layer onto the existing
checkout. Each becomes its own spec → plan → TDD implementation when chosen.

## Dependencies / notes
- Payments need merchant credentials (bKash/Nagad/SSLCommerz) from the owner + HTTPS webhooks
  (Render). Live GPS / realtime dispatch needs paid hosting (see the rider roadmap).
- All money DecimalField(10,2), BDT. Reuse the existing COD order lifecycle where possible.
- Related: `docs/superpowers/specs/2026-07-19-rider-ecosystem-future-roadmap.md`.
