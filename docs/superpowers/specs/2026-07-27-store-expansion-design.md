# Store expansion: category editor fix + taxonomy + real seed data (SP1 + SP2)

Date: 2026-07-27
Status: approved in brainstorming; this doc is the written spec for review.

## Context

The storefront (`catalog` + `storefront` apps) currently has a small,
clothing-leaning catalog. We are expanding it into a multi-vertical store:
Fashion (fabrilife-style depth), Phones / Computers / Gadgets (dazzle-style),
plus reseller inventory from two partner computer shops
(potakait.com, canvasit.com.bd) whose owners have invited us to resell at
dealer pricing. A pharmacy vertical (SP3), the Customer-app store surface
(SP4) and a Messenger chat button (SP5) are approved on the roadmap but are
**out of scope for this spec** — each gets its own spec.

Sub-project order (user-approved): SP1 → SP2 → SP3 → SP4 → SP5.

## SP1 — Fix the admin category editor

### Symptom (reported, reproduced from console log)

Admin > Categories > Edit "Men's Fashion" shows "Item Not Found" /
"Error Fetching…". Console: `GET /api/getForm/category/1/ → 404` with
message `Model Item Not Found`. (One stray 500 also appeared in the
console; reproduce the page during implementation and chase it only if it
recurs — it may be unrelated noise.)

### Root cause (hypothesis to confirm with a failing test first)

`DynamicFormController.get` (`accounts/controllers/DynamicFormController.py:106`)
resolves the edit target with:

```python
model_class.objects.filter(id=id, domain_user_id=request.user.domain_user_id)
```

Seeded / platform-global categories have `domain_user_id` NULL (or a
different user), so the row exists — the list endpoint returns it — but the
edit-form fetch 404s. The save path (`post` with `id`) resolves the target
the same way and would fail identically.

### Fix

The dynamic form's edit filter now uses the same platform-scope rule as the
list views: Super Admins and domain-root users (where `user.role == 'Super Admin'
or user.domain_user_id_id == user.id`) can edit any row; everyone else filters
strictly to their own domain. This widens visibility from seeded rows (owned by
the first Super Admin via `seed_bd_store`) to all platform staff, matching
what the category/product list endpoints already show.

Ownership is preserved on update — the `post` endpoint no longer overwrites
`domain_user_id` and `added_by_user_id` when editing, so seeded rows retain
their creator even when edited by a different admin. New rows are still
assigned to the editing user's domain.

### Tests (write first, watch them fail)

1. Admin fetches edit form for a NULL-domain category → 200 with fields.
2. Admin saves an edit to a NULL-domain category → 200, row updated.
3. A user from domain A still gets 404 for domain B's category (no leak).
4. Existing behaviour for own-domain rows unchanged.

## SP2 — Taxonomy + real seed data + reseller price sync

### Category tree

All under the existing `Categories.parent_id` hierarchy, seeded
platform-owned (NULL domain). Top level → subcategories:

- **Fashion** — Men (T-shirts, Polos, Shirts, Panjabi, Hoodies & Sweatshirts,
  Jackets, Joggers & Trousers, Shorts), Women (Kurti & Tops, T-shirts,
  Salwar Kameez, Co-ords, Leggings & Palazzo), Kids (Boys, Girls).
  Mirrors fabrilife.com.
- **Phones** — Smartphones, Tablets. Brand lives on `Products.brand`,
  not in the tree.
- **Computers** — Laptops, Desktops & All-in-Ones, Monitors, Components
  (CPU/RAM/SSD/GPU/PSU), Keyboards & Mice, Printers & Office, Networking.
  Mirrors dazzle + the two partner stores.
- **Gadgets** — Smart Watches, Earbuds & Headphones, Speakers & Audio,
  Power Banks & Chargers, Cases & Protection, Cameras & Drones, Smart Home.

Existing categories (e.g. today's "Men's Fashion") are re-parented/renamed
into this tree by the seed only when their slugs match; otherwise left
untouched for the admin to reconcile.

### Data sources and scrape feasibility (checked 2026-07-27)

| Site            | Vertical            | Tech                 | Scrapability                                               |
| --------------- | ------------------- | -------------------- | ---------------------------------------------------------- |
| fabrilife.com   | Fashion             | server-rendered HTML | easy; `/product/[id]-[slug]`                               |
| dazzle.com.bd   | Phones/Gadgets      | Next.js              | parse `__NEXT_DATA__` JSON; fallback: hand-curated fixture |
| potakait.com    | Computers (partner) | OpenCart, SSR        | easy; BDT price plain in HTML                              |
| canvasit.com.bd | Computers (partner) | OpenCart, SSR        | easy; BDT price plain in HTML                              |

Copyright note: dazzle/fabrilife data is competitor content used as seed
data; the partner stores have given explicit permission. If any source
objects, their fixture is replaceable — nothing else depends on where a
product came from.

### Pipeline

```
tools/scrape/*.py  →  catalog/fixtures/seed/*.json  →  seed_store_catalog
(one-time, local)      (committed, reviewable)          (idempotent, prod-safe)
```

1. **Scrape scripts** — `backend/EcommerceInventory/tools/scrape/`
   (`scrape_fabrilife.py`, `scrape_dazzle.py`, `scrape_opencart.py` shared
   by both partner stores). Python, `requests` + BeautifulSoup, polite
   rate-limiting (1 req/s), never imported by Django code, never run in prod.
2. **Fixtures** — `catalog/fixtures/seed/{fabrilife_fashion,dazzle_tech,
potakait,canvasit}.json`. One schema for all sources:

   ```json
   {
     "category_path": ["Computers", "Laptops"],
     "name": "...",
     "slug": "...",
     "price": 84500,
     "discount_price": 82000,
     "description": "...",
     "specifications": { "CPU": "..." },
     "brand": "Asus",
     "brand_model": "Vivobook 15",
     "gender": "MEN",
     "sizes": ["S", "M", "L", "XL"],
     "material": "Cotton",
     "images": ["https://…"],
     "source_url": "https://potakait.com/…" // partner items only
   }
   ```

   Fashion entries use `gender`/`sizes`/`material` (→ one `ProductVariant`
   per size); tech entries use `specifications`/`brand`. Volume: ~10
   products per leaf subcategory (~150–250 total).

3. **Seed command** — `seed_store_catalog`, **create-only** (the
   `seed_bancharampur` lesson: re-running a seed must never clobber admin
   edits; `--force-update` is the explicit escape hatch). Idempotency key is
   the product slug. At seed time each image URL is downloaded once and
   re-uploaded through the existing storage helper or in our database by compressing to a affordable size (S3 when AWS keys are
   set, else local `MEDIA_ROOT`); the stored product keeps _our_ URL, never
   a hotlink.

### Reseller price sync (partner stores only)

New nullable fields on `Products` (one migration):

- `source_url` (URLField, blank) — the partner product page.
- `source_price` (Float, null) — last price seen at the source.
- `price_synced_at` (DateTime, null).

`sync_source_prices` management command: for every product with a
`source_url`, re-fetch the page, parse the current price with the same
per-site parser the scraper uses, and when it changed update
`initial_selling_price` (and `discount_price` when the source shows one),
stamp `source_price`/`price_synced_at`, and print a change summary.
`--dry-run` supported. A markup percentage (env `RESELLER_MARKUP_PERCENT`,
default 0) is applied on top of the source retail price:
`our price = source retail × (1 + markup%)`. Default 0 mirrors the partner
site's retail price exactly.

"Real-time" in practice: an admin-only endpoint
`POST /api/products/admin/sync-prices/` runs the same service function, so
the admin panel gets a "Sync prices now" button (SP2 ships the endpoint;
the button is a one-liner in the products admin page). Scheduled runs can
be added later via the existing cron-backstop pattern; on-demand covers the
current need.

### Frontend checks (storefront is API-driven; expected small)

- MegaMenu / CategoryGrid / ProductCatalog should pick up the new tree
  automatically — verify against the seeded DB.
- `ProductDetail` must render `specifications` as a spec table for tech
  items; add that section if it doesn't.

### Testing

- SP1 regression tests (above).
- Seed: running `seed_store_catalog` twice creates no duplicates; an
  admin-edited product name survives a re-run; category tree integrity
  (every subcategory has its parent); fixture schema validation (every
  entry has name, price > 0, category_path resolving into the tree).
- Price sync: parser unit tests against saved HTML snippets from both
  partner sites (no network in tests); price-change updates the right
  fields; `--dry-run` writes nothing; markup applied correctly.

### Out of scope (later specs)

- SP3 pharmacy vertical (OTC live first; Rx flow feature-flagged until
  DGDA license; AI prescription reading with mandatory human review).
- SP4 store surface in the Customer app.
- SP5 Messenger floating chat button (m.me deep link; Meta discontinued
  the embeddable chat plugin in 2024).
- Facebook page integration / live human support chat (user side-request,
  parked with SP5).
