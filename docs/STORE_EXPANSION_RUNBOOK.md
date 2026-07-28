# Store expansion — runbook for the owner

Branch: `feature/store-expansion`. Everything below is safe to run repeatedly.

Run all commands from `backend/EcommerceInventory`. On Windows PowerShell the
Python is `.\.venv\Scripts\python.exe`; in Git Bash it is
`./.venv/Scripts/python.exe`.

---

## 1. Generate the partner-store fixtures (the slow part — please run this)

These hit potakait.com and canvasit.com.bd at **1 request/second** (your
friends' stores, reseller permission). Each command below is roughly
70 categories × products ≈ a few minutes. Let it finish; do not run them in
parallel.

**Potaka IT:**

```bash
./.venv/Scripts/python.exe tools/scrape/scrape_opencart.py https://potakait.com \
  catalog/fixtures/seed/potakait.json \
  --map laptops=computers-laptops \
  --map gaming-pc=computers-desktops \
  --map monitors=computers-monitors \
  --map processors=computers-components \
  --map keyboards=computers-keyboards-mice \
  --map printers=computers-printers-office \
  --map routers=computers-networking \
  --limit 10
```

**Canvas IT:**

```bash
./.venv/Scripts/python.exe tools/scrape/scrape_opencart.py https://canvasit.com.bd \
  catalog/fixtures/seed/canvasit.json \
  --map laptop=computers-laptops \
  --map desktop-pc=computers-desktops \
  --map monitor=computers-monitors \
  --map processor=computers-components \
  --map keyboard=computers-keyboards-mice \
  --map printer=computers-printers-office \
  --map router=computers-networking \
  --limit 10
```

**If a `--map` path 404s or yields 0 products**, that path doesn't exist on
that site. Open the store's menu in a browser, copy the real category URL
slug, and swap it in — the left side of each `=` is just the path after the
domain. Drop any `--map` you can't find a match for; a missing category is
fine, a wrong one is not.

**Paste me the output** of both commands (the "wrote N entries" lines and any
errors) and I'll validate the fixtures and wire them into the seeder.

The right-hand slugs must stay exactly as written — they are the category
slugs from `seed_store_catalog.TAXONOMY`.

---

## 2. Seed your local database (optional, to see it before deploying)

```bash
./.venv/Scripts/python.exe manage.py migrate
./.venv/Scripts/python.exe manage.py seed_store_catalog --categories-only
```

`--categories-only` creates just the Fashion / Phones / Computers / Gadgets
tree. Product seeding from the fixtures lands in the next task (it downloads
and compresses every product image, so it is slow on first run).

Safety: `seed_store_catalog` is **create-only**. Re-running it never
overwrites a category you renamed in the admin panel. `--force-update` is the
only thing that overwrites, and only use it deliberately.

---

## 3. Verify the category-editor bug is actually fixed (after deploy)

This was the "Item Not Found / Error Fetching" you reported. Once merged and
deployed:

1. Open Admin → Categories → edit **Men's Fashion**.
2. The form should load with its fields populated instead of 404-ing.
3. Change the name, save, reload — the change should stick, and the category
   should still belong to whoever owned it before (the fix deliberately does
   not re-own rows to whoever edits them).

---

## 4. Merge to main and deploy to the live server

Only after step 1 is done and I've confirmed the fixtures. Then:

```bash
cd /c/Users/bhnbi/Music/SaaS/fabrything/fabrythingweb

# 1. Confirm the whole suite is green on the branch
cd backend/EcommerceInventory
DJANGO_SETTINGS_MODULE=config.settings.test ./.venv/Scripts/python.exe manage.py test
cd ../..

# 2. Merge (no fast-forward, so the feature stays one reviewable unit)
git checkout main
git pull origin main
git merge --no-ff feature/store-expansion -m "Store expansion: category editor fix, expanded taxonomy, real seed data"

# 3. Push — Render auto-deploys from main
git push origin main
```

**Then watch the deploy:**

```bash
# Wait for Render to finish, then confirm the schema matches the code.
# 200 = healthy. 503 = migrations pending; do not ignore it.
curl https://fabrythingweb.onrender.com/api/health/
```

A new migration ships in this branch (`catalog` — the three `source_*`
columns on Products). `build.sh` runs `migrate`, **but the live Render service
was created by hand and its Build Command may not be `./build.sh`** — that has
bitten this project before. If `/api/health/` reports pending migrations after
the deploy, that is the cause; tell me and we'll fix the deploy config rather
than guessing.

**Rollback if needed:** `git revert -m 1 <merge-commit-sha> && git push origin main`.

---

## What's already done on this branch

| | |
| --- | --- |
| Category editor 404 | Fixed — admins can edit platform-owned rows; edits no longer re-own them |
| `Products.source_url` / `source_price` / `price_synced_at` | Added (migration included) |
| Category taxonomy | Fashion / Phones / Computers / Gadgets, create-only seeder, adopts your existing Men's/Women's Fashion into the tree |
| Scrapers + parsers | Partner OpenCart stores + Fabrilife, with real captured-HTML tests |
| Fabrilife fashion fixture | 64 real products with real prices, sizes and images |

Still to come: dazzle.com.bd tech fixture, product seeding with image
compression, partner price sync + admin "Sync prices" button, deploy wiring.
