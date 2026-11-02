# Fabrything release checkpoint — 2026-11-03

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
