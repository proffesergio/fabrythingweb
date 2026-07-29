# Admin product import

A screen under **Products → Import Products** (`/admin/manage/product-import`)
that lets an admin pull the latest listings from a reference site, pick the
ones worth stocking, and add them straight into our catalog — without anyone
running a scrape script by hand. Built to fill the (currently empty) Phones
and Gadgets categories — though note Phones → Smartphones specifically has no
source yet; see "The verified category lists" below.

## How to use it

1. Open **Products → Import Products** in the admin sidebar.
2. Pick a **source** (see below).
3. Pick a **category on that site** from the dropdown. On sources that
   support it (see the table below), you can type a **search term** instead
   (e.g. "hoodie") — one or the other is required. On a source with no
   working search, the search box is disabled with an inline note; browse by
   category there.
4. Click **Fetch latest**. This takes a few seconds — every candidate is
   fetched from a real product page on the source site, one request at a
   time (see "Why it's slow" below).
5. Review the results grid: image, name, price (with the discount price
   struck through when the item is on sale), and an **"Already in store"**
   badge on anything we already carry. If the grid comes back empty, the
   message tells you *why*: "no products found" (the category/search is
   genuinely empty) reads differently from "found N product links but
   couldn't fetch any of them" (the source is down or blocking us) — see
   "Zero results vs. unreachable" below.
6. Click candidates to select them (checkbox), pick the **target category**
   in our own taxonomy, and click **Import N selected**.
7. Wait for it — the button shows progress and disables itself while the
   import runs. When it finishes, an **Import results** list shows exactly
   what happened to each product: **Imported**, **Already in store**
   (skipped), or **Failed** with the reason (e.g. no price found on the
   page). Nothing is silently dropped.

Re-running an import with the same source URLs is safe — anything already
present is skipped, never duplicated or overwritten.

## Supported sources

| Source | Status | Browse by category | Search |
| --- | --- | --- | --- |
| potakait.com | Supported — partner store (explicit reseller permission) | Yes (16 verified categories: computer hardware + gadgets/tablets) | **No** — no working search endpoint exists (see below) |
| canvasit.com.bd | Supported — partner store (explicit reseller permission) | Yes (17 verified categories: computer hardware + gadgets/tablets) | Yes |
| fabrilife.com | Supported — one-time seed source, **not** a resale partner | Yes (fashion facet categories) | Yes |
| Arogga.com | **Not yet** — shown in the source picker, disabled | — | — |

**Why potakait.com has no search box.** Every plausible search URL was
checked directly against the live site (`index.php?route=product/search&
search=`, `/search?search=`, `/search?q=`, `/catalogsearch/result/?q=`) and
all four return 404; the homepage HTML also has no `<form>` with a search
input to reverse-engineer a working route from. Rather than ship a search box
that silently returns zero results every time, it's disabled for this source
— both in the UI (hidden, with an explanatory note) and in the API (a search
request against potakait is rejected with a 400 and a `field_errors.q`
message, never a quietly-empty 200). If potakait adds a working search later,
flip `SOURCE_SEARCH_SUPPORTED["potakait"]` in
`catalog/services_scrape_import.py` (and the mirrored constant in
`ImportProducts.js`) once a real URL is verified.

**Why Arogga isn't a source yet.** It's a planned source for the separate
pharmacy/medical phase (SP3). There is no HTML/JSON parser for it in
`catalog/scrape_parsers.py` yet, and building one wasn't in scope for this
tool — importing medicine listings needs its own review (prescriptions,
dosage data, regulatory fields) that a generic "pick and import" screen
shouldn't paper over. It's listed and disabled rather than hidden so it's
clear it's coming, not forgotten.

**potakait.com and canvasit.com.bd** imports get `source_url` set on the
product — that field is what `sync_source_prices` (the "Sync prices" button
on the main Products screen) uses to keep our price mirrored to theirs, and
it only exists for these two partner stores. **fabrilife.com imports never
get `source_url`** — fabrilife hasn't given us resale/re-pricing permission,
so those products are a one-time import, not a synced one. This matches the
existing offline scrape tools (`tools/scrape/scrape_opencart.py` vs.
`tools/scrape/scrape_fabrilife.py`) and is enforced in
`catalog/services_scrape_import.py`, not left to convention.

## The verified category lists

potakait.com and canvasit.com.bd don't expose a machine-readable category
tree `scrape_parsers` can fetch and parse, so the "category on site" dropdown
is a hand-picked list — but every path in it below was checked with a real
request against the live site (200, product grid parsed successfully, a
nonzero live product count) before being added, not guessed.

**Computer hardware:**

| | potakait.com | canvasit.com.bd | Maps to our category |
| --- | --- | --- | --- |
| Laptops | `laptops` | `laptop` | Computers → Laptops |
| Desktops | `gaming-pc` | `desktop-pc` | Computers → Desktops |
| Monitors | `monitors` | `monitor` | Computers → Monitors |
| Processors | `processors` | `processor` | Computers → Components |
| Keyboards | `keyboards` | `keyboard` | Computers → Keyboards & Mice |
| Printers | `printers` | `printer` | Computers → Printers & Office |
| Routers | `router` | `router` | Computers → Networking |

Note **`router` is singular on both sites** — `routers` 404s on both; that
typo already cost a whole scrape run once, so it's called out here
deliberately.

**Gadgets & tablets** (verified 2026-07-29 — live product counts in
parentheses; some potakait/canvasit categories intentionally map to the same
target slug, e.g. both "Earbuds" and "Headphones" land in Gadgets → Earbuds &
Headphones — that's expected, they're separate *source* categories feeding
one *destination* category):

| Maps to our category | potakait.com | canvasit.com.bd |
| --- | --- | --- |
| Gadgets → Earbuds & Headphones | `earbuds` (3), `headphones` (24) | `earbuds` (9), `headphone` (20) |
| Gadgets → Speakers & Audio | `speaker-and-home-theater` (24) | `speaker` (19) |
| Gadgets → Power Banks & Chargers | `power-bank` (5) | `power-bank` (7) |
| Gadgets → Smart Watches | `smart-watches` (3) | `smart-watch` (3) |
| Gadgets → Cameras & Drones | `action-camera` (4) | `action-camera` (4), `drones` (20) |
| Gadgets → Cases & Protection | `mobile-phone-accessories` (2) | `mobile-phone-accessories` (2) |
| Phones → Tablets | `tablet-pc` (4) | `phone-tablet` (20) |
| Gadgets (top-level) | `gadgets` (24) | `gadget` (20) |

**Phones → Smartphones has no source yet.** Neither partner store actually
sells smartphones — potakait and canvasit only carry tablets and phone
*accessories* (cases, chargers, cables), which is why `tablet-pc`/
`phone-tablet` map to Phones → Tablets and there is no equivalent smartphone
path in either list above. **The Phones → Smartphones category can't be
stocked from this import tool today** — filling it needs either a new source
site with a parser added to `catalog/scrape_parsers.py`, or manual entry
through the normal "Add Product" form. This isn't a bug to work around; it's
what these two reference sites actually sell.

fabrilife's category list *is* live/authoritative — it's the same
facet-category mapping `tools/scrape/scrape_fabrilife.py` already uses to
build fixtures, not a guess.

## Zero results vs. unreachable

A browse response distinguishes two very different reasons the candidate
grid can come back empty, because silent empty states have bitten this
codebase before (see `CLAUDE.md`):

- **`listing_product_count: 0`** — the listing/search page itself returned no
  product links at all. The category or search term genuinely has nothing in
  it right now. The UI shows *"No products found for that category/search."*
- **`listing_product_count > 0` but `candidates` is still empty** — the
  listing found product links, but every one of those product pages then
  failed to fetch or parse (`fetch_failures` counts them). This usually means
  the source site is down, blocking us, or its markup changed. The UI shows
  *"Found N product link(s) on the source site but couldn't fetch/read any
  of them — it may be down or blocking us."* instead of the misleading
  "nothing found" message.

A hard failure to reach the listing/search endpoint itself (bad category,
network error, timeout) is different again — that's a **502** with a message,
not a 200 with an empty list, so it's never confused with either of the two
cases above.

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
  network. `OPENCART_CATEGORY_PATHS` (per-source, verified) and
  `SOURCE_SEARCH_SUPPORTED` (which sources have a working search) live here.
- `catalog/controllers/ProductImportController.py` — the two endpoints,
  both platform-scope only (`core.helpers.isPlatformScope`):
  - `GET /api/products/admin/import/browse/?source=&category=&q=`
  - `POST /api/products/admin/import/` — `{source, source_urls[], category_id}`
- `frontend/.../pages/products/ImportProducts.js` — the admin screen,
  mounted at `/admin/manage/product-import`; nav entry seeded by
  `python manage.py seed_admin_modules` (child of "Products"). Its
  `FALLBACK_CATEGORIES` and `SEARCH_SUPPORTED` constants mirror the backend
  ones above and should be kept in sync if either changes.
