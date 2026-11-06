# NobleSeek newspaper UI completion — 2026-11-07

The approved editorial redesign is implemented in the shared workspace. The
saved Superdesign direction remains draft `361ec0de-05f0-4501-8301-aaa76fcc02da`,
version 2, project `2588e80e-e4e8-4fb0-8db5-afea00e61257`. Its existing 12ui
alignment kits were retained and reviewed; no new design purchases were made.

## Delivered behavior

- Flat Bengali newspaper layout with centered official masthead, serif
  headlines below live API photographs, a 5/3/4 desktop lead/secondary/sidebar
  grid, section rules, responsive story rows and labelled advertising spaces.
- Actual categories, news, latest/popular tabs, poll and Facebook follow link
  remain connected. Empty sections are omitted; missing images use a neutral
  fallback. Draft screenshot imagery and invented stories are not shipped.
- Category/search/archive navigation, load-more pagination, retry and protection
  against late responses remain covered by focused tests.
- Homepage request failures now show a retry control instead of claiming no
  articles have been published.
- Search initializes from its URL query, supports Escape and restores focus on
  close. The breaking ticker has pause/resume and hides duplicate links from
  assistive navigation; reduced motion hides the repeated visual copy.
- The global shopping install banner and iOS instructions are suppressed on
  news routes and the dedicated news hostname, including SPA transitions.
  Storefront installation behavior is preserved.

## Verification

- Seven focused news/advertising/sharing/storefront suites passed: 54 tests.
- After the homepage and header fixes, the final list/header rerun passed:
  2 suites, 13 tests. These overlap the preceding run.
- Install prompt regression suite passed: 8 tests covering news routes,
  hostname, SPA transitions and retained storefront installation behavior.
- Browser used the local frontend and real production API responses. A
  browser-test request bridge was needed because the production API rejects
  cross-origin localhost requests; this did not change application code or
  production CORS settings.
- Browser confirmed live lead headline and image, 1440px desktop and 390px
  mobile without horizontal overflow, search navigation/results heading, and
  no page exceptions during the mobile/search interaction. The install dialog
  was absent on the final news-page recheck.
- Approved image and rendered desktop/mobile images were visually inspected.
  Screenshots: `.playwright-mcp/newspaper-final-desktop.png` and
  `.playwright-mcp/newspaper-final-mobile.png`. These local artifacts are ignored.
- Final optimized production build passed with existing lint/dependency
  warnings. Main JavaScript bundle: 287.36 kB gzip.

Existing CRA/Babel/Browserslist and unrelated source lint warnings remain.
Code-review-graph tools were unavailable in this session; targeted file
inspection and focused tests were used.

## Release state

This UI completion has not been deployed or pushed. The earlier production
release recorded in `PUBLISHING_CAPACITY_2026-11-07.md` remains the production
checkpoint. Source changes are retained in the shared workspace.
