# Product detail page: the overlap fix, the size chart, and the visual refresh

Covers three changes to `frontend/ecommerce_inventory/src/storefront/pages/ProductDetail.js`
and the catalog backend behind the size chart, done in that order on
`fix/product-details-ui` (Task 1 fixed and committed alone first because it
was a visible, live bug on every product page).

## 1. The image-overlap bug

**Symptom reported by the owner:** the white product-image tile visually sat
on top of the details column, clipping the left edge of the brand name
("FABRILIFE" rendered as "BRILIFE"), the title, and the price (৳1,240 rendered
as "51,240").

**Root cause.** The image tile is a `Box` with both a percentage width and
padding:

```js
<Box sx={{ width: '100%', height: {...}, p: { xs: 2, md: 3 }, bgcolor: '#fff', ... }}>
```

That combination is only safe under `box-sizing: border-box` (padding counted
*inside* the declared width). The storefront route is **never wrapped in
`<CssBaseline />`** — only the admin shell (`layout/layout.js`) and the food
frontend (`food/theme.js` / `FoodThemeContext`) mount it; `App.js`'s
`StorefrontWrapper` wraps the storefront in a plain `ThemeProvider` only. MUI's
own `Grid` component forces `box-sizing: border-box` on itself via a styled
rule regardless of `CssBaseline` (confirmed by reading
`node_modules/@mui/material/Grid/Grid.js`), so the two `Grid item` *columns*
are always sized correctly — the bug was one level deeper, in the plain `Box`
elements inside the image column. Under the browser's real default
(`content-box`, since nothing resets it on this route), the tile's padding was
added **on top of** its 100% width, rendering it wider than its 50% column and
letting its opaque white background paint over the start of the details
column's text. The thumbnail boxes (fixed `64px` width + padding) had the same
trap at a smaller scale.

**Fix (commit "Fix product image tile overlapping product details").** Made
`boxSizing: 'border-box'` explicit on both the main image tile and each
thumbnail box, plus `maxWidth: '100%'` and `display: 'block'` on the `<img>` as
belt-and-suspenders. This is a local, low-risk fix scoped to the one file
rather than adding `<CssBaseline />` to the whole storefront (`StorefrontWrapper`
in `App.js`) — the wider fix is arguably "more correct" and would prevent the
same class of bug elsewhere on the storefront, but it changes global box
sizing (and default margins/background) across every storefront page and
could not be visually verified in this session (no browser available). If a
similar overlap ever turns up on another storefront page, that is the fix to
reach for; flagged here rather than done blind.

**What could not be visually confirmed:** no browser was available in this
session (`mcp__claude-in-chrome` reported "Browser extension is not
connected"), so the fix is verified by CSS/box-model reasoning and the MUI
source, not a screenshot. Reasoning was cross-checked against
`node_modules/@mui/material/Grid/Grid.js` (Grid always forces border-box) and
by confirming no other global reset exists on the storefront route (`grep -n
"box-sizing"` across `public/index.html` and every `src/*.css` returns
nothing). **A human should load a product page on desktop and mobile in a
real browser and confirm the brand/title/price are fully visible and the
image tile no longer visually overlaps the details column** before
considering this fully closed.

## 2. Size chart

### Data: where it comes from and how it gets onto a product

`catalog.Products.size_chart` (`{"M": {"chest": 36, "length": 30, "sleeve":
21}, ...}`, inches) already existed and `ProductDetail.js` already rendered
it — the problem was that all 64 seeded Fabrilife products had it empty,
because the parser that seeded them predates chart extraction.

**Parser (`catalog/scrape_parsers.py`).** `parse_fabrilife_product` now also
returns `size_chart`, read by `_extract_fabrilife_size_chart` from the "Size
chart - In inches (Expected Deviation < 3%)" table on the live product page
(INCH tab only — the site also renders a CM tab with the same numbers × 2.54,
which is intentionally ignored so there is only one source of truth; CM is
computed at render time instead, both in the parser's test coverage and in
the frontend). The committed fixture (`catalog/test_fixtures/fabrilife_product.html`,
a Panjabi) has no size chart at all, so a second fixture,
`fabrilife_product_size_chart.html`, was captured fresh from
`https://fabrilife.com/product/74169-womens-premium-tops-estrella` (a product
confirmed live to have one), trimmed to ~8&nbsp;KB. Both are exercised in
`catalog/test_scrape_parsers.py`.

`size_chart` was also wired into `seed_product_entry`
(`catalog/services_import.py`) and into the one-time offline scraper
(`tools/scrape/scrape_fabrilife.py`), so a *future* re-scrape of Fabrilife
(or a fresh product) carries its chart through automatically. Neither of
those touches the 64 products already in the database — that needed a
separate backfill.

### Backfill: how the 64 already-seeded products get a chart

Fabrilife products deliberately carry no `source_url` (`catalog/scrape_parsers.py`'s
module docstring: fabrilife.com is a one-time seed source, not a reseller
partner like potakait/canvasit, which do get re-priced by `sync_source_prices`
via their stored URL). So there is no stored page to refetch by URL.

**Approach taken:** look each candidate product up by its exact name against
fabrilife.com's own public, search-only Algolia index (`app 2UIXGXYA5O`,
index `products` — the same endpoint `parse_fabrilife_listing` and
`scrape_fabrilife.py` already use for category listings). Confirmed live
(2026-07-29, querying for "Womens Premium Tops - Estrella"): the search hit
itself carries a `size_chart` field — a JSON-encoded string with the same
inch/cm chart data the page renders — so **no second fetch of the product
page HTML is needed at all**; `parse_fabrilife_algolia_size_chart` reads it
straight off the hit.

**Reliability / match safety:** a hit only counts as a match when its `title`
equals the product's stored `name` **exactly** (case-insensitive). This is
deliberately strict — an approximate/fuzzy match risks silently writing one
product's measurements onto a different, similarly-named product on a live
page, which is worse than leaving the chart empty. Products seeded from this
same fixture data were named directly from the scraped page title, so an
exact match is expected to succeed for every product that still exists on the
live site under the same name; a renamed or delisted product is reported as
`no_match` rather than guessed at.

**Is this reliable? Yes, with the caveat above.** It is not a heuristic
scrape of rendered markup (which could break on a template change) — it reads
structured data the site's own search index already exposes, gated by an
exact name match. The only way it silently misses a product is if
fabrilife.com renamed or delisted that product since seeding, which shows up
plainly as `no_match`/`error` in the report rather than a wrong write.

**Command:** `catalog/management/commands/backfill_fabrilife_size_chart.py`,
dry-run by default (house style of `purge_demo_catalog`):

```bash
python manage.py backfill_fabrilife_size_chart            # report only
python manage.py backfill_fabrilife_size_chart --apply     # write
```

Only ever touches `size_chart`; a product that already has one is never a
candidate again (idempotent, safe to re-run). **Do not run this yourself for
the owner** — per the repo's test/token budget, hand this one-time,
network-heavy job (up to 64 outbound requests) to the owner to run.

**On Render (no shell on the free plan)** — mirrors the
`PURGE_DEMO_CATALOG`/`APPLY_PRICING_MARKUP` two-stage pattern in `build.sh`:

1. Set **`BACKFILL_FABRILIFE_SIZE_CHART=report`** in the Render dashboard,
   deploy, and read the dry-run (which products matched with a chart, which
   matched but have no chart on the live site, which had no exact-name match,
   which errored) in the build log.
2. Once it looks right, set **`BACKFILL_FABRILIFE_SIZE_CHART=apply`** and
   deploy again — this writes `size_chart` onto the matched products.
3. **Remove the variable.** The command is idempotent (matched products are
   never candidates again), but there's no reason to keep re-running it on
   every deploy.

### Presentation

Shown only for fashion items that actually have chart data — the "Size
Chart" button and the dialog are both gated on `hasSizeChart` (at least one
size with at least one measurement), so an empty table can never render.
Matches the reference: "Size chart - In inches (Expected Deviation < 3%)"
heading, **INCH/CM** tabs, a `Size` column plus one column per measurement key
present in the data (currently `chest`, `length`, `sleeve` for the seeded
Fabrilife tops). CM is computed in the browser as inches × 2.54 (rounded to
one decimal) rather than sourced separately, so it can never drift from the
inch values — same rule the parser uses when it ignores the site's own CM
table.

## 3. Visual refresh (Task 3)

Scoped to `ProductDetail.js` only, within the existing MUI theme, no new
dependencies:

- Main image tile is an outlined `Paper` instead of a bare `Box`, for a
  slightly more defined card edge; thumbnails always show a subtle border
  (theme `divider`, or `secondary.main` when selected) instead of only on
  selection, plus a small hover lift. `object-fit: contain` and the white
  (`#fff`) tile background are unchanged, per instruction — the product
  photos are shot on white.
- Brand is now a bold `overline` in the secondary color instead of a plain
  gray caption; the title uses responsive font sizes instead of one fixed
  `h4` size; the price wraps cleanly on narrow screens (`flexWrap: 'wrap'`).
- Quantity stepper is a rounded pill with a bolder count and the minus button
  now actually disables at quantity 1 (it silently no-op'd before).
- Size buttons have a fixed height for a more consistent, easier-to-tap row.
- Description gets its own "Description" heading instead of a bare paragraph
  floating among the other sections.
- Specifications/Reviews/Q&A now live inside a bordered `Paper` card with a
  **scrollable** `Tabs` strip (the old fixed-width tabs could clip on narrow
  phones) and zebra-striped specification rows.

Mobile stack order was already correct — the image `Grid item` precedes the
details `Grid item` in JSX, so at `xs` (both `xs={12}`) they stack image-first
— and is unchanged.

## Verification

- Backend: `manage.py test catalog` (181 tests) and `manage.py test
  storefront` (48 tests) while iterating; full suite once before the final
  commit — **698/698 passing** (baseline was 681; the difference is the new
  parser/backfill tests added here).
- Frontend: `npm test -- --watchAll=false` — **169/169 passing**, excluding
  the pre-existing `swiper` module-resolution failure in `App.test.js`
  (documented in the repo's `CLAUDE.md`, not touched by this work).
  `CI=false npx react-scripts build` exits 0 with no new lint warnings (none
  reported against `ProductDetail.js`).
- **Needs a human eye in a browser:** the Task 1 overlap fix itself (no
  screenshot was possible this session — see "What could not be visually
  confirmed" above), and a general look at the Task 3 visual refresh on a
  real phone-width viewport, since CSS/box-model reasoning and passing tests
  don't substitute for seeing the rendered page.
