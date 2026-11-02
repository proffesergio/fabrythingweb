# Storefront discovery release — 2026-11-03

## Changes

- Popular collection shows up to 12 products. A new Discover More carousel shows
  up to 16 additional catalog items, with category variety and no overlap with
  new arrivals. These are live catalog products, not invented sample listings.
- Product details show up to eight suggestions, ordered by category, brand, then
  recency. Inactive products and the current product are excluded. Promotion
  respects the store's prescription-sales switch.
- Cards enter with a short staggered fade/slide as they come into view. Reduced
  motion disables translation, hover movement, and carousel animation. Browsing
  controls have accessible labels and remain visible on mobile.
- Following a suggestion clears the previous image, size, quantity, and details
  tab. Late responses from the previous product cannot overwrite the new item.
- The interrupted Control Center source and its setup/verification guides are
  preserved with this release. Provider activation requirements remain documented
  in [CONTROL_CENTER_SETUP.md](CONTROL_CENTER_SETUP.md).

## Automated verification

- Frontend full run: 67 suites passed, with one new test assertion requiring an
  asynchronous wait. After correcting that test, the focused discovery suite
  passed 2/2. The final source is covered by passing runs of all 68 suites / 509
  tests. No runtime change was needed for the assertion correction.
- Backend: 48 discovery/sync/pricing/import tests passed; final discovery rerun
  5/5 passed; migration drift check clean. See
  [STOREFRONT_BACKEND_VERIFICATION.md](STOREFRONT_BACKEND_VERIFICATION.md).
- Staged text scan found no private key blocks, AWS access key IDs, GitHub tokens,
  or PostgreSQL connection strings. This is a focused check, not a comprehensive
  credential audit.

## Production API

API deployment `dpl_5Y716VeysyDzkqLLmsXWmYfA33X5` is Ready and aliased to
`fabrythingapi.vercel.app`. Post-deployment checks found healthy direct/proxied
health endpoints, 12 arrivals, 16 unique non-overlapping discovery products, and
eight unique suggestions excluding the sampled current item. See
[PRODUCTION_CHECK_2026-11-03.md](PRODUCTION_CHECK_2026-11-03.md).

## Frontend verification

- Optimized production build passed with existing lint/dependency warnings.
  Local verification used a 1536 MB V8 heap and disabled source maps after the
  initial 1024 MB heap limit proved insufficient. Hosting configuration is unchanged.
- Chrome checks of the built frontend passed at 1440 px desktop and 390 px mobile:
  12 popular cards, 16 discovery cards, eight suggestions, working next navigation,
  product-to-product navigation, no document overflow and no page exceptions.
- Mobile check used reduced motion and confirmed the carousel's transition speed
  is zero. Desktop uses the normal 350 ms navigation transition.
- Swiper accessibility messages explicitly retain collection-specific navigation
  labels. This fixes the generic labels found during browser QA.
- Browser API responses were intercepted fixtures; screenshot names beginning
  `storefront-` show test products, not production catalog listings. The separate
  production script and HTTP audit verify the deployed application and real data.

## Final production result

Frontend `dpl_7xcuNBtuWZVGwyH7L2x4xsAGg5kB` is Ready with apex/www aliases.
The production browser check passed against real data: 12 arrivals, 16 discovery
products, eight suggestions, carousel navigation, no page exceptions, and no
mobile document overflow. The production screenshots show real catalog items.
No cart, order, payment, or administrator action was submitted.

The final HTTP audit passed for apex redirect, HTTPS www home/shop/detail pages,
direct/proxied API health, sitemap (521 canonical www URLs), and sampled media.
No DNS or hosting configuration change was necessary. Source and recovery memory
are versioned together; local tooling deletions and local design caches are excluded.
