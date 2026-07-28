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
  --map laptop=computers-laptops --map desktop-pc=computers-desktops \
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
tree — that is also exactly what runs on every deploy.

To seed the actual products (downloads every product image, compresses it to
max 800×800 JPEG, and re-hosts it on our storage — slow on first run):

```bash
./.venv/Scripts/python.exe manage.py seed_store_catalog
```

### ⚠️ Read this before seeding products on the live server

Image upload goes to **S3 when AWS keys are set, otherwise to the local
`MEDIA_ROOT`** — and Render's filesystem is **ephemeral**, wiped on every
deploy. So if S3 is not configured on Render, product images seeded there will
disappear at the next release and every product will show a broken image.

That is why the deploy only seeds _categories_. Before you seed products in
production, confirm these four env vars are set in the Render dashboard:
`AWS_ACCESS_KEY_ID`, `AWS_ACESS_KEY_SECRET` (note the spelling — the codebase
has this typo), `AWS_S3_REGION_NAME`, `AWS_STORAGE_BUCKET_NAME`.

**Tell me whether S3 is configured** and I'll either wire product seeding into
the deploy or set up a storage approach that survives restarts.

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

|                                                            |                                                                                                                        |
| ---------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------- |
| Category editor 404                                        | Fixed — admins can edit platform-owned rows; edits no longer re-own them                                               |
| `Products.source_url` / `source_price` / `price_synced_at` | Added (migration included)                                                                                             |
| Category taxonomy                                          | Fashion / Phones / Computers / Gadgets, create-only seeder, adopts your existing Men's/Women's Fashion into the tree   |
| Scrapers + parsers                                         | Partner OpenCart stores + Fabrilife, with real captured-HTML tests                                                     |
| Fabrilife fashion fixture                                  | 64 real products with real prices, sizes and images                                                                    |
| Product seeding                                            | Fixtures → products + sellable variants, images downloaded, compressed to 800×800 JPEG and re-hosted                   |
| Partner price sync                                         | `sync_source_prices` command + admin "Sync prices" button; only ever touches products with a `source_url`              |
| Deploy wiring                                              | `build.sh` seeds categories on every deploy (safe/idempotent); product seeding stays manual — see the S3 warning above |

Backend suite: **432 tests green**.

Still to come: the dazzle.com.bd tech fixture (step 1 above covers the two
partner stores, which matter more).

### Two serious bugs the final review caught — both fixed on this branch

Worth knowing about, because both were invisible from the outside:

1. **Privilege escalation.** My original fix for your category-editor 404 was
   too broad: it widened access for _every_ model the dynamic form handles —
   including Users and Warehouse — not just categories and products. That
   would have let an admin of one tenant edit another tenant's user accounts
   and promote them to Super Admin. Now restricted to categories and products
   only, with tests covering the other models.
2. **Price sync updated the wrong table.** Checkout charges from the product
   _variant_, but the sync only wrote the product row. Your storefront would
   have shown the new partner price while charging customers the old one. The
   sync now updates variants too, and a test pins it.
