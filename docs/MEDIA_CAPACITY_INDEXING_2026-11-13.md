# Media, capacity, order alerts and indexing — November 13

## Delivery status

The owner approved the [Media & capacity design](https://p.superdesign.dev/draft/f0bb5897-c88b-4ef1-a5d1-ba60f201aa8c), then authorized Git pushes and CI/CD deployment. Release checks are in progress. Existing live services and the EchoLink worker have not been restarted or interrupted. Only isolated task-owned preview processes were used.

Automatic image processing and WhatsApp sends require a separately running store worker. No production worker has been activated in this change. The owner chose the store's existing WhatsApp number ending9899; the destination migration fills an empty admin number without overwriting an existing manual choice.

## Delivered behavior

- Shop Control Center → Media & capacity: before/after photos, automatic-import queue switch, existing-product selection, cleanup history, retry and safe restore.
- New product saves and shared import batches create durable image jobs inside the database transaction. No download or segmentation runs inside a web request. Failed imports roll back their jobs.
- CPU-only `u2netp`, reused model session and one ONNX thread; one image lease across worker processes. Inputs are bounded to5MiB and20megapixels, redirects/private networks are rejected, and uncertain masks are held for review. Output is a1200px white-canvas WebP. Original bytes are retained in the configured durable storage before applying the cutout. An editor's changed photo is never overwritten. Product marks/details are preserved; background removal is not a guaranteed watermark eraser.
- Independent order-alert lane, durable outbox per order, bounded rate-limit retry and no automatic retry of an ambiguous send. Checkout makes no WhatsApp HTTP call. Signed delivery callbacks distinguish provider acceptance from delivered/read and preserve callbacks arriving before the send response. Old unsent alerts expire after24hours.
- Measured PostgreSQL size and database-image payload; current image destination, catalog reference locations, tracked writes and bounded hourly bucket inventory. Measurement times, partial inventory and unknown limits are explicit. Operator budgets warn at75%/90%; cleanup writes hold at95%. Growth projections require at least a day of measured history. Retention is35days.
- R2's free allowance is not a hard storage ceiling. A second database connection does not automatically add capacity or balance data. Move database images to object storage, upgrade the primary plan or design a reviewed data partition before exhaustion.

## Search indexing audit and fixes

The supplied report inspected `https://fabrything.com/`, which correctly returns308 to `https://www.fabrything.com/`. Google excludes an intentional redirect and indexes the canonical destination instead. Do not remove that redirect or try to make both hosts index separately. [Google canonical guidance](https://developers.google.com/search/docs/crawling-indexing/consolidate-duplicate-urls).

Before this change, sampled live product documents returned an empty app root and generic Fabrything title before JavaScript. Home, shop, deals and product routes now deliver public HTML, product links, useful text, canonical URLs, unique metadata and supported Product/Breadcrumb schema before JavaScript. The same HTML is served to visitors and crawlers. The current deployed React assets then provide the existing interactive store/cart. The frontend document function preserves the deployment's analytics, ownership verification, fonts and exact asset hashes. Unknown/inactive products return404; transient origin failures return retryable503 rather than indexable empty success. [Google JavaScript SEO](https://developers.google.com/search/docs/crawling-indexing/javascript/javascript-seo-basics).

Filtered shop views are noindex; real pagination has matching server/client canonicals. The store sitemap lists the store host; NobleSeek's separate sitemap lists its news host. Robots advertises the canonical sitemap. The previously reported44 excluded URLs were not individually provided, so their individual Search Console causes cannot be asserted from the apex report.

After deployment, submit `https://www.fabrything.com/sitemap.xml` in the verified Search Console property and inspect/request indexing for the canonical www homepage and representative product URLs. Search Console processing, actual indexing and ranking remain Google's decisions; code cannot promise immediate inclusion.

## Activation and private configuration

The authorized CLI account now has access to the Fabrything team. Production env export succeeded to an owner-private directory outside both repositories. Vercel wrote22 protected values as `[SENSITIVE]` placeholders. Those are not usable database/storage credentials and do not prove production is unhealthy. No WhatsApp token, phone ID or callback secrets were present. No secret values were printed, committed or changed. [Vercel Secret variables are write-only](https://vercel.com/docs/environment-variables/sensitive-environment-variables).

Once original private settings are available on the chosen worker host, use the separate CPU-worker requirements and `backend/scripts/store_worker.py --env-file <private-file>`. The launcher rejects protected placeholders. It starts only the store worker; it has no restart/kill logic for other services. `run_store_operations --alerts-only` can run without image processing. The API deployment alone does not drain these queues.

WhatsApp additionally needs an approved `store_new_order_admin` template with five ordered body parameters: order number, contact name, contact phone, item count and total/currency. The default language is `en`, editable in admin. Credentials stay server-side: `WHATSAPP_ACCESS_TOKEN`, `WHATSAPP_PHONE_NUMBER_ID`, optional `WHATSAPP_API_VERSION` (defaultv27.0), and `WHATSAPP_APP_SECRET`/`WHATSAPP_VERIFY_TOKEN` for `/api/store/webhooks/whatsapp/`. Subscribe the official Meta messages webhook. Credential presence does not verify template approval or delivery. No live test message or order was sent.

Capacity limits remain unknown until confirmed against the actual provider plan or entered as an explicit operator budget. No provider quota API credentials were exported. No paid provisioning, automatic failover, database migration between providers, deletion of originals or mass cleanup of old catalog images occurs automatically.

## Verification and design

Backend suite, focused React tests, Node document tests, migration checks, isolated build and responsive browser checks are recorded at release below. Real-image CPU QA produced a16,792-byte WebP from a26,526-byte product photo, at1200×1200. First initialization/download took220seconds; the next fresh-process initialization took4.77seconds, and a reused session processed the image in0.91seconds. These are measurements of one image on this PC, not throughput guarantees.

The SuperDesign target was converted with hosted12ui and the implemented URL was aligned against that unchanged LayerDoc. The kit reported20.3% anchor overlap because the protected shell and real empty/unconfigured states differ from the illustrative design. Applied its panel-border and heading hierarchy refinements. Preserved the real logo, existing Roboto family, functional MUI icons, real photos and supported metrics. Rejected proposed substitutions of unknown capacity with sample gigabytes, sample sends/test pings, and a misidentified logo crop inside the source photo. Desktop1440 and mobile768/390/320 have no viewport overflow or JavaScript page errors; a local-only cart remains interactive.

## File map

- `backend/storeops/`: policy, image/outbox/asset/snapshot/heartbeat/lease/receipt models; migrations0001–0004; signal/import integration; CPU processor; capacity and WhatsApp services; staff APIs and signed callbacks; worker command; Django admin; tests.
- `backend/scripts/store_worker.py`, `backend/requirements-worker.txt`: optional persistent CPU worker, private env validation.
- `backend/catalog/admin.py`, `models.py`, `services_import.py`: selection action, atomic product/job creation and automatic import queue.
- `backend/config/settings/base.py`: app registration.
- `backend/core/storage.py`, `whatsapp.py`, `test_whatsapp.py`: asset ledger, resilient legacy logging and current API default.
- `backend/orders/services.py`, `backend/storefront/test_whatsapp_alerts.py`: transactional order outbox and checkout integration tests.
- `backend/storefront/store_documents.py`, `templates/storefront/store_document.html`, `test_store_documents.py`, `seo.py`, `urls.py`, `backend/nobleseek/test_publishing.py`: public HTML, same-host sitemap and regression checks.
- `frontend/src/admin/pages/MediaOperations.jsx`, `.css`, `.test.jsx`, `ModuleControlCenter.jsx`; `frontend/src/pages/products/ManageProducts.js`: approved operations tab and catalog entry point.
- `frontend/api/store-document.js`, `frontend/server/store-document.cjs`, `frontend/scripts/store-document.test.cjs`, `frontend/vercel.json`: deployed HTML composition and tested failure/asset behavior.
- `frontend/src/index.js`, `frontend/src/utils/config.js`, `frontend/src/storefront/layout/StorefrontLayout.js` and `.social.test.js`: progressive enhancement, production API fallback and consistent metadata.
- `backend/.env.example`, `README.md`, this handoff and `docs/project-memory/`: public variable names, client-facing capabilities and recovery memory. README contains no setup steps.

## Release evidence

Local verification:1,220 backend tests;33 final image/outbox/document regression tests;38 focused React tests;4 Node document-composition/failure tests; new Python modules pass Ruff. Migration drift and Django system checks are clean. Isolated production build passed with the existing CRA/Browserslist warnings. Full frontend lint has165 baseline errors/234 warnings, zero new errors (the prior baseline was166 errors). Browser source/canonical/cart and responsive admin checks passed at1440/768/390/320 with zero JavaScript page errors and no real orders, notifications or website writes.

Source90370b6 deployed successfully for both projects; storeops migrations0001–0004 applied through the existing backend build. Live verification caught a frontend packaging/root-routing regression, corrected in2fcf19d. Both correction deployments are READY: frontend `dpl_Ek1oA1RhugCvUvkoDQAivKVVauZo`, backend `dpl_3nqTjDTQvTPrrCC8Phosk1AXFJ1d`. The build now packages its public HTML as a traced module rather than depending on the function's working directory, and moves the static fallback to `app-shell.html` so filesystem index precedence cannot bypass the homepage rewrite. Five Node regression tests pass, including an unrelated runtime working directory.

Observed live after correction: home/shop/page2/deals/product200 with full HTML, matching canonical and current React scripts; blog200; robots/sitemap200 with899 sitemap URLs; unauthenticated operations401; apex308 towww. Production build metadata reports PostgreSQL56,303,616bytes, database image payload29,874,490bytes across715 images, and886 catalog products/885 active. Provider limits remain unverified. Protected Vercel environment exports contain22 placeholders and cannot activate the separate worker.

November14 approved homepage banner and customer export extension: see [follow-up handoff](HOMEPAGE_CUSTOMER_EXPORT_2026-11-14.md).

<details><summary>Exact release file manifest (54 files)</summary>

```text
README.md
backend/.env.example
backend/catalog/admin.py
backend/catalog/models.py
backend/catalog/services_import.py
backend/config/settings/base.py
backend/core/storage.py
backend/core/test_whatsapp.py
backend/core/whatsapp.py
backend/nobleseek/test_publishing.py
backend/orders/services.py
backend/requirements-worker.txt
backend/scripts/store_worker.py
backend/storefront/seo.py
backend/storefront/store_documents.py
backend/storefront/templates/storefront/store_document.html
backend/storefront/test_store_documents.py
backend/storefront/test_whatsapp_alerts.py
backend/storefront/urls.py
backend/storeops/__init__.py
backend/storeops/admin.py
backend/storeops/alerts.py
backend/storeops/apps.py
backend/storeops/capacity.py
backend/storeops/images.py
backend/storeops/management/__init__.py
backend/storeops/management/commands/__init__.py
backend/storeops/management/commands/run_store_operations.py
backend/storeops/migrations/0001_initial.py
backend/storeops/migrations/0002_admin_alert_destination.py
backend/storeops/migrations/0003_imageworkerlease.py
backend/storeops/migrations/0004_whatsappdeliveryreceipt.py
backend/storeops/migrations/__init__.py
backend/storeops/models.py
backend/storeops/signals.py
backend/storeops/tests.py
backend/storeops/urls.py
backend/storeops/views.py
docs/MEDIA_CAPACITY_INDEXING_2026-11-13.md
docs/project-memory/CURRENT.md
docs/project-memory/graph.json
frontend/api/store-document.js
frontend/scripts/store-document.test.cjs
frontend/server/store-document.cjs
frontend/src/admin/pages/MediaOperations.css
frontend/src/admin/pages/MediaOperations.jsx
frontend/src/admin/pages/MediaOperations.test.jsx
frontend/src/admin/pages/ModuleControlCenter.jsx
frontend/src/index.js
frontend/src/pages/products/ManageProducts.js
frontend/src/storefront/layout/StorefrontLayout.js
frontend/src/storefront/layout/StorefrontLayout.social.test.js
frontend/src/utils/config.js
frontend/vercel.json
```

</details>
