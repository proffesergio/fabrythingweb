# Food Customer Delivery UI + COD Ordering — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship the customer-facing Food Delivery experience — a fully separate themed `/food` app where a guest can browse restaurants, build a single-restaurant cart, and place a COD order that a vendor/admin can drive to "delivered" — plus fix the empty admin product list.

**Architecture:** Backend adds `FoodOrder`/`FoodOrderItem` to the existing `food` Django app with a server-authoritative placement service (`place_food_cod_order`) mirroring `orders.services.place_cod_order`, exposed via customer/vendor/admin endpoints in the existing `renderResponse` envelope. Frontend mounts a new `/food/*` route tree outside the storefront wrapper with its own MUI theme, layout, and an independent Redux `foodCart` slice.

**Tech Stack:** Django REST Framework, SimpleJWT, Postgres (Neon), React 18 + MUI 5, Redux Toolkit, react-router-dom v6, axios (via `useApi`), Jest + React Testing Library.

## Global Constraints

- Money: `DecimalField(max_digits=10, decimal_places=2)`, currency BDT (৳). Server recomputes all order totals; client amounts are never trusted.
- All API responses use `core.helpers.renderResponse(data=..., message=..., status=...)` — the `{"data", "message"}` envelope.
- Authenticated DRF views MUST set `authentication_classes = [JWTAuthentication]` explicitly (no global default configured).
- `/api/food/` is in `core.middleware.PUBLIC_API_PREFIXES`, so food admin endpoints are NOT gated by PermissionMiddleware — they MUST carry `IsPlatformAdmin`; vendor endpoints MUST carry `IsRestaurantOwner`.
- Localization: expose `display_name` via `food.i18n.localized(obj, "name", lang)`, `lang = "bn"` only when `?lang=bn`, English fallback.
- Backend tests: Django `TestCase` + `rest_framework.test.APIClient`; authenticate with `RefreshToken.for_user(user).access_token` (see `food/tests/test_vendor_api.py::auth`). Run with the isolated sqlite settings used by the repo.
- Frontend: reuse `hooks/APIHandler.js` (`useApi`), MUI, react-hook-form where forms exist. New food code lives under `src/food/`.
- One restaurant per food cart. COD only. Guest checkout allowed (name + phone + address).
- Commit after every task. Do NOT push/merge — the human does that manually.

---

## Test-running reference

- Backend (from `backend/EcommerceInventory/`): `python manage.py test food --settings=EcommerceInventory.test_settings -v 2`
  (confirm the settings module name from `be31668`/existing test runs; `backend/EcommerceInventory/EcommerceInventory/test_settings.py` is the isolated sqlite config.)
- Single test: append `food.tests.test_orders.OrderPlacementTests.test_name`.
- Frontend (from `frontend/ecommerce_inventory/`): `CI=true npx react-scripts test src/food --watchAll=false`

---

## Task 1: Fix empty admin product list (seeded product ownership + null-safe serializer)

**Files:**
- Modify: `backend/EcommerceInventory/catalog/controllers/ProductController.py:46-50` (null-safe `get_domain_user_id`/`get_added_by_user_id`)
- Modify: `backend/EcommerceInventory/catalog/management/commands/seed_bd_store.py` (assign `domain_user_id` + `added_by_user_id`)
- Test: `backend/EcommerceInventory/catalog/tests/test_admin_product_list.py` (create dir + `__init__.py` if missing)

**Interfaces:**
- Consumes: existing `Products`, `Users`, `ProductListView`.
- Produces: seeded products own a `domain_user_id`; `ProductSerializer` never raises on null owner.

- [ ] **Step 1: Write the failing test**

Create `backend/EcommerceInventory/catalog/tests/__init__.py` (empty) if the folder doesn't exist, then `backend/EcommerceInventory/catalog/tests/test_admin_product_list.py`:

```python
from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken
from catalog.models import Products, Categories

User = get_user_model()


def auth(client, user):
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {RefreshToken.for_user(user).access_token}")


class AdminProductListTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = User.objects.create(username="admin1", email="admin1@x.com", role="Super Admin")
        self.cat = Categories.objects.create(name="Shirts", slug="shirts")

    def test_list_does_not_crash_when_product_owner_is_null(self):
        # Regression: seeded products had null domain_user_id/added_by_user_id and
        # the admin serializer dereferenced .id, 500-ing the whole list.
        Products.objects.create(name="Null Owner Tee", slug="null-owner-tee",
                                sku="FT-0001", category_id=self.cat, status="ACTIVE",
                                initial_selling_price=100)
        auth(self.client, self.admin)
        res = self.client.get("/api/products/")
        self.assertEqual(res.status_code, 200, res.content)
        self.assertGreaterEqual(len(res.json()["data"]), 1)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python manage.py test catalog.tests.test_admin_product_list -v 2`
Expected: FAIL — 500 / AttributeError `'NoneType' object has no attribute 'id'`.

- [ ] **Step 3: Make the serializer null-safe**

In `catalog/controllers/ProductController.py`, replace the two methods:

```python
    def get_domain_user_id(self,obj):
        if not obj.domain_user_id:
            return None
        return "#"+str(obj.domain_user_id.id)+" "+obj.domain_user_id.username

    def get_added_by_user_id(self,obj):
        if not obj.added_by_user_id:
            return None
        return "#"+str(obj.added_by_user_id.id)+" "+obj.added_by_user_id.username
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python manage.py test catalog.tests.test_admin_product_list -v 2`
Expected: PASS.

- [ ] **Step 5: Assign ownership in the seed (root cause)**

In `seed_bd_store.py`, at the start of `handle()` (after the clear block), resolve an owner and pass it into both category and product `defaults`:

```python
from accounts.models import Users
owner = (Users.objects.filter(role="Super Admin").order_by("id").first()
         or Users.objects.filter(role="Admin").order_by("id").first()
         or Users.objects.order_by("id").first())
if owner is None:
    self.stdout.write(self.style.ERROR(
        "No admin user found. Run `python manage.py create_admin` first."))
    return
```

Add `"domain_user_id": owner, "added_by_user_id": owner,` to the product `defaults` dict, and `"domain_user_id": owner,` to the category `defaults` dict (Categories has the same nullable owner field — verify field name in `catalog/models.py`; skip if the field is absent on Categories).

- [ ] **Step 6: Add a seed-ownership test**

Append to the test file:

```python
    def test_seed_assigns_product_owner(self):
        from django.core.management import call_command
        User.objects.create(username="seedadmin", email="seed@x.com", role="Super Admin")
        call_command("seed_bd_store")
        self.assertGreater(Products.objects.count(), 0)
        self.assertEqual(Products.objects.filter(domain_user_id__isnull=True).count(), 0)
```

- [ ] **Step 7: Run tests**

Run: `python manage.py test catalog.tests.test_admin_product_list -v 2`
Expected: PASS (both tests).

- [ ] **Step 8: Re-seed the real database and verify**

Run: `python manage.py seed_bd_store` (against the configured DB). Then confirm the admin Manage Products page lists products. Report the product count back to the human.

- [ ] **Step 9: Commit**

```bash
git add backend/EcommerceInventory/catalog/controllers/ProductController.py \
        backend/EcommerceInventory/catalog/management/commands/seed_bd_store.py \
        backend/EcommerceInventory/catalog/tests/
git commit -m "fix(catalog): seed product ownership + null-safe admin serializer so admin product list loads"
```

---

## Task 2: FoodOrder + FoodOrderItem models + status machine

**Files:**
- Modify: `backend/EcommerceInventory/food/models.py` (append order models)
- Create: `backend/EcommerceInventory/food/migrations/0002_food_orders.py` (via makemigrations)
- Test: `backend/EcommerceInventory/food/tests/test_orders.py`

**Interfaces:**
- Produces:
  - `FoodOrder` with fields `customer`(nullable FK), `guest_name`, `guest_phone`, `delivery_address`, `restaurant`(FK), `zone`(FK nullable), `order_code`(unique), `status`, `subtotal`, `delivery_fee`, `tip`, `total`, `eta_minutes`, `payment_method`, `payment_status`, `created_at`, `updated_at`.
  - `FoodOrder.Status` = `PLACED | CONFIRMED | PREPARING | OUT_FOR_DELIVERY | DELIVERED | CANCELLED`.
  - `FoodOrder.ALLOWED_TRANSITIONS` dict; `can_transition_to(new)`; `transition_to(new, changed_by=None, reason="")`.
  - `FoodOrderItem` with `order`(FK), `item`(FK nullable SET_NULL), `item_name`, `unit_price`, `quantity`, `selected_options`(JSON), `line_total`.
  - `generate_food_order_code()` → `FD-XXXXXX`.

- [ ] **Step 1: Write the failing test**

Create `food/tests/test_orders.py`:

```python
from decimal import Decimal
from django.test import TestCase
from food.models import Restaurant, FoodOrder, FoodOrderItem


class FoodOrderModelTests(TestCase):
    def setUp(self):
        self.r = Restaurant.objects.create(name="R", slug="r", status=Restaurant.Status.ACTIVE)

    def test_order_code_is_generated_and_unique(self):
        o1 = FoodOrder.objects.create(restaurant=self.r, guest_name="A", guest_phone="1",
                                      delivery_address="addr", subtotal=Decimal("100.00"),
                                      delivery_fee=Decimal("20.00"), tip=Decimal("0.00"),
                                      total=Decimal("120.00"))
        o2 = FoodOrder.objects.create(restaurant=self.r, guest_name="B", guest_phone="2",
                                      delivery_address="addr", subtotal=Decimal("50.00"),
                                      delivery_fee=Decimal("20.00"), tip=Decimal("0.00"),
                                      total=Decimal("70.00"))
        self.assertTrue(o1.order_code.startswith("FD-"))
        self.assertNotEqual(o1.order_code, o2.order_code)

    def test_default_status_is_placed(self):
        o = FoodOrder.objects.create(restaurant=self.r, guest_name="A", guest_phone="1",
                                     delivery_address="a", subtotal=1, delivery_fee=0, tip=0, total=1)
        self.assertEqual(o.status, FoodOrder.Status.PLACED)

    def test_legal_transition_advances(self):
        o = FoodOrder.objects.create(restaurant=self.r, guest_name="A", guest_phone="1",
                                     delivery_address="a", subtotal=1, delivery_fee=0, tip=0, total=1)
        o.transition_to(FoodOrder.Status.CONFIRMED)
        self.assertEqual(o.status, FoodOrder.Status.CONFIRMED)

    def test_illegal_transition_rejected(self):
        from rest_framework.exceptions import ValidationError
        o = FoodOrder.objects.create(restaurant=self.r, guest_name="A", guest_phone="1",
                                     delivery_address="a", subtotal=1, delivery_fee=0, tip=0, total=1)
        with self.assertRaises(ValidationError):
            o.transition_to(FoodOrder.Status.DELIVERED)  # cannot skip from PLACED
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python manage.py test food.tests.test_orders -v 2`
Expected: FAIL — `FoodOrder` import error.

- [ ] **Step 3: Add the models**

Append to `food/models.py`:

```python
import uuid


def generate_food_order_code():
    return f"FD-{uuid.uuid4().hex[:6].upper()}"


class FoodOrder(TimeStamped):
    class Status(models.TextChoices):
        PLACED = "PLACED", "Placed"
        CONFIRMED = "CONFIRMED", "Confirmed"
        PREPARING = "PREPARING", "Preparing"
        OUT_FOR_DELIVERY = "OUT_FOR_DELIVERY", "Out for Delivery"
        DELIVERED = "DELIVERED", "Delivered"
        CANCELLED = "CANCELLED", "Cancelled"

    ALLOWED_TRANSITIONS = {
        Status.PLACED: {Status.CONFIRMED, Status.CANCELLED},
        Status.CONFIRMED: {Status.PREPARING, Status.CANCELLED},
        Status.PREPARING: {Status.OUT_FOR_DELIVERY, Status.CANCELLED},
        Status.OUT_FOR_DELIVERY: {Status.DELIVERED, Status.CANCELLED},
        Status.DELIVERED: set(),
        Status.CANCELLED: set(),
    }

    customer = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                                 on_delete=models.SET_NULL, related_name="food_orders")
    guest_name = models.CharField(max_length=120)
    guest_phone = models.CharField(max_length=20)
    delivery_address = models.TextField()
    restaurant = models.ForeignKey(Restaurant, on_delete=models.PROTECT, related_name="orders")
    zone = models.ForeignKey(DeliveryZone, null=True, blank=True, on_delete=models.SET_NULL,
                             related_name="orders")
    order_code = models.CharField(max_length=12, unique=True, default=generate_food_order_code)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PLACED)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    delivery_fee = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    tip = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    total = models.DecimalField(max_digits=10, decimal_places=2)
    eta_minutes = models.PositiveIntegerField(default=45)
    payment_method = models.CharField(max_length=8, default="COD")
    payment_status = models.CharField(max_length=12, default="PENDING")  # PENDING | COLLECTED
    notes = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["restaurant", "status"]),
            models.Index(fields=["order_code"]),
        ]

    def can_transition_to(self, new_status):
        return new_status in self.ALLOWED_TRANSITIONS.get(self.status, set())

    def transition_to(self, new_status, changed_by=None, reason=""):
        from rest_framework.exceptions import ValidationError
        new_status = FoodOrder.Status(new_status)
        if new_status == self.status:
            return self
        if not self.can_transition_to(new_status):
            raise ValidationError(f"Cannot move order from {self.status} to {new_status}.")
        self.status = new_status
        self.save(update_fields=["status", "updated_at"])
        return self

    def __str__(self):
        return f"{self.order_code} ({self.status})"


class FoodOrderItem(TimeStamped):
    order = models.ForeignKey(FoodOrder, on_delete=models.CASCADE, related_name="items")
    item = models.ForeignKey(FoodItem, null=True, on_delete=models.SET_NULL, related_name="order_items")
    item_name = models.CharField(max_length=150)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField()
    selected_options = models.JSONField(default=list, blank=True)  # [{"name":..., "price_delta":...}]
    line_total = models.DecimalField(max_digits=10, decimal_places=2)
```

- [ ] **Step 4: Make + run migration**

Run: `python manage.py makemigrations food` then `python manage.py migrate --settings=...test_settings` (the test runner migrates automatically; run makemigrations for real).
Expected: migration `0002_...` created.

- [ ] **Step 5: Run tests**

Run: `python manage.py test food.tests.test_orders -v 2`
Expected: PASS (4 tests).

- [ ] **Step 6: Commit**

```bash
git add backend/EcommerceInventory/food/models.py backend/EcommerceInventory/food/migrations/ \
        backend/EcommerceInventory/food/tests/test_orders.py
git commit -m "feat(food): FoodOrder/FoodOrderItem models with COD status machine (TDD)"
```

---

## Task 3: `place_food_cod_order` service (server-authoritative pricing)

**Files:**
- Create: `backend/EcommerceInventory/food/services.py`
- Test: `backend/EcommerceInventory/food/tests/test_order_service.py`

**Interfaces:**
- Consumes: `Restaurant`, `FoodItem`, `FoodItemOption`, `DeliveryZone`, `RestaurantZone`, `FoodOrder`, `FoodOrderItem`, `food.geo.haversine_km`.
- Produces:
  ```python
  DELIVERY_BUFFER_MINUTES = 20
  def place_food_cod_order(*, customer, restaurant_slug, items, contact_name,
                           contact_phone, delivery_address, zone_id=None,
                           lat=None, lng=None, tip="0.00", notes="") -> FoodOrder
  ```
  where `items = [{"item_id": int, "quantity": int, "option_ids": [int, ...]}]`.
  Raises `rest_framework.exceptions.ValidationError` on: empty cart, unknown/unavailable item, item from another restaurant, invalid option id, restaurant closed, below `min_order_amount`, non-serviceable zone.

- [ ] **Step 1: Write the failing tests**

Create `food/tests/test_order_service.py`:

```python
from decimal import Decimal
from django.test import TestCase
from django.utils import timezone
from rest_framework.exceptions import ValidationError
from food.models import (Restaurant, RestaurantHours, DeliveryZone, RestaurantZone,
                         FoodCategory, FoodItem, FoodItemOptionGroup, FoodItemOption, FoodOrder)
from food.services import place_food_cod_order


def open_all_week(restaurant):
    for wd in range(7):
        RestaurantHours.objects.create(restaurant=restaurant, weekday=wd,
                                       open_time="00:00", close_time="23:59")


class PlaceFoodOrderTests(TestCase):
    def setUp(self):
        self.zone = DeliveryZone.objects.create(name="Zone1", center_lat="23.8",
                                                center_lng="90.4", radius_km="5")
        self.r = Restaurant.objects.create(name="R", slug="r", status=Restaurant.Status.ACTIVE,
                                           is_open=True, base_delivery_fee=Decimal("30.00"),
                                           min_order_amount=Decimal("100.00"), avg_prep_minutes=25)
        RestaurantZone.objects.create(restaurant=self.r, zone=self.zone)
        open_all_week(self.r)
        self.cat = FoodCategory.objects.create(restaurant=self.r, name="Main")
        self.item = FoodItem.objects.create(restaurant=self.r, category_id=self.cat,
                                            name="Biriyani", slug="biriyani", price=Decimal("120.00"))
        self.grp = FoodItemOptionGroup.objects.create(item=self.item, name="Size", max_select=1)
        self.opt = FoodItemOption.objects.create(group=self.grp, name="Large", price_delta=Decimal("50.00"))

    def _lines(self, qty=1, options=None):
        return [{"item_id": self.item.id, "quantity": qty, "option_ids": options or []}]

    def test_totals_are_computed_server_side(self):
        order = place_food_cod_order(customer=None, restaurant_slug="r",
                                     items=self._lines(qty=1, options=[self.opt.id]),
                                     contact_name="A", contact_phone="017", delivery_address="addr",
                                     zone_id=self.zone.id, tip="10.00")
        # subtotal = (120 + 50) * 1 = 170; fee = 30; tip = 10; total = 210
        self.assertEqual(order.subtotal, Decimal("170.00"))
        self.assertEqual(order.delivery_fee, Decimal("30.00"))
        self.assertEqual(order.total, Decimal("210.00"))
        self.assertEqual(order.eta_minutes, 25 + 20)
        self.assertEqual(order.items.count(), 1)

    def test_below_min_order_rejected(self):
        self.r.min_order_amount = Decimal("500.00"); self.r.save()
        with self.assertRaises(ValidationError):
            place_food_cod_order(customer=None, restaurant_slug="r", items=self._lines(),
                                 contact_name="A", contact_phone="017",
                                 delivery_address="a", zone_id=self.zone.id)

    def test_closed_restaurant_rejected(self):
        self.r.is_open = False; self.r.save()
        with self.assertRaises(ValidationError):
            place_food_cod_order(customer=None, restaurant_slug="r", items=self._lines(qty=2),
                                 contact_name="A", contact_phone="017",
                                 delivery_address="a", zone_id=self.zone.id)

    def test_non_serviceable_zone_rejected(self):
        other = DeliveryZone.objects.create(name="Z2", center_lat="10", center_lng="10", radius_km="1")
        with self.assertRaises(ValidationError):
            place_food_cod_order(customer=None, restaurant_slug="r", items=self._lines(qty=2),
                                 contact_name="A", contact_phone="017",
                                 delivery_address="a", zone_id=other.id)

    def test_unavailable_item_rejected(self):
        self.item.is_available = False; self.item.save()
        with self.assertRaises(ValidationError):
            place_food_cod_order(customer=None, restaurant_slug="r", items=self._lines(qty=2),
                                 contact_name="A", contact_phone="017",
                                 delivery_address="a", zone_id=self.zone.id)

    def test_zone_resolved_from_latlng_when_no_zone_id(self):
        order = place_food_cod_order(customer=None, restaurant_slug="r", items=self._lines(qty=2),
                                     contact_name="A", contact_phone="017", delivery_address="a",
                                     lat="23.80", lng="90.40")
        self.assertEqual(order.zone_id, self.zone.id)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python manage.py test food.tests.test_order_service -v 2`
Expected: FAIL — `food.services` import error.

- [ ] **Step 3: Implement the service**

Create `food/services.py`:

```python
"""Food COD checkout service — the single server-authoritative pricing/validation path.

Mirrors orders.services.place_cod_order: totals are recomputed here from live DB rows,
never taken from the client. One restaurant per order.
"""
from decimal import Decimal

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from food.models import (Restaurant, FoodItem, FoodItemOption, DeliveryZone,
                         RestaurantZone, FoodOrder, FoodOrderItem)

DELIVERY_BUFFER_MINUTES = 20


def _resolve_zone(restaurant, zone_id, lat, lng):
    served = DeliveryZone.objects.filter(is_active=True, zone_restaurants__restaurant=restaurant)
    if zone_id:
        zone = served.filter(id=zone_id).first()
        if not zone:
            raise ValidationError("This restaurant does not deliver to the selected area.")
        return zone
    if lat is not None and lng is not None:
        for zone in served:
            if zone.serves(lat, lng):
                return zone
        raise ValidationError("Your location is outside this restaurant's delivery area.")
    raise ValidationError("A delivery area is required.")


def _delivery_fee(restaurant, zone):
    rz = RestaurantZone.objects.filter(restaurant=restaurant, zone=zone).first()
    if rz and rz.delivery_fee is not None:
        return Decimal(rz.delivery_fee)
    return Decimal(restaurant.base_delivery_fee)


@transaction.atomic
def place_food_cod_order(*, customer, restaurant_slug, items, contact_name, contact_phone,
                         delivery_address, zone_id=None, lat=None, lng=None, tip="0.00", notes=""):
    if not items:
        raise ValidationError("Your cart is empty.")

    restaurant = Restaurant.objects.filter(slug=restaurant_slug,
                                           status=Restaurant.Status.ACTIVE).first()
    if not restaurant:
        raise ValidationError("Restaurant is not available.")
    if not restaurant.is_currently_open(timezone.localtime()):
        raise ValidationError("This restaurant is currently closed.")

    zone = _resolve_zone(restaurant, zone_id, lat, lng)

    subtotal = Decimal("0.00")
    built = []
    for line in items:
        item_id = line.get("item_id")
        qty = int(line.get("quantity", 0))
        if not item_id or qty <= 0:
            raise ValidationError("Each cart line needs an item and a positive quantity.")
        item = FoodItem.objects.filter(id=item_id, restaurant=restaurant,
                                       is_available=True).first()
        if not item:
            raise ValidationError("One of the items is no longer available.")
        unit = Decimal(item.effective_price)
        opts = []
        for oid in line.get("option_ids", []):
            opt = FoodItemOption.objects.filter(id=oid, group__item=item).first()
            if not opt:
                raise ValidationError("An invalid option was selected.")
            unit += Decimal(opt.price_delta)
            opts.append({"name": opt.name, "price_delta": str(opt.price_delta)})
        line_total = (unit * qty).quantize(Decimal("0.01"))
        subtotal += line_total
        built.append((item, qty, unit, opts, line_total))

    if subtotal < Decimal(restaurant.min_order_amount):
        raise ValidationError(
            f"Minimum order is ৳{restaurant.min_order_amount}. Add more items.")

    delivery_fee = _delivery_fee(restaurant, zone)
    tip_amount = Decimal(str(tip or "0.00"))
    total = subtotal + delivery_fee + tip_amount

    order = FoodOrder.objects.create(
        customer=customer if getattr(customer, "is_authenticated", False) else None,
        guest_name=contact_name, guest_phone=contact_phone, delivery_address=delivery_address,
        restaurant=restaurant, zone=zone, subtotal=subtotal, delivery_fee=delivery_fee,
        tip=tip_amount, total=total, notes=notes or "",
        eta_minutes=restaurant.avg_prep_minutes + DELIVERY_BUFFER_MINUTES,
    )
    for item, qty, unit, opts, line_total in built:
        FoodOrderItem.objects.create(order=order, item=item, item_name=item.name,
                                     unit_price=unit, quantity=qty, selected_options=opts,
                                     line_total=line_total)
    return order
```

- [ ] **Step 4: Run tests**

Run: `python manage.py test food.tests.test_order_service -v 2`
Expected: PASS (6 tests).

- [ ] **Step 5: Commit**

```bash
git add backend/EcommerceInventory/food/services.py backend/EcommerceInventory/food/tests/test_order_service.py
git commit -m "feat(food): server-authoritative place_food_cod_order service (TDD)"
```

---

## Task 4: Customer order endpoints (place / track / history) + serializers

**Files:**
- Create: `backend/EcommerceInventory/food/serializers_orders.py`
- Create: `backend/EcommerceInventory/food/views_orders.py`
- Modify: `backend/EcommerceInventory/food/urls.py`
- Test: `backend/EcommerceInventory/food/tests/test_order_api.py`

**Interfaces:**
- Consumes: `place_food_cod_order`, `FoodOrder`.
- Produces routes:
  - `POST /api/food/orders/` (AllowAny + JWTAuthentication) → `{order_code, status, subtotal, delivery_fee, tip, total, eta_minutes}`.
  - `GET /api/food/orders/` (auth) → caller's order history (paginated envelope).
  - `GET /api/food/orders/<str:order_code>/?phone=` → track; guest must match `guest_phone`, auth reads own.
- Serializers: `FoodOrderItemSerializer`, `FoodOrderSerializer` (fields listed in Step 3).

- [ ] **Step 1: Write the failing tests**

Create `food/tests/test_order_api.py`:

```python
from decimal import Decimal
from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken
from food.models import (Restaurant, RestaurantHours, DeliveryZone, RestaurantZone,
                         FoodCategory, FoodItem)

User = get_user_model()


def auth(client, user):
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {RefreshToken.for_user(user).access_token}")


class OrderApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.zone = DeliveryZone.objects.create(name="Z", center_lat="23.8", center_lng="90.4", radius_km="5")
        self.r = Restaurant.objects.create(name="R", slug="r", status=Restaurant.Status.ACTIVE,
                                           is_open=True, base_delivery_fee=Decimal("30.00"),
                                           min_order_amount=Decimal("0.00"))
        RestaurantZone.objects.create(restaurant=self.r, zone=self.zone)
        for wd in range(7):
            RestaurantHours.objects.create(restaurant=self.r, weekday=wd, open_time="00:00", close_time="23:59")
        self.cat = FoodCategory.objects.create(restaurant=self.r, name="Main")
        self.item = FoodItem.objects.create(restaurant=self.r, category_id=self.cat,
                                            name="Biriyani", slug="biriyani", price=Decimal("120.00"))

    def _payload(self, **over):
        p = {"restaurant_slug": "r", "zone_id": self.zone.id, "contact_name": "A",
             "contact_phone": "017", "delivery_address": "addr",
             "items": [{"item_id": self.item.id, "quantity": 1, "option_ids": []}]}
        p.update(over); return p

    def test_guest_can_place_cod_order(self):
        res = self.client.post("/api/food/orders/", self._payload(), format="json")
        self.assertEqual(res.status_code, 201, res.content)
        d = res.json()["data"]
        self.assertTrue(d["order_code"].startswith("FD-"))
        self.assertEqual(Decimal(str(d["total"])), Decimal("150.00"))

    def test_server_ignores_client_supplied_total(self):
        res = self.client.post("/api/food/orders/", self._payload(total="1.00", subtotal="1.00"), format="json")
        self.assertEqual(res.status_code, 201, res.content)
        self.assertEqual(Decimal(str(res.json()["data"]["total"])), Decimal("150.00"))

    def test_guest_track_requires_matching_phone(self):
        code = self.client.post("/api/food/orders/", self._payload(), format="json").json()["data"]["order_code"]
        ok = self.client.get(f"/api/food/orders/{code}/?phone=017")
        self.assertEqual(ok.status_code, 200)
        bad = self.client.get(f"/api/food/orders/{code}/?phone=999")
        self.assertIn(bad.status_code, (403, 404))

    def test_auth_history_lists_only_own(self):
        u = User.objects.create(username="cust", email="cust@x.com", role="Customer")
        auth(self.client, u)
        self.client.post("/api/food/orders/", self._payload(), format="json")
        res = self.client.get("/api/food/orders/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(res.json()["data"]), 1)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python manage.py test food.tests.test_order_api -v 2`
Expected: FAIL — 404 (routes not wired).

- [ ] **Step 3: Add serializers**

Create `food/serializers_orders.py`:

```python
from rest_framework import serializers
from food.models import FoodOrder, FoodOrderItem


class FoodOrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = FoodOrderItem
        fields = ["id", "item_name", "unit_price", "quantity", "selected_options", "line_total"]


class FoodOrderSerializer(serializers.ModelSerializer):
    items = FoodOrderItemSerializer(many=True, read_only=True)
    restaurant_name = serializers.CharField(source="restaurant.name", read_only=True)
    restaurant_slug = serializers.CharField(source="restaurant.slug", read_only=True)

    class Meta:
        model = FoodOrder
        fields = ["id", "order_code", "status", "restaurant_name", "restaurant_slug",
                  "guest_name", "guest_phone", "delivery_address", "subtotal", "delivery_fee",
                  "tip", "total", "eta_minutes", "payment_method", "payment_status",
                  "created_at", "items"]
```

- [ ] **Step 4: Add views**

Create `food/views_orders.py`:

```python
from rest_framework.views import APIView
from rest_framework.generics import ListAPIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.exceptions import ValidationError
from rest_framework_simplejwt.authentication import JWTAuthentication

from core.helpers import renderResponse, CustomPageNumberPagination, CommonListAPIMixin
from food.models import FoodOrder
from food.services import place_food_cod_order
from food.serializers_orders import FoodOrderSerializer


class FoodOrderView(APIView):
    """POST = place a COD order (guest or auth). GET = auth customer's history."""
    authentication_classes = [JWTAuthentication]
    permission_classes = [AllowAny]

    def post(self, request):
        d = request.data
        try:
            order = place_food_cod_order(
                customer=request.user,
                restaurant_slug=d.get("restaurant_slug"),
                items=d.get("items") or [],
                contact_name=d.get("contact_name", ""),
                contact_phone=d.get("contact_phone", ""),
                delivery_address=d.get("delivery_address", ""),
                zone_id=d.get("zone_id"),
                lat=d.get("lat"), lng=d.get("lng"),
                tip=d.get("tip", "0.00"),
                notes=d.get("notes", ""),
            )
        except ValidationError as exc:
            detail = exc.detail
            msgs = detail if isinstance(detail, list) else [str(detail)]
            return renderResponse(data=[str(m) for m in msgs],
                                  message="Could not place order", status=400)
        return renderResponse(data=FoodOrderSerializer(order).data,
                              message="Order placed", status=201)

    def get(self, request):
        if not request.user.is_authenticated:
            return renderResponse(data=[], message="Login required", status=401)
        qs = FoodOrder.objects.filter(customer=request.user).prefetch_related("items")
        return renderResponse(data=FoodOrderSerializer(qs, many=True).data,
                              message="Order history")


class FoodOrderTrackView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [AllowAny]

    def get(self, request, order_code):
        order = FoodOrder.objects.filter(order_code=order_code).prefetch_related("items").first()
        if not order:
            return renderResponse(data={}, message="Order not found", status=404)
        if request.user.is_authenticated and order.customer_id == request.user.id:
            pass
        elif request.GET.get("phone") and request.GET.get("phone") == order.guest_phone:
            pass
        else:
            return renderResponse(data={}, message="Order not found", status=404)
        return renderResponse(data=FoodOrderSerializer(order).data, message="Order")
```

- [ ] **Step 5: Wire URLs**

In `food/urls.py`, add imports and paths (place the `orders/` routes BEFORE the router include; order the track route after the list route):

```python
from food.views_orders import FoodOrderView, FoodOrderTrackView
```
Add to `urlpatterns` list:
```python
    path("orders/", FoodOrderView.as_view(), name="food_orders"),
    path("orders/<str:order_code>/", FoodOrderTrackView.as_view(), name="food_order_track"),
```

- [ ] **Step 6: Run tests**

Run: `python manage.py test food.tests.test_order_api -v 2`
Expected: PASS (4 tests).

- [ ] **Step 7: Commit**

```bash
git add backend/EcommerceInventory/food/serializers_orders.py \
        backend/EcommerceInventory/food/views_orders.py \
        backend/EcommerceInventory/food/urls.py \
        backend/EcommerceInventory/food/tests/test_order_api.py
git commit -m "feat(food): customer order place/track/history API (TDD)"
```

---

## Task 5: Vendor + admin order fulfillment endpoints

**Files:**
- Modify: `backend/EcommerceInventory/food/views_orders.py` (add vendor/admin views)
- Modify: `backend/EcommerceInventory/food/urls.py`
- Test: `backend/EcommerceInventory/food/tests/test_fulfillment_api.py`

**Interfaces:**
- Produces:
  - `GET /api/food/vendor/orders/` (IsRestaurantOwner) → owner's restaurant orders.
  - `PATCH /api/food/vendor/orders/<int:pk>/status/` body `{status, reason?}` (IsRestaurantOwner, own restaurant only).
  - `GET /api/food/admin/orders/?status=` (IsPlatformAdmin) → all orders (paginated).
  - `PATCH /api/food/admin/orders/<int:pk>/status/` (IsPlatformAdmin).

- [ ] **Step 1: Write the failing tests**

Create `food/tests/test_fulfillment_api.py`:

```python
from decimal import Decimal
from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken
from food.models import Restaurant, FoodOrder

User = get_user_model()


def auth(c, u):
    c.credentials(HTTP_AUTHORIZATION=f"Bearer {RefreshToken.for_user(u).access_token}")


class FulfillmentTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.owner_a = User.objects.create(username="oa", email="oa@x.com", role="Restaurant")
        self.owner_b = User.objects.create(username="ob", email="ob@x.com", role="Restaurant")
        self.ra = Restaurant.objects.create(owner=self.owner_a, name="A", slug="a", status=Restaurant.Status.ACTIVE)
        self.rb = Restaurant.objects.create(owner=self.owner_b, name="B", slug="b", status=Restaurant.Status.ACTIVE)
        self.order_a = FoodOrder.objects.create(restaurant=self.ra, guest_name="G", guest_phone="1",
                                                delivery_address="a", subtotal=1, delivery_fee=0, tip=0, total=1)

    def test_vendor_lists_only_own_orders(self):
        FoodOrder.objects.create(restaurant=self.rb, guest_name="G", guest_phone="1",
                                 delivery_address="a", subtotal=1, delivery_fee=0, tip=0, total=1)
        auth(self.client, self.owner_a)
        res = self.client.get("/api/food/vendor/orders/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(res.json()["data"]), 1)

    def test_vendor_advances_own_order_status(self):
        auth(self.client, self.owner_a)
        res = self.client.patch(f"/api/food/vendor/orders/{self.order_a.id}/status/",
                                {"status": "CONFIRMED"}, format="json")
        self.assertEqual(res.status_code, 200, res.content)
        self.order_a.refresh_from_db()
        self.assertEqual(self.order_a.status, "CONFIRMED")

    def test_vendor_cannot_touch_other_restaurant_order(self):
        auth(self.client, self.owner_b)
        res = self.client.patch(f"/api/food/vendor/orders/{self.order_a.id}/status/",
                                {"status": "CONFIRMED"}, format="json")
        self.assertIn(res.status_code, (403, 404))
        self.order_a.refresh_from_db()
        self.assertEqual(self.order_a.status, "PLACED")

    def test_illegal_transition_rejected(self):
        auth(self.client, self.owner_a)
        res = self.client.patch(f"/api/food/vendor/orders/{self.order_a.id}/status/",
                                {"status": "DELIVERED"}, format="json")
        self.assertEqual(res.status_code, 400)

    def test_admin_lists_all_orders(self):
        admin = User.objects.create(username="adm", email="adm@x.com", role="Admin")
        FoodOrder.objects.create(restaurant=self.rb, guest_name="G", guest_phone="1",
                                 delivery_address="a", subtotal=1, delivery_fee=0, tip=0, total=1)
        auth(self.client, admin)
        res = self.client.get("/api/food/admin/orders/")
        self.assertEqual(res.status_code, 200)
        self.assertGreaterEqual(len(res.json()["data"]), 2)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python manage.py test food.tests.test_fulfillment_api -v 2`
Expected: FAIL — 404.

- [ ] **Step 3: Add vendor/admin views**

Append to `food/views_orders.py`:

```python
from rest_framework.permissions import IsAuthenticated
from food.permissions import IsRestaurantOwner, IsPlatformAdmin


class VendorOrderListView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, IsRestaurantOwner]

    def get(self, request):
        qs = FoodOrder.objects.filter(restaurant=request.user.restaurant).prefetch_related("items")
        status_f = request.GET.get("status")
        if status_f:
            qs = qs.filter(status=status_f)
        return renderResponse(data=FoodOrderSerializer(qs, many=True).data, message="Vendor orders")


class VendorOrderStatusView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, IsRestaurantOwner]

    def patch(self, request, pk):
        order = FoodOrder.objects.filter(pk=pk, restaurant=request.user.restaurant).first()
        if not order:
            return renderResponse(data={}, message="Order not found", status=404)
        try:
            order.transition_to(request.data.get("status"), changed_by=request.user,
                                reason=request.data.get("reason", ""))
        except ValidationError as exc:
            return renderResponse(data=str(exc.detail), message="Invalid transition", status=400)
        return renderResponse(data={"id": order.id, "status": order.status}, message="Status updated")


class AdminFoodOrderListView(ListAPIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, IsPlatformAdmin]
    serializer_class = FoodOrderSerializer
    pagination_class = CustomPageNumberPagination

    def get_queryset(self):
        qs = FoodOrder.objects.all().prefetch_related("items").order_by("-created_at")
        status_f = self.request.GET.get("status")
        if status_f:
            qs = qs.filter(status=status_f)
        return qs

    @CommonListAPIMixin.common_list_decorator(FoodOrderSerializer)
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)


class AdminFoodOrderStatusView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, IsPlatformAdmin]

    def patch(self, request, pk):
        order = FoodOrder.objects.filter(pk=pk).first()
        if not order:
            return renderResponse(data={}, message="Order not found", status=404)
        try:
            order.transition_to(request.data.get("status"), changed_by=request.user,
                                reason=request.data.get("reason", ""))
        except ValidationError as exc:
            return renderResponse(data=str(exc.detail), message="Invalid transition", status=400)
        return renderResponse(data={"id": order.id, "status": order.status}, message="Status updated")
```

- [ ] **Step 4: Wire URLs**

In `food/urls.py` add imports and paths (these are single-object/custom routes, so add to the `urlpatterns` list, not the router):

```python
from food.views_orders import (VendorOrderListView, VendorOrderStatusView,
                               AdminFoodOrderListView, AdminFoodOrderStatusView)
```
```python
    path("vendor/orders/", VendorOrderListView.as_view(), name="food_vendor_orders"),
    path("vendor/orders/<int:pk>/status/", VendorOrderStatusView.as_view(), name="food_vendor_order_status"),
    path("admin/orders/", AdminFoodOrderListView.as_view(), name="food_admin_orders"),
    path("admin/orders/<int:pk>/status/", AdminFoodOrderStatusView.as_view(), name="food_admin_order_status"),
```

- [ ] **Step 5: Run tests**

Run: `python manage.py test food.tests.test_fulfillment_api -v 2`
Expected: PASS (5 tests). Then run the whole food suite: `python manage.py test food -v 2` — all green.

- [ ] **Step 6: Commit**

```bash
git add backend/EcommerceInventory/food/views_orders.py backend/EcommerceInventory/food/urls.py \
        backend/EcommerceInventory/food/tests/test_fulfillment_api.py
git commit -m "feat(food): vendor + admin order fulfillment endpoints (TDD)"
```

---

## Task 6: Food cart Redux slice (one-restaurant guard)

**Files:**
- Create: `frontend/ecommerce_inventory/src/food/redux/foodCartSlice.js`
- Modify: `frontend/ecommerce_inventory/src/redux/store/store.js`
- Test: `frontend/ecommerce_inventory/src/food/redux/foodCartSlice.test.js`

**Interfaces:**
- Produces actions `addFoodItem, removeFoodItem, updateFoodQty, setTip, clearFoodCart`; selectors `selectFoodCart, selectFoodRestaurant, selectFoodCount, selectFoodSubtotal`.
- `addFoodItem` payload: `{ lineId, restaurantId, restaurantSlug, restaurantName, itemId, name, image, unitPrice, quantity, selectedOptions:[{optionId,name,priceDelta}], force?:bool }`.
- One-restaurant guard: if cart non-empty and `restaurantId` differs and `!force`, the reducer no-ops (component shows the "start new order?" prompt, then re-dispatches with `force:true`).

- [ ] **Step 1: Write the failing test**

Create `foodCartSlice.test.js`:

```javascript
import reducer, {
  addFoodItem, removeFoodItem, updateFoodQty, clearFoodCart,
  selectFoodSubtotal, selectFoodCount,
} from './foodCartSlice';

const line = (over = {}) => ({
  lineId: 'l1', restaurantId: 1, restaurantSlug: 'r1', restaurantName: 'R1',
  itemId: 10, name: 'Biriyani', image: '', unitPrice: 120, quantity: 1,
  selectedOptions: [{ optionId: 5, name: 'Large', priceDelta: 50 }], ...over,
});

test('adds an item and computes subtotal (unit+options)*qty', () => {
  const s = reducer(undefined, addFoodItem(line()));
  expect(s.items).toHaveLength(1);
  expect(selectFoodSubtotal({ foodCart: s })).toBe(170);
  expect(selectFoodCount({ foodCart: s })).toBe(1);
});

test('rejects an item from a different restaurant without force', () => {
  let s = reducer(undefined, addFoodItem(line()));
  s = reducer(s, addFoodItem(line({ lineId: 'l2', restaurantId: 2, restaurantSlug: 'r2' })));
  expect(s.items).toHaveLength(1);
  expect(s.restaurantId).toBe(1);
});

test('force replaces the cart with the new restaurant', () => {
  let s = reducer(undefined, addFoodItem(line()));
  s = reducer(s, addFoodItem(line({ lineId: 'l2', restaurantId: 2, restaurantSlug: 'r2', force: true })));
  expect(s.items).toHaveLength(1);
  expect(s.restaurantId).toBe(2);
});

test('clearFoodCart empties everything', () => {
  let s = reducer(undefined, addFoodItem(line()));
  s = reducer(s, clearFoodCart());
  expect(s.items).toHaveLength(0);
  expect(s.restaurantId).toBeNull();
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `CI=true npx react-scripts test src/food/redux/foodCartSlice.test.js --watchAll=false`
Expected: FAIL — module not found.

- [ ] **Step 3: Implement the slice**

Create `foodCartSlice.js`:

```javascript
import { createSlice } from '@reduxjs/toolkit';

const STORAGE_KEY = 'food_cart_v1';

const empty = { restaurantId: null, restaurantSlug: null, restaurantName: null, items: [], tip: 0 };

const load = () => {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? JSON.parse(raw) : { ...empty };
  } catch {
    return { ...empty };
  }
};

const persist = (state) => {
  const { restaurantId, restaurantSlug, restaurantName, items, tip } = state;
  localStorage.setItem(STORAGE_KEY, JSON.stringify({ restaurantId, restaurantSlug, restaurantName, items, tip }));
};

const lineTotal = (i) =>
  (Number(i.unitPrice) + (i.selectedOptions || []).reduce((s, o) => s + Number(o.priceDelta || 0), 0)) * i.quantity;

const foodCartSlice = createSlice({
  name: 'foodCart',
  initialState: load(),
  reducers: {
    addFoodItem: (state, { payload }) => {
      const differs = state.restaurantId != null && state.restaurantId !== payload.restaurantId;
      if (differs && !payload.force) return; // guard: component prompts, then re-dispatches with force
      if (differs && payload.force) {
        state.items = []; state.tip = 0;
      }
      state.restaurantId = payload.restaurantId;
      state.restaurantSlug = payload.restaurantSlug;
      state.restaurantName = payload.restaurantName;
      const existing = state.items.find((i) => i.lineId === payload.lineId);
      if (existing) existing.quantity += payload.quantity;
      else state.items.push({
        lineId: payload.lineId, itemId: payload.itemId, name: payload.name, image: payload.image,
        unitPrice: payload.unitPrice, quantity: payload.quantity, selectedOptions: payload.selectedOptions || [],
      });
      persist(state);
    },
    removeFoodItem: (state, { payload }) => {
      state.items = state.items.filter((i) => i.lineId !== payload.lineId);
      if (state.items.length === 0) { state.restaurantId = null; state.restaurantSlug = null; state.restaurantName = null; state.tip = 0; }
      persist(state);
    },
    updateFoodQty: (state, { payload }) => {
      const i = state.items.find((x) => x.lineId === payload.lineId);
      if (i) i.quantity = Math.max(1, payload.quantity);
      persist(state);
    },
    setTip: (state, { payload }) => { state.tip = Math.max(0, Number(payload) || 0); persist(state); },
    clearFoodCart: (state) => { Object.assign(state, { ...empty }); persist(state); },
  },
});

export const { addFoodItem, removeFoodItem, updateFoodQty, setTip, clearFoodCart } = foodCartSlice.actions;

export const selectFoodCart = (s) => s.foodCart.items;
export const selectFoodRestaurant = (s) => ({ id: s.foodCart.restaurantId, slug: s.foodCart.restaurantSlug, name: s.foodCart.restaurantName });
export const selectFoodCount = (s) => s.foodCart.items.reduce((n, i) => n + i.quantity, 0);
export const selectFoodSubtotal = (s) => s.foodCart.items.reduce((sum, i) => sum + lineTotal(i), 0);
export const selectFoodTip = (s) => s.foodCart.tip;

export default foodCartSlice.reducer;
```

- [ ] **Step 4: Wire into the store**

In `redux/store/store.js`, import and register:
```javascript
import foodCartReducer from "../../food/redux/foodCartSlice";
```
Add `foodCart: foodCartReducer,` to the `reducer` object.

- [ ] **Step 5: Run tests**

Run: `CI=true npx react-scripts test src/food/redux/foodCartSlice.test.js --watchAll=false`
Expected: PASS (4 tests).

- [ ] **Step 6: Commit**

```bash
git add frontend/ecommerce_inventory/src/food/redux/ frontend/ecommerce_inventory/src/redux/store/store.js
git commit -m "feat(food): independent food cart slice with one-restaurant guard (TDD)"
```

---

## Task 7: Food theme, layout, and route mounting (the UI switch)

**Files:**
- Create: `frontend/ecommerce_inventory/src/food/theme.js`
- Create: `frontend/ecommerce_inventory/src/food/layout/FoodLayout.js`
- Create: `frontend/ecommerce_inventory/src/food/context/FoodLocationContext.js`
- Modify: `frontend/ecommerce_inventory/src/App.js` (mount `/food/*`, retire `FoodComingSoon` route)
- Modify: storefront header component that links to `/food` (confirm it already points to `/food` — it does; no change needed unless it points elsewhere)
- Test: `frontend/ecommerce_inventory/src/food/layout/FoodLayout.test.js`

**Interfaces:**
- Produces `getFoodTheme()` (dark immersive MUI theme), `<FoodLayout/>` with `<Outlet/>`, and `FoodLocationProvider` exposing `{ zoneId, setZoneId, zones, lang, setLang, coords, useMyLocation }`.
- App mounts:
  ```
  { path:"/food", element:<FoodApp/>, children:[
      {index:true, element:<FoodHome/>},
      {path:"restaurant/:slug", element:<RestaurantDetail/>},
      {path:"cart", element:<FoodCartPage/>},
      {path:"checkout", element:<FoodCheckout/>},
      {path:"order/:code", element:<FoodOrderTrack/>},
      {path:"orders", element:<ProtectedRoute element={<FoodMyOrders/>}/>},
  ]}
  ```
  where `FoodApp` wraps `FoodLocationProvider` + `ThemeProvider(getFoodTheme())` + `<FoodLayout/>`.

- [ ] **Step 1: Write the failing test**

Create `FoodLayout.test.js`:

```javascript
import { render, screen } from '@testing-library/react';
import { Provider } from 'react-redux';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { ThemeProvider } from '@mui/material/styles';
import store from '../../redux/store/store';
import { getFoodTheme } from '../theme';
import FoodLayout from './FoodLayout';

test('food layout renders brand and a cart affordance', () => {
  render(
    <Provider store={store}>
      <ThemeProvider theme={getFoodTheme()}>
        <MemoryRouter initialEntries={['/food']}>
          <Routes><Route path="/food" element={<FoodLayout />} /></Routes>
        </MemoryRouter>
      </ThemeProvider>
    </Provider>
  );
  expect(screen.getByText(/food/i)).toBeInTheDocument();
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `CI=true npx react-scripts test src/food/layout/FoodLayout.test.js --watchAll=false`
Expected: FAIL — modules not found.

- [ ] **Step 3: Create the theme**

Create `food/theme.js` (dark immersive; warm food-app accent):

```javascript
import { createTheme } from '@mui/material/styles';

export function getFoodTheme() {
  return createTheme({
    palette: {
      mode: 'dark',
      primary: { main: '#FF6B35', light: '#FF8C5F', dark: '#E14E1D', contrastText: '#FFFFFF' },
      secondary: { main: '#FFC93C', contrastText: '#1A1200' },
      background: { default: '#0E0F12', paper: '#17191F' },
      text: { primary: '#F5F6F7', secondary: '#9BA1AC' },
      divider: '#262A32',
      success: { main: '#22C55E' }, warning: { main: '#F59E0B' }, error: { main: '#EF4444' },
    },
    typography: {
      fontFamily: "'Inter','Roboto','Helvetica Neue',sans-serif",
      h1: { fontWeight: 800, letterSpacing: '-0.03em' },
      h4: { fontWeight: 800 }, h5: { fontWeight: 700 }, h6: { fontWeight: 700 },
      button: { textTransform: 'none', fontWeight: 700 },
    },
    shape: { borderRadius: 16 },
    components: {
      MuiButton: { styleOverrides: { root: { borderRadius: 999, padding: '10px 22px', boxShadow: 'none' },
        containedPrimary: { background: 'linear-gradient(135deg,#FF8C5F,#E14E1D)' } } },
      MuiCard: { styleOverrides: { root: { backgroundImage: 'none', border: '1px solid #262A32', borderRadius: 20 } } },
      MuiPaper: { styleOverrides: { root: { backgroundImage: 'none' } } },
      MuiAppBar: { styleOverrides: { root: { backgroundColor: 'rgba(14,15,18,0.85)', backdropFilter: 'blur(14px)', color: '#F5F6F7', boxShadow: '0 1px 0 0 #262A32' } } },
      MuiChip: { styleOverrides: { root: { borderRadius: 999, fontWeight: 600 } } },
    },
  });
}

export default getFoodTheme();
```

- [ ] **Step 4: Create the location context**

Create `food/context/FoodLocationContext.js`:

```javascript
import { createContext, useContext, useEffect, useState, useCallback } from 'react';
import useApi from '../../hooks/APIHandler';

const Ctx = createContext(null);
export const useFoodLocation = () => useContext(Ctx);

export function FoodLocationProvider({ children }) {
  const { callApi } = useApi();
  const [zones, setZones] = useState([]);
  const [zoneId, setZoneId] = useState(() => localStorage.getItem('food_zone') || '');
  const [lang, setLangState] = useState(() => localStorage.getItem('food_lang') || 'en');
  const [coords, setCoords] = useState(null);

  useEffect(() => { (async () => {
    const res = await callApi({ url: 'food/zones/', method: 'GET' });
    setZones(res?.data?.data || []);
  })(); }, []); // eslint-disable-line

  const setZone = useCallback((id) => { setZoneId(id); localStorage.setItem('food_zone', id || ''); }, []);
  const setLang = useCallback((l) => { setLangState(l); localStorage.setItem('food_lang', l); }, []);

  const useMyLocation = useCallback(() => new Promise((resolve, reject) => {
    if (!navigator.geolocation) return reject(new Error('Geolocation unavailable'));
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        const c = { lat: pos.coords.latitude, lng: pos.coords.longitude };
        setCoords(c);
        // resolve to the first serviceable zone client-side (authoritative check re-runs server-side)
        const km = (a, b, x, y) => {
          const R = 6371, dLat = (x - a) * Math.PI / 180, dLng = (y - b) * Math.PI / 180;
          const s = Math.sin(dLat / 2) ** 2 + Math.cos(a * Math.PI / 180) * Math.cos(x * Math.PI / 180) * Math.sin(dLng / 2) ** 2;
          return 2 * R * Math.asin(Math.sqrt(s));
        };
        const hit = zones.find((z) => km(Number(z.center_lat), Number(z.center_lng), c.lat, c.lng) <= Number(z.radius_km));
        if (hit) setZone(String(hit.id));
        resolve({ coords: c, zone: hit || null });
      },
      (err) => reject(err), { enableHighAccuracy: true, timeout: 8000 });
  }), [zones, setZone]);

  return <Ctx.Provider value={{ zones, zoneId, setZoneId: setZone, lang, setLang, coords, useMyLocation }}>{children}</Ctx.Provider>;
}
```

- [ ] **Step 5: Create the layout**

Create `food/layout/FoodLayout.js`:

```javascript
import { Outlet, Link, useNavigate } from 'react-router-dom';
import { AppBar, Toolbar, Box, Typography, IconButton, Badge, Button, Container, MenuItem, Select } from '@mui/material';
import ShoppingBagOutlinedIcon from '@mui/icons-material/ShoppingBagOutlined';
import StorefrontOutlinedIcon from '@mui/icons-material/StorefrontOutlined';
import { useSelector } from 'react-redux';
import { selectFoodCount } from '../redux/foodCartSlice';
import { useFoodLocation } from '../context/FoodLocationContext';

export default function FoodLayout() {
  const count = useSelector(selectFoodCount);
  const navigate = useNavigate();
  const loc = useFoodLocation() || {};
  return (
    <Box sx={{ minHeight: '100vh', bgcolor: 'background.default' }}>
      <AppBar position="sticky" elevation={0}>
        <Container maxWidth="lg">
          <Toolbar disableGutters sx={{ gap: 2 }}>
            <Typography variant="h5" component={Link} to="/food" sx={{ color: 'primary.main', textDecoration: 'none', fontWeight: 900 }}>
              Fabrything<Box component="span" sx={{ color: 'text.primary' }}>Food</Box>
            </Typography>
            {loc.zones && (
              <Select size="small" value={loc.zoneId || ''} displayEmpty onChange={(e) => loc.setZoneId(e.target.value)} sx={{ minWidth: 150 }}>
                <MenuItem value=""><em>Choose area</em></MenuItem>
                {loc.zones.map((z) => <MenuItem key={z.id} value={String(z.id)}>{z.name}</MenuItem>)}
              </Select>
            )}
            <Box sx={{ flexGrow: 1 }} />
            {loc.setLang && (
              <Button size="small" color="inherit" onClick={() => loc.setLang(loc.lang === 'en' ? 'bn' : 'en')}>
                {loc.lang === 'en' ? 'বাংলা' : 'EN'}
              </Button>
            )}
            <Button size="small" color="inherit" startIcon={<StorefrontOutlinedIcon />} component={Link} to="/">Store</Button>
            <IconButton color="inherit" onClick={() => navigate('/food/cart')}>
              <Badge badgeContent={count} color="primary"><ShoppingBagOutlinedIcon /></Badge>
            </IconButton>
          </Toolbar>
        </Container>
      </AppBar>
      <Container maxWidth="lg" sx={{ py: 3 }}><Outlet /></Container>
    </Box>
  );
}
```

- [ ] **Step 6: Mount in App.js**

In `src/App.js`: remove the `FoodComingSoon` import and its `{path:"food",...}` child route under the storefront. Add food imports and a top-level `/food` route. Add a `FoodApp` wrapper component (near `StorefrontWrapper`):

```javascript
import { getFoodTheme } from './food/theme';
import { FoodLocationProvider } from './food/context/FoodLocationContext';
import FoodLayout from './food/layout/FoodLayout';
import FoodHome from './food/pages/FoodHome';
import RestaurantDetail from './food/pages/RestaurantDetail';
import FoodCartPage from './food/pages/FoodCartPage';
import FoodCheckout from './food/pages/FoodCheckout';
import FoodOrderTrack from './food/pages/FoodOrderTrack';
import FoodMyOrders from './food/pages/FoodMyOrders';

function FoodApp() {
  const theme = useMemo(() => getFoodTheme(), []);
  return (
    <ThemeProvider theme={theme}>
      <FoodLocationProvider><FoodLayout /></FoodLocationProvider>
    </ThemeProvider>
  );
}
```
Add this route object to the router array (a sibling of `/` and `/vendor`):
```javascript
      {
        path:"/food",
        element:<FoodApp/>,
        children:[
          {index:true,element:<FoodHome/>},
          {path:"restaurant/:slug",element:<RestaurantDetail/>},
          {path:"cart",element:<FoodCartPage/>},
          {path:"checkout",element:<FoodCheckout/>},
          {path:"order/:code",element:<FoodOrderTrack/>},
          {path:"orders",element:<ProtectedRoute element={<FoodMyOrders/>}/>},
        ]
      },
```
Create thin placeholder page stubs now so the app compiles; Tasks 8–11 fill them:
`food/pages/FoodHome.js`, `RestaurantDetail.js`, `FoodCartPage.js`, `FoodCheckout.js`, `FoodOrderTrack.js`, `FoodMyOrders.js` — each `export default function X(){ return <div/>; }`.
Delete `storefront/pages/FoodComingSoon.js` and `FoodComingSoon.test.js`.

- [ ] **Step 7: Run tests + smoke build**

Run: `CI=true npx react-scripts test src/food/layout/FoodLayout.test.js --watchAll=false`
Expected: PASS. Then `CI=true npx react-scripts build` compiles without errors (or `npm start` and load `/food`).

- [ ] **Step 8: Commit**

```bash
git add frontend/ecommerce_inventory/src/food frontend/ecommerce_inventory/src/App.js
git rm frontend/ecommerce_inventory/src/storefront/pages/FoodComingSoon.js frontend/ecommerce_inventory/src/storefront/pages/FoodComingSoon.test.js
git commit -m "feat(food): separate themed /food app shell, layout, location context, routing (TDD)"
```

---

## Task 8: Food Home page (location gate + cuisine chips + restaurant grid)

**Files:**
- Create: `frontend/ecommerce_inventory/src/food/components/RestaurantCard.js`
- Rewrite: `frontend/ecommerce_inventory/src/food/pages/FoodHome.js`
- Test: `frontend/ecommerce_inventory/src/food/pages/FoodHome.test.js`

**Interfaces:**
- Consumes: `useFoodLocation()` (`zoneId`, `zones`, `lang`, `useMyLocation`), `useApi`, `GET food/restaurants/?zone=&search=&cuisine=&lang=`.
- `RestaurantCard` props: `{ restaurant }` where restaurant has `slug, display_name, cover_image, cuisine_type, avg_prep_minutes, base_delivery_fee, is_open`.

- [ ] **Step 1: Write the failing test**

Create `FoodHome.test.js` (mock `useApi` to return one restaurant; assert it renders and links to detail):

```javascript
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';

jest.mock('../../hooks/APIHandler', () => () => ({
  loading: false, error: '',
  callApi: jest.fn(async ({ url }) => {
    if (url.startsWith('food/restaurants')) {
      return { data: { data: { data: [{ id: 1, slug: 'r1', display_name: 'Tasty', cover_image: '', cuisine_type: 'Bengali', avg_prep_minutes: 25, base_delivery_fee: '30.00', is_open: true }] } } } };
    }
    return { data: { data: [] } };
  }),
}));
jest.mock('../context/FoodLocationContext', () => ({
  useFoodLocation: () => ({ zoneId: '1', zones: [{ id: 1, name: 'Zone 1' }], lang: 'en', useMyLocation: jest.fn() }),
}));

import FoodHome from './FoodHome';

test('renders restaurant cards for the selected zone', async () => {
  render(<MemoryRouter><FoodHome /></MemoryRouter>);
  await waitFor(() => expect(screen.getByText('Tasty')).toBeInTheDocument());
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `CI=true npx react-scripts test src/food/pages/FoodHome.test.js --watchAll=false`
Expected: FAIL — empty stub renders nothing.

- [ ] **Step 3: Build `RestaurantCard`**

Create `food/components/RestaurantCard.js`:

```javascript
import { Card, CardMedia, CardContent, Box, Typography, Chip, Stack } from '@mui/material';
import AccessTimeIcon from '@mui/icons-material/AccessTime';
import TwoWheelerIcon from '@mui/icons-material/TwoWheeler';
import { Link } from 'react-router-dom';

export default function RestaurantCard({ restaurant: r }) {
  return (
    <Card component={Link} to={`/food/restaurant/${r.slug}`} sx={{ textDecoration: 'none', display: 'block', overflow: 'hidden', opacity: r.is_open ? 1 : 0.6 }}>
      <Box sx={{ position: 'relative' }}>
        <CardMedia component="img" height="150" image={r.cover_image || 'https://placehold.co/600x300/17191F/FF6B35?text=Food'} alt={r.display_name} loading="lazy" />
        {!r.is_open && <Chip label="Closed" size="small" color="default" sx={{ position: 'absolute', top: 10, left: 10 }} />}
      </Box>
      <CardContent>
        <Typography variant="h6" noWrap sx={{ color: 'text.primary' }}>{r.display_name}</Typography>
        <Typography variant="body2" color="text.secondary" noWrap>{r.cuisine_type || 'Restaurant'}</Typography>
        <Stack direction="row" spacing={1} sx={{ mt: 1 }}>
          <Chip size="small" icon={<AccessTimeIcon />} label={`${r.avg_prep_minutes}+ min`} />
          <Chip size="small" icon={<TwoWheelerIcon />} label={`৳${r.base_delivery_fee}`} />
        </Stack>
      </CardContent>
    </Card>
  );
}
```

- [ ] **Step 4: Build `FoodHome`**

Rewrite `food/pages/FoodHome.js`:

```javascript
import { useEffect, useState, useCallback } from 'react';
import { Grid, Box, Typography, TextField, Chip, Stack, Button, CircularProgress } from '@mui/material';
import MyLocationIcon from '@mui/icons-material/MyLocation';
import useApi from '../../hooks/APIHandler';
import { useFoodLocation } from '../context/FoodLocationContext';
import RestaurantCard from '../components/RestaurantCard';

const CUISINES = ['Bengali', 'Fast Food', 'Biryani', 'Chinese', 'Pizza', 'Dessert'];

export default function FoodHome() {
  const { zoneId, lang, useMyLocation } = useFoodLocation() || {};
  const { callApi, loading } = useApi();
  const [restaurants, setRestaurants] = useState([]);
  const [search, setSearch] = useState('');
  const [cuisine, setCuisine] = useState('');

  const fetchRestaurants = useCallback(async () => {
    const params = { lang };
    if (zoneId) params.zone = zoneId;
    if (search) params.search = search;
    if (cuisine) params.cuisine = cuisine;
    const res = await callApi({ url: 'food/restaurants/', method: 'GET', params });
    setRestaurants(res?.data?.data?.data || []);
  }, [zoneId, lang, search, cuisine]); // eslint-disable-line

  useEffect(() => { fetchRestaurants(); }, [fetchRestaurants]);

  return (
    <Box>
      <Box sx={{ p: { xs: 3, md: 5 }, mb: 3, borderRadius: 4, background: 'linear-gradient(135deg,#1B1D24,#0E0F12)', border: '1px solid #262A32' }}>
        <Typography variant="h4" sx={{ color: 'text.primary', mb: 1 }}>Hungry? Order in.</Typography>
        <Typography color="text.secondary" sx={{ mb: 2 }}>Fresh food from restaurants near you.</Typography>
        <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1}>
          <TextField fullWidth size="small" placeholder="Search restaurants" value={search}
            onChange={(e) => setSearch(e.target.value)} />
          <Button variant="outlined" color="inherit" startIcon={<MyLocationIcon />}
            onClick={() => useMyLocation && useMyLocation()}>Use my location</Button>
        </Stack>
      </Box>

      <Stack direction="row" spacing={1} sx={{ mb: 3, overflowX: 'auto', pb: 1 }}>
        <Chip label="All" color={cuisine === '' ? 'primary' : 'default'} onClick={() => setCuisine('')} />
        {CUISINES.map((c) => (
          <Chip key={c} label={c} color={cuisine === c ? 'primary' : 'default'} onClick={() => setCuisine(c)} />
        ))}
      </Stack>

      {loading ? <Box sx={{ textAlign: 'center', py: 6 }}><CircularProgress /></Box>
        : restaurants.length === 0
          ? <Typography color="text.secondary" sx={{ py: 6, textAlign: 'center' }}>No restaurants deliver to this area yet.</Typography>
          : <Grid container spacing={2}>
              {restaurants.map((r) => <Grid item xs={12} sm={6} md={4} key={r.id}><RestaurantCard restaurant={r} /></Grid>)}
            </Grid>}
    </Box>
  );
}
```

- [ ] **Step 5: Run tests**

Run: `CI=true npx react-scripts test src/food/pages/FoodHome.test.js --watchAll=false`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add frontend/ecommerce_inventory/src/food/pages/FoodHome.js frontend/ecommerce_inventory/src/food/pages/FoodHome.test.js frontend/ecommerce_inventory/src/food/components/RestaurantCard.js
git commit -m "feat(food): home page with cuisine filters and zone-scoped restaurant grid (TDD)"
```

---

## Task 9: Restaurant detail + item option modal (add to cart)

**Files:**
- Create: `frontend/ecommerce_inventory/src/food/components/ItemOptionModal.js`
- Rewrite: `frontend/ecommerce_inventory/src/food/pages/RestaurantDetail.js`
- Test: `frontend/ecommerce_inventory/src/food/components/ItemOptionModal.test.js`

**Interfaces:**
- Consumes: `GET food/restaurants/<slug>/?lang=`, `addFoodItem`, `selectFoodRestaurant`.
- `ItemOptionModal` props: `{ open, item, restaurant, onClose, onAdd }`; `onAdd(line)` builds the `addFoodItem` payload including a stable `lineId` (`${itemId}:${sortedOptionIds}`) and honors each group's `is_required`/`min_select`/`max_select`.

- [ ] **Step 1: Write the failing test**

Create `ItemOptionModal.test.js`:

```javascript
import { render, screen, fireEvent } from '@testing-library/react';
import ItemOptionModal from './ItemOptionModal';

const item = {
  id: 10, display_name: 'Biriyani', price: '120.00', effective_price: '120.00',
  option_groups: [{ id: 1, name: 'Size', min_select: 1, max_select: 1, is_required: true,
    options: [{ id: 5, name: 'Large', price_delta: '50.00' }, { id: 6, name: 'Regular', price_delta: '0.00' }] }],
};

test('requires a required group before adding and emits a line', () => {
  const onAdd = jest.fn();
  render(<ItemOptionModal open item={item} restaurant={{ id: 1, slug: 'r1', display_name: 'R1' }} onClose={() => {}} onAdd={onAdd} />);
  fireEvent.click(screen.getByText('Large'));
  fireEvent.click(screen.getByRole('button', { name: /add to cart/i }));
  expect(onAdd).toHaveBeenCalledTimes(1);
  const line = onAdd.mock.calls[0][0];
  expect(line.itemId).toBe(10);
  expect(line.selectedOptions).toHaveLength(1);
  expect(line.selectedOptions[0].optionId).toBe(5);
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `CI=true npx react-scripts test src/food/components/ItemOptionModal.test.js --watchAll=false`
Expected: FAIL — module not found.

- [ ] **Step 3: Build `ItemOptionModal`**

Create `food/components/ItemOptionModal.js`:

```javascript
import { useMemo, useState } from 'react';
import { Dialog, DialogTitle, DialogContent, DialogActions, Typography, FormGroup, FormControlLabel, Checkbox, Radio, RadioGroup, Box, Button, IconButton } from '@mui/material';
import AddIcon from '@mui/icons-material/Add';
import RemoveIcon from '@mui/icons-material/Remove';

export default function ItemOptionModal({ open, item, restaurant, onClose, onAdd }) {
  const [selected, setSelected] = useState({}); // groupId -> Set(optionId)
  const [qty, setQty] = useState(1);
  if (!item) return null;

  const toggle = (group, optId) => {
    setSelected((prev) => {
      const cur = new Set(prev[group.id] || []);
      if (group.max_select === 1) { cur.clear(); cur.add(optId); }
      else if (cur.has(optId)) cur.delete(optId);
      else if (cur.size < group.max_select) cur.add(optId);
      return { ...prev, [group.id]: cur };
    });
  };

  const flatOptions = useMemo(() => {
    const map = {};
    (item.option_groups || []).forEach((g) => g.options.forEach((o) => { map[o.id] = { ...o, groupId: g.id }; }));
    return map;
  }, [item]);

  const missingRequired = (item.option_groups || []).some(
    (g) => g.is_required && (!(selected[g.id]) || selected[g.id].size < Math.max(1, g.min_select))
  );

  const submit = () => {
    const optionIds = Object.values(selected).flatMap((s) => Array.from(s));
    const selectedOptions = optionIds.map((id) => ({
      optionId: id, name: flatOptions[id].name, priceDelta: Number(flatOptions[id].price_delta),
    }));
    onAdd({
      lineId: `${item.id}:${optionIds.slice().sort((a, b) => a - b).join('-')}`,
      restaurantId: restaurant.id, restaurantSlug: restaurant.slug, restaurantName: restaurant.display_name,
      itemId: item.id, name: item.display_name, image: item.image || '',
      unitPrice: Number(item.effective_price ?? item.price), quantity: qty, selectedOptions,
    });
    onClose();
  };

  return (
    <Dialog open={open} onClose={onClose} fullWidth maxWidth="xs">
      <DialogTitle>{item.display_name}</DialogTitle>
      <DialogContent dividers>
        {(item.option_groups || []).map((g) => (
          <Box key={g.id} sx={{ mb: 2 }}>
            <Typography variant="subtitle2">{g.name}{g.is_required ? ' *' : ''}</Typography>
            {g.max_select === 1 ? (
              <RadioGroup>
                {g.options.map((o) => (
                  <FormControlLabel key={o.id} control={<Radio checked={!!selected[g.id]?.has(o.id)} onChange={() => toggle(g, o.id)} />}
                    label={`${o.name}${Number(o.price_delta) ? ` +৳${o.price_delta}` : ''}`} />
                ))}
              </RadioGroup>
            ) : (
              <FormGroup>
                {g.options.map((o) => (
                  <FormControlLabel key={o.id} control={<Checkbox checked={!!selected[g.id]?.has(o.id)} onChange={() => toggle(g, o.id)} />}
                    label={`${o.name}${Number(o.price_delta) ? ` +৳${o.price_delta}` : ''}`} />
                ))}
              </FormGroup>
            )}
          </Box>
        ))}
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <IconButton onClick={() => setQty((q) => Math.max(1, q - 1))}><RemoveIcon /></IconButton>
          <Typography>{qty}</Typography>
          <IconButton onClick={() => setQty((q) => q + 1)}><AddIcon /></IconButton>
        </Box>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose} color="inherit">Cancel</Button>
        <Button variant="contained" onClick={submit} disabled={missingRequired}>Add to cart</Button>
      </DialogActions>
    </Dialog>
  );
}
```

- [ ] **Step 4: Build `RestaurantDetail`**

Rewrite `food/pages/RestaurantDetail.js` — fetch detail, render cover + category-sectioned menu, open modal on dish click, enforce one-restaurant guard using `window.confirm` before a cross-restaurant add:

```javascript
import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { useDispatch, useSelector } from 'react-redux';
import { Box, Typography, Card, CardContent, Grid, Chip, Stack, Divider, CircularProgress, Button } from '@mui/material';
import useApi from '../../hooks/APIHandler';
import { useFoodLocation } from '../context/FoodLocationContext';
import { addFoodItem, selectFoodRestaurant } from '../redux/foodCartSlice';
import ItemOptionModal from '../components/ItemOptionModal';

export default function RestaurantDetail() {
  const { slug } = useParams();
  const { lang } = useFoodLocation() || {};
  const { callApi, loading } = useApi();
  const dispatch = useDispatch();
  const cartRestaurant = useSelector(selectFoodRestaurant);
  const [data, setData] = useState(null);
  const [modalItem, setModalItem] = useState(null);

  useEffect(() => { (async () => {
    const res = await callApi({ url: `food/restaurants/${slug}/`, method: 'GET', params: { lang } });
    setData(res?.data?.data || null);
  })(); }, [slug, lang]); // eslint-disable-line

  const addLine = (line) => {
    if (cartRestaurant.id && cartRestaurant.id !== line.restaurantId) {
      if (!window.confirm(`Your cart has items from ${cartRestaurant.name}. Start a new order?`)) return;
      dispatch(addFoodItem({ ...line, force: true }));
    } else {
      dispatch(addFoodItem(line));
    }
  };

  const onItemClick = (item) => {
    if (item.option_groups && item.option_groups.length) { setModalItem(item); return; }
    addLine({
      lineId: `${item.id}:`, restaurantId: data.id, restaurantSlug: data.slug, restaurantName: data.display_name,
      itemId: item.id, name: item.display_name, image: item.image || '',
      unitPrice: Number(item.effective_price ?? item.price), quantity: 1, selectedOptions: [],
    });
  };

  if (loading || !data) return <Box sx={{ textAlign: 'center', py: 8 }}><CircularProgress /></Box>;

  return (
    <Box>
      <Box sx={{ height: 200, borderRadius: 4, mb: 2, backgroundImage: `url(${data.cover_image || 'https://placehold.co/1200x400/17191F/FF6B35?text=Food'})`, backgroundSize: 'cover', backgroundPosition: 'center' }} />
      <Typography variant="h4">{data.display_name}</Typography>
      <Stack direction="row" spacing={1} sx={{ my: 1 }}>
        <Chip size="small" label={data.is_open ? 'Open' : 'Closed'} color={data.is_open ? 'success' : 'default'} />
        <Chip size="small" label={`${data.avg_prep_minutes}+ min`} />
        <Chip size="small" label={`Delivery ৳${data.base_delivery_fee}`} />
        {Number(data.min_order_amount) > 0 && <Chip size="small" label={`Min ৳${data.min_order_amount}`} />}
      </Stack>
      {(data.categories || []).map((cat) => (
        <Box key={cat.id} sx={{ mt: 3 }}>
          <Typography variant="h6" sx={{ mb: 1 }}>{cat.name}</Typography>
          <Divider sx={{ mb: 2 }} />
          <Grid container spacing={2}>
            {cat.items.map((item) => (
              <Grid item xs={12} sm={6} key={item.id}>
                <Card sx={{ display: 'flex', justifyContent: 'space-between', p: 2, cursor: 'pointer' }} onClick={() => onItemClick(item)}>
                  <CardContent sx={{ flex: 1, p: 0 }}>
                    <Typography variant="subtitle1">{item.display_name}</Typography>
                    <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>{item.description}</Typography>
                    <Typography variant="subtitle2" color="primary.main">৳{item.effective_price}</Typography>
                  </CardContent>
                  <Button variant="contained" size="small" sx={{ alignSelf: 'center' }}>Add</Button>
                </Card>
              </Grid>
            ))}
          </Grid>
        </Box>
      ))}
      <ItemOptionModal open={!!modalItem} item={modalItem} restaurant={data} onClose={() => setModalItem(null)} onAdd={addLine} />
    </Box>
  );
}
```

- [ ] **Step 5: Run tests**

Run: `CI=true npx react-scripts test src/food/components/ItemOptionModal.test.js --watchAll=false`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add frontend/ecommerce_inventory/src/food/pages/RestaurantDetail.js frontend/ecommerce_inventory/src/food/components/ItemOptionModal.js frontend/ecommerce_inventory/src/food/components/ItemOptionModal.test.js
git commit -m "feat(food): restaurant detail menu + item option modal with one-restaurant guard (TDD)"
```

---

## Task 10: Food cart page + COD checkout

**Files:**
- Rewrite: `frontend/ecommerce_inventory/src/food/pages/FoodCartPage.js`
- Rewrite: `frontend/ecommerce_inventory/src/food/pages/FoodCheckout.js`
- Test: `frontend/ecommerce_inventory/src/food/pages/FoodCheckout.test.js`

**Interfaces:**
- Consumes: cart selectors, `useFoodLocation`, `POST food/orders/`.
- Checkout posts `{ restaurant_slug, zone_id|lat/lng, contact_name, contact_phone, delivery_address, tip, items:[{item_id, quantity, option_ids}] }`, then `clearFoodCart()` and navigates to `/food/order/<code>`.

- [ ] **Step 1: Write the failing test**

Create `FoodCheckout.test.js` — seed the store with a cart, mock the POST, submit, assert navigation to the order code:

```javascript
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { Provider } from 'react-redux';
import { MemoryRouter } from 'react-router-dom';
import store from '../../redux/store/store';
import { addFoodItem } from '../redux/foodCartSlice';

const mockNavigate = jest.fn();
jest.mock('react-router-dom', () => ({ ...jest.requireActual('react-router-dom'), useNavigate: () => mockNavigate }));
const mockPost = jest.fn(async () => ({ data: { data: { order_code: 'FD-ABC123' } }, status: 201 }));
jest.mock('../../hooks/APIHandler', () => () => ({ loading: false, error: '', callApi: mockPost }));
jest.mock('../context/FoodLocationContext', () => ({
  useFoodLocation: () => ({ zoneId: '1', zones: [{ id: 1, name: 'Zone 1' }], useMyLocation: jest.fn() }),
}));

import FoodCheckout from './FoodCheckout';

test('places a COD order and navigates to tracking', async () => {
  store.dispatch(addFoodItem({ lineId: 'l1', restaurantId: 1, restaurantSlug: 'r1', restaurantName: 'R1', itemId: 10, name: 'Biriyani', unitPrice: 120, quantity: 1, selectedOptions: [] }));
  render(<Provider store={store}><MemoryRouter><FoodCheckout /></MemoryRouter></Provider>);
  fireEvent.change(screen.getByLabelText(/name/i), { target: { value: 'Karim' } });
  fireEvent.change(screen.getByLabelText(/phone/i), { target: { value: '017' } });
  fireEvent.change(screen.getByLabelText(/address/i), { target: { value: 'Village Rd' } });
  fireEvent.click(screen.getByRole('button', { name: /place order/i }));
  await waitFor(() => expect(mockNavigate).toHaveBeenCalledWith('/food/order/FD-ABC123'));
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `CI=true npx react-scripts test src/food/pages/FoodCheckout.test.js --watchAll=false`
Expected: FAIL — stub renders nothing.

- [ ] **Step 3: Build `FoodCartPage`**

Rewrite `food/pages/FoodCartPage.js`:

```javascript
import { useNavigate } from 'react-router-dom';
import { useSelector, useDispatch } from 'react-redux';
import { Box, Typography, Card, IconButton, Button, Divider, Stack } from '@mui/material';
import AddIcon from '@mui/icons-material/Add';
import RemoveIcon from '@mui/icons-material/Remove';
import DeleteOutlineIcon from '@mui/icons-material/DeleteOutline';
import { selectFoodCart, selectFoodSubtotal, selectFoodRestaurant, updateFoodQty, removeFoodItem } from '../redux/foodCartSlice';

export default function FoodCartPage() {
  const items = useSelector(selectFoodCart);
  const subtotal = useSelector(selectFoodSubtotal);
  const restaurant = useSelector(selectFoodRestaurant);
  const dispatch = useDispatch();
  const navigate = useNavigate();

  if (!items.length) return <Typography color="text.secondary" sx={{ py: 8, textAlign: 'center' }}>Your food bag is empty.</Typography>;

  return (
    <Box sx={{ maxWidth: 600, mx: 'auto' }}>
      <Typography variant="h5" sx={{ mb: 2 }}>Your bag · {restaurant.name}</Typography>
      {items.map((i) => (
        <Card key={i.lineId} sx={{ p: 2, mb: 1, display: 'flex', alignItems: 'center', gap: 2 }}>
          <Box sx={{ flex: 1 }}>
            <Typography>{i.name}</Typography>
            {i.selectedOptions.length > 0 && <Typography variant="caption" color="text.secondary">{i.selectedOptions.map((o) => o.name).join(', ')}</Typography>}
            <Typography variant="body2" color="primary.main">৳{(Number(i.unitPrice) + i.selectedOptions.reduce((s, o) => s + Number(o.priceDelta), 0)) * i.quantity}</Typography>
          </Box>
          <IconButton size="small" onClick={() => dispatch(updateFoodQty({ lineId: i.lineId, quantity: i.quantity - 1 }))}><RemoveIcon /></IconButton>
          <Typography>{i.quantity}</Typography>
          <IconButton size="small" onClick={() => dispatch(updateFoodQty({ lineId: i.lineId, quantity: i.quantity + 1 }))}><AddIcon /></IconButton>
          <IconButton size="small" color="error" onClick={() => dispatch(removeFoodItem({ lineId: i.lineId }))}><DeleteOutlineIcon /></IconButton>
        </Card>
      ))}
      <Divider sx={{ my: 2 }} />
      <Stack direction="row" justifyContent="space-between"><Typography>Subtotal</Typography><Typography>৳{subtotal}</Typography></Stack>
      <Button fullWidth variant="contained" sx={{ mt: 2 }} onClick={() => navigate('/food/checkout')}>Proceed to checkout</Button>
    </Box>
  );
}
```

- [ ] **Step 4: Build `FoodCheckout`**

Rewrite `food/pages/FoodCheckout.js`:

```javascript
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useSelector, useDispatch } from 'react-redux';
import { Box, Typography, TextField, Button, Card, Stack, Divider, MenuItem, Alert } from '@mui/material';
import { toast } from 'react-toastify';
import useApi from '../../hooks/APIHandler';
import { useFoodLocation } from '../context/FoodLocationContext';
import { selectFoodCart, selectFoodSubtotal, selectFoodRestaurant, selectFoodTip, clearFoodCart } from '../redux/foodCartSlice';

export default function FoodCheckout() {
  const items = useSelector(selectFoodCart);
  const subtotal = useSelector(selectFoodSubtotal);
  const restaurant = useSelector(selectFoodRestaurant);
  const tip = useSelector(selectFoodTip);
  const { zoneId, zones, coords, useMyLocation } = useFoodLocation() || {};
  const { callApi, loading } = useApi();
  const dispatch = useDispatch();
  const navigate = useNavigate();
  const [form, setForm] = useState({ name: '', phone: '', address: '' });
  const [zone, setZone] = useState(zoneId || '');
  const [err, setErr] = useState('');

  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }));

  const submit = async () => {
    setErr('');
    if (!form.name || !form.phone || !form.address) { setErr('Name, phone and address are required.'); return; }
    if (!zone && !coords) { setErr('Choose a delivery area or use your location.'); return; }
    const body = {
      restaurant_slug: restaurant.slug, contact_name: form.name, contact_phone: form.phone,
      delivery_address: form.address, tip,
      items: items.map((i) => ({ item_id: i.itemId, quantity: i.quantity, option_ids: i.selectedOptions.map((o) => o.optionId) })),
    };
    if (zone) body.zone_id = zone; else if (coords) { body.lat = coords.lat; body.lng = coords.lng; }
    const res = await callApi({ url: 'food/orders/', method: 'POST', body });
    if (res?.status === 201) {
      const code = res.data.data.order_code;
      dispatch(clearFoodCart());
      toast.success('Order placed!');
      navigate(`/food/order/${code}`);
    } else if (res?.data?.data) {
      setErr(Array.isArray(res.data.data) ? res.data.data.join(' ') : String(res.data.data));
    }
  };

  if (!items.length) return <Typography color="text.secondary" sx={{ py: 8, textAlign: 'center' }}>Your food bag is empty.</Typography>;

  return (
    <Box sx={{ maxWidth: 560, mx: 'auto' }}>
      <Typography variant="h5" sx={{ mb: 2 }}>Checkout</Typography>
      {err && <Alert severity="error" sx={{ mb: 2 }}>{err}</Alert>}
      <Card sx={{ p: 2, mb: 2 }}>
        <Stack spacing={2}>
          <TextField label="Name" value={form.name} onChange={set('name')} fullWidth />
          <TextField label="Phone" value={form.phone} onChange={set('phone')} fullWidth />
          <TextField label="Delivery address" value={form.address} onChange={set('address')} fullWidth multiline rows={2} />
          <TextField select label="Delivery area" value={zone} onChange={(e) => setZone(e.target.value)} fullWidth>
            <MenuItem value=""><em>Select area</em></MenuItem>
            {(zones || []).map((z) => <MenuItem key={z.id} value={String(z.id)}>{z.name}</MenuItem>)}
          </TextField>
          <Button variant="outlined" color="inherit" onClick={() => useMyLocation && useMyLocation().then(() => toast.info('Location detected')).catch(() => toast.error('Could not get location'))}>
            Use my location instead
          </Button>
        </Stack>
      </Card>
      <Card sx={{ p: 2, mb: 2 }}>
        <Stack direction="row" justifyContent="space-between"><Typography>Subtotal</Typography><Typography>৳{subtotal}</Typography></Stack>
        <Typography variant="caption" color="text.secondary">Delivery fee & total are confirmed by the restaurant at checkout.</Typography>
        <Divider sx={{ my: 1 }} />
        <Typography variant="subtitle2">Payment: Cash on Delivery</Typography>
      </Card>
      <Button fullWidth variant="contained" disabled={loading} onClick={submit}>Place order (COD)</Button>
    </Box>
  );
}
```

- [ ] **Step 5: Run tests**

Run: `CI=true npx react-scripts test src/food/pages/FoodCheckout.test.js --watchAll=false`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add frontend/ecommerce_inventory/src/food/pages/FoodCartPage.js frontend/ecommerce_inventory/src/food/pages/FoodCheckout.js frontend/ecommerce_inventory/src/food/pages/FoodCheckout.test.js
git commit -m "feat(food): cart page + guest COD checkout posting to order API (TDD)"
```

---

## Task 11: Order confirmation / tracking + my orders

**Files:**
- Rewrite: `frontend/ecommerce_inventory/src/food/pages/FoodOrderTrack.js`
- Rewrite: `frontend/ecommerce_inventory/src/food/pages/FoodMyOrders.js`
- Test: `frontend/ecommerce_inventory/src/food/pages/FoodOrderTrack.test.js`

**Interfaces:**
- Consumes: `GET food/orders/<code>/?phone=`, `GET food/orders/`.
- Track page reads `:code` from the route; if the user is a guest it prompts for phone; renders a status stepper from `FoodOrder.Status` order; polls every 15s while status is not terminal.

- [ ] **Step 1: Write the failing test**

Create `FoodOrderTrack.test.js`:

```javascript
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Routes, Route } from 'react-router-dom';

jest.mock('../../hooks/APIHandler', () => () => ({
  loading: false, error: '',
  callApi: jest.fn(async () => ({ status: 200, data: { data: {
    order_code: 'FD-ABC123', status: 'PREPARING', restaurant_name: 'R1', total: '150.00',
    eta_minutes: 45, items: [{ id: 1, item_name: 'Biriyani', quantity: 1, line_total: '120.00', selected_options: [] }],
  } } })),
}));

import FoodOrderTrack from './FoodOrderTrack';

test('renders order code and current status', async () => {
  render(<MemoryRouter initialEntries={['/food/order/FD-ABC123']}>
    <Routes><Route path="/food/order/:code" element={<FoodOrderTrack />} /></Routes>
  </MemoryRouter>);
  await waitFor(() => expect(screen.getByText(/FD-ABC123/)).toBeInTheDocument());
  expect(screen.getByText(/preparing/i)).toBeInTheDocument();
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `CI=true npx react-scripts test src/food/pages/FoodOrderTrack.test.js --watchAll=false`
Expected: FAIL — stub renders nothing.

- [ ] **Step 3: Build `FoodOrderTrack`**

Rewrite `food/pages/FoodOrderTrack.js`:

```javascript
import { useEffect, useState, useCallback } from 'react';
import { useParams } from 'react-router-dom';
import { Box, Typography, Card, Stepper, Step, StepLabel, Divider, Stack, TextField, Button, CircularProgress } from '@mui/material';
import useApi from '../../hooks/APIHandler';

const STEPS = ['PLACED', 'CONFIRMED', 'PREPARING', 'OUT_FOR_DELIVERY', 'DELIVERED'];
const LABELS = { PLACED: 'Placed', CONFIRMED: 'Confirmed', PREPARING: 'Preparing', OUT_FOR_DELIVERY: 'On the way', DELIVERED: 'Delivered' };

export default function FoodOrderTrack() {
  const { code } = useParams();
  const { callApi } = useApi();
  const [order, setOrder] = useState(null);
  const [phone, setPhone] = useState('');
  const [needPhone, setNeedPhone] = useState(false);
  const [loading, setLoading] = useState(true);

  const fetchOrder = useCallback(async (ph) => {
    setLoading(true);
    const params = {};
    if (ph) params.phone = ph;
    const res = await callApi({ url: `food/orders/${code}/`, method: 'GET', params });
    setLoading(false);
    if (res?.status === 200) { setOrder(res.data.data); setNeedPhone(false); }
    else if (res?.status === 404 && !ph) setNeedPhone(true);
  }, [code]); // eslint-disable-line

  useEffect(() => { fetchOrder(); }, [fetchOrder]);

  useEffect(() => {
    if (!order || ['DELIVERED', 'CANCELLED'].includes(order.status)) return;
    const t = setInterval(() => fetchOrder(phone), 15000);
    return () => clearInterval(t);
  }, [order, phone, fetchOrder]);

  if (needPhone) return (
    <Box sx={{ maxWidth: 400, mx: 'auto', py: 6 }}>
      <Typography variant="h6" sx={{ mb: 2 }}>Enter your phone to view order {code}</Typography>
      <Stack direction="row" spacing={1}>
        <TextField size="small" label="Phone" value={phone} onChange={(e) => setPhone(e.target.value)} fullWidth />
        <Button variant="contained" onClick={() => fetchOrder(phone)}>View</Button>
      </Stack>
    </Box>
  );
  if (loading || !order) return <Box sx={{ textAlign: 'center', py: 8 }}><CircularProgress /></Box>;

  const activeStep = order.status === 'CANCELLED' ? -1 : STEPS.indexOf(order.status);

  return (
    <Box sx={{ maxWidth: 640, mx: 'auto' }}>
      <Typography variant="h5">Order {order.order_code}</Typography>
      <Typography color="text.secondary" sx={{ mb: 3 }}>{order.restaurant_name} · ETA ~{order.eta_minutes} min</Typography>
      {order.status === 'CANCELLED'
        ? <Typography color="error">This order was cancelled.</Typography>
        : <Stepper activeStep={activeStep} alternativeLabel sx={{ mb: 3 }}>
            {STEPS.map((s) => <Step key={s}><StepLabel>{LABELS[s]}</StepLabel></Step>)}
          </Stepper>}
      <Card sx={{ p: 2 }}>
        {order.items.map((it) => (
          <Stack key={it.id} direction="row" justifyContent="space-between" sx={{ mb: 1 }}>
            <Typography>{it.quantity}× {it.item_name}</Typography>
            <Typography>৳{it.line_total}</Typography>
          </Stack>
        ))}
        <Divider sx={{ my: 1 }} />
        <Stack direction="row" justifyContent="space-between"><Typography>Total (COD)</Typography><Typography fontWeight={700}>৳{order.total}</Typography></Stack>
      </Card>
    </Box>
  );
}
```

- [ ] **Step 4: Build `FoodMyOrders`**

Rewrite `food/pages/FoodMyOrders.js` (auth history list; each row links to `/food/order/<code>`):

```javascript
import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Box, Typography, Card, Stack, Chip, CircularProgress } from '@mui/material';
import useApi from '../../hooks/APIHandler';

export default function FoodMyOrders() {
  const { callApi, loading } = useApi();
  const [orders, setOrders] = useState([]);
  useEffect(() => { (async () => {
    const res = await callApi({ url: 'food/orders/', method: 'GET' });
    setOrders(res?.data?.data || []);
  })(); }, []); // eslint-disable-line

  if (loading) return <Box sx={{ textAlign: 'center', py: 8 }}><CircularProgress /></Box>;
  if (!orders.length) return <Typography color="text.secondary" sx={{ py: 8, textAlign: 'center' }}>No food orders yet.</Typography>;

  return (
    <Box sx={{ maxWidth: 640, mx: 'auto' }}>
      <Typography variant="h5" sx={{ mb: 2 }}>My food orders</Typography>
      {orders.map((o) => (
        <Card key={o.id} component={Link} to={`/food/order/${o.order_code}`} sx={{ p: 2, mb: 1, display: 'block', textDecoration: 'none' }}>
          <Stack direction="row" justifyContent="space-between" alignItems="center">
            <Box>
              <Typography>{o.order_code} · {o.restaurant_name}</Typography>
              <Typography variant="body2" color="text.secondary">৳{o.total}</Typography>
            </Box>
            <Chip size="small" label={o.status} color={o.status === 'DELIVERED' ? 'success' : 'default'} />
          </Stack>
        </Card>
      ))}
    </Box>
  );
}
```

- [ ] **Step 5: Run tests**

Run: `CI=true npx react-scripts test src/food/pages/FoodOrderTrack.test.js --watchAll=false`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add frontend/ecommerce_inventory/src/food/pages/FoodOrderTrack.js frontend/ecommerce_inventory/src/food/pages/FoodMyOrders.js frontend/ecommerce_inventory/src/food/pages/FoodOrderTrack.test.js
git commit -m "feat(food): order tracking stepper (guest+auth) and my-orders history (TDD)"
```

---

## Task 12: Minimal vendor order-management UI (fulfillment loop)

**Files:**
- Create: `frontend/ecommerce_inventory/src/vendor/VendorOrders.js`
- Modify: `frontend/ecommerce_inventory/src/App.js` (add `/vendor/orders` child route)
- Modify: `frontend/ecommerce_inventory/src/vendor/VendorLayout.js` (add nav link to orders)
- Test: `frontend/ecommerce_inventory/src/vendor/VendorOrders.test.js`

**Interfaces:**
- Consumes: `GET food/vendor/orders/`, `PATCH food/vendor/orders/<id>/status/`.
- Advance buttons offer the next legal status per `FoodOrder.ALLOWED_TRANSITIONS`.

- [ ] **Step 1: Write the failing test**

Create `VendorOrders.test.js`:

```javascript
import { render, screen, waitFor, fireEvent } from '@testing-library/react';

const patch = jest.fn(async () => ({ status: 200, data: { data: { id: 1, status: 'CONFIRMED' } } }));
jest.mock('../hooks/APIHandler', () => () => ({
  loading: false, error: '',
  callApi: jest.fn(async ({ url, method }) => {
    if (method === 'PATCH') return patch();
    return { status: 200, data: { data: [{ id: 1, order_code: 'FD-1', status: 'PLACED', guest_name: 'A', total: '150.00', items: [] }] } };
  }),
}));

import VendorOrders from './VendorOrders';

test('lists vendor orders and advances status', async () => {
  render(<VendorOrders />);
  await waitFor(() => expect(screen.getByText('FD-1')).toBeInTheDocument());
  fireEvent.click(screen.getByRole('button', { name: /confirm/i }));
  await waitFor(() => expect(patch).toHaveBeenCalled());
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `CI=true npx react-scripts test src/vendor/VendorOrders.test.js --watchAll=false`
Expected: FAIL — module not found.

- [ ] **Step 3: Build `VendorOrders`**

Create `vendor/VendorOrders.js`:

```javascript
import { useEffect, useState, useCallback } from 'react';
import { Box, Typography, Card, Stack, Chip, Button, CircularProgress } from '@mui/material';
import useApi from '../hooks/APIHandler';

const NEXT = {
  PLACED: [['CONFIRMED', 'Confirm'], ['CANCELLED', 'Cancel']],
  CONFIRMED: [['PREPARING', 'Start preparing'], ['CANCELLED', 'Cancel']],
  PREPARING: [['OUT_FOR_DELIVERY', 'Send out'], ['CANCELLED', 'Cancel']],
  OUT_FOR_DELIVERY: [['DELIVERED', 'Mark delivered']],
  DELIVERED: [], CANCELLED: [],
};

export default function VendorOrders() {
  const { callApi, loading } = useApi();
  const [orders, setOrders] = useState([]);

  const fetchOrders = useCallback(async () => {
    const res = await callApi({ url: 'food/vendor/orders/', method: 'GET' });
    setOrders(res?.data?.data || []);
  }, []); // eslint-disable-line
  useEffect(() => { fetchOrders(); }, [fetchOrders]);

  const advance = async (id, status) => {
    const res = await callApi({ url: `food/vendor/orders/${id}/status/`, method: 'PATCH', body: { status } });
    if (res?.status === 200) fetchOrders();
  };

  if (loading && !orders.length) return <Box sx={{ textAlign: 'center', py: 8 }}><CircularProgress /></Box>;

  return (
    <Box sx={{ p: 2, maxWidth: 800, mx: 'auto' }}>
      <Typography variant="h5" sx={{ mb: 2 }}>Incoming orders</Typography>
      {orders.length === 0 && <Typography color="text.secondary">No orders yet.</Typography>}
      {orders.map((o) => (
        <Card key={o.id} sx={{ p: 2, mb: 1 }}>
          <Stack direction="row" justifyContent="space-between" alignItems="center">
            <Box>
              <Typography fontWeight={700}>{o.order_code}</Typography>
              <Typography variant="body2" color="text.secondary">{o.guest_name} · ৳{o.total} · {o.items.length} items</Typography>
            </Box>
            <Chip label={o.status} size="small" />
          </Stack>
          <Stack direction="row" spacing={1} sx={{ mt: 1 }}>
            {(NEXT[o.status] || []).map(([status, label]) => (
              <Button key={status} size="small" variant={status === 'CANCELLED' ? 'outlined' : 'contained'}
                color={status === 'CANCELLED' ? 'error' : 'primary'} onClick={() => advance(o.id, status)}>{label}</Button>
            ))}
          </Stack>
        </Card>
      ))}
    </Box>
  );
}
```

- [ ] **Step 4: Wire route + nav**

In `App.js`, under the `/vendor` children, add:
```javascript
          {path:"orders",element:<VendorOrders/>},
```
and `import VendorOrders from './vendor/VendorOrders';`. In `VendorLayout.js`, add a nav link to `/vendor/orders` labeled "Orders" alongside the existing profile/menu links (match the existing link markup).

- [ ] **Step 5: Run tests + full frontend food suite**

Run: `CI=true npx react-scripts test src/food src/vendor/VendorOrders.test.js --watchAll=false`
Expected: PASS across the food + vendor-orders tests.

- [ ] **Step 6: Commit**

```bash
git add frontend/ecommerce_inventory/src/vendor/VendorOrders.js frontend/ecommerce_inventory/src/vendor/VendorLayout.js frontend/ecommerce_inventory/src/App.js
git commit -m "feat(food): minimal vendor order-management UI to close the COD loop (TDD)"
```

---

## Final verification (before handing back for manual merge)

- [ ] Backend full suite: `python manage.py test food catalog -v 2` — all green.
- [ ] Frontend food suite: `CI=true npx react-scripts test src/food src/vendor --watchAll=false` — all green.
- [ ] Manual smoke (dev servers up): seed data (`seed_food_modules`, seed a restaurant/menu, `seed_bd_store`), then as a guest go `/` → click **Food** → `/food` switches theme → pick a zone → open a restaurant → add a dish (with options) → cart → checkout (COD) → land on tracking. Log in as the restaurant vendor → `/vendor/orders` → advance to Delivered → tracking page reflects it.
- [ ] Admin: confirm Manage Products now lists seeded products.
- [ ] Report results to the human and provide the manual commit/pull/merge instructions (do NOT push or merge automatically).

## Spec coverage self-check
- Separate themed `/food` app (DoD 1) → Task 7. Guest COD end-to-end (DoD 2) → Tasks 2–5, 10. Tracking guest+auth (DoD 3) → Tasks 4, 11. Vendor/admin advance to delivered (DoD 4) → Tasks 5, 12. Admin products fix (DoD 5) → Task 1. Tests (DoD 6) → every task. Zone dropdown primary + optional geolocation → Tasks 7 (context), 10 (checkout). One restaurant per cart → Task 6 (slice) + Task 9 (UI guard). bn/en toggle → Task 7 (layout) + lang param throughout.
