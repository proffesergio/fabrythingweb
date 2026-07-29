# Admin product import

A screen under **Products → Import Products** (`/admin/manage/product-import`)
that lets an admin pull the latest listings from a reference site, pick the
ones worth stocking, and add them straight into our catalog — without anyone
running a scrape script by hand. Built to fill the (currently empty) Phones
and Gadgets categories.

## How to use it

1. Open **Products → Import Products** in the admin sidebar.
2. Pick a **source** (see below).
3. Pick a **category on that site** from the dropdown, or type a **search
   term** instead (e.g. "hoodie"). One or the other is required.
4. Click **Fetch latest**. This takes a few seconds — every candidate is
   fetched from a real product page on the source site, one request at a
   time (see "Why it's slow" below).
5. Review the results grid: image, name, price (with the discount price
   struck through when the item is on sale), and an **"Already in store"**
   badge on anything we already carry.
6. Click candidates to select them (checkbox), pick the **target category**
   in our own taxonomy, and click **Import N selected**.
7. Wait for it — the button shows progress and disables itself while the
   import runs. When it finishes, an **Import results** list shows exactly
   what happened to each product: **Imported**, **Already in store**
   (skipped), or **Failed** with the reason (e.g. no price found on the
   page). Nothing is silently dropped.

Re-running an import with the same source URLs is safe — anything already
present is skipped, never duplicated or overwritten.

## Supported sources — and why Arogga isn't one yet

| Source | Status |
| --- | --- |
| potakait.com | Supported — partner store (explicit reseller permission) |
| canvasit.com.bd | Supported — partner store (explicit reseller permission) |
| fabrilife.com | Supported — one-time seed source, **not** a resale partner |
| Arogga.com | **Not yet** — shown in the source picker, disabled |

Arogga is a planned source for the separate pharmacy/medical phase (SP3).
There is no HTML/JSON parser for it in `catalog/scrape_parsers.py` yet, and
building one wasn't in scope for this tool — importing medicine listings
needs its own review (prescriptions, dosage data, regulatory fields) that a
generic "pick and import" screen shouldn't paper over. It's listed and
disabled rather than hidden so it's clear it's coming, not forgotten.

**potakait.com and canvasit.com.bd** imports get `source_url` set on the
product — that field is what `sync_source_prices` (the "Sync prices" button
on the main Products screen) uses to keep our price mirrored to theirs, and
it only exists for these two partner stores. **fabrilife.com imports never
get `source_url`** — fabrilife hasn't given us resale/re-pricing permission,
so those products are a one-time import, not a synced one. This matches the
existing offline scrape tools (`tools/scrape/scrape_opencart.py` vs.
`tools/scrape/scrape_fabrilife.py`) and is enforced in
`catalog/services_scrape_import.py`, not left to convention.

## The per-request import cap (12 products)

Every fetch against potakait.com, canvasit.com.bd or fabrilife.com goes
through `tools/scrape/common.polite_get`, which sleeps first so we never
exceed **1 request/second** — these are the owner's friends' stores, not
scrape targets, and hammering them would be a good way to lose the resale
permission. That makes both browsing and importing inherently slow: each
candidate costs at least one request (and browsing costs one *listing*
fetch plus one *product-detail* fetch per candidate, because neither
OpenCart theme's listing card carries price or images — only the full
product page does).

**Import is capped at 12 products per request** for two reasons:
- A bigger batch would take well over 10-15 seconds and risk tripping a
  gateway/proxy timeout mid-import, which would leave the admin unsure what
  actually got created.
- It keeps each request's load on the source site small and predictable.

The UI enforces this by disabling the Import button once more than 12 are
selected (with an inline warning); the API rejects an over-cap request with
a 400 rather than silently importing only the first 12 — split a bigger pull
into multiple import runs instead.

Browsing is capped at 12 candidates per search for the same reason.

## What "already in store" matches on

A candidate is flagged **Already in store** when a product with the same
**slug** (Django's `slugify()` of the candidate's name — the same
slugification every product in this catalog already uses) exists in our
`Products` table. This is a name match, not a source-URL match: if you
already hand-entered "iPhone 15 128GB" and the source site also calls it
that, it's flagged as owned even though nothing was ever imported from that
URL. Re-importing an already-flagged candidate is harmless either way — the
import endpoint independently re-checks the same slug at import time and
skips it rather than creating a duplicate or overwriting your edits.

## Under the hood (for future maintenance)

- `catalog/scrape_parsers.py` — the pure HTML/JSON parsers (unchanged,
  reused as-is).
- `catalog/services_import.py` — `seed_product_entry()`, the single
  "fixture/scraped entry → Products + ProductVariant" creation path, shared
  by `seed_store_catalog` (the one-time fixture seeder) and this tool.
  Extracted from `seed_store_catalog._seed_products` so the two can never
  drift apart.
- `catalog/services_scrape_import.py` — `browse_candidates()` and
  `import_candidates()`, the machinery behind the two endpoints below. Every
  network call goes through an injectable `fetch`, so tests never touch the
  network.
- `catalog/controllers/ProductImportController.py` — the two endpoints,
  both platform-scope only (`core.helpers.isPlatformScope`):
  - `GET /api/products/admin/import/browse/?source=&category=&q=`
  - `POST /api/products/admin/import/` — `{source, source_urls[], category_id}`
- `frontend/.../pages/products/ImportProducts.js` — the admin screen,
  mounted at `/admin/manage/product-import`; nav entry seeded by
  `python manage.py seed_admin_modules` (child of "Products").

### The category dropdown is curated, not live

potakait.com and canvasit.com.bd don't expose a machine-readable category
tree `scrape_parsers` can fetch and parse, so the "category on site"
dropdown is a hand-picked starting list
(`OPENCART_CATEGORY_PATHS` in `services_scrape_import.py`), weighted toward
Phones and Gadgets since that's what's empty today. fabrilife's list *is*
live/authoritative — it's the same facet-category mapping
`tools/scrape/scrape_fabrilife.py` already uses. If a curated potakait/
canvasit path doesn't match the live site, use the search box instead — it
falls back to the site's own search route.
