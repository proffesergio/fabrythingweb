# Production releases

## Storefront discovery — 2026-11-03

- API `dpl_5Y716VeysyDzkqLLmsXWmYfA33X5` and frontend
  `dpl_7xcuNBtuWZVGwyH7L2x4xsAGg5kB` are Ready with existing production aliases.
- Homepage: 12 popular/new-arrival products and 16 distinct discovery products.
  Product details: eight category/brand/recent suggestions with safer navigation.
- Desktop/mobile browser checks, reduced-motion behavior, live catalog browser
  smoke, domain/HTTPS, direct/proxied health, sitemap, and image checks passed.
- DNS and hosting configuration were retained. See
  [release evidence](STOREFRONT_DISCOVERY_RELEASE.md),
  [domain/production audit](PRODUCTION_CHECK_2026-11-03.md), and
  [recovery memory](project-memory/CURRENT.md).

## Control center release

The control center upgrade was deployed to production on 2026-11-02:

- API deployment: `dpl_Cm7Pb7p2mm2JTyjeHdcwVd1Hz3Lz`, aliased to `https://fabrythingapi.vercel.app`.
- Frontend deployment: `dpl_8apcqQxB3ssDqn2NsPpmqbx71Sf5`, aliased to `https://www.fabrything.com`, `https://fabrything.com`, and `https://fabrythingweb.vercel.app`.
- The production API build ran all Django migrations. Catalog `0016_syncjob_syncrun_and_more`, `0017_syncjob_cursor_syncjob_pricing_policy`, `0018_productexternalidentity_and_more`, and `0019_products_source_currency` each completed with `OK`.
- Both the API health endpoint and the storefront `/api/health/` proxy returned `status: ok`, `database: reachable`, and `pending_migrations: []` after deployment.
- Unauthenticated requests to the new sync job endpoint returned HTTP 401.
- A real browser request to the protected dashboard redirected to `/admin/auth` and rendered the username/password sign-in form. Authenticated task mutations were covered by the pre-release backend tests and fixture browser checks; no production administrator credentials were entered.
- The dashboard is at `/admin/shop/control-center`; deployment does not activate a background worker or grant Google property access.

The [operator setup guide](CONTROL_CENTER_SETUP.md) lists the remaining Google credentials, access grants, worker hosting, and FX inputs. No supplier or Google sync jobs were triggered during this release.

## Earlier storefront release

Recovered the interrupted release from the existing workspace and validated the
Vercel frontend and Django backend. Render deployment/keep-warm configuration is
legacy; production runs on Vercel with Neon PostgreSQL and Cloudflare R2 media.

## Changes included

- Vercel Django WSGI deployment, production migrations, database connection
  settings, trusted CSRF origins, and corrected storage secret variable fallback.
- Frontend API proxy and dynamic sitemap rewrite; canonical browser metadata.
- Updated customer WhatsApp number, preserving separately configured numbers.
- Product card annotations, category/restaurant links, and storefront fallback
  content; removed Render keep-warm calls and workflow.
- Sitemap excludes unpublished and future scheduled articles. Regression tests
  cover publication visibility, product visibility, canonical XML, and caching.
- Root `.vercelignore` excludes local environment exports and CLI state from
  uploads. Deploy from the repository root so configured root directories work.

## Validation

- Backend suite: 1,083 tests passed using isolated SQLite test settings.
- New sitemap regression tests: 2 passed after fixing scheduled article exposure.
- Frontend suite: 65 suites / 495 tests passed. Existing React test warnings remain.
- Desktop/mobile browser: home, product details, images, canonical metadata,
  guest cart persistence, totals, checkout entry, and food landing page checked.
- No real customer order or payment was submitted. Authenticated admin workflows
  were covered by automated tests, not a production administrator login.
- Both apex and www domains verify as `configured_correctly`; existing
  Cloudflare proxy/DNS configuration retained.
- Media object returned HTTP 200; sitemap parsed with 521 canonical URLs.
- Browser-generated metadata does not provide server-rendered social previews.

## Release commands

From the repository root:

```sh
vercel deploy --dry --json
vercel deploy --prod --yes --project fabrythingapi
vercel deploy --prod --yes --project fabrythingweb
curl --fail https://fabrythingapi.vercel.app/api/health/
curl --fail https://www.fabrything.com/api/health/
```

Health must report `status: ok`, `database: reachable`, and no pending migrations.
The frontend `/api/health/` must return JSON, not the SPA HTML fallback.
