# Catalog flash on homepage startup

The owner's screenshot shows the crawlable server catalog, not missing CSS. The document function sends a simplified product layout and then starts the approved React storefront. Source4825347 prevented a bare-text frame, but deliberately retained that catalog while React loaded. Its earlier checks measured styling, not whether the alternate layout became visible. This follow-up fixes that distinct first-paint defect.

A small head bootstrap now gates the catalog before body paint. JavaScript-enabled visits show the existing brand mark and a theme-matched progress indicator until the actual storefront route commits; there is no minimum display duration. The layout then replaces the indicator and catalog in one pre-paint commit. Real product HTML, schema, canonical URLs and no-JS readability remain in the response; the behavior is identical for all user agents.

Critical first-party script/CSS failures or a15-second bootstrap timeout expose the usable catalog with an explanatory reload link. Once this fallback is visible, a late script cannot unexpectedly replace it. Provider and product-image failures do not switch the site into fallback. Saved dark mode, blocked browser storage and reduced-motion preferences are handled. Existing services, credentials, analytics configuration, backend data and publishing workflows remain untouched.

Verification:12 Node checks, three React checks, targeted ESLint and an isolated production build pass (existing CRA/lint warnings remain). Real-browser first-paint checks deliberately hold the main script, verify the catalog is hidden before release, then check desktop refresh, mobile light/dark modes, no-JS, failed route downloads and delayed-script timeout recovery. All six scenarios pass. Successful loads record zero alternate-catalog and blank frames; failure modes retain stable product links. Screenshots and frame counts are retained privately. The known Google account-side nested alias404/ORB remains outside this change. Test tracking transports were intercepted; no order, notification, article or conversion was written.

Files: `frontend/server/store-document.cjs`; `frontend/scripts/store-document.test.cjs`; `frontend/src/utils/storeDocument.js`; `frontend/src/utils/storeDocument.test.js`; this report and `docs/project-memory/`. The supplied screenshot and the owner's existing untracked files are preserved outside the commit. No migration or environment change is needed.

Release: local verification complete; authorized Git/Vercel deployment pending live first-paint verification.
