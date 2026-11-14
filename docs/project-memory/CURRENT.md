# Live activation follow-up — 2026-11-14

- Latest storefront/API source16360a5 is deployed; homepage, sitemap and protected export endpoint were rechecked.
- Owner authorized applying all changes live. EchoLink sibling now has SQL017–021 and the gracefully updated worker/bridge; public capability health is verified. Its Fabrything catalog refresh succeeded and a three-product preparation batch queued; the first completed real caption/design passed editorial checks and automatically scheduled for06:36Z (12:36 Dhaka). Other preparations remain subject to RAM admission.
- Dedicated store image/WhatsApp worker is still pending usable original settings. Owner will place these in repository-root `.env.local`; do not confuse backend/.env.local (CLI token only) or the protected-placeholder export with a usable worker environment. Never print or commit credentials.

# Homepage and customer export extension — 2026-11-14

- Owner approved the hosted product spotlight; implemented catalog-driven responsive banner, pause/reduced motion and real-photo fallbacks without replacing managed banners. CSV/JSON exports include all search matches and use staff-only authorization, safe fields and CSV formula protection.
- Extension sourcebf06014 is live: frontend6fo6qmtDysmsK7DFCyNuCTq1sFFS and backendHZKFvwu6Q5iVuFeQ2RqUX4ZSKn41 succeeded. Live1440/390 banner/photo QA passes with zero JS errors and no viewport overflow; anonymous export401. Full frontend lint163 existing errors/234 warnings, zero new errors. Task-owned preview processes were closed; existing services were untouched.
- Core media/indexing source90370b6 and routing correction2fcf19d both deployed through Git integration. Live home/shop/deals/product and pagination return200 with canonical/full HTML/React scripts; sitemap899 URLs, operations401 anonymous, apex308 intentional. Storeops migrations0001–0004 applied. New worker still pending original private credentials/Meta setup; existing workers untouched.
- Current extension checks:1,224 backend, five React and five Node tests, isolated build, four-width browser QA. Scope/design/file details: [homepage and export handoff](../HOMEPAGE_CUSTOMER_EXPORT_2026-11-14.md).
- Final customer download encoding restores one UTF-8 BOM even if the browser consumed it; both customer UI tests pass with a raw-byte download assertion. No production customer data was exported during QA.

# Media, capacity, alerts and crawlable commerce — 2026-11-13

- Owner approved the hosted Media & capacity design and Git/CI release. New Shop tab, catalog selection action, transactional CPU image queue with originals/CAS restore, measured storage and durable signed-callback order alerts are implemented.
- Home/shop/deals/product documents now contain crawlable HTML and preserve the existing deployed React shell/analytics/verification. Apex-to-www redirect remains intentional; main/news sitemaps use their own canonical hosts.
- No existing live service or EchoLink worker was restarted. Background processing/sending remains pending a dedicated worker and usable private settings.
- Authorized Vercel export succeeded outside the repositories, but22 protected values are placeholders, not usable worker credentials. WhatsApp API/callback settings are absent. Never treat placeholder probe failures as production outages.
- Scope, original design/conversion alignment, checks, migration0001–0004, activation limits and file map: [media and indexing handoff](../MEDIA_CAPACITY_INDEXING_2026-11-13.md). CI deployment evidence will be recorded there after verification.

---

# Journal and EchoLink release — 2026-11-13

- Approved journal buyer-guide/topic interfaces and signed EchoLink bridge are implemented and pushed in31a5af9. Frontend67jVYtawZKyBywAAuKagePx9718a and backendAVjh6xyjiz6pAfspjSFBpYvCnaxi deployed successfully through the existing Vercel Git integration.
- Full canonical articles/archives render server-side with real Fabrything branding, typed blocks, disclosures, sources and metadata. Live /blog, /journal.css and topic API return200. Empty/review/future topics stay out of navigation and sitemap.
- 1,187 backend tests;18 journal/legal React tests; migration/system checks and isolated build pass. Full frontend lint retains166 baseline errors/234 warnings, zero new errors. Responsive browser QA320/390/768/1440 passes without real website writes or model calls.
- Signing secret/tenant allowlist, topic plan, real evidence/licensed images, affiliate/account verification and AdSense/consent configuration remain owner work. External EchoLink worker SQL017–020 and graceful activation are separate; no existing live process was interrupted.
- Complete scope, migration/delivery contract and exact manifests: [journal handoff](../JOURNAL_ECHOLINK_HANDOFF.md). Historical checkpoints below remain history.

---

# Newspaper UI completion — 2026-11-07

- Approved NobleSeek newspaper design is implemented; recovered alignment kits
  and design direction were preserved. See [completion report](../NEWSPAPER_UI_2026-11-07.md).
- Closed homepage failure/retry, search focus/query, accessible ticker and
  shopping install prompt leakage on news routes. Focused tests pass.
- Local browser with real API responses confirms desktop/mobile layout,
  search, no horizontal overflow and no interaction page exceptions.
- Final optimized production build passed. No deployment or push in this completion
  session; previous production release below is unchanged.

# Publishing/domain release checkpoint — 2026-11-07

- User approved Superdesign draft and completed Cloudflare DNS. Vercel verified `nobleseek.fabrything.com`; HTTPS renews automatically.
- API production `dpl_HsTAX1r3TLMBdq3zLXfuE63yVbN3` ready; migration 0004 and news canonical update succeeded.
- Blog/editor, NEWS/BLOG split, publishing policies, SEO audit and measured operations panel implemented. Blog has no articles yet.
- Decimal attractive BDT prices apply after markup on import/sync. Existing prices not bulk repriced; never stack markup onto selling prices.
- Production snapshot: PostgreSQL 53,207,040 bytes; news28, live26; database image payload29,874,490 bytes. Correct Vercel team fabrything/Hobby. R2/Neon quotas and reader limits remain unverified.
- Backend1,148 tests passed; focused frontend tests passed. Final frontend deployment/route evidence: see [publishing checkpoint](../PUBLISHING_CAPACITY_2026-11-07.md).
- Manual: AdSense account setup/manual slots with Auto ads OFF; Search Console verification/sitemap submission; n8n link updates and optional automation:true review gate; editorial blog content.
- Client-rendered HTML remains a crawler limitation. Admin reports usage/estimates; it does not provision paid scaling or expose provider credentials.
- Source remains uncommitted in the shared workspace; production was deployed directly through the authorized Vercel CLI. Historical release notes follow.

---

# Fabrything release checkpoint — 2026-11-03

## Local admin/performance/SEO work — pending release

- User chose one Control Center per module and preservation of every current
  feature. Operations, granted management tools, Shop automation and legacy
  business reports are consolidated in the existing dark/cyan style.
- Frontend route shells are lazy-loaded; first build main gzip is 37% smaller.
  Route metadata, crawlable product links and image priority are improved.
- Permission middleware now checks before executing views; Food platform scope
  excludes tenant admins. User-scoped caches and stale-report response handling
  prevent cross-session and date-range confusion.
- Backend 1,112 tests pass; frontend 530 tests covered by passing runs; production
  build passes. See ../ADMIN_PERFORMANCE_SEO_2026-11-03.md for scope and limitations.
- Supplied PageSpeed PDF is malformed and contains no usable audit metrics.
  This work has not changed the production deployments listed below.

The storefront discovery release is deployed and verified. Source and recovery
memory are versioned together on `main`, targeting
`https://github.com/proffesergio/fabrythingweb`.

## Production

- Frontend: https://www.fabrything.com, Vercel `fabrythingweb`, deployment
  `dpl_7xcuNBtuWZVGwyH7L2x4xsAGg5kB` (Ready).
- API: https://fabrythingapi.vercel.app, Vercel `fabrythingapi`, deployment
  `dpl_5Y716VeysyDzkqLLmsXWmYfA33X5` (Ready).
- Apex redirects to www over HTTPS. Cloudflare DNS/proxy configuration was retained.
- Direct and frontend-proxied health report reachable database and no pending
  migrations. Sitemap has 521 canonical www URLs; sampled media GET succeeds.
- Neon PostgreSQL and Cloudflare R2 remain the data/media services. Preserve the
  frontend API trailing-slash rewrites; obsolete Render deployment files are removed.

## Delivered and verified

- Homepage: up to 12 popular products plus 16 distinct discovery products, category
  variety, scroll entrance animation, labeled carousel controls, reduced motion.
- Details: up to eight suggestions prioritized by category, brand and recency;
  excludes current/inactive products and respects prescription-sales configuration.
- Product navigation resets selection/quantity and ignores stale fetch responses.
- Frontend: 68 suites / 509 tests covered by passing runs (new discovery suite
  rerun 2/2 after an asynchronous test assertion fix), optimized build passed.
- Backend: 48 discovery/sync/pricing/import tests passed; final discovery 5/5;
  migration drift check clean.
- Built-frontend fixture Chrome checks passed desktop/mobile/reduced motion.
  Real production browser checks passed with no page exceptions or mobile overflow.
- Full evidence: ../STOREFRONT_DISCOVERY_RELEASE.md and
  ../PRODUCTION_CHECK_2026-11-03.md. Screenshot names beginning `storefront-` use
  fixtures; names beginning `production-` show real catalog products.

## Recovery and operating notes

- Recovered Nov 2 Control Center and supplier/Google sync source are preserved.
  Google providers need credentials/access grants and a separate persistent worker;
  deployment alone does not activate jobs. See ../CONTROL_CENTER_SETUP.md.
- Machine has about 4 GB RAM. Run heavy checks sequentially. Tests work with
  NODE_OPTIONS=--max-old-space-size=1024; local build passed with 1536 MB and
  GENERATE_SOURCEMAP=false. Existing lint/dependency warnings remain.
- Code-review-graph MCP was unavailable; app/service/release relationships are in
  graph.json and mirrored in MCP memory under Fabrything.
- Never commit credentials, environment exports, customer data, or access tokens.

## Active structure cleanup — 2026-11-03

- User requested flattening both applications and removing unused files before
  the next push. Application roots are now backend/ and frontend/; their redundant
  wrappers are gone, including for ignored local configuration and dependencies.
- Both Vercel project rootDirectory settings are updated to backend and frontend.
  Existing production deployments are unchanged until a release completes.
- Removed legacy Render bootstrap/config/export, duplicate OpenCode config,
  unused WSGI/Gunicorn shims, non-idempotent module bootstrap, unused source SVGs,
  retired agent guides/configs/backups and completed implementation checklists.
  User-deleted files stay deleted. Useful future specs are now in docs/design/.
- Setup guides are consolidated under docs/; root and frontend READMEs describe
  the actual stack, migration workflow and current structure.
- Full backend run: 1105/1105 tests pass after fixing a currency-default regression.
  Dynamic-form validation respects model defaults; focused checks also pass.
- Frontend: 68/68 suites and 509/509 tests pass; production build passes with
  existing warnings. Migration drift check is clean. Staged review confirms no
  secrets or generated artifacts are included. Vercel upload previews exclude
  private state. Cleanup is verified and ready for its GitHub push.
