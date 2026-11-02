# Control center verification

## Frontend

- Focused control-center and data-hook tests passed: 12/12.
- Browser QA passed against intercepted QA fixtures: actions, schedule PATCH, demo controls, stale-refresh banner, no page errors, and mobile width (390 px viewport and document width). Screenshots are in `docs/screenshots/control-center-desktop.png` and `docs/screenshots/control-center-mobile.png`.
- QA fixtures are explicitly demo data; browser results do not verify live provider credentials or external provider ingestion.
- Production build passed (`CI=false react-scripts build`). CRA emitted ESLint warnings in existing app files and standard outdated Browserslist/dependency notices; the control-center files did not add build errors.

## Backend

- Root reports 325 catalog and orders backend tests passed against isolated SQLite.
- A separate `makemigrations --check --dry-run` reported no changes; no live migration was run.
- Production activation still needs the provider credentials and worker setup documented in the backend runbook; browser QA used intercepted demo fixtures.
