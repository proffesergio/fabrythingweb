# Food Delivery — Phase 0 + Phase 1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship the marketplace supply side — a `food` Django app with restaurants, delivery zones, and per-restaurant menus, managed by admins (onboarding/approval) and vendors (own menu), plus a public read API and an animated "Food" storefront header entry.

**Architecture:** New Django `food` app sharing the existing `accounts`/`core` infrastructure and JWT auth. Two new user roles (`Restaurant`, `Rider`). Three API audiences — public read (AllowAny), vendor (owner-scoped), admin (permission-middleware-gated). React/MUI admin pages + a role-gated vendor dashboard, following existing `storefront/` and `pages/` conventions. No PostGIS: serviceability is point-in-radius in Python.

**Tech Stack:** Django 5 + DRF, SimpleJWT, Postgres (Neon), React 18 + MUI + react-hook-form + framer-motion, Django built-in test runner.

## Global Constraints

- Backend tests, `makemigrations`, and `check` run with `DJANGO_SETTINGS_MODULE=config.settings.test`, which uses a local in-memory SQLite database and is fully isolated from the Neon production DB. NEVER run `manage.py test` under `dev`/`prod` (they point at Neon). Commands may need `SECRET_KEY` only if unset; `test.py` provides a fallback.
- Money fields: `DecimalField(max_digits=10, decimal_places=2)`, currency BDT (৳).
- Lat/lng fields: `DecimalField(max_digits=9, decimal_places=6)`. No PostGIS.
- Every model has `AutoField` PK, `created_at = DateTimeField(auto_now_add=True)`, `updated_at = DateTimeField(auto_now=True)` — match existing apps.
- Localization: user-facing text models carry `<field>` (English) + `<field>_bn` (Bangla); resolver falls back to English when `_bn` is empty.
- New role choices added to `accounts.Users.role`: `("Restaurant","Restaurant")`, `("Rider","Rider")`.
- Response envelope: use `core.helpers.renderResponse(data, message, status)`. Pagination: `core.helpers.CustomPageNumberPagination`.
- API auth: JWT via `rest_framework_simplejwt`. Public endpoints use `permission_classes=[AllowAny]`.
- Backend tests live in a `food/tests/` package (`__init__.py` present), run with `python manage.py test food`.
- Do NOT commit automatically at the plan level — the product owner commits after testing. Each task's final step stages+commits ONLY if the owner has opted into auto-commit; otherwise stop at "run tests, report green." (Default: leave changes staged, do not commit.)

---

### Task 1: Create `food` app + add roles

**Files:**
- Create: `backend/EcommerceInventory/food/__init__.py`, `food/apps.py`, `food/models.py`, `food/admin.py`, `food/tests/__init__.py`
- Modify: `backend/EcommerceInventory/config/settings/base.py` (LOCAL_APPS)
- Modify: `backend/EcommerceInventory/accounts/models.py:96-108` (role choices)

**Interfaces:**
- Produces: installed app label `food`; `Users.role` accepts `"Restaurant"` and `"Rider"`.

- [ ] **Step 1: Create the app package**

`food/apps.py`:
```python
from django.apps import AppConfig


class FoodConfig(AppConfig):
    default_auto_field = "django.db.models.AutoField"
    name = "food"
```
`food/__init__.py`, `food/tests/__init__.py`: empty files. `food/models.py`, `food/admin.py`: empty for now.

- [ ] **Step 2: Register the app**

In `config/settings/base.py`, add `"food",` to `LOCAL_APPS` (after `"storefront"`).

- [ ] **Step 3: Add roles**

In `accounts/models.py`, extend the `role` `choices` tuple with:
```python
            ("Restaurant", "Restaurant"),
            ("Rider", "Rider"),
```

- [ ] **Step 4: Make migrations and verify apps load**

Run: `DJANGO_SETTINGS_MODULE=config.settings.test python manage.py makemigrations food accounts`
Expected: creates `accounts/migrations/000X_*` (role choices) and no-op/empty for food (no models yet).
Run: `DJANGO_SETTINGS_MODULE=config.settings.test python manage.py check`
Expected: `System check identified no issues`.

- [ ] **Step 5: Stage changes** (do not commit unless owner opted in)

```bash
git add backend/EcommerceInventory/food backend/EcommerceInventory/config/settings/base.py backend/EcommerceInventory/accounts
```

---

### Task 2: `DeliveryZone` model + serviceability helper

**Files:**
- Modify: `food/models.py`
- Create: `food/geo.py`
- Test: `food/tests/test_geo.py`

**Interfaces:**
- Produces:
  - `food.geo.haversine_km(lat1, lng1, lat2, lng2) -> float`
  - `DeliveryZone` model with `serves(lat, lng) -> bool`
  - `DeliveryZone.objects` fields: `name, name_bn, center_lat, center_lng, radius_km, is_active`

- [ ] **Step 1: Write the failing test**

`food/tests/test_geo.py`:
```python
from decimal import Decimal
from django.test import TestCase
from food.geo import haversine_km
from food.models import DeliveryZone


class HaversineTests(TestCase):
    def test_zero_distance(self):
        self.assertAlmostEqual(haversine_km(23.81, 90.41, 23.81, 90.41), 0.0, places=3)

    def test_known_distance(self):
        # ~1.11 km per 0.01 deg latitude near the equator/BD latitudes
        d = haversine_km(23.80, 90.40, 23.81, 90.40)
        self.assertAlmostEqual(d, 1.11, delta=0.05)


class DeliveryZoneServesTests(TestCase):
    def setUp(self):
        self.zone = DeliveryZone.objects.create(
            name="Test Upazila", name_bn="টেস্ট",
            center_lat=Decimal("23.8100"), center_lng=Decimal("90.4100"),
            radius_km=Decimal("3.0"), is_active=True,
        )

    def test_point_inside_radius_is_served(self):
        self.assertTrue(self.zone.serves(Decimal("23.8150"), Decimal("90.4150")))

    def test_point_outside_radius_not_served(self):
        self.assertFalse(self.zone.serves(Decimal("23.9000"), Decimal("90.5000")))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `DJANGO_SETTINGS_MODULE=config.settings.test python manage.py test food.tests.test_geo -v 2`
Expected: FAIL — `ImportError`/`cannot import name` (geo/model missing).

- [ ] **Step 3: Implement geo helper**

`food/geo.py`:
```python
import math


def haversine_km(lat1, lng1, lat2, lng2):
    """Great-circle distance in kilometers between two lat/lng points."""
    r = 6371.0
    p1, p2 = math.radians(float(lat1)), math.radians(float(lat2))
    dphi = math.radians(float(lat2) - float(lat1))
    dlmb = math.radians(float(lng2) - float(lng1))
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))
```

- [ ] **Step 4: Implement the model**

In `food/models.py`:
```python
from django.db import models
from food.geo import haversine_km


class TimeStamped(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class DeliveryZone(TimeStamped):
    name = models.CharField(max_length=120)
    name_bn = models.CharField(max_length=120, blank=True, default="")
    center_lat = models.DecimalField(max_digits=9, decimal_places=6)
    center_lng = models.DecimalField(max_digits=9, decimal_places=6)
    radius_km = models.DecimalField(max_digits=5, decimal_places=2, default=3)
    is_active = models.BooleanField(default=True)

    def serves(self, lat, lng):
        return haversine_km(self.center_lat, self.center_lng, lat, lng) <= float(self.radius_km)

    def __str__(self):
        return self.name
```

- [ ] **Step 5: Migrate and run tests**

Run: `DJANGO_SETTINGS_MODULE=config.settings.test python manage.py makemigrations food && DJANGO_SETTINGS_MODULE=config.settings.test python manage.py test food.tests.test_geo -v 2`
Expected: PASS (4 tests).

- [ ] **Step 6: Stage changes**

```bash
git add backend/EcommerceInventory/food
```

---

### Task 3: `Restaurant`, `RestaurantHours`, `RestaurantZone` + business logic

**Files:**
- Modify: `food/models.py`
- Test: `food/tests/test_restaurant.py`

**Interfaces:**
- Produces:
  - `Restaurant` fields: `owner, name, name_bn, slug, description, description_bn, logo, cover_image, cuisine_type, phone, address, pickup_lat, pickup_lng, commission_percentage, base_delivery_fee, avg_prep_minutes, min_order_amount, status, is_open`
  - `Restaurant.Status` choices: `PENDING, ACTIVE, SUSPENDED, REJECTED`
  - `Restaurant.is_currently_open(now) -> bool` (honors `is_open` AND `RestaurantHours`)
  - `Restaurant.payout_for(subtotal) -> Decimal` (subtotal minus commission)
  - `RestaurantHours` fields: `restaurant, weekday(0-6), open_time, close_time, is_closed`
  - `RestaurantZone` fields: `restaurant, zone, delivery_fee(nullable)`

- [ ] **Step 1: Write the failing test**

`food/tests/test_restaurant.py`:
```python
from decimal import Decimal
from datetime import time, datetime
from django.test import TestCase
from django.contrib.auth import get_user_model
from food.models import Restaurant, RestaurantHours

User = get_user_model()


class RestaurantLogicTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create(username="vendor1", role="Restaurant")
        self.r = Restaurant.objects.create(
            owner=self.owner, name="Rahim Hotel", slug="rahim-hotel",
            pickup_lat=Decimal("23.81"), pickup_lng=Decimal("90.41"),
            commission_percentage=Decimal("15.00"), base_delivery_fee=Decimal("30.00"),
            status=Restaurant.Status.ACTIVE, is_open=True,
        )

    def test_payout_subtracts_commission(self):
        # 15% commission on 1000 -> payout 850
        self.assertEqual(self.r.payout_for(Decimal("1000.00")), Decimal("850.00"))

    def test_closed_when_toggle_off(self):
        self.r.is_open = False
        self.assertFalse(self.r.is_currently_open(datetime(2026, 7, 20, 12, 0)))  # Monday noon

    def test_open_within_hours(self):
        # Monday = weekday 0 in our model
        RestaurantHours.objects.create(
            restaurant=self.r, weekday=0, open_time=time(9, 0), close_time=time(22, 0),
        )
        self.assertTrue(self.r.is_currently_open(datetime(2026, 7, 20, 12, 0)))

    def test_closed_outside_hours(self):
        RestaurantHours.objects.create(
            restaurant=self.r, weekday=0, open_time=time(9, 0), close_time=time(11, 0),
        )
        self.assertFalse(self.r.is_currently_open(datetime(2026, 7, 20, 12, 0)))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `DJANGO_SETTINGS_MODULE=config.settings.test python manage.py test food.tests.test_restaurant -v 2`
Expected: FAIL — `Restaurant`/`RestaurantHours` not defined.

- [ ] **Step 3: Implement models**

Append to `food/models.py`:
```python
from decimal import Decimal
from django.conf import settings


class Restaurant(TimeStamped):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        ACTIVE = "ACTIVE", "Active"
        SUSPENDED = "SUSPENDED", "Suspended"
        REJECTED = "REJECTED", "Rejected"

    owner = models.OneToOneField(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name="restaurant",
    )
    name = models.CharField(max_length=150)
    name_bn = models.CharField(max_length=150, blank=True, default="")
    slug = models.SlugField(max_length=170, unique=True)
    description = models.TextField(blank=True, default="")
    description_bn = models.TextField(blank=True, default="")
    logo = models.URLField(max_length=500, blank=True, default="")          # image URL (matches catalog's URL-based images)
    cover_image = models.URLField(max_length=500, blank=True, default="")
    cuisine_type = models.CharField(max_length=120, blank=True, default="")
    phone = models.CharField(max_length=20, blank=True, default="")
    address = models.CharField(max_length=255, blank=True, default="")
    pickup_lat = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    pickup_lng = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    commission_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("15.00"))
    base_delivery_fee = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    avg_prep_minutes = models.PositiveIntegerField(default=30)
    min_order_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    is_open = models.BooleanField(default=True)
    zones = models.ManyToManyField(DeliveryZone, through="RestaurantZone", related_name="restaurants")

    class Meta:
        indexes = [models.Index(fields=["slug"]), models.Index(fields=["status"])]

    def payout_for(self, subtotal):
        subtotal = Decimal(subtotal)
        return (subtotal * (Decimal("100") - self.commission_percentage) / Decimal("100")).quantize(Decimal("0.01"))

    def is_currently_open(self, now):
        if not self.is_open:
            return False
        hours = self.hours.filter(weekday=now.weekday(), is_closed=False)
        t = now.time()
        return any(h.open_time <= t <= h.close_time for h in hours)

    def __str__(self):
        return self.name


class RestaurantHours(TimeStamped):
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE, related_name="hours")
    weekday = models.PositiveSmallIntegerField()  # 0=Mon .. 6=Sun (datetime.weekday())
    open_time = models.TimeField()
    close_time = models.TimeField()
    is_closed = models.BooleanField(default=False)


class RestaurantZone(TimeStamped):
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE, related_name="restaurant_zones")
    zone = models.ForeignKey(DeliveryZone, on_delete=models.CASCADE, related_name="zone_restaurants")
    delivery_fee = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    class Meta:
        unique_together = ("restaurant", "zone")
```

> Images: the existing catalog stores images as URLs in `JSONField` (no Pillow, no local media — `MEDIA_ROOT` is ephemeral on Render). Follow that pattern: single images here are `URLField` holding an image URL. Do NOT use Django `ImageField` and do NOT add Pillow.

- [ ] **Step 4: Migrate and run tests**

Run: `DJANGO_SETTINGS_MODULE=config.settings.test python manage.py makemigrations food && DJANGO_SETTINGS_MODULE=config.settings.test python manage.py test food.tests.test_restaurant -v 2`
Expected: PASS (4 tests).

- [ ] **Step 5: Stage changes**

```bash
git add backend/EcommerceInventory/food backend/EcommerceInventory/requirements.txt
```

---

### Task 4: Menu models — `FoodCategory`, `FoodItem`, option groups/options

**Files:**
- Modify: `food/models.py`
- Test: `food/tests/test_menu.py`

**Interfaces:**
- Produces:
  - `FoodCategory` fields: `restaurant, name, name_bn, display_order, is_active`
  - `FoodItem` fields: `restaurant, category_id, name, name_bn, slug, description, description_bn, image, price, discount_price, prep_minutes, is_available, is_veg, spice_level, display_order`
  - `FoodItem.effective_price -> Decimal` (discount_price or price)
  - `FoodItemOptionGroup` fields: `item, name, name_bn, min_select, max_select, is_required`
  - `FoodItemOption` fields: `group, name, name_bn, price_delta, is_default, display_order`

- [ ] **Step 1: Write the failing test**

`food/tests/test_menu.py`:
```python
from decimal import Decimal
from django.test import TestCase
from food.models import Restaurant, FoodCategory, FoodItem


class MenuTests(TestCase):
    def setUp(self):
        self.r = Restaurant.objects.create(name="R", slug="r", status=Restaurant.Status.ACTIVE)
        self.c = FoodCategory.objects.create(restaurant=self.r, name="Rice", display_order=1)

    def test_effective_price_prefers_discount(self):
        item = FoodItem.objects.create(
            restaurant=self.r, category_id=self.c, name="Biriyani", slug="biriyani",
            price=Decimal("250.00"), discount_price=Decimal("200.00"),
        )
        self.assertEqual(item.effective_price, Decimal("200.00"))

    def test_effective_price_falls_back_to_price(self):
        item = FoodItem.objects.create(
            restaurant=self.r, category_id=self.c, name="Polao", slug="polao",
            price=Decimal("180.00"),
        )
        self.assertEqual(item.effective_price, Decimal("180.00"))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `DJANGO_SETTINGS_MODULE=config.settings.test python manage.py test food.tests.test_menu -v 2`
Expected: FAIL — models not defined.

- [ ] **Step 3: Implement models**

Append to `food/models.py`:
```python
class FoodCategory(TimeStamped):
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE, related_name="categories")
    name = models.CharField(max_length=120)
    name_bn = models.CharField(max_length=120, blank=True, default="")
    display_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        indexes = [models.Index(fields=["restaurant", "display_order"])]


class FoodItem(TimeStamped):
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE, related_name="items")
    category_id = models.ForeignKey(FoodCategory, on_delete=models.CASCADE, related_name="items")
    name = models.CharField(max_length=150)
    name_bn = models.CharField(max_length=150, blank=True, default="")
    slug = models.SlugField(max_length=170)
    description = models.TextField(blank=True, default="")
    description_bn = models.TextField(blank=True, default="")
    image = models.URLField(max_length=500, blank=True, default="")  # image URL (matches catalog pattern; no Pillow)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    discount_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    prep_minutes = models.PositiveIntegerField(null=True, blank=True)
    is_available = models.BooleanField(default=True)
    is_veg = models.BooleanField(default=False)
    spice_level = models.CharField(max_length=20, blank=True, default="")
    display_order = models.PositiveIntegerField(default=0)

    class Meta:
        indexes = [models.Index(fields=["restaurant", "is_available"])]
        constraints = [models.UniqueConstraint(fields=["restaurant", "slug"], name="uniq_item_slug_per_restaurant")]

    @property
    def effective_price(self):
        return self.discount_price if self.discount_price is not None else self.price


class FoodItemOptionGroup(TimeStamped):
    item = models.ForeignKey(FoodItem, on_delete=models.CASCADE, related_name="option_groups")
    name = models.CharField(max_length=120)
    name_bn = models.CharField(max_length=120, blank=True, default="")
    min_select = models.PositiveSmallIntegerField(default=0)
    max_select = models.PositiveSmallIntegerField(default=1)
    is_required = models.BooleanField(default=False)


class FoodItemOption(TimeStamped):
    group = models.ForeignKey(FoodItemOptionGroup, on_delete=models.CASCADE, related_name="options")
    name = models.CharField(max_length=120)
    name_bn = models.CharField(max_length=120, blank=True, default="")
    price_delta = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    is_default = models.BooleanField(default=False)
    display_order = models.PositiveIntegerField(default=0)
```

- [ ] **Step 4: Migrate and run tests**

Run: `DJANGO_SETTINGS_MODULE=config.settings.test python manage.py makemigrations food && DJANGO_SETTINGS_MODULE=config.settings.test python manage.py test food.tests.test_menu -v 2`
Expected: PASS (2 tests).

- [ ] **Step 5: Stage changes**

```bash
git add backend/EcommerceInventory/food
```

---

### Task 5: Serializers (localized, N+1-safe)

**Files:**
- Create: `food/serializers.py`
- Create: `food/i18n.py`
- Test: `food/tests/test_serializers.py`

**Interfaces:**
- Produces:
  - `food.i18n.localized(obj, field, lang) -> str` — returns `<field>_bn` when `lang=="bn"` and non-empty, else `<field>`.
  - `RestaurantListSerializer`, `RestaurantDetailSerializer`, `FoodCategorySerializer`, `FoodItemSerializer`, `FoodItemOptionGroupSerializer`, `DeliveryZoneSerializer`.
  - Each list/detail serializer accepts `context={"lang": "bn"|"en"}`.

- [ ] **Step 1: Write the failing test**

`food/tests/test_serializers.py`:
```python
from decimal import Decimal
from django.test import TestCase
from food.models import Restaurant, FoodCategory, FoodItem
from food.serializers import RestaurantDetailSerializer
from food.i18n import localized


class I18nTests(TestCase):
    def test_bn_fallback_to_en(self):
        r = Restaurant(name="Rahim", name_bn="")
        self.assertEqual(localized(r, "name", "bn"), "Rahim")

    def test_bn_used_when_present(self):
        r = Restaurant(name="Rahim", name_bn="রহিম")
        self.assertEqual(localized(r, "name", "bn"), "রহিম")


class RestaurantDetailSerializerTests(TestCase):
    def setUp(self):
        self.r = Restaurant.objects.create(name="Rahim", name_bn="রহিম", slug="rahim",
                                           status=Restaurant.Status.ACTIVE)
        c = FoodCategory.objects.create(restaurant=self.r, name="Rice")
        FoodItem.objects.create(restaurant=self.r, category_id=c, name="Biriyani",
                                slug="biriyani", price=Decimal("250"), is_available=True)
        FoodItem.objects.create(restaurant=self.r, category_id=c, name="Hidden",
                                slug="hidden", price=Decimal("100"), is_available=False)

    def test_detail_includes_only_available_items(self):
        data = RestaurantDetailSerializer(self.r, context={"lang": "en"}).data
        names = [i["name"] for cat in data["categories"] for i in cat["items"]]
        self.assertIn("Biriyani", names)
        self.assertNotIn("Hidden", names)

    def test_bn_name_rendered(self):
        data = RestaurantDetailSerializer(self.r, context={"lang": "bn"}).data
        self.assertEqual(data["name"], "রহিম")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `DJANGO_SETTINGS_MODULE=config.settings.test python manage.py test food.tests.test_serializers -v 2`
Expected: FAIL — module missing.

- [ ] **Step 3: Implement i18n helper**

`food/i18n.py`:
```python
def localized(obj, field, lang):
    if lang == "bn":
        val = getattr(obj, f"{field}_bn", "") or ""
        if val:
            return val
    return getattr(obj, field, "")
```

- [ ] **Step 4: Implement serializers**

`food/serializers.py`:
```python
from rest_framework import serializers
from food.models import (
    Restaurant, FoodCategory, FoodItem, FoodItemOptionGroup, FoodItemOption, DeliveryZone,
)
from food.i18n import localized


class _LangMixin:
    @property
    def lang(self):
        return self.context.get("lang", "en")


class DeliveryZoneSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeliveryZone
        fields = ["id", "name", "name_bn", "center_lat", "center_lng", "radius_km", "is_active"]


class FoodItemOptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = FoodItemOption
        fields = ["id", "name", "name_bn", "price_delta", "is_default", "display_order"]


class FoodItemOptionGroupSerializer(serializers.ModelSerializer):
    options = FoodItemOptionSerializer(many=True, read_only=True)

    class Meta:
        model = FoodItemOptionGroup
        fields = ["id", "name", "name_bn", "min_select", "max_select", "is_required", "options"]


class FoodItemSerializer(_LangMixin, serializers.ModelSerializer):
    display_name = serializers.SerializerMethodField()
    effective_price = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    option_groups = FoodItemOptionGroupSerializer(many=True, read_only=True)

    class Meta:
        model = FoodItem
        fields = ["id", "name", "name_bn", "display_name", "slug", "description", "description_bn",
                  "image", "price", "discount_price", "effective_price", "prep_minutes",
                  "is_available", "is_veg", "spice_level", "display_order", "option_groups"]

    def get_display_name(self, obj):
        return localized(obj, "name", self.lang)


class FoodCategorySerializer(_LangMixin, serializers.ModelSerializer):
    items = serializers.SerializerMethodField()

    class Meta:
        model = FoodCategory
        fields = ["id", "name", "name_bn", "display_order", "items"]

    def get_items(self, obj):
        # obj.items prefetched+filtered in the view; filter available in python to keep it 0-query
        items = [i for i in obj.items.all() if i.is_available]
        return FoodItemSerializer(items, many=True, context=self.context).data


class RestaurantListSerializer(_LangMixin, serializers.ModelSerializer):
    display_name = serializers.SerializerMethodField()

    class Meta:
        model = Restaurant
        fields = ["id", "name", "name_bn", "display_name", "slug", "logo", "cover_image",
                  "cuisine_type", "base_delivery_fee", "avg_prep_minutes", "min_order_amount",
                  "is_open", "status"]

    def get_display_name(self, obj):
        return localized(obj, "name", self.lang)


class RestaurantDetailSerializer(RestaurantListSerializer):
    categories = serializers.SerializerMethodField()

    class Meta(RestaurantListSerializer.Meta):
        fields = RestaurantListSerializer.Meta.fields + ["description", "description_bn",
                 "address", "phone", "pickup_lat", "pickup_lng", "categories"]

    def get_categories(self, obj):
        cats = [c for c in obj.categories.all() if c.is_active]
        return FoodCategorySerializer(cats, many=True, context=self.context).data
```

- [ ] **Step 5: Run tests**

Run: `DJANGO_SETTINGS_MODULE=config.settings.test python manage.py test food.tests.test_serializers -v 2`
Expected: PASS (4 tests).

- [ ] **Step 6: Stage changes**

```bash
git add backend/EcommerceInventory/food
```

---

### Task 6: Public read API + N+1 guard

**Files:**
- Create: `food/views_public.py`
- Create: `food/urls.py`
- Modify: `config/urls.py` (include `food.urls` under `api/food/`)
- Test: `food/tests/test_public_api.py`

**Interfaces:**
- Consumes: serializers from Task 5.
- Produces: routes `GET /api/food/restaurants/`, `GET /api/food/restaurants/<slug>/`, `GET /api/food/zones/`.
- Detail view prefetches `categories -> items -> option_groups -> options` so serialization is query-bounded.

- [ ] **Step 1: Write the failing test**

`food/tests/test_public_api.py`:
```python
from decimal import Decimal
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from food.models import Restaurant, FoodCategory, FoodItem


class PublicApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.active = Restaurant.objects.create(name="Active", slug="active", status=Restaurant.Status.ACTIVE)
        self.pending = Restaurant.objects.create(name="Pending", slug="pending", status=Restaurant.Status.PENDING)
        c = FoodCategory.objects.create(restaurant=self.active, name="Rice")
        for i in range(5):
            FoodItem.objects.create(restaurant=self.active, category_id=c, name=f"Item{i}",
                                    slug=f"item{i}", price=Decimal("100"), is_available=True)

    def test_list_hides_non_active(self):
        res = self.client.get("/api/food/restaurants/")
        self.assertEqual(res.status_code, 200)
        slugs = [r["slug"] for r in res.json()["data"]["data"]]
        self.assertIn("active", slugs)
        self.assertNotIn("pending", slugs)

    def test_detail_is_query_bounded(self):
        # Detail must not scale queries with item count (no N+1).
        with self.assertNumQueries(4):
            self.client.get("/api/food/restaurants/active/")
```

> The exact number in `assertNumQueries` may need adjusting to the real bounded count after implementing prefetch; pick the observed constant and assert it stays constant when items grow (add a second restaurant with 20 items and assert equal query count).

- [ ] **Step 2: Run test to verify it fails**

Run: `DJANGO_SETTINGS_MODULE=config.settings.test python manage.py test food.tests.test_public_api -v 2`
Expected: FAIL — 404/route missing.

- [ ] **Step 3: Implement views**

`food/views_public.py`:
```python
from django.db.models import Prefetch
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView
from rest_framework.generics import ListAPIView
from core.helpers import renderResponse, CustomPageNumberPagination
from food.models import Restaurant, FoodCategory, FoodItem, FoodItemOptionGroup, DeliveryZone
from food.serializers import RestaurantListSerializer, RestaurantDetailSerializer, DeliveryZoneSerializer


def _lang(request):
    return "bn" if request.GET.get("lang") == "bn" else "en"


class PublicRestaurantListView(ListAPIView):
    permission_classes = [AllowAny]
    serializer_class = RestaurantListSerializer
    pagination_class = CustomPageNumberPagination

    def get_queryset(self):
        qs = Restaurant.objects.filter(status=Restaurant.Status.ACTIVE)
        zone = self.request.GET.get("zone")
        if zone:
            qs = qs.filter(zones__id=zone).distinct()
        search = self.request.GET.get("search")
        if search:
            qs = qs.filter(name__icontains=search)
        cuisine = self.request.GET.get("cuisine")
        if cuisine:
            qs = qs.filter(cuisine_type__icontains=cuisine)
        return qs.order_by("name")

    def get_serializer_context(self):
        return {"lang": _lang(self.request)}


def _detail_prefetch():
    opt_groups = Prefetch(
        "option_groups",
        queryset=FoodItemOptionGroup.objects.prefetch_related("options"),
    )
    items = Prefetch("items", queryset=FoodItem.objects.prefetch_related(opt_groups))
    cats = Prefetch("categories", queryset=FoodCategory.objects.prefetch_related(items))
    return cats


class PublicRestaurantDetailView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, slug):
        restaurant = (
            Restaurant.objects.filter(status=Restaurant.Status.ACTIVE, slug=slug)
            .prefetch_related(_detail_prefetch())
            .first()
        )
        if not restaurant:
            return renderResponse(data={}, message="Restaurant not found", status=404)
        data = RestaurantDetailSerializer(restaurant, context={"lang": _lang(request)}).data
        return renderResponse(data=data, message="Restaurant detail")


class PublicZoneListView(ListAPIView):
    permission_classes = [AllowAny]
    serializer_class = DeliveryZoneSerializer
    pagination_class = None

    def get_queryset(self):
        return DeliveryZone.objects.filter(is_active=True).order_by("name")
```

`food/urls.py`:
```python
from django.urls import path
from food.views_public import (
    PublicRestaurantListView, PublicRestaurantDetailView, PublicZoneListView,
)

urlpatterns = [
    path("restaurants/", PublicRestaurantListView.as_view(), name="food_restaurants"),
    path("restaurants/<slug:slug>/", PublicRestaurantDetailView.as_view(), name="food_restaurant_detail"),
    path("zones/", PublicZoneListView.as_view(), name="food_zones"),
]
```

In `config/urls.py`, add under the existing `api/` includes: `path("api/food/", include("food.urls")),`.

> Ensure `/api/food/` is covered by the storefront-style public bypass. `core/middleware.py` `PUBLIC_API_PREFIXES` gates only `/api/store/` and auth — **add `/api/food/`** to `PUBLIC_API_PREFIXES` so public GETs are not forced through the JWT gate. Do this in this task.

- [ ] **Step 4: Run tests, then tune the query-count assertion**

Run: `DJANGO_SETTINGS_MODULE=config.settings.test python manage.py test food.tests.test_public_api -v 2`
If `assertNumQueries(4)` mismatches, read the reported actual count, set it, and add the "20 items → same count" invariant test. Re-run: Expected PASS.

- [ ] **Step 5: Stage changes**

```bash
git add backend/EcommerceInventory/food backend/EcommerceInventory/config/urls.py backend/EcommerceInventory/core/middleware.py
```

---

### Task 7: Vendor API (owner-scoped menu CRUD)

**Files:**
- Create: `food/permissions.py`
- Create: `food/views_vendor.py`
- Create: `food/serializers_write.py`
- Modify: `food/urls.py`
- Test: `food/tests/test_vendor_api.py`

**Interfaces:**
- Consumes: models (Tasks 3–4), JWT auth.
- Produces:
  - `food.permissions.IsRestaurantOwner` (role == "Restaurant" and has `restaurant`).
  - Routes under `/api/food/vendor/`: `GET/PATCH restaurant/`, CRUD `categories/`, `items/`, `items/<id>/options-groups/`.
  - Write serializers: `FoodCategoryWriteSerializer`, `FoodItemWriteSerializer`.
- Guarantees: a vendor can only read/write objects belonging to their own restaurant (else 403/404).

- [ ] **Step 1: Write the failing test**

`food/tests/test_vendor_api.py`:
```python
from decimal import Decimal
from django.test import TestCase
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import RefreshToken
from food.models import Restaurant, FoodCategory

User = get_user_model()


def auth(client, user):
    token = str(RefreshToken.for_user(user).access_token)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")


class VendorScopingTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.owner_a = User.objects.create(username="a", role="Restaurant")
        self.owner_b = User.objects.create(username="b", role="Restaurant")
        self.ra = Restaurant.objects.create(owner=self.owner_a, name="A", slug="a")
        self.rb = Restaurant.objects.create(owner=self.owner_b, name="B", slug="b")
        self.cat_b = FoodCategory.objects.create(restaurant=self.rb, name="B-cat")

    def test_vendor_lists_only_own_categories(self):
        FoodCategory.objects.create(restaurant=self.ra, name="A-cat")
        auth(self.client, self.owner_a)
        res = self.client.get("/api/food/vendor/categories/")
        names = [c["name"] for c in res.json()["data"]]
        self.assertEqual(names, ["A-cat"])

    def test_vendor_cannot_edit_others_category(self):
        auth(self.client, self.owner_a)
        res = self.client.patch(f"/api/food/vendor/categories/{self.cat_b.id}/",
                                {"name": "hacked"}, format="json")
        self.assertIn(res.status_code, (403, 404))
        self.cat_b.refresh_from_db()
        self.assertEqual(self.cat_b.name, "B-cat")

    def test_non_restaurant_role_blocked(self):
        customer = User.objects.create(username="c", role="Customer")
        auth(self.client, customer)
        res = self.client.get("/api/food/vendor/categories/")
        self.assertEqual(res.status_code, 403)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `DJANGO_SETTINGS_MODULE=config.settings.test python manage.py test food.tests.test_vendor_api -v 2`
Expected: FAIL — routes/permission missing.

- [ ] **Step 3: Implement permission + write serializers + views**

`food/permissions.py`:
```python
from rest_framework.permissions import BasePermission


class IsRestaurantOwner(BasePermission):
    message = "Restaurant account required."

    def has_permission(self, request, view):
        u = request.user
        return bool(u and u.is_authenticated and u.role == "Restaurant" and getattr(u, "restaurant", None))
```

`food/serializers_write.py`:
```python
from rest_framework import serializers
from food.models import FoodCategory, FoodItem, FoodItemOptionGroup, FoodItemOption


class FoodCategoryWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = FoodCategory
        fields = ["id", "name", "name_bn", "display_order", "is_active"]


class FoodItemWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = FoodItem
        fields = ["id", "category_id", "name", "name_bn", "slug", "description", "description_bn",
                  "image", "price", "discount_price", "prep_minutes", "is_available",
                  "is_veg", "spice_level", "display_order"]
```

`food/views_vendor.py`:
```python
from rest_framework.viewsets import ModelViewSet
from rest_framework.permissions import IsAuthenticated
from food.models import FoodCategory, FoodItem
from food.permissions import IsRestaurantOwner
from food.serializers_write import FoodCategoryWriteSerializer, FoodItemWriteSerializer


class VendorCategoryViewSet(ModelViewSet):
    permission_classes = [IsAuthenticated, IsRestaurantOwner]
    serializer_class = FoodCategoryWriteSerializer
    pagination_class = None

    def get_queryset(self):
        return FoodCategory.objects.filter(restaurant=self.request.user.restaurant).order_by("display_order")

    def perform_create(self, serializer):
        serializer.save(restaurant=self.request.user.restaurant)


class VendorItemViewSet(ModelViewSet):
    permission_classes = [IsAuthenticated, IsRestaurantOwner]
    serializer_class = FoodItemWriteSerializer
    pagination_class = None

    def get_queryset(self):
        return FoodItem.objects.filter(restaurant=self.request.user.restaurant).order_by("display_order")

    def perform_create(self, serializer):
        # category must belong to this restaurant
        category = serializer.validated_data.get("category_id")
        if category and category.restaurant_id != self.request.user.restaurant.id:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Category does not belong to your restaurant.")
        serializer.save(restaurant=self.request.user.restaurant)
```

Wire routes in `food/urls.py` using a DRF router:
```python
from rest_framework.routers import DefaultRouter
from food.views_vendor import VendorCategoryViewSet, VendorItemViewSet

router = DefaultRouter()
router.register("vendor/categories", VendorCategoryViewSet, basename="vendor-categories")
router.register("vendor/items", VendorItemViewSet, basename="vendor-items")

urlpatterns += router.urls
```
(Add `urlpatterns += router.urls` at the end of the existing `urlpatterns` list.)

> `IsRestaurantOwner` returning `False` yields DRF 403 for authenticated non-owners — satisfies `test_non_restaurant_role_blocked`. For a vendor hitting another restaurant's object, `get_queryset` scoping yields 404 — satisfies the edit-guard test.

- [ ] **Step 4: Run tests**

Run: `DJANGO_SETTINGS_MODULE=config.settings.test python manage.py test food.tests.test_vendor_api -v 2`
Expected: PASS (3 tests).

- [ ] **Step 5: Stage changes**

```bash
git add backend/EcommerceInventory/food
```

---

### Task 8: Admin API (approve/suspend/commission, zones CRUD)

**Files:**
- Create: `food/views_admin.py`
- Create: `food/serializers_admin.py`
- Modify: `food/urls.py`
- Test: `food/tests/test_admin_api.py`

**Interfaces:**
- Produces:
  - Routes under `/api/food/admin/`: CRUD `restaurants/`, `POST restaurants/<id>/approve/`, `POST restaurants/<id>/suspend/`, CRUD `zones/`.
  - `RestaurantAdminSerializer` (all fields incl. `commission_percentage`, `status`).
- Guarantees: only `Admin`/`Super Admin` roles reach these (via existing `PermissionMiddleware` + registered modules); the tests authenticate an Admin user directly and assert transitions.

- [ ] **Step 1: Write the failing test**

`food/tests/test_admin_api.py`:
```python
from django.test import TestCase
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import RefreshToken
from food.models import Restaurant

User = get_user_model()


class AdminApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = User.objects.create(username="admin1", role="Super Admin")
        token = str(RefreshToken.for_user(self.admin).access_token)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        self.r = Restaurant.objects.create(name="Pending Co", slug="pending-co",
                                           status=Restaurant.Status.PENDING)

    def test_approve_sets_active(self):
        res = self.client.post(f"/api/food/admin/restaurants/{self.r.id}/approve/")
        self.assertEqual(res.status_code, 200)
        self.r.refresh_from_db()
        self.assertEqual(self.r.status, Restaurant.Status.ACTIVE)

    def test_suspend_sets_suspended(self):
        res = self.client.post(f"/api/food/admin/restaurants/{self.r.id}/suspend/")
        self.assertEqual(res.status_code, 200)
        self.r.refresh_from_db()
        self.assertEqual(self.r.status, Restaurant.Status.SUSPENDED)
```

> Note: because `core/middleware.PermissionMiddleware` gates `/api/` non-public paths, the test Admin must either be `Super Admin` (bypasses module checks in the middleware) or have module permissions seeded. Using `Super Admin` keeps the test focused on the view logic. Confirm `/api/food/admin/` is NOT in `PUBLIC_API_PREFIXES`.

- [ ] **Step 2: Run test to verify it fails**

Run: `DJANGO_SETTINGS_MODULE=config.settings.test python manage.py test food.tests.test_admin_api -v 2`
Expected: FAIL — route missing.

- [ ] **Step 3: Implement serializer + views**

`food/serializers_admin.py`:
```python
from rest_framework import serializers
from food.models import Restaurant, DeliveryZone


class RestaurantAdminSerializer(serializers.ModelSerializer):
    class Meta:
        model = Restaurant
        fields = "__all__"


class DeliveryZoneAdminSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeliveryZone
        fields = "__all__"
```

`food/views_admin.py`:
```python
from rest_framework.viewsets import ModelViewSet
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from core.helpers import renderResponse
from food.models import Restaurant, DeliveryZone
from food.serializers_admin import RestaurantAdminSerializer, DeliveryZoneAdminSerializer


class AdminRestaurantViewSet(ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = RestaurantAdminSerializer
    queryset = Restaurant.objects.all().order_by("-created_at")

    def _set_status(self, pk, status):
        r = self.get_object()
        r.status = status
        r.save(update_fields=["status", "updated_at"])
        return renderResponse(data=RestaurantAdminSerializer(r).data, message=f"Restaurant {status.lower()}")

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        return self._set_status(pk, Restaurant.Status.ACTIVE)

    @action(detail=True, methods=["post"])
    def suspend(self, request, pk=None):
        return self._set_status(pk, Restaurant.Status.SUSPENDED)


class AdminZoneViewSet(ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = DeliveryZoneAdminSerializer
    queryset = DeliveryZone.objects.all().order_by("name")
```

Wire in `food/urls.py`:
```python
from food.views_admin import AdminRestaurantViewSet, AdminZoneViewSet
router.register("admin/restaurants", AdminRestaurantViewSet, basename="admin-restaurants")
router.register("admin/zones", AdminZoneViewSet, basename="admin-zones")
```

- [ ] **Step 4: Run tests**

Run: `DJANGO_SETTINGS_MODULE=config.settings.test python manage.py test food.tests.test_admin_api -v 2`
Expected: PASS (2 tests).

- [ ] **Step 5: Stage changes**

```bash
git add backend/EcommerceInventory/food
```

---

### Task 9: `seed_food_modules` command (register Food admin menu)

**Files:**
- Create: `food/management/__init__.py`, `food/management/commands/__init__.py`, `food/management/commands/seed_food_modules.py`
- Test: `food/tests/test_seed_modules.py`

**Interfaces:**
- Consumes: `accounts.models.Modules`.
- Produces: a top-level "Food" module with children (Restaurants `/manage/food/restaurants`, Delivery Zones `/manage/food/zones`), idempotent.

- [ ] **Step 1: Write the failing test**

`food/tests/test_seed_modules.py`:
```python
from django.test import TestCase
from django.core.management import call_command
from accounts.models import Modules


class SeedFoodModulesTests(TestCase):
    def test_idempotent_and_creates_food_menu(self):
        call_command("seed_food_modules")
        call_command("seed_food_modules")  # run twice — must not duplicate
        self.assertEqual(Modules.objects.filter(module_name="Food").count(), 1)
        self.assertTrue(Modules.objects.filter(module_url="/manage/food/restaurants").exists())
```

- [ ] **Step 2: Run test to verify it fails**

Run: `DJANGO_SETTINGS_MODULE=config.settings.test python manage.py test food.tests.test_seed_modules -v 2`
Expected: FAIL — unknown command `seed_food_modules`.

- [ ] **Step 3: Implement command (mirror `seed_admin_modules` shape)**

First inspect `accounts/management/commands/seed_admin_modules.py` to copy the exact `Modules` field names and parent-linking approach. Then `food/management/commands/seed_food_modules.py`:
```python
from django.core.management.base import BaseCommand
from accounts.models import Modules

MODULES = [
    {"module_name": "Food", "module_icon": "Restaurant", "module_url": None, "display_order": 5, "parent": None},
    {"module_name": "Restaurants", "module_icon": "Storefront", "module_url": "/manage/food/restaurants", "display_order": 1, "parent": "Food"},
    {"module_name": "Delivery Zones", "module_icon": "Map", "module_url": "/manage/food/zones", "display_order": 2, "parent": "Food"},
]


class Command(BaseCommand):
    help = "Register Food admin-panel modules (idempotent)."

    def handle(self, *args, **options):
        name_to_obj = {}
        for m in MODULES:
            parent = name_to_obj.get(m["parent"]) if m["parent"] else None
            obj, _ = Modules.objects.get_or_create(
                module_name=m["module_name"],
                defaults={
                    "module_icon": m["module_icon"],
                    "module_url": m["module_url"],
                    "display_order": m["display_order"],
                    "parent": parent,
                },
            )
            name_to_obj[m["module_name"]] = obj
        self.stdout.write(self.style.SUCCESS("Food modules seeded."))
```
> Adjust field names (`parent` vs `parent_id`, etc.) to match the real `Modules` model after inspecting it.

- [ ] **Step 4: Run tests**

Run: `DJANGO_SETTINGS_MODULE=config.settings.test python manage.py test food.tests.test_seed_modules -v 2`
Expected: PASS.

- [ ] **Step 5: Add to build.sh so prod registers modules on deploy**

In `backend/EcommerceInventory/build.sh`, after `python manage.py seed_demo`, add:
```bash
python manage.py seed_food_modules
```

- [ ] **Step 6: Full backend test run + stage**

Run: `DJANGO_SETTINGS_MODULE=config.settings.test python manage.py test food -v 2`
Expected: ALL pass.
```bash
git add backend/EcommerceInventory/food backend/EcommerceInventory/build.sh
```

---

### Task 10: Frontend — Food admin pages (Restaurants + Zones)

**Files:**
- Create: `frontend/ecommerce_inventory/src/pages/food/ManageRestaurants.js`
- Create: `frontend/ecommerce_inventory/src/pages/food/ManageZones.js`
- Modify: `frontend/ecommerce_inventory/src/App.js` (routes `/manage/food/restaurants`, `/manage/food/zones`)
- Test: `frontend/ecommerce_inventory/src/pages/food/ManageRestaurants.test.js`

**Interfaces:**
- Consumes: admin API `/api/food/admin/restaurants/`, `/api/food/admin/zones/` via the existing `useApi` hook (`src/hooks/APIHandler`).
- Follows the structure of an existing admin list page (inspect `src/pages/products/` and `src/pages/category/` first and mirror table + dialog patterns).

- [ ] **Step 1: Inspect the existing admin list pattern**

Read `src/pages/category/` (or `ManageUsers.js`) to copy the MUI table + `useApi` + pagination + edit-dialog conventions. Do not invent a new pattern.

- [ ] **Step 2: Write a render smoke test**

`src/pages/food/ManageRestaurants.test.js`:
```javascript
import { render, screen } from '@testing-library/react';
import ManageRestaurants from './ManageRestaurants';

jest.mock('../../hooks/APIHandler', () => () => ({
  callApi: jest.fn().mockResolvedValue({ data: { data: { data: [], totalPages: 1 } } }),
  loading: false,
}));

test('renders restaurants heading', async () => {
  render(<ManageRestaurants />);
  expect(await screen.findByText(/Restaurants/i)).toBeInTheDocument();
});
```

- [ ] **Step 3: Run test to verify it fails**

Run (from `frontend/ecommerce_inventory`): `CI=true npx react-scripts test --watchAll=false src/pages/food/ManageRestaurants.test.js`
Expected: FAIL — component missing.

- [ ] **Step 4: Implement `ManageRestaurants.js`**

Build a page that: fetches `admin/restaurants/`, renders a MUI table (name, status, commission, delivery fee), with row actions **Approve** (`POST admin/restaurants/<id>/approve/`), **Suspend** (`POST admin/restaurants/<id>/suspend/`), and an edit dialog to set `commission_percentage`/`base_delivery_fee`. Use `useApi`, MUI `Table`, `Chip` for status, `toast` for feedback — mirroring the pattern from Step 1. Heading text must include "Restaurants".

- [ ] **Step 5: Implement `ManageZones.js`**

CRUD page for `admin/zones/`: table (name, center lat/lng, radius, active) + create/edit dialog (react-hook-form fields: `name`, `name_bn`, `center_lat`, `center_lng`, `radius_km`, `is_active`).

- [ ] **Step 6: Wire routes**

In `src/App.js`, add protected admin routes (mirroring existing `/manage/*` routes) for `/manage/food/restaurants` → `ManageRestaurants` and `/manage/food/zones` → `ManageZones`.

- [ ] **Step 7: Run test + build**

Run: `CI=true npx react-scripts test --watchAll=false src/pages/food/ManageRestaurants.test.js` → PASS.
Run: `CI=false npm run build` → build succeeds.

- [ ] **Step 8: Stage changes**

```bash
git add frontend/ecommerce_inventory/src/pages/food frontend/ecommerce_inventory/src/App.js
```

---

### Task 11: Frontend — Vendor dashboard (profile + menu builder)

**Files:**
- Create: `frontend/ecommerce_inventory/src/vendor/VendorLayout.js`
- Create: `frontend/ecommerce_inventory/src/vendor/VendorRestaurant.js` (profile + hours + open toggle)
- Create: `frontend/ecommerce_inventory/src/vendor/VendorMenu.js` (categories + items + options)
- Modify: `frontend/ecommerce_inventory/src/App.js` (route group `/vendor/*`, gated to role `Restaurant`)
- Test: `frontend/ecommerce_inventory/src/vendor/VendorMenu.test.js`

**Interfaces:**
- Consumes: `/api/food/vendor/restaurant/`, `/api/food/vendor/categories/`, `/api/food/vendor/items/` via `useApi`.
- Role gate: reuse however the app currently distinguishes logged-in roles (inspect `App.js` + `CustomerAuth`/auth flow first); vendors are redirected to `/vendor` after login.

- [ ] **Step 1: Inspect current auth/role routing** — read `src/App.js` and the auth handling to learn how role-based redirects and protected routes are done today. Mirror it.

- [ ] **Step 2: Write a smoke test** for `VendorMenu` (mock `useApi` returning empty categories; assert an "Add Category" control renders). Same mock pattern as Task 10 Step 2.

- [ ] **Step 3: Run test → FAIL.**

Run: `CI=true npx react-scripts test --watchAll=false src/vendor/VendorMenu.test.js`

- [ ] **Step 4: Implement `VendorRestaurant.js`** — load `vendor/restaurant/`, form (react-hook-form) for profile fields + `is_open` switch + weekly hours editor; PATCH on save; mobile-first, lightweight layout.

- [ ] **Step 5: Implement `VendorMenu.js`** — categories list with add/edit; per category, items list with add/edit dialog (name, name_bn, price, discount_price, image upload, is_available); option groups per item. All calls scoped to vendor endpoints. Use `FormData` for image upload (mirror existing product image upload).

- [ ] **Step 6: Implement `VendorLayout.js` + routes** — a slim sidebar/topbar for vendors; add `/vendor`, `/vendor/menu` routes gated to role `Restaurant` in `App.js`.

- [ ] **Step 7: Run test + build → PASS + build succeeds.**

- [ ] **Step 8: Stage changes**

```bash
git add frontend/ecommerce_inventory/src/vendor frontend/ecommerce_inventory/src/App.js
```

---

### Task 12: Frontend — animated "Food" header entry + placeholder

**Files:**
- Modify: the storefront header/nav component (inspect `src/storefront/components/MegaMenu.js` and the storefront layout to find where nav links render)
- Create: `frontend/ecommerce_inventory/src/storefront/pages/FoodComingSoon.js`
- Modify: `frontend/ecommerce_inventory/src/App.js` (route `/food`)
- Test: `frontend/ecommerce_inventory/src/storefront/pages/FoodComingSoon.test.js`

**Interfaces:**
- Produces: an animated, highlighted "Food" link in the storefront header routing to `/food`.
- Phase 1 `/food` shows a "coming to your area" page listing `ACTIVE` restaurants (from `/api/food/restaurants/`) — a stub for the full Phase 2 browse.

- [ ] **Step 1: Locate the header nav** — read the storefront layout/header to find where top-level nav items render; identify the insertion point.

- [ ] **Step 2: Write a smoke test** for `FoodComingSoon` (mock `useApi` → empty list; assert heading "Food" renders). Same mock pattern as before.

- [ ] **Step 3: Run test → FAIL.**

- [ ] **Step 4: Implement `FoodComingSoon.js`** — fetch `/api/food/restaurants/`, show a hero ("Food delivery is coming to your community") + a grid of active restaurants (name, logo, cuisine) or an empty-state message. Lightweight, image-lazy.

- [ ] **Step 5: Add the animated header link** — insert a "Food" nav item using the existing `framer-motion` dependency: a subtle pulse/gradient highlight (e.g., `animate={{ scale: [1, 1.06, 1] }}` on a `motion.span` with `transition={{ repeat: Infinity, duration: 2 }}`), linking to `/food`. Keep it cheap (transform-only animation) for low-end devices.

- [ ] **Step 6: Wire the `/food` route** in `App.js` (public storefront route).

- [ ] **Step 7: Run test + build → PASS + build succeeds.**

- [ ] **Step 8: Final Phase 0+1 verification**

Run backend: `DJANGO_SETTINGS_MODULE=config.settings.test python manage.py test food -v 2` → all pass.
Run frontend: `CI=false npm run build` → succeeds.
Manually (optional): start backend + frontend, seed a zone + restaurant, approve it, build a menu as a vendor, confirm it appears at `/food` and `/api/food/restaurants/`.

- [ ] **Step 9: Stage changes**

```bash
git add frontend/ecommerce_inventory/src
```

---

## Self-Review Notes (author)

- **Spec coverage:** roles (Task 1) ✓; zones + serviceability (Task 2) ✓; restaurant + hours + commission/payout (Task 3) ✓; menu + options (Task 4) ✓; localized N+1-safe serializers (Tasks 5–6) ✓; vendor owner-scoping (Task 7) ✓; admin approve/suspend/commission/zones (Task 8) ✓; module registration + build.sh (Task 9) ✓; admin pages (10) ✓; vendor dashboard (11) ✓; animated Food header + placeholder (12) ✓. Payments/dispatch/GPS are later phases, intentionally out of this plan.
- **Localization** carried through models (`_bn`) and serializers (`localized`).
- **Low-bandwidth mission** reflected in lazy images + lightweight vendor/customer screens (Tasks 11–12).
- **N+1 discipline** enforced by an explicit query-count invariant test (Task 6), mirroring the storefront homepage fix.
- **Deferred/assumption:** vendor signup is invite-only for v1 (admin creates the `Restaurant` + owner). Self-serve vendor signup is not built here — revisit before Phase 2 if needed.
```
