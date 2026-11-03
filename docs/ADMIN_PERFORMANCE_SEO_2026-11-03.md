# Admin, performance and SEO improvements — 2026-11-03

Implemented locally; this work has not been deployed.

## Scope and behavior

The user chose to merge Overview into Control Center and preserve all existing
features. Shop, Food, News and Custom Printing now share one Control Center
structure. Operations preserves each overview's reports, alerts and tables.
Shop's automation and original business reports remain available in separate
tabs. Management tools are searchable and come from the permission-filtered
backend menu, including shared administration. Existing management routes remain.

The shell adopts the existing dark/cyan Control Center style, supports mobile
navigation and keyboard controls, and retains theme selection. Duplicate Overview
navigation is removed. Existing provider configuration and workers are still
required for live external integrations; demo mode remains explicit and read-only.

## Performance and SEO

- Lazy-load admin and Food application shells instead of including them in the
  storefront's initial bundle. First measured build: main JS gzip 458,689 →
  287,819 bytes (37% smaller); raw 1,576,885 → 933,222 bytes. This measures the main
  bundle, not total page transfer or Core Web Vitals.
  Final build after follow-up fixes: 287,977 bytes gzip / 933,866 bytes raw,
  still approximately 37% smaller gzip than the baseline.
- Prioritize the first hero/product-detail image; defer later carousel images and
  decode asynchronously. Remove unused global AdSense connection hints.
- Give public routes distinct titles/descriptions and product names crawlable
  links. Admin and authentication pages explicitly request noindex.
- Reviewed Google's guide:
  https://developers.google.com/search/docs/fundamentals/seo-starter-guide

The root file `PageSpeed Insights.pdf` is only 1,689 bytes and has invalid PDF
cross-reference/trailer data. Inspection yielded a tiny image, no readable audit
metrics or opportunities. No PageSpeed score or field-performance improvement is
claimed. The user subsequently supplied the audit text: mobile performance 29,
accessibility 88, best practices 96, SEO 100; FCP 1.5s, LCP 20s, TBT 1,130ms,
CLS 0.266, Speed Index 10.5s. Estimated image savings were 2,145 KiB and total
transfer 3,577 KiB. These are the supplied baseline, not post-change measurements.

## Follow-up: authenticated module switching

A real JWT HTTP regression reproduced 403 responses from analytics endpoints
that omitted JWT authentication configuration. Earlier tests used forced
authentication and did not exercise that boundary. The analytics views now use
JWT authentication explicitly. Overview requests also ignore old module responses,
and failures report session/access errors without the obsolete server-wakeup claim.

## Follow-up: supplied Lighthouse audit and contact number

- Hero loading and final slides reserve consistent minimum heights (320px mobile,
  440px desktop), reducing a known source of layout movement.
- Storefront has a main landmark and accessible names for menu, theme and cart
  controls. These address specific audit findings, not a claim that all contrast
  or heading findings are resolved.
- Footer phone and floating WhatsApp share one public configuration response;
  migration 0012 sets the current number to 8801353529899. Shared static support
  text also uses that number. This avoids the old hardcoded footer number.
- Focused follow-up tests: 4 storefront suites / 29 tests and 2 admin suites /
  10 tests passed; full backend rerun: 1,112 tests passed.
- The audit's estimated 2,145 KiB image savings has not been measured or fully
  implemented. No remote image resizing service was introduced. Existing local
  imports cap images at 800×800, but remote image transformation URLs were not
  verified. A new deployed Lighthouse run is still needed to measure LCP/TBT/CLS.

## Security and reliability

- Permission middleware now checks authorization before a view can mutate data.
  Only explicitly unassigned module URLs skip the module permission check.
- Platform-wide Food administration excludes tenant sub-administrators.
- Administrative routes have a role gate; server permissions remain authoritative.
- Menu and report caches are per user; reports have a 15-minute expiry and separate
  date-range keys. Logout clears in-memory state through a fresh application load.
- Overview requests ignore stale responses after range changes and support retry.

## Validation

- Full backend suite: 1,112 passing tests using isolated SQLite settings.
- Frontend full run: 70 suites / 526 tests passed. Additional report/cache suites:
  2 suites / 4 tests passed. Production build passed with existing project warnings.
- Final affected frontend checks: 6 suites / 23 tests passed after integration.
- Browser screenshots and responsive checks use local fixture data; they do not
  demonstrate live provider connectivity or production API responses.
- All four Control Centers passed desktop/mobile checks with no page exceptions
  or document overflow. Granted/shared tool links, legacy redirects, read-only
  demo actions, the mobile drawer and anonymous admin redirects were verified.
  Evidence: [Shop management](screenshots/admin-shop-tools-desktop.png),
  [Shop automation](screenshots/admin-shop-automation-desktop.png),
  [Custom Printing mobile](screenshots/admin-print-mobile.png).

## Design reference

The existing Control Center screenshot was retained as the approved visual source.
12ui conversion/plan artifacts are under `/tmp/fabrything-admin-design`. Existing
live charts, vector icons and brand assets remain functional components; chart
screenshots and extracted icon rasters were not substituted for these controls.
The user-requested unified tabs and module structure take precedence over the
old screenshot's duplicate Overview navigation and purple shell.
Final alignment reused the original LayerDoc under `/tmp/fabrything-admin-alignment`
without a new purchase. Its image-based plan is unanchored, so responsive visual
review and behavior checks provide the acceptance evidence rather than a claimed
automatic pixel-match score.

12ui ledger (actual charges settle server-side):

| Purchase | Stage | Shared stage ceiling |
| --- | --- | --- |
| 4226a253-4100-4de4-a116-27595deb876a | convert | $0.55 |
| 204db2eb-11cc-462c-b8e4-d1b9131abb05 | convert | same $0.55 ceiling |

Two recorded purchases share one stage ceiling, not two separate $0.55 ceilings.
