# Publishing, SEO, and capacity checkpoint — 2026-11-07

## User decisions

- BDT prices: nearest 5 below 50, nearest 10 from 50–499, nearest 100 minus 1 from 500. Half-up ties. Examples: 26→25, 69→70, 800→799, 273→270, 2137→2099.
- AdSense only on product blog and NobleSeek news. Paid Google Ads campaigns are outside this request.
- n8n produces approximately **20 articles daily**, also posting to the associated Facebook page.
- Visual draft approved; blog and SEO/operations interfaces implemented.

## Local implementation

Pricing calculations use Decimal; existing product FloatFields remain for compatibility. Manually entered prices and historical orders are preserved. Imports, price sync and the existing pricing backfill use the shared calculation. Explicit supplier shipping/fee/margin promises round upward when necessary. Run the existing pricing backfill in dry-run mode and review its output before any production repricing; do not apply markup twice to a selling price.

Migration `nobleseek/0004_article_content_type_publishingsettings.py` adds NEWS/BLOG separation and publishing policy. Existing articles default to NEWS. The production migration has been applied successfully. Existing catalog prices have not been bulk repriced; refresh automatic prices from source data to avoid double markup.

New API contracts, all beneath `/api/store/nobleseek/`:

| Endpoint | Purpose |
| --- | --- |
| `blog/` | Public, paginated, published/due blog articles |
| `blog/<slug>/` | Public blog detail, canonical URL and BlogPosting structured data |
| `admin/articles/?content_type=BLOG` | Existing staff editor API, filtered to guides |
| `admin/publishing-settings/` | Staff JWT GET/PATCH publishing controls |
| `admin/operations/` | Staff JWT counts, last-24h output, metadata audit, PostgreSQL database size and explicitly labeled estimates |

Publishing settings default to no pause, no daily cap, no automation review requirement. These defaults preserve the current workflow. `require_review_for_automation` applies only when the caller explicitly sends `automation: true`; it cannot identify an existing n8n caller by itself. Pause/cap cover the shared API/trend creation service, not arbitrary ORM writes or independent n8n/Facebook jobs. Pausing this service does not cancel Facebook posts, scheduled publication, or existing-article updates. Route all automation writes through the API rather than direct SQL. A shared row lock serializes cap checks on PostgreSQL.

Rich-text writes are sanitized. Older stored HTML is not automatically rewritten. News view increments are atomic; cache deduplication is best effort because the default Django cache is process-local on serverless instances.

The browser ad guard now allows only exact `/blog` and `/nobleseek` path families. Turn **Auto ads OFF** and use manual editorial slots for the strictest separation: loading an external advertising script once in a React SPA cannot reliably revoke all third-party behavior after client navigation. Configure AdSense page exclusions as an additional control. This change does not change the AdSense account or publisher registration.

## Subdomain rollout

Cloudflare DNS is configured and Vercel reports `nobleseek.fabrything.com` configured correctly. HTTPS is active with automatic certificate renewal. Existing Cloudflare nameservers are unchanged.

The API production release is ready. Migration 0004 succeeded and `configure_news_domain --if-default` set the canonical news origin to `https://nobleseek.fabrything.com`. News article paths remain `/nobleseek/<slug>`. Frontend deployment includes root-to-news routing, permanent old www news redirects, same-origin API proxying, and news-specific robots/XML sitemap. Blog remains under `https://www.fabrything.com/blog`.

Search Console verification/submission and n8n/Facebook link updates require the relevant account/workflow owner. Existing published Facebook posts are not rewritten.

## Capacity at 20 articles/day

Illustrative assumptions: 30,000 bytes text and one 200,000-byte image per article. Decimal GB is used below.

The configurable API estimator starts with more conservative image assumptions: 20,000 text bytes and 300,000 image bytes per article. Those defaults imply approximately 2.336 GB/year at 20 articles/day; replace them with measured averages. The table below is a separate illustrative scenario, not measured usage.

| Period | Articles | Text | Images | Combined |
| --- | ---: | ---: | ---: | ---: |
| 30 days | 600 | 18 MB | 120 MB | 138 MB |
| 365 days | 7,300 | 219 MB | 1.46 GB | 1.679 GB |

These figures exclude indexes, revisions, inline images, customer/product/order tables, backups, restore history and replicas. They assume every article has one image. R2 bytes and database bytes must be budgeted separately. With R2 configured, image URLs—not image bytes—normally live in PostgreSQL. The existing upload fallback can store image bytes in PostgreSQL when object-storage credentials are absent, so verify uploads actually reach R2.

20 writes/day is a small publishing rate; it is **not evidence of safe reader capacity**. For example, 100,000 uncached article reads/day means approximately 1.16 average requests/sec, with potentially much larger Facebook bursts. One 200 KB image fetched per view is approximately 20 GB of transfer/day, before browser/CDN cache effects. Multiple widgets can issue several API requests per page. Database search, counts, view writes, cold starts and simultaneous connections may dominate.

### Measured production snapshot

Deployment build read-only snapshot (2026-11-06 19:36 UTC):

- PostgreSQL: **53,207,040 bytes** (53.2 MB).
- News: **28 total**, 26 live published, 15 created in the preceding 24 hours; no blog articles yet.
- Catalog: 789 products, 788 active.
- Database-backed images: 715 records, **29,874,490 payload bytes**. Do not delete them without a verified migration and URL compatibility plan.
- All five R2 connection settings are present; actual object count/storage/transfer remain unmeasured.
- Correct Vercel team is `fabrything`, plan Hobby. Paid Observability Plus is required for the attempted invocation metrics query; billing cost data was unavailable. Neither response means zero usage. No paid upgrade was made.
- Neon plan/headroom, R2 usage, request concurrency and production latency have not been verified.

## Management and measurement

The operations API reports actual application counts and PostgreSQL database size when supported. Provider costs, quotas, requests and R2 storage are explicitly unavailable until the correct accounts are connected. The approved SEO/operations UI is implemented at `/admin/manage/nobleseek?tab=operations`, using live APIs and preserving unavailable telemetry labels.

Before publishing a numerical concurrent-reader claim:

- Obtain read-only access to the correct Vercel, Neon and Cloudflare projects; record plan limits and current use.
- Measure article/page sizes, R2 object bytes/count, query durations, connection use, function CPU/duration/errors and cache hit rate.
- Test a staging copy with a realistic catalog/news volume. Ramp readers through expected Facebook bursts, measuring p50/p95/p99 latency, errors and DB connections; do not stress production during checkout traffic.
- Set operational alerts against measured quotas, errors and latency. Keep n8n retry/backoff and a persistent external job queue; handle API pause/cap responses without retry storms. A daily cap is a publishing control, not a distributed request rate limiter.
- Use the Neon pooled connection endpoint for bursty serverless traffic; review connection lifetime and concurrency. Shared Redis is needed for cross-instance counters/deduplication. Existing in-process cache cannot enforce distributed limits.
- Keep images on R2/CDN and resize/compress them; keep article archives accessible unless retention is explicitly chosen. No automatic deletion has been added.

Cloud-provider scaling, billing and quota changes require server-side provider integrations with scoped credentials, audited writes and failure handling. They are not implemented by the application counts/settings endpoint. Never put provider tokens in React settings or a browser bundle.

## Search and editorial guidance

Unique useful product guides, visible sources, responsible authorship, accurate dates, descriptive titles, internal product links, image descriptions and canonical URLs support both ordinary and AI search discovery. Schema must match visible content; it does not guarantee rankings or inclusion. SEO title/description audit flags are editorial suggestions: headline/excerpt fallbacks can be valid, and Google has no mandatory universal title/description character limit. Word count alone does not establish AdSense readiness.

The current app is client-rendered React. Metadata and article text rendered only after JavaScript remain a discovery limitation for crawlers that do not execute JavaScript. Server-rendering or prerendering the **same visible editorial pages**, real HTTP 404s for missing articles and a paginated sitemap strategy should be addressed before claiming comprehensive AI/search crawler support. The current monolithic sitemap should be split before reaching the standard 50,000-URL limit. No ranking, indexing, AI citation or AdSense approval is promised.

Review generated stories for factual accuracy, source rights and added value before publishing. Automation itself is not the issue; large amounts of unoriginal material primarily created to manipulate rankings can violate Google's scaled-content policy.

Sources checked for this work:

- https://developers.google.com/search/docs/fundamentals/ai-optimization-guide
- https://developers.google.com/search/docs/essentials/spam-policies
- https://support.google.com/adsense/answer/9262311
- https://vercel.com/docs/domains/working-with-domains/add-a-domain
- https://neon.com/docs/connect/connection-pooling
- https://developers.cloudflare.com/r2/pricing/

Open decisions: image count/size, retention, monthly budget, correct Neon/R2 account access, and whether existing automation should opt into review.

## Visual approval and verification

Approved draft: https://p.superdesign.dev/draft/d35dadb6-a92b-4807-9c07-85c7a0b7999a . Implementation uses real API values and explicit unavailable provider telemetry.

All **1,148 backend tests** passed with test settings. Migration consistency and Django checks passed. Focused frontend verification: 13 advertising tests, 22 storefront/blog/navigation tests, and 8 admin tests passed. Existing React testing/CRA dependency warnings remain. Production deployment and route smoke results are recorded below when completed.

## Manual account and editorial tasks

1. Publish original product guides through the News/Blog editor; `/blog` deliberately starts empty.
2. In AdSense, turn Auto ads off and use manual editorial slots/page exclusions for blog/news only; confirm publisher registration and ads.txt. The app cannot change account settings without account access.
3. Verify the news subdomain in Search Console and submit `https://nobleseek.fabrything.com/sitemap.xml`; retain the www sitemap for store/blog.
4. Update n8n website links to the news subdomain. Send `automation: true` when opting into the review gate. Facebook jobs remain separately controlled in n8n.
5. Refresh automatically imported product prices using normal source sync. Do not apply a fresh profit margin to existing selling prices.
6. Supply the intended retention/budget and correct Neon/R2 access for measured quota alerts/scaling work. There is no safe concurrent-reader promise without staging load tests.

Client-rendered article HTML remains a search limitation; SSR/prerendering is a separate architectural change. No ranking or AdSense approval is guaranteed.

## Production route verification

API deployment `dpl_HsTAX1r3TLMBdq3zLXfuE63yVbN3` and final frontend `dpl_5rCqSSshEXayhZAf96H9VvPxBc6v` are production releases. Browser checks confirmed news root redirect, old www article redirect preserving query strings, mobile article rendering/canonical/NewsArticle schema, and shop without AdSense scripts or slots. Blog renders its empty state. News robots.txt returns the subdomain sitemap; XML sitemap has 32 news/policy URLs on the correct host. Same-origin news API returns 26 live stories; unauthenticated operations returns401. Browser news article logged no errors and mobile pages had no horizontal overflow. Plain Python requests to www were blocked403, while normal browser requests succeeded; use browser results for that host.

The robots static-file precedence and blog layout metadata ownership issues found during smoke checks were corrected. The final11-test storefront/blog rerun passed, including two new metadata ownership regressions. Remote production builds passed with existing CRA/Browserslist warnings.

Changes were deployed directly from this shared workspace and remain uncommitted; GitHub has not been synchronized by this iteration.
