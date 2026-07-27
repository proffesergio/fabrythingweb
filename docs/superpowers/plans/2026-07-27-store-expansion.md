# Store Expansion (SP1 + SP2) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix the admin category editor's domain-scoping 404, then expand the store into Fashion/Phones/Computers/Gadgets with real scraped seed data and a reseller price-sync for the two partner stores.

**Architecture:** SP1 widens `DynamicFormController`'s row lookup to the same platform-scope rule the list views already use. SP2 adds parsers (`catalog/scrape_parsers.py`, prod code) shared by offline scrape scripts (`tools/scrape/`) and a runtime price-sync service; fixtures are committed JSON; `seed_store_catalog` is a create-only management command that also downloads → compresses → re-uploads images via a new `core/storage.py` helper.

**Tech Stack:** Django 5 + DRF, Pillow (image compression), requests + BeautifulSoup4 (scrape/sync), SQLite test settings, S3-or-local storage.

## Global Constraints

- Tests run with `DJANGO_SETTINGS_MODULE=config.settings.test` from `backend/EcommerceInventory` (venv at `fabrythingweb/.venv`). The full suite must stay green.
- API responses use `core.helpers.renderResponse` → `{data, message}` on 2xx, `{errors, field_errors, message}` on errors.
- Every authenticated view declares `authentication_classes = [JWTAuthentication]` (no project default).
- Seeds are **create-only**; re-running must never clobber admin edits (`--force-update` is the explicit escape hatch). This is the `seed_bancharampur` lesson.
- Platform-scope rule (already used by `ProductListView`/`CategoryListView`): `user.role == 'Super Admin' or user.domain_user_id_id == user.id`. SP1 must reuse this exact rule, not invent a new one.
- Scrapers: polite 1 request/second, only run manually/locally, never imported by Django app code. Parsers live in `catalog/scrape_parsers.py` so the price-sync service can import them in prod.
- Images: always downloaded and re-uploaded to our storage (S3 when AWS keys set, else local `MEDIA_ROOT`), compressed with Pillow to max 800×800 JPEG quality 80. Never hotlink source sites.
- Frontend build check is `CI=false npx react-scripts build`; only fix warnings in files you touched.
- Real data honesty: if a site blocks scraping, stop and report — do not fabricate data and present it as scraped.

---

### Task 1: SP1 — DynamicFormController platform-scope fix

**Files:**
- Modify: `backend/EcommerceInventory/core/helpers.py` (add `isPlatformScope`)
- Modify: `backend/EcommerceInventory/accounts/controllers/DynamicFormController.py:74-83` (post) and `:105-112` (get)
- Test: `backend/EcommerceInventory/accounts/test_dynamic_form_scope.py` (new)
- Modify: `docs/superpowers/specs/2026-07-27-store-expansion-design.md` (SP1 Fix section — see Step 6)

**Interfaces:**
- Produces: `core.helpers.isPlatformScope(user) -> bool` — later tasks (price-sync endpoint) reuse it.

**Background for the implementer:** The admin list views already widen visibility: `ProductListView`/`CategoryListView` (`catalog/controllers/`) show everything when `user.role == 'Super Admin' or user.domain_user_id_id == user.id`. The dynamic form's get/post still filter `domain_user_id=request.user.domain_user_id` exactly, so rows seeded to a *different* admin (what `seed_bd_store` does: first Super Admin by id) list fine but 404 on edit — the reported bug. Also: the post-update path force-overwrites `domain_user_id`/`added_by_user_id`, which would silently re-own rows; ownership must be preserved on update.

- [ ] **Step 1: Write the failing tests**

Create `backend/EcommerceInventory/accounts/test_dynamic_form_scope.py`:

```python
"""Platform-scope rule for the dynamic form editor.

The admin LIST views (ProductListView/CategoryListView) already show every row
to Super Admins and domain-root users, but DynamicFormController filtered the
edit target by exact domain match — so seeded categories (owned by the first
Super Admin) listed fine and 404'd on edit ("Model Item Not Found").
"""
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from accounts.models import Users
from catalog.models import Categories


def auth(client, user):
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {RefreshToken.for_user(user).access_token}")


class DynamicFormScopeTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        # seeder: first Super Admin — owns the seeded rows
        self.seeder = Users.objects.create_user(
            username="seedadmin", email="seed@x.com", password="x",
            role="Super Admin", country="Bangladesh")
        # the admin actually using the panel — a *different* domain root
        self.admin = Users.objects.create_user(
            username="fadmin", email="fadmin@x.com", password="x",
            role="Admin", country="Bangladesh")
        # a staff user inside the seeder's domain (non-root)
        self.staff = Users.objects.create_user(
            username="staff1", email="staff1@x.com", password="x",
            role="Staff", country="Bangladesh", domain_user_id=self.seeder)
        self.seeded_cat = Categories.objects.create(
            name="Men's Fashion", slug="mens-fashion", description="seeded",
            domain_user_id=self.seeder, added_by_user_id=self.seeder)
        self.orphan_cat = Categories.objects.create(
            name="Orphan", slug="orphan-cat", description="null owner")
        Categories.objects.filter(pk=self.orphan_cat.pk).update(domain_user_id=None)

    def test_admin_can_fetch_edit_form_for_foreign_owned_row(self):
        auth(self.client, self.admin)
        res = self.client.get(f"/api/getForm/category/{self.seeded_cat.id}/")
        self.assertEqual(res.status_code, 200, res.content)

    def test_admin_can_fetch_edit_form_for_null_domain_row(self):
        auth(self.client, self.admin)
        res = self.client.get(f"/api/getForm/category/{self.orphan_cat.id}/")
        self.assertEqual(res.status_code, 200, res.content)

    def test_admin_update_preserves_original_owner(self):
        auth(self.client, self.admin)
        res = self.client.post(
            f"/api/getForm/category/{self.seeded_cat.id}/",
            {"name": "Men", "description": "renamed"}, format="json")
        self.assertEqual(res.status_code, 200, res.content)
        self.seeded_cat.refresh_from_db()
        self.assertEqual(self.seeded_cat.name, "Men")
        self.assertEqual(self.seeded_cat.domain_user_id_id, self.seeder.id,
                         "update must not re-own the row to the editor")

    def test_non_root_staff_cannot_edit_foreign_domain_row(self):
        foreign = Categories.objects.create(
            name="Foreign", slug="foreign-cat", description="",
            domain_user_id=self.admin, added_by_user_id=self.admin)
        auth(self.client, self.staff)
        res = self.client.get(f"/api/getForm/category/{foreign.id}/")
        self.assertEqual(res.status_code, 404)

    def test_own_domain_row_still_editable(self):
        mine = Categories.objects.create(
            name="Mine", slug="mine-cat", description="",
            domain_user_id=self.admin, added_by_user_id=self.admin)
        auth(self.client, self.admin)
        res = self.client.get(f"/api/getForm/category/{mine.id}/")
        self.assertEqual(res.status_code, 200, res.content)

    def test_create_still_assigns_owner(self):
        auth(self.client, self.admin)
        res = self.client.post(
            "/api/getForm/category/",
            {"name": "New Cat", "description": "d"}, format="json")
        self.assertEqual(res.status_code, 200, res.content)
        cat = Categories.objects.get(slug="new-cat")
        self.assertEqual(cat.domain_user_id_id, self.admin.domain_user_id_id)
```

Note: `Users.objects.create_user` self-assigns `domain_user_id` to self when omitted (see `accounts/test_domain_user.py`), so `self.admin` is a domain root — exactly the prod `fadmin` situation.

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd backend/EcommerceInventory
DJANGO_SETTINGS_MODULE=config.settings.test python manage.py test accounts.test_dynamic_form_scope -v 2
```

Expected: `test_admin_can_fetch_edit_form_for_foreign_owned_row`, `..._null_domain_row`, `test_admin_update_preserves_original_owner` FAIL (404s / owner reassigned). The other three may already pass.

- [ ] **Step 3: Implement the fix**

In `core/helpers.py` (below `getDynamicFormModels`):

```python
def isPlatformScope(user):
    """The widening rule the admin list views already use
    (ProductListView/CategoryListView): Super Admins and domain-root users
    operate on the whole platform's rows, everyone else only on their domain."""
    return user.role == 'Super Admin' or user.domain_user_id_id == user.id
```

In `DynamicFormController.py`, import it (`from core.helpers import ... , isPlatformScope`) and replace the two lookups.

`get` (was `filter(id=id, domain_user_id=request.user.domain_user_id)`):

```python
        if id:
            qs = model_class.objects.filter(id=id)
            if not isPlatformScope(request.user):
                qs = qs.filter(domain_user_id=request.user.domain_user_id)
            model_instance = qs.first()
            if model_instance is None:
                return renderResponse(data='Model Item Not Found', message='Model Item Not Found', status=404)
        else:
            model_instance = model_class()
```

(keep the local variable name the rest of the method uses).

`post` — replace lines 70-83 (the two unconditional assignments + update/create split) with:

```python
        if id:
            qs = model_class.objects.filter(id=id)
            if not isPlatformScope(request.user):
                qs = qs.filter(domain_user_id=request.user.domain_user_id)
            model_instace = qs.first()
            if model_instace is None:
                return renderResponse(data='Model Item Not Found', message='Model Item Not Found', status=404)
            # Editing must never re-own the row: ownership set at creation only.
            fieldsdata.pop('domain_user_id', None)
            fieldsdata.pop('added_by_user_id', None)
            for key, value in fieldsdata.items():
                setattr(model_instace, key, value)
            model_instace.save()
        else:
            fieldsdata['domain_user_id'] = request.user.domain_user_id
            fieldsdata['added_by_user_id'] = Users.objects.get(id=request.user.id)
            model_instace = model_class.objects.create(**fieldsdata)
```

Also delete the three debug `print(...)` calls at lines 53-57 while touching this file.

- [ ] **Step 4: Run the new tests, then the full suite**

```bash
DJANGO_SETTINGS_MODULE=config.settings.test python manage.py test accounts.test_dynamic_form_scope -v 2
DJANGO_SETTINGS_MODULE=config.settings.test python manage.py test
```

Expected: all pass (~200 tests, ~5s).

- [ ] **Step 5: Amend the spec's Fix section**

The spec hypothesized NULL-domain rows; reality (from `seed_bd_store`) is rows owned by the *first Super Admin*. Update `docs/superpowers/specs/2026-07-27-store-expansion-design.md` SP1 "Fix" paragraph to describe the platform-scope rule actually implemented (code wins; fix the doc in the same commit).

- [ ] **Step 6: Commit**

```bash
git add backend/EcommerceInventory/core/helpers.py \
        backend/EcommerceInventory/accounts/controllers/DynamicFormController.py \
        backend/EcommerceInventory/accounts/test_dynamic_form_scope.py \
        docs/superpowers/specs/2026-07-27-store-expansion-design.md
git commit -m "fix: category editor 404 - dynamic form uses the platform-scope rule the list views use"
```

---

### Task 2: Products source fields migration

**Files:**
- Modify: `backend/EcommerceInventory/catalog/models.py` (Products)
- Create: `backend/EcommerceInventory/catalog/migrations/00XX_products_source_fields.py` (via makemigrations)
- Test: `backend/EcommerceInventory/catalog/tests.py` (append)

**Interfaces:**
- Produces: `Products.source_url: str` (blank default ''), `Products.source_price: float|None`, `Products.price_synced_at: datetime|None` — Tasks 7 and 8 read/write these.

- [ ] **Step 1: Write the failing test** (append to `catalog/tests.py`)

```python
class ProductSourceFieldsTests(TestCase):
    def test_source_fields_default_empty(self):
        cat = Categories.objects.create(name="Laptops", slug="laptops-t", description="")
        p = Products.objects.create(
            name="X", slug="x-src", sku="FT-9001", category_id=cat,
            description="", initial_buying_price=1, initial_selling_price=2)
        self.assertEqual(p.source_url, "")
        self.assertIsNone(p.source_price)
        self.assertIsNone(p.price_synced_at)
```

- [ ] **Step 2: Run it — expect FAIL** (`AttributeError: source_url`)

```bash
DJANGO_SETTINGS_MODULE=config.settings.test python manage.py test catalog.tests.ProductSourceFieldsTests -v 2
```

- [ ] **Step 3: Add fields to `Products`** (after the SEO block, before `addition_details`)

```python
    # Reseller source (partner stores we sync prices from)
    source_url=models.URLField(max_length=500,blank=True,default='')
    source_price=models.FloatField(blank=True,null=True)
    price_synced_at=models.DateTimeField(blank=True,null=True)
```

- [ ] **Step 4: Make the migration and run tests**

```bash
python manage.py makemigrations catalog
DJANGO_SETTINGS_MODULE=config.settings.test python manage.py test catalog -v 1
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/EcommerceInventory/catalog/
git commit -m "feat: source_url/source_price/price_synced_at on Products for reseller sync"
```

---

### Task 3: Taxonomy in `seed_store_catalog` (categories only)

**Files:**
- Create: `backend/EcommerceInventory/catalog/management/commands/seed_store_catalog.py`
- Test: `backend/EcommerceInventory/catalog/test_seed_store_catalog.py` (new file)

**Interfaces:**
- Consumes: nothing new.
- Produces: `seed_store_catalog` command; its `TAXONOMY` constant and `_seed_categories(owner) -> dict[slug, Categories]`; Task 7 extends this same command with product seeding.

**Design notes:** create-only by slug (`get_or_create`), owner = same rule as `seed_bd_store` (first Super Admin, else Admin, else first user). Existing top-level `mens-fashion`/`womens-fashion` (from `seed_bd_store`) are **re-parented** under the new `fashion` root and renamed Men/Women — only via `REPARENT`, which runs even without `--force-update` because it's structural, not an admin-content overwrite. Other seed_bd_store categories (shoes, watches, …) are left exactly where they are.

- [ ] **Step 1: Write failing tests**

Create `catalog/test_seed_store_catalog.py`:

```python
from django.core.management import call_command
from django.test import TestCase

from accounts.models import Users
from catalog.models import Categories


class SeedStoreCatalogCategoryTests(TestCase):
    def setUp(self):
        self.owner = Users.objects.create_user(
            username="root", email="root@x.com", password="x",
            role="Super Admin", country="Bangladesh")

    def test_creates_tree(self):
        call_command("seed_store_catalog", "--categories-only")
        fashion = Categories.objects.get(slug="fashion")
        men = Categories.objects.get(slug="fashion-men")
        self.assertEqual(men.parent_id_id, fashion.id)
        self.assertTrue(Categories.objects.filter(slug="phones").exists())
        self.assertTrue(Categories.objects.filter(slug="computers-laptops").exists())
        self.assertTrue(Categories.objects.filter(slug="gadgets-smart-watches").exists())

    def test_idempotent_and_preserves_admin_edits(self):
        call_command("seed_store_catalog", "--categories-only")
        n = Categories.objects.count()
        cat = Categories.objects.get(slug="phones")
        cat.name = "Phones & Tabs"
        cat.save()
        call_command("seed_store_catalog", "--categories-only")
        self.assertEqual(Categories.objects.count(), n)
        cat.refresh_from_db()
        self.assertEqual(cat.name, "Phones & Tabs", "re-run clobbered an admin edit")

    def test_reparents_legacy_fashion_categories(self):
        legacy = Categories.objects.create(
            name="Men's Fashion", slug="mens-fashion", description="legacy",
            domain_user_id=self.owner, added_by_user_id=self.owner)
        call_command("seed_store_catalog", "--categories-only")
        legacy.refresh_from_db()
        self.assertEqual(legacy.parent_id_id, Categories.objects.get(slug="fashion").id)
        # fashion-men must NOT be created as a duplicate when mens-fashion was adopted
        self.assertFalse(Categories.objects.filter(slug="fashion-men").exists())
```

- [ ] **Step 2: Run — expect FAIL** (`Unknown command: 'seed_store_catalog'`)

```bash
DJANGO_SETTINGS_MODULE=config.settings.test python manage.py test catalog.test_seed_store_catalog -v 2
```

- [ ] **Step 3: Implement the command (category half)**

`catalog/management/commands/seed_store_catalog.py`:

```python
"""Seed the expanded multi-vertical store taxonomy (and, with fixtures,
real products scraped from partner/reference sites).

    python manage.py seed_store_catalog                    # categories + all fixtures
    python manage.py seed_store_catalog --categories-only
    python manage.py seed_store_catalog --fixture potakait # one fixture
    python manage.py seed_store_catalog --force-update     # overwrite existing rows

Create-only by slug (the seed_bancharampur lesson): re-runs never clobber
admin edits unless --force-update is passed. Legacy top-level
mens-fashion/womens-fashion (from seed_bd_store) are adopted into the new
Fashion tree; that re-parent is structural and always applies.
"""
from django.core.management.base import BaseCommand
from django.db import transaction

from accounts.models import Users
from catalog.models import Categories

# (slug, name, description, children)
TAXONOMY = [
    ("fashion", "Fashion", "Clothing for men, women & kids — everyday to festive.", [
        ("fashion-men", "Men", "T-shirts, polos, shirts, panjabi & more.", [
            ("men-tshirts", "T-shirts", "Half & full sleeve tees.", []),
            ("men-polos", "Polos", "Pique & jacquard polo shirts.", []),
            ("men-shirts", "Shirts", "Formal & casual shirts.", []),
            ("men-panjabi", "Panjabi", "Eid & festive panjabi.", []),
            ("men-hoodies", "Hoodies & Sweatshirts", "Fleece & terry warmers.", []),
            ("men-jackets", "Jackets", "Denim, bomber & windbreakers.", []),
            ("men-bottoms", "Joggers & Trousers", "Joggers, chinos & trousers.", []),
            ("men-shorts", "Shorts", "Cotton & sport shorts.", []),
        ]),
        ("fashion-women", "Women", "Kurti, tops, salwar kameez & co-ords.", [
            ("women-kurti-tops", "Kurti & Tops", "Kurtis, tops & tunics.", []),
            ("women-tshirts", "T-shirts", "Relaxed & fitted tees.", []),
            ("women-salwar-kameez", "Salwar Kameez", "2pc & 3pc sets.", []),
            ("women-coords", "Co-ords", "Matching two-piece sets.", []),
            ("women-bottoms", "Leggings & Palazzo", "Leggings, palazzo & comfy trousers.", []),
        ]),
        ("fashion-kids", "Kids", "Boys' & girls' clothing.", [
            ("kids-boys", "Boys", "Tees, polos, shorts & sets.", []),
            ("kids-girls", "Girls", "Frocks, tees, skirts & sets.", []),
        ]),
    ]),
    ("phones", "Phones", "Smartphones & tablets from every major brand.", [
        ("phones-smartphones", "Smartphones", "Android & iPhone.", []),
        ("phones-tablets", "Tablets", "iPad & Android tablets.", []),
    ]),
    ("computers", "Computers", "Laptops, desktops, components & office gear.", [
        ("computers-laptops", "Laptops", "Ultrabooks, gaming & MacBooks.", []),
        ("computers-desktops", "Desktops & All-in-Ones", "Gaming PCs, brand PCs & AIOs.", []),
        ("computers-monitors", "Monitors", "Office, gaming & professional monitors.", []),
        ("computers-components", "Components", "CPU, RAM, SSD, GPU, PSU, casing.", []),
        ("computers-keyboards-mice", "Keyboards & Mice", "Mechanical keyboards, mice & combos.", []),
        ("computers-printers-office", "Printers & Office", "Printers, scanners & POS.", []),
        ("computers-networking", "Networking", "Routers, adapters & switches.", []),
    ]),
    ("gadgets", "Gadgets", "Wearables, audio & smart devices.", [
        ("gadgets-smart-watches", "Smart Watches", "Smart & fitness watches.", []),
        ("gadgets-earbuds", "Earbuds & Headphones", "TWS earbuds & headphones.", []),
        ("gadgets-speakers", "Speakers & Audio", "Bluetooth speakers & soundbars.", []),
        ("gadgets-power", "Power Banks & Chargers", "Power banks, chargers & cables.", []),
        ("gadgets-cases", "Cases & Protection", "Phone cases & screen protectors.", []),
        ("gadgets-cameras", "Cameras & Drones", "Action cams & drones.", []),
        ("gadgets-smart-home", "Smart Home", "Smart bulbs, plugs & security cams.", []),
    ]),
]

# legacy seed_bd_store slugs adopted into the new tree: slug -> (new parent slug, new name)
REPARENT = {
    "mens-fashion": ("fashion", "Men"),
    "womens-fashion": ("fashion", "Women"),
}
# when a legacy slug is adopted, skip creating this duplicate node
REPARENT_REPLACES = {"mens-fashion": "fashion-men", "womens-fashion": "fashion-women"}


def _owner():
    return (Users.objects.filter(role="Super Admin").order_by("id").first()
            or Users.objects.filter(role="Admin").order_by("id").first()
            or Users.objects.order_by("id").first())


class Command(BaseCommand):
    help = "Seed the expanded store taxonomy and fixture products (create-only)."

    def add_arguments(self, parser):
        parser.add_argument("--categories-only", action="store_true")
        parser.add_argument("--fixture", default=None,
                            help="Seed only this fixture (basename without .json).")
        parser.add_argument("--force-update", action="store_true",
                            help="Overwrite existing seeded rows (clobbers admin edits).")

    @transaction.atomic
    def handle(self, *args, **options):
        owner = _owner()
        if owner is None:
            self.stdout.write(self.style.ERROR("No user to own seeded rows; aborting."))
            return
        cat_map = self._seed_categories(owner, force=options["force_update"])
        self.stdout.write(self.style.SUCCESS(f"Categories ready: {len(cat_map)} in tree."))
        if not options["categories_only"]:
            self._seed_products(owner, cat_map, only=options["fixture"],
                                force=options["force_update"])  # Task 7

    def _seed_categories(self, owner, force=False):
        adopted = {}
        for legacy_slug, (parent_slug, new_name) in REPARENT.items():
            legacy = Categories.objects.filter(slug=legacy_slug).first()
            if legacy is not None:
                adopted[REPARENT_REPLACES[legacy_slug]] = legacy

        cat_map, order = {}, 0

        def walk(nodes, parent):
            nonlocal order
            for slug, name, desc, children in nodes:
                order += 10
                if slug in adopted:
                    cat = adopted[slug]
                    if cat.parent_id_id != (parent.id if parent else None) or cat.name != name:
                        cat.parent_id = parent
                        cat.name = name
                        cat.save()
                else:
                    cat, created = Categories.objects.get_or_create(
                        slug=slug,
                        defaults={"name": name, "description": desc,
                                  "display_order": order,
                                  "domain_user_id": owner, "added_by_user_id": owner})
                    if not created and force:
                        cat.name, cat.description = name, desc
                        cat.parent_id = parent
                        cat.save()
                    elif created and parent is not None:
                        cat.parent_id = parent
                        cat.save()
                cat_map[slug] = cat
                walk(children, cat)

        walk(TAXONOMY, None)
        return cat_map

    def _seed_products(self, owner, cat_map, only=None, force=False):
        self.stdout.write("No product fixtures wired yet (Task 7).")
```

Careful detail: `get_or_create` with `parent_id` in defaults would also work, but setting it after creation keeps one code path for adopted/created nodes.

- [ ] **Step 4: Run tests — expect PASS**

```bash
DJANGO_SETTINGS_MODULE=config.settings.test python manage.py test catalog.test_seed_store_catalog -v 2
DJANGO_SETTINGS_MODULE=config.settings.test python manage.py test catalog accounts -v 1
```

- [ ] **Step 5: Commit**

```bash
git add backend/EcommerceInventory/catalog/
git commit -m "feat: seed_store_catalog command - expanded Fashion/Phones/Computers/Gadgets taxonomy"
```

---

### Task 4: Shared parsers + OpenCart scraper (partner stores)

**Files:**
- Create: `backend/EcommerceInventory/catalog/scrape_parsers.py`
- Create: `backend/EcommerceInventory/tools/scrape/__init__.py` (empty), `tools/scrape/common.py`, `tools/scrape/scrape_opencart.py`
- Create: `backend/EcommerceInventory/catalog/test_fixtures/opencart_product.html` (trimmed real page, see Step 3)
- Test: `backend/EcommerceInventory/catalog/test_scrape_parsers.py`
- Modify: `backend/EcommerceInventory/requirements.txt` (add `beautifulsoup4`, `Pillow` if absent)

**Interfaces:**
- Produces (imported by Tasks 5-8):
  - `catalog.scrape_parsers.parse_bdt_price(text: str) -> float | None` — `"8,500৳"` → `8500.0`; returns None when no digits.
  - `catalog.scrape_parsers.parse_opencart_product(html: str) -> dict` — keys: `name, price, discount_price, description, specifications, brand, images` (absolute URLs).
  - `catalog.scrape_parsers.parse_opencart_listing(html: str, base_url: str) -> list[str]` — product page URLs.
  - `tools/scrape/common.py`: `polite_get(url) -> str` (requests GET, UA header, 1s sleep, raise on non-200), `write_fixture(path, entries)`.
- Consumes: nothing.

- [ ] **Step 1: Capture a real test fixture**

Fetch the potakait.com homepage (network is available; this is the partner store), pick any real product URL from it, then save that product page as the test fixture:

```bash
python -c "import requests,pathlib; h={'User-Agent':'Mozilla/5.0 (fabrything import)'}; r=requests.get('<REAL_PRODUCT_URL>',headers=h,timeout=15); pathlib.Path('catalog/test_fixtures').mkdir(exist_ok=True); pathlib.Path('catalog/test_fixtures/opencart_product.html').write_text(r.text,encoding='utf-8'); print(r.status_code,len(r.text))"
```

Then open the saved file, note the actual selectors OpenCart uses on this theme (product title `h1`, price block, description tab, spec table, image gallery), and trim the file to <100 KB keeping those regions. **Write the parser against what the file actually contains, not against generic OpenCart assumptions.** If the site blocks the fetch (403/CAPTCHA), stop and report to the user — the partner can likely whitelist us or provide an export.

- [ ] **Step 2: Write failing parser tests**

`catalog/test_scrape_parsers.py`:

```python
from pathlib import Path
from django.test import SimpleTestCase

from catalog.scrape_parsers import parse_bdt_price, parse_opencart_product

FIXTURES = Path(__file__).resolve().parent / "test_fixtures"


class BdtPriceTests(SimpleTestCase):
    def test_plain(self):
        self.assertEqual(parse_bdt_price("8,500৳"), 8500.0)

    def test_symbol_first_and_spaces(self):
        self.assertEqual(parse_bdt_price("৳ 12,990"), 12990.0)

    def test_garbage_returns_none(self):
        self.assertIsNone(parse_bdt_price("Out of stock"))


class OpenCartProductTests(SimpleTestCase):
    def setUp(self):
        self.html = (FIXTURES / "opencart_product.html").read_text(encoding="utf-8")

    def test_extracts_core_fields(self):
        p = parse_opencart_product(self.html)
        self.assertTrue(p["name"])
        self.assertIsInstance(p["price"], float)
        self.assertGreater(p["price"], 0)
        self.assertIsInstance(p["images"], list)
        self.assertTrue(all(u.startswith("http") for u in p["images"]))
        self.assertIsInstance(p["specifications"], dict)
```

(Assert on the *specific* values you saw in the captured page too — e.g. the exact product name — so selector drift fails loudly.)

- [ ] **Step 3: Run — expect FAIL** (module not found)

```bash
DJANGO_SETTINGS_MODULE=config.settings.test python manage.py test catalog.test_scrape_parsers -v 2
```

- [ ] **Step 4: Implement `catalog/scrape_parsers.py`**

```python
"""HTML parsers shared by the offline scrape scripts (tools/scrape/) and the
runtime price-sync service. Pure functions: str in, plain data out — no
network, no ORM, so they are unit-testable against saved page snippets."""
import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup

_PRICE_RE = re.compile(r"[\d,]+(?:\.\d+)?")


def parse_bdt_price(text):
    if not text:
        return None
    m = _PRICE_RE.search(text.replace("৳", "").strip())  # ৳
    if not m or not any(c.isdigit() for c in m.group()):
        return None
    try:
        return float(m.group().replace(",", ""))
    except ValueError:
        return None
```

…then `parse_opencart_product` / `parse_opencart_listing` written against the captured fixture's real selectors (typical OpenCart theme: `h1` title, `.price-new`/`.price-old` or a `.product-price` block, `#tab-description`, `#tab-specification table` rows, `.thumbnails img` / `.swiper-slide img` gallery — but trust the fixture, not this list). Images: `urljoin(base, src)` and strip query strings; dedupe preserving order. `discount_price` only when both old and new prices exist (new < old → price=old, discount_price=new).

- [ ] **Step 5: Run parser tests — expect PASS**

- [ ] **Step 6: Implement `tools/scrape/common.py` and `scrape_opencart.py`**

`common.py`:

```python
import json
import pathlib
import time

import requests

UA = {"User-Agent": "Mozilla/5.0 (fabrything catalog import; contact: bhnbids@gmail.com)"}


def polite_get(url, delay=1.0):
    time.sleep(delay)
    r = requests.get(url, headers=UA, timeout=20)
    r.raise_for_status()
    return r.text


def write_fixture(path, entries):
    p = pathlib.Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(entries, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote {len(entries)} entries -> {p}")
```

`scrape_opencart.py` (CLI: `python tools/scrape/scrape_opencart.py <base_url> <out.json> --map laptop=computers-laptops --map processor=computers-components --limit 10`): for each `--map src_path=category_slug`, fetch `<base>/<src_path>`, `parse_opencart_listing`, take first `--limit` product URLs, `parse_opencart_product` each, and emit fixture entries:

```python
entry = {
    "category_path": category_slug,          # a slug from seed_store_catalog TAXONOMY
    "name": p["name"], "price": p["price"],
    "discount_price": p.get("discount_price"),
    "description": p.get("description") or p["name"],
    "specifications": p.get("specifications") or {},
    "brand": p.get("brand") or "",
    "images": p["images"][:3],
    "source_url": url,                        # partner stores only
}
```

Run it under the project venv (`.venv`) so `catalog.scrape_parsers` imports; add `sys.path` bootstrap at the top:

```python
import pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))  # EcommerceInventory/
```

- [ ] **Step 7: Requirements + commit**

Check `requirements.txt`; add `beautifulsoup4` (needed in prod for price sync) and `Pillow` (Task 7) if missing, and `pip install` them into `.venv`. Then:

```bash
git add backend/EcommerceInventory/catalog/scrape_parsers.py \
        backend/EcommerceInventory/catalog/test_scrape_parsers.py \
        backend/EcommerceInventory/catalog/test_fixtures/ \
        backend/EcommerceInventory/tools/scrape/ \
        backend/EcommerceInventory/requirements.txt
git commit -m "feat: shared BDT/OpenCart parsers + polite scrape tooling"
```

---

### Task 5: Fabrilife scraper + fashion fixture

**Files:**
- Create: `backend/EcommerceInventory/tools/scrape/scrape_fabrilife.py`
- Create: `backend/EcommerceInventory/catalog/test_fixtures/fabrilife_product.html` (captured, trimmed)
- Modify: `backend/EcommerceInventory/catalog/scrape_parsers.py` (add `parse_fabrilife_product`, `parse_fabrilife_listing`)
- Test: `backend/EcommerceInventory/catalog/test_scrape_parsers.py` (append `FabrilifeProductTests`, same shape as `OpenCartProductTests`)
- Create: `backend/EcommerceInventory/catalog/fixtures/seed/fabrilife_fashion.json` (generated, committed)

**Interfaces:**
- Consumes: `polite_get`, `write_fixture`, `parse_bdt_price` from Task 4.
- Produces: `parse_fabrilife_product(html) -> dict` with the same keys as the OpenCart parser **plus** `gender` (`"MEN"|"WOMEN"|"KIDS"`), `sizes` (list, from the size selector), `material` (from description when stated, else `""`); fixture file consumed by Task 7.

Steps mirror Task 4 exactly: capture one real product page → trimmed test fixture → failing tests → parser → green tests → scraper CLI. Category source paths for the CLI (from the site's faceted URLs, e.g. `/shop?refinementList[cats][0]=Men%20%3E%20T-shirt`): map onto taxonomy slugs `men-tshirts`, `men-polos`, `men-panjabi`, `men-hoodies`, `women-kurti-tops`, `women-tshirts`, `kids-boys`, `kids-girls` — ~10 products each. Fabrilife entries do **not** get `source_url` (not a partner; one-time seed only).

- [ ] **Step 1: Capture fixture page** (as Task 4 Step 1, from fabrilife.com)
- [ ] **Step 2: Write failing `FabrilifeProductTests`** (assert name, price, sizes non-empty, gender in set)
- [ ] **Step 3: Run — FAIL**
- [ ] **Step 4: Implement parser; run — PASS**
- [ ] **Step 5: Write + run `scrape_fabrilife.py`, generate `fabrilife_fashion.json`; eyeball 3 entries for sane name/price/images**
- [ ] **Step 6: Commit**

```bash
git add backend/EcommerceInventory/tools/scrape/scrape_fabrilife.py \
        backend/EcommerceInventory/catalog/scrape_parsers.py \
        backend/EcommerceInventory/catalog/test_scrape_parsers.py \
        backend/EcommerceInventory/catalog/test_fixtures/fabrilife_product.html \
        backend/EcommerceInventory/catalog/fixtures/seed/fabrilife_fashion.json
git commit -m "feat: fabrilife scraper + committed fashion seed fixture"
```

---

### Task 6: Dazzle scraper + tech fixture; partner fixtures

**Files:**
- Create: `backend/EcommerceInventory/tools/scrape/scrape_dazzle.py`
- Modify: `backend/EcommerceInventory/catalog/scrape_parsers.py` (add `parse_next_data(html) -> dict` returning the embedded `__NEXT_DATA__` JSON, and `dazzle_products_from_page(html) -> list[dict]`)
- Test: append `DazzleParserTests` to `catalog/test_scrape_parsers.py` (fixture: `catalog/test_fixtures/dazzle_category.html`)
- Create (generated, committed): `catalog/fixtures/seed/dazzle_tech.json`, `catalog/fixtures/seed/potakait.json`, `catalog/fixtures/seed/canvasit.json`

**Interfaces:**
- Consumes: Task 4's tooling; Task 4's `scrape_opencart.py` CLI for the two partner fixtures.
- Produces: the three fixture files Task 7 seeds.

- [ ] **Step 1: Capture a dazzle category page**, confirm `<script id="__NEXT_DATA__">` contains product data (name, price, image, slug). If the data is not embedded (fully client-fetched), find the JSON API the page calls (Network tab pattern: usually `/_next/data/<buildId>/…json`) and capture that instead. If neither works, **fall back to a hand-curated `dazzle_tech.json`** with ~8 phones/tablets/watches at realistic BDT prices and loremflickr placeholder images, mark each entry `"curated": true`, and tell the user in the task report that dazzle was curated, not scraped.
- [ ] **Step 2: Failing `DazzleParserTests`** (products list non-empty; each has name + price > 0)
- [ ] **Step 3: Implement `parse_next_data` (json.loads of the script tag) + extraction; tests PASS**
- [ ] **Step 4: Generate fixtures** — dazzle: category slugs `phones-smartphones`, `phones-tablets`, `gadgets-smart-watches`, `gadgets-earbuds`, `gadgets-power`; partner stores via the Task 4 CLI, mapping their real category paths onto `computers-laptops`, `computers-desktops`, `computers-monitors`, `computers-components`, `computers-keyboards-mice`, `computers-printers-office`, `computers-networking` (~10 each; both sites include `source_url`).
- [ ] **Step 5: Sanity-check fixtures** — script over each file: every entry has `name`, `price > 0`, `category_path` in TAXONOMY slugs, ≥1 image URL. Fix mapping typos now, not at seed time.
- [ ] **Step 6: Commit**

```bash
git add backend/EcommerceInventory/tools/scrape/scrape_dazzle.py \
        backend/EcommerceInventory/catalog/scrape_parsers.py \
        backend/EcommerceInventory/catalog/test_scrape_parsers.py \
        backend/EcommerceInventory/catalog/test_fixtures/dazzle_category.html \
        backend/EcommerceInventory/catalog/fixtures/seed/
git commit -m "feat: dazzle scraper + tech/partner seed fixtures (dazzle, potakait, canvasit)"
```

---

### Task 7: Product seeding with image copy + compression

**Files:**
- Create: `backend/EcommerceInventory/core/storage.py`
- Modify: `backend/EcommerceInventory/core/views.py` (`FileUploadViewInS3` delegates to it)
- Modify: `backend/EcommerceInventory/catalog/management/commands/seed_store_catalog.py` (`_seed_products` real implementation)
- Test: `backend/EcommerceInventory/catalog/test_seed_store_catalog.py` (append), `backend/EcommerceInventory/core/test_storage.py` (new)

**Interfaces:**
- Consumes: fixtures from Tasks 5-6; `cat_map` from Task 3; `Products.source_url` from Task 2.
- Produces:
  - `core.storage.save_file(filename: str, content: bytes, content_type: str) -> str` — uploads to S3 when configured else `MEDIA_ROOT/uploads/`, returns public URL. (Exact S3/local branching copied from `FileUploadViewInS3`, which then calls this.)
  - `seed_store_catalog` full behavior; `_import_image(url) -> str | None` (download → Pillow → `save_file`).
  - Every seeded product has ≥1 active `ProductVariant` (checkout sells variants, not products).

- [ ] **Step 1: Failing storage test** — `core/test_storage.py`:

```python
import os
from django.conf import settings
from django.test import SimpleTestCase

from core.storage import save_file


class SaveFileLocalTests(SimpleTestCase):
    def test_local_save_returns_media_url_and_writes_file(self):
        url = save_file("unit_test_probe.jpg", b"\xff\xd8\xff\xdbfake", "image/jpeg")
        self.assertIn("/uploads/", url)
        name = url.rsplit("/", 1)[1]
        path = os.path.join(settings.MEDIA_ROOT, "uploads", name)
        self.assertTrue(os.path.exists(path))
        os.remove(path)
```

(`core/views.py` reads `MEDIA_ROOT`/`MEDIA_URL` from `django.conf.settings` at module import — `core/storage.py` should do the same.)

- [ ] **Step 2: Run — FAIL. Implement `core/storage.py`** by extracting the S3/local branches from `FileUploadViewInS3.post` into `save_file` (unique-name generation stays in the view; `save_file` takes the final name). Refactor the view to call it. Run `core` + full suite — PASS (the upload view has no behavior change).

- [ ] **Step 3: Failing seed-products tests** (append to `catalog/test_seed_store_catalog.py`):

```python
import json
from unittest.mock import patch

from catalog.models import Products, ProductVariant


class SeedStoreCatalogProductTests(TestCase):
    def setUp(self):
        self.owner = Users.objects.create_user(
            username="root2", email="root2@x.com", password="x",
            role="Super Admin", country="Bangladesh")

    def _run(self):
        # never hit network or real storage in tests
        with patch("catalog.management.commands.seed_store_catalog.Command._import_image",
                   return_value="https://cdn.test/x.jpg"):
            call_command("seed_store_catalog")

    def test_seeds_products_with_variants_and_owner(self):
        self._run()
        self.assertGreater(Products.objects.count(), 0)
        self.assertEqual(Products.objects.filter(domain_user_id__isnull=True).count(), 0)
        for p in Products.objects.all():
            self.assertTrue(p.variants.filter(is_active=True).exists(),
                            f"{p.slug} has no sellable variant")

    def test_partner_products_carry_source_url(self):
        self._run()
        self.assertTrue(Products.objects.exclude(source_url="").exists())

    def test_rerun_preserves_admin_price_edit(self):
        self._run()
        p = Products.objects.exclude(source_url="").first()
        p.initial_selling_price = 12345
        p.save()
        self._run()
        p.refresh_from_db()
        self.assertEqual(p.initial_selling_price, 12345)
```

These run against the real committed fixtures — which also validates fixture integrity in CI forever.

- [ ] **Step 4: Implement `_seed_products` + `_import_image`**

In `seed_store_catalog.py`:

```python
import io
import json
import os

import requests
from django.utils import timezone
from django.utils.text import slugify

from catalog.models import Products, ProductVariant

FIXTURE_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "fixtures", "seed")
SKU_PREFIX = "FS"  # FS-xxxx: distinct from seed_bd_store's FT-xxxx


    def _import_image(self, url):
        """Download → compress (max 800x800 JPEG q80) → our storage. None on any failure."""
        from PIL import Image
        from core.storage import save_file
        try:
            r = requests.get(url, timeout=20,
                             headers={"User-Agent": "Mozilla/5.0 (fabrything import)"})
            r.raise_for_status()
            img = Image.open(io.BytesIO(r.content)).convert("RGB")
            img.thumbnail((800, 800))
            buf = io.BytesIO()
            img.save(buf, "JPEG", quality=80, optimize=True)
            name = os.urandom(12).hex() + ".jpg"
            return save_file(name, buf.getvalue(), "image/jpeg")
        except Exception as e:  # noqa: BLE001 — a bad image must never sink the seed
            self.stdout.write(self.style.WARNING(f"  image skipped ({url}): {e}"))
            return None

    def _seed_products(self, owner, cat_map, only=None, force=False):
        files = sorted(f for f in os.listdir(FIXTURE_DIR) if f.endswith(".json"))
        if only:
            files = [f for f in files if f == f"{only}.json"]
        sku_n = 1000 + Products.objects.filter(sku__startswith=SKU_PREFIX).count()
        created = 0
        for fname in files:
            with open(os.path.join(FIXTURE_DIR, fname), encoding="utf-8") as fh:
                entries = json.load(fh)
            self.stdout.write(f"{fname}: {len(entries)} entries")
            for e in entries:
                slug = slugify(e["name"])[:250]
                cat = cat_map.get(e["category_path"])
                if cat is None:
                    self.stdout.write(self.style.WARNING(
                        f"  unknown category_path {e['category_path']!r} — skipped {slug}"))
                    continue
                if Products.objects.filter(slug=slug).exists() and not force:
                    continue
                images = [u for u in (self._import_image(src) for src in e.get("images", [])[:3]) if u]
                sku_n += 1
                sell = float(e["price"])
                disc = float(e["discount_price"]) if e.get("discount_price") else None
                defaults = {
                    "name": e["name"], "slug": slug,
                    "description": e.get("description") or e["name"],
                    "specifications": e.get("specifications") or {},
                    "brand": e.get("brand") or "",
                    "gender": e.get("gender") or "UNISEX",
                    "material": e.get("material") or "",
                    "available_sizes": e.get("sizes") or [],
                    "image": images,
                    "initial_buying_price": round(sell * 0.85),  # dealer-price placeholder
                    "initial_selling_price": sell,
                    "discount_price": disc,
                    "source_url": e.get("source_url") or "",
                    "source_price": sell if e.get("source_url") else None,
                    "price_synced_at": timezone.now() if e.get("source_url") else None,
                    "category_id": cat, "status": "ACTIVE",
                    "domain_user_id": owner, "added_by_user_id": owner,
                    "seo_title": f"{e['name']} - Fabrything",
                    "seo_description": (e.get("description") or e["name"])[:160],
                }
                product, was_created = Products.objects.update_or_create(
                    slug=slug, defaults={"sku": f"{SKU_PREFIX}-{sku_n}", **defaults}
                ) if force else Products.objects.get_or_create(
                    slug=slug, defaults={"sku": f"{SKU_PREFIX}-{sku_n}", **defaults})
                if was_created:
                    created += 1
                sizes = e.get("sizes") or [""]
                for size in sizes:
                    ProductVariant.objects.get_or_create(
                        product=product, size=size, color="",
                        defaults={"sku": f"{product.sku}-{size or 'DEF'}",
                                  "price": disc or sell, "stock_quantity": 25})
        self.stdout.write(self.style.SUCCESS(f"Products: {created} created."))
```

(Method bodies go inside the `Command` class; module-level imports at the top of the file.)

- [ ] **Step 5: Run the catalog suite, then everything**

```bash
DJANGO_SETTINGS_MODULE=config.settings.test python manage.py test catalog core -v 1
DJANGO_SETTINGS_MODULE=config.settings.test python manage.py test
```

Expected: PASS.

- [ ] **Step 6: Run the real seed locally against dev DB if one is running; otherwise rely on tests.** Commit.

```bash
git add backend/EcommerceInventory/core/ backend/EcommerceInventory/catalog/
git commit -m "feat: seed_store_catalog products - fixtures to catalog with compressed re-hosted images"
```

---

### Task 8: Price-sync service, command, admin endpoint

**Files:**
- Create: `backend/EcommerceInventory/catalog/services_price_sync.py`
- Create: `backend/EcommerceInventory/catalog/management/commands/sync_source_prices.py`
- Modify: `backend/EcommerceInventory/catalog/controllers/ProductController.py` (add `AdminSyncPricesView`)
- Modify: `backend/EcommerceInventory/catalog/urls.py` (add route)
- Test: `backend/EcommerceInventory/catalog/test_price_sync.py`

**Interfaces:**
- Consumes: `Products.source_url/source_price/price_synced_at` (Task 2), `parse_opencart_product`, `parse_bdt_price` (Task 4), `isPlatformScope` (Task 1).
- Produces: `sync_source_prices(fetcher=None, dry_run=False, markup_percent=None) -> list[dict]` where each dict is `{"slug", "old_price", "new_price", "old_discount", "new_discount", "updated"}`; endpoint `POST /api/products/admin/sync-prices/` returning `{data: {"changes": [...], "checked": n}, message}`.

- [ ] **Step 1: Failing tests** — `catalog/test_price_sync.py`:

```python
from django.test import TestCase

from accounts.models import Users
from catalog.models import Categories, Products
from catalog.services_price_sync import sync_source_prices

PAGE = """<html><body><div id="content">
<h1>Test GPU</h1>
<ul class="list-unstyled"><li><span class="price-new">44,500৳</span>
<span class="price-old">46,000৳</span></li></ul>
</div></body></html>"""


def fake_fetcher(url):
    return PAGE


class PriceSyncTests(TestCase):
    def setUp(self):
        owner = Users.objects.create_user(username="r", email="r@x.com", password="x",
                                          role="Super Admin", country="Bangladesh")
        cat = Categories.objects.create(name="Components", slug="c-t", description="")
        self.p = Products.objects.create(
            name="Test GPU", slug="test-gpu", sku="FS-9001", category_id=cat,
            description="", initial_buying_price=1, initial_selling_price=40000,
            source_url="https://potakait.com/test-gpu",
            domain_user_id=owner, added_by_user_id=owner)

    def test_updates_price_and_stamps_sync(self):
        changes = sync_source_prices(fetcher=fake_fetcher)
        self.p.refresh_from_db()
        self.assertEqual(self.p.initial_selling_price, 46000.0)
        self.assertEqual(self.p.discount_price, 44500.0)
        self.assertEqual(self.p.source_price, 46000.0)
        self.assertIsNotNone(self.p.price_synced_at)
        self.assertEqual(len([c for c in changes if c["updated"]]), 1)

    def test_dry_run_writes_nothing(self):
        sync_source_prices(fetcher=fake_fetcher, dry_run=True)
        self.p.refresh_from_db()
        self.assertEqual(self.p.initial_selling_price, 40000)
        self.assertIsNone(self.p.price_synced_at)

    def test_markup_applied(self):
        sync_source_prices(fetcher=fake_fetcher, markup_percent=10)
        self.p.refresh_from_db()
        self.assertEqual(self.p.initial_selling_price, 50600.0)  # 46000 * 1.10

    def test_fetch_failure_skips_product(self):
        def boom(url):
            raise OSError("down")
        changes = sync_source_prices(fetcher=boom)
        self.p.refresh_from_db()
        self.assertEqual(self.p.initial_selling_price, 40000)
        self.assertFalse(changes[0]["updated"])
```

Note the test page uses the same price markup family the Task 4 fixture showed; if the captured partner HTML differs, mirror *that* here — the service must parse the partner sites' real structure.

- [ ] **Step 2: Run — FAIL. Implement `services_price_sync.py`:**

```python
"""Re-price partner-sourced products from their live pages.

Products with a source_url came from the partner computer stores
(potakait.com / canvasit.com.bd — see the 2026-07-27 spec: explicit reseller
permission). Selling price mirrors their retail price plus an optional
markup; dealer margin is the difference the owner negotiates offline.
"""
import os

from django.utils import timezone

from catalog.models import Products
from catalog.scrape_parsers import parse_opencart_product


def _default_fetcher(url):
    import requests
    r = requests.get(url, timeout=20,
                     headers={"User-Agent": "Mozilla/5.0 (fabrything price sync)"})
    r.raise_for_status()
    return r.text


def sync_source_prices(fetcher=None, dry_run=False, markup_percent=None):
    fetch = fetcher or _default_fetcher
    if markup_percent is None:
        markup_percent = float(os.environ.get("RESELLER_MARKUP_PERCENT", "0"))
    factor = 1 + markup_percent / 100.0
    changes = []
    for p in Products.objects.exclude(source_url="").iterator():
        rec = {"slug": p.slug, "old_price": p.initial_selling_price,
               "new_price": None, "old_discount": p.discount_price,
               "new_discount": None, "updated": False}
        try:
            parsed = parse_opencart_product(fetch(p.source_url))
        except Exception:  # noqa: BLE001 — one dead page must not stop the run
            changes.append(rec)
            continue
        price = parsed.get("price")
        if not price:
            changes.append(rec)
            continue
        new_price = round(price * factor, 2)
        disc = parsed.get("discount_price")
        new_disc = round(disc * factor, 2) if disc else None
        rec["new_price"], rec["new_discount"] = new_price, new_disc
        if not dry_run:
            p.initial_selling_price = new_price
            p.discount_price = new_disc
            p.source_price = price
            p.price_synced_at = timezone.now()
            p.save(update_fields=["initial_selling_price", "discount_price",
                                  "source_price", "price_synced_at", "updated_at"])
        rec["updated"] = True
        changes.append(rec)
    return changes
```

- [ ] **Step 3: Run service tests — PASS.**

- [ ] **Step 4: Command + endpoint.**

`catalog/management/commands/sync_source_prices.py`:

```python
from django.core.management.base import BaseCommand

from catalog.services_price_sync import sync_source_prices


class Command(BaseCommand):
    help = "Re-fetch partner-store prices for products with a source_url."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **options):
        changes = sync_source_prices(dry_run=options["dry_run"])
        for c in changes:
            mark = "~" if c["updated"] else "!"
            self.stdout.write(f" {mark} {c['slug']}: {c['old_price']} -> {c['new_price']}")
        n = sum(1 for c in changes if c["updated"])
        self.stdout.write(self.style.SUCCESS(
            f"{'DRY RUN: ' if options['dry_run'] else ''}{n}/{len(changes)} updated."))
```

`AdminSyncPricesView` in `catalog/controllers/ProductController.py`:

```python
from core.helpers import isPlatformScope, renderResponse
from catalog.services_price_sync import sync_source_prices


class AdminSyncPricesView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if not isPlatformScope(request.user):
            return renderResponse(data='Forbidden', message='Forbidden', status=403)
        changes = sync_source_prices()
        return renderResponse(
            data={"changes": [c for c in changes if c["updated"]],
                  "checked": len(changes)},
            message='Prices synced')
```

Route in `catalog/urls.py`: `path('admin/sync-prices/', AdminSyncPricesView.as_view(), name='admin_sync_prices'),` (final URL `/api/products/admin/sync-prices/`). Add an endpoint test in `test_price_sync.py`: platform admin POST → 200 (patch `catalog.controllers.ProductController.sync_source_prices` to return `[]`); Staff (non-root, `domain_user_id=owner`) POST → 403.

- [ ] **Step 5: Full suite green. Commit.**

```bash
git add backend/EcommerceInventory/catalog/
git commit -m "feat: partner price sync - service, management command, admin endpoint"
```

---

### Task 9: Deploy wiring + admin Sync button

**Files:**
- Modify: `backend/EcommerceInventory/build.sh` (after the `seed_food_demo` line)
- Modify: the admin products list page — locate with `Grep "api/products" frontend/ecommerce_inventory/src/pages/products/` and add the button to the page listing products (it renders the list header/toolbar).
- Test: co-located `*.test.js` next to that page if one exists (extend it); otherwise verify via build.

- [ ] **Step 1: build.sh** — add after line 42:

```bash
# Expanded store taxonomy + scraped fixtures. Create-only: safe on every deploy,
# only fills gaps (first run downloads + re-hosts product images, so it is slow once).
python manage.py seed_store_catalog || echo "WARNING: seed_store_catalog failed (non-fatal)"
```

- [ ] **Step 2: Frontend button.** In the products admin page's toolbar (next to the existing Add/actions buttons), following the page's existing `callApi` import pattern:

```jsx
const [syncing, setSyncing] = useState(false);
const handleSyncPrices = async () => {
  setSyncing(true);
  const res = await callApi({ url: 'products/admin/sync-prices/', method: 'POST', rawError: true });
  setSyncing(false);
  if (res?.data?.data) {
    const n = res.data.data.changes?.length ?? 0;
    alert(`Price sync complete — ${n} product${n === 1 ? '' : 's'} updated.`);
    fetchData?.(); // whatever the page's list-refresh function is called
  } else {
    alert('Price sync failed — check console.');
  }
};
// in the toolbar JSX:
<Button variant="outlined" startIcon={<SyncIcon />} disabled={syncing} onClick={handleSyncPrices}>
  {syncing ? 'Syncing…' : 'Sync prices'}
</Button>
```

Adapt names (`callApi` signature, refresh function, snackbar-vs-alert) to what the page actually uses — read it first; if the page uses a snackbar/toast helper, use that instead of `alert`.

- [ ] **Step 3: Verify**

```bash
cd frontend/ecommerce_inventory && npm test -- --watchAll=false
CI=false npx react-scripts build
```

Expected: tests pass; build succeeds (pre-existing warnings tolerated, none new in touched files).

- [ ] **Step 4: Commit**

```bash
git add backend/EcommerceInventory/build.sh frontend/ecommerce_inventory/src/pages/products/
git commit -m "feat: seed expanded catalog on deploy + admin Sync prices button"
```

---

### Task 10: End-to-end verification + docs

**Files:**
- Modify: `CLAUDE.md` (project map: new commands, parsers module, source fields — a few lines in the right sections)

- [ ] **Step 1: Backend full suite** — `DJANGO_SETTINGS_MODULE=config.settings.test python manage.py test` → green.
- [ ] **Step 2: Frontend** — `npm test -- --watchAll=false` and `CI=false npx react-scripts build` → green.
- [ ] **Step 3: Storefront smoke.** Seed a scratch SQLite/dev DB (`python manage.py migrate && python manage.py create_admin ... && python manage.py seed_store_catalog`), `npm start`, and verify: MegaMenu shows Fashion/Phones/Computers/Gadgets with children (`StorefrontCategorySerializer` recurses `children` — should be automatic); a tech product's detail page renders its `specifications` table (ProductDetail.js:75 already reads it); a fashion product shows size options. Screenshot or describe findings.
- [ ] **Step 4: Update `CLAUDE.md`** — commands section gains `seed_store_catalog` + `sync_source_prices`; a line about `catalog/scrape_parsers.py` shared by tools/scrape and price sync; a line in "Conventions that bite" documenting the platform-scope rule now shared by list views and DynamicFormController.
- [ ] **Step 5: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: project map - store expansion commands and conventions"
```

- [ ] **Step 6: Push and confirm deploy** — `git push origin main`, then after Render deploys: `curl https://fabrythingweb.onrender.com/api/health/` (must be 200, no pending migrations), and ask the user to retry the category edit that started all this.
