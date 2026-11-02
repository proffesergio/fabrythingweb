# Production release — 2026-11-02

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
