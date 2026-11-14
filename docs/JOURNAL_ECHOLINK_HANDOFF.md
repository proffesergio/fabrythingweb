# Fabrything journal — approved release handoff

## November14: automatic website-only profile

The owner authorized the separate EchoLink `Fabrything Blog` profile, English first, focused on existing Gadgets/personal-audio compatibility. Its initial ceiling is two source-backed guides/day, at least12 hours apart. Five real topic levels are configured; no synthetic articles were seeded. Existing public catalog images supply article imagery; separate image/WhatsApp worker credentials remain pending.

The backend now supports a signed, tenant-bound GET receipt lookup by sourceKey. It returns saved status, canonical URL and exact payload hash without article content or writes. EchoLink uses this to reconcile an interrupted publication response before considering any further action. Twelve journal tests pass, including authentication, cross-tenant rejection and a read-only receipt check.

The supplied root `.env.local` database URL was validated with verified TLS and used only for this store's real topic configuration. Existing production migrations were already applied. Four dedicated journal bridge settings were securely configured on the production backend; existing database/storage/app secrets were preserved. Source8d0625b frontend/backend deployments and signed live health succeeded; EchoLink enabled the new profile. The first real guide is under preparation, with a schema/checkpoint correction applied in EchoLink; no completed publication has yet been confirmed. No Meta credentials are needed for website publication. Affiliate and advertising accounts remain unapproved; the shop stays ad-free and no affiliate URLs are fabricated.

Designs approved November13. The article/topic UI, reusable blocks, signed publishing bridge and SEO routes are implemented and locally verified. Source31a5af9 is pushed to main; frontend and backend Vercel deployments succeeded. Live /blog and topic API return200; no existing live process was restarted or killed. No synthetic production publication or manual live migration was submitted.

Full cross-repository scope, verification limits and exact manifests: EchoLink `docs/LOCAL_COMMERCE_JOURNAL_REVIEW.md`.

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

## Owner configuration and activation checklist

1. Approved UI and320/390/768/1440px browser QA are complete. Frontend67jVYtawZKyBywAAuKagePx9718a and backendAVjh6xyjiz6pAfspjSFBpYvCnaxi succeeded from source31a5af9. The live public topic query succeeds, confirming the deployed journal schema is available.
2. Review migration `backend/storefront/migrations/0005_topiccluster_journalarticle.py`
   and apply it to the intended database only during the owner's release process.
   Tests used isolated in-memory SQLite. The existing production Vercel release hook runs migrations during deployment; none were manually applied by this task.
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


## Final verification — November13

1,187 backend tests pass; Django migration drift/system checks pass.18 journal/legal frontend tests pass. Isolated build compiles with baseline warnings. Full ESLint166 existing errors/234 warnings, zero new errors. Browser checks pass at320/390/768/1440 with no overflow or JS errors and no real API writes. Both direct canonical and React structured contracts retain disclosures and sponsored links. Empty/future/review-only topics are excluded from navigation and sitemap.

Only the existing confirmed price-policy test expectations changed; production pricing was preserved. The timestamp fixture now uses explicit separate times. Policy/affiliate/AdSense/account configuration still needs owner review.

<!-- FILE_MANIFEST -->
## Exact release files relative to fetched main

### EchoLink

- `README.md`
- `docs/AGENT_HANDOFF.md`
- `docs/LOCAL_COMMERCE_JOURNAL_REVIEW.md`
- `docs/PROJECT_MEMORY.json`
- `platform/client/app.jsx`
- `platform/client/assets/commerce/palette.png`
- `platform/client/assets/commerce/shield.png`
- `platform/client/commerce-settings.css`
- `platform/client/commerce-settings.jsx`
- `platform/client/font-settings.jsx`
- `platform/client/journal-settings.jsx`
- `platform/client/settings-dialog.jsx`
- `platform/client/tests/motion-profile.browser.mjs`
- `platform/scripts/journal-image.mjs`
- `platform/server/api.mjs`
- `platform/server/commerce-design.mjs`
- `platform/server/commerce-settings.mjs`
- `platform/server/fonts.mjs`
- `platform/server/index.mjs`
- `platform/server/jobs.mjs`
- `platform/server/journal-images.mjs`
- `platform/server/journal.mjs`
- `platform/server/product-design.mjs`
- `platform/server/providers.mjs`
- `platform/server/read-model.mjs`
- `platform/server/validation.mjs`
- `platform/shared/commerce-design.mjs`
- `platform/sql/020-journal-connector.sql`
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

- `docs/project-memory/CURRENT.md`
- `.gitignore`
- `README.md`
- `backend/.env.example`
- `backend/catalog/test_admin_product_import.py`
- `backend/catalog/test_apply_pricing_markup.py`
- `backend/catalog/test_price_sync.py`
- `backend/catalog/test_seed_store_catalog.py`
- `backend/chat/tests/test_customer_api.py`
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
- `backend/storefront/templates/storefront/journal_blocks.html`
- `backend/storefront/templates/storefront/journal_cards.html`
- `backend/storefront/templates/storefront/journal_document.html`
- `backend/storefront/templates/storefront/journal_product_details.html`
- `backend/storefront/test_journal.py`
- `backend/storefront/urls.py`
- `docs/JOURNAL_ECHOLINK_HANDOFF.md`
- `frontend/package.json`
- `frontend/public/index.html`
- `frontend/public/journal.css`
- `frontend/public/journal/chevron.png`
- `frontend/scripts/verify-build.cjs`
- `frontend/src/App.js`
- `frontend/src/storefront/components/JournalBlocks.js`
- `frontend/src/storefront/layout/StorefrontLayout.js`
- `frontend/src/storefront/pages/BlogPages.js`
- `frontend/src/storefront/pages/BlogPages.test.js`
- `frontend/src/storefront/pages/legal/LegalPage.js`
- `frontend/src/storefront/pages/legal/content.js`
- `frontend/src/storefront/useSeo.js`
- `frontend/vercel.json`
