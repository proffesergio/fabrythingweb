# Fabrything journal — local review handoff

This is a local, unactivated change set. No push, deployment, running-service
restart or production migration was performed. The final commerce/journal UI
implementation is awaiting visual approval in the EchoLink task. Do not push this
as a completed frontend release while the topic route and structured renderer remain pending.

## Prepared backend and technical SEO

Existing NobleSeek BLOG records/URLs remain compatible. `TopicCluster` represents
industry → category → subcategory → micro-niche → buyer intent with validated
parents. `JournalArticle` adds structured blocks, product references, sources,
editorial receipt and durable source/payload identity to the existing Article.
Configure one focused topic ecosystem before broadening coverage; no synthetic
articles, products or affiliate accounts were seeded.

The public API supports topic/intent filtering and published related guides.
Draft/future/review content stays private. Blog JSON-LD uses Article, visible
Product/Review/FAQPage and BreadcrumbList data without invented ratings/offers.
Legacy BlogPosting remains supported, with Fabrything publisher identity. A
manual HTML correction disables the older structured projection instead of
silently overriding the editor's correction. Source material is attribution,
not evidence of first-hand product testing.

Canonical article HTML, disclosure, sources, related links and metadata are
available through `GET /api/store/journal/document/<slug>/`. The prepared Vercel
rewrite serves it at `/blog/<slug>` for readers and crawlers alike. Dynamic
robots/sitemap routes include live articles and trust pages. About/privacy/terms
use their existing templates; Contact and Affiliate & Advertising Disclosure
reuse the same legal-page template. Policy wording still needs owner/legal review.

## Signed delivery contract

- POST `/api/store/journal/publish/` accepts `fabrything-journal-v1` structured JSON.
- Headers: `X-EchoLink-Timestamp` is Unix seconds; `X-EchoLink-Signature` is hex
  HMAC-SHA256 over `timestamp + '.' + exact raw JSON bytes`.
- Validity window5 minutes. Body at most200000 bytes. Workspace/Page must match
  the configured allowlist, including the `sourceKey` prefix.
- `sourceKey = workspaceUUID:pageUUID:postUUID`. Identical retries return the
  existing article; different content under that key returns409 without overwrite.
- GET on the same route signs the empty body and checks connectivity without creating content.
- Required metadata: title/slug/excerpt/SEO title+description, problem/audience/
  keyword/intent/clusterSlug, attributable sources, typed blocks and supplied
  products. Product platforms: fabrything/amazon/alibaba/other. No prices are required.
- Images need alt text and dimensions; public variants support responsive embeds.
  A placeholder is an image plan, not a claim that a licensed image was generated.
- Default receipt status is REVIEW. `PUBLISHED` requires explicit journal opt-in,
  a signed reviewed payload and ordinary shared ingestion/capacity gates. Journal
  opt-in does not disable NobleSeek's separate automated-news review setting.

## Owner activation checklist — not performed

1. Approve and complete the hosted design implementation and remaining browser QA.
2. Review migration `backend/storefront/migrations/0005_topiccluster_journalarticle.py`
   and apply it to the intended database only during the owner's release process.
   Tests used isolated in-memory SQLite; no production migration was applied.
3. Configure an active valid topic chain in Django admin. Set matching Page plan
   and per-article verified source/card/image briefs in EchoLink.
4. Set backend `ECHOLINK_BLOG_SECRET` (random, at least32 characters),
   `ECHOLINK_BLOG_WORKSPACE_ID`, `ECHOLINK_BLOG_PAGE_ID`. Leave
   `ECHOLINK_BLOG_AUTO_PUBLISH=false` until reviewed automatic publication is intended.
   Put the same secret in EchoLink's encrypted `fabrything_blog` API-key field;
   connection and website origins must match. Do not commit actual values.
5. Review real business contact details, affiliate programme approvals/destination
   URLs and current legal/privacy/advertising wording. No Amazon/Alibaba account
   enrollment or affiliate ID is supplied. Attach only licensed images, upload
   real WebP variants to controlled storage and use their public URLs.
6. Configure Search Console ownership (DNS TXT or verified method), submit the
   production sitemap, inspect rendered pages/canonical routes and check Core Web
   Vitals on real hosting. No DNS or Search Console account was changed.
7. Supply the owner's AdSense publisher/slot IDs, domain verification and ads.txt
   entries; configure a certified consent mechanism where required before loading
   advertising. Existing ads remain governed by existing configuration. No ad
   account was enabled, verification token invented or approval promised.
8. Finish local review, commit/push through the owner's CI/CD and plan worker/backend
   activation separately. This task did not restart any live process.

## Checks and limitations

Full backend209 tests passed before the final additional projection case; final
bridge suite8 checks passes. Django check/migration drift check passed. Existing
journal/legal frontend16 tests pass. Isolated production build compiles, with
pre-existing CRA/Browserslist/ESLint warnings. Full lint:166 existing errors and
234 warnings; baseline comparison found zero new errors. No TypeScript project.
No real inference, social posting, website publication or paid affiliate/API call
was used as a test. Hosted SuperDesign/12ui design work was explicitly authorized.

<!-- FILE_MANIFEST -->

## Exact changed files

### EchoLink

- `docs/AGENT_HANDOFF.md`
- `docs/LOCAL_COMMERCE_JOURNAL_REVIEW.md`
- `docs/PROJECT_MEMORY.json`
- `platform/client/font-settings.jsx`
- `platform/scripts/journal-image.mjs`
- `platform/server/api.mjs`
- `platform/server/commerce-design.mjs`
- `platform/server/commerce-settings.mjs`
- `platform/server/fonts.mjs`
- `platform/server/jobs.mjs`
- `platform/server/journal-images.mjs`
- `platform/server/journal.mjs`
- `platform/server/product-design.mjs`
- `platform/server/providers.mjs`
- `platform/server/validation.mjs`
- `platform/test/channel-brand.test.mjs`
- `platform/test/commerce-design.test.mjs`
- `platform/test/fixtures/fonts/NotoSansBengali.woff`
- `platform/test/fixtures/fonts/NotoSansBengali.woff2`
- `platform/test/fixtures/fonts/OFL.txt`
- `platform/test/fonts.test.mjs`
- `platform/test/journal-images.test.mjs`
- `platform/test/journal.test.mjs`
- `platform/test/product-design.test.mjs`

### Fabrything

- `.gitignore`
- `backend/.env.example`
- `backend/nobleseek/models.py`
- `backend/nobleseek/sanitization.py`
- `backend/nobleseek/serializers.py`
- `backend/nobleseek/views.py`
- `backend/storefront/admin.py`
- `backend/storefront/journal.py`
- `backend/storefront/journal_bridge.py`
- `backend/storefront/journal_contract.py`
- `backend/storefront/journal_models.py`
- `backend/storefront/journal_views.py`
- `backend/storefront/migrations/0005_topiccluster_journalarticle.py`
- `backend/storefront/models.py`
- `backend/storefront/seo.py`
- `backend/storefront/test_journal.py`
- `backend/storefront/urls.py`
- `docs/JOURNAL_ECHOLINK_HANDOFF.md`
- `frontend/package.json`
- `frontend/scripts/verify-build.cjs`
- `frontend/src/App.js`
- `frontend/src/storefront/layout/StorefrontLayout.js`
- `frontend/src/storefront/pages/legal/LegalPage.js`
- `frontend/src/storefront/pages/legal/content.js`
- `frontend/src/storefront/useSeo.js`
- `frontend/vercel.json`
