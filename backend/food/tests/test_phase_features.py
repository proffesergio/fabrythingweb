from datetime import time, timedelta
from decimal import Decimal
from django.test import TestCase
from django.utils import timezone
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework.exceptions import ValidationError
from rest_framework_simplejwt.tokens import RefreshToken
from food.models import (Restaurant, RestaurantHours, DeliveryZone, RestaurantZone,
                         FoodCategory, FoodItem, Coupon, FoodOrder, Rider, PaymentTransaction,
                         Notification, LoyaltyAccount)
from food.services import place_food_cod_order

User = get_user_model()


def auth(c, u):
    c.credentials(HTTP_AUTHORIZATION=f"Bearer {RefreshToken.for_user(u).access_token}")


def make_restaurant(**over):
    z = DeliveryZone.objects.create(name="Z", center_lat="23.8", center_lng="90.4", radius_km="5")
    r = Restaurant.objects.create(name="R", slug="r", status=Restaurant.Status.ACTIVE, is_open=True,
                                  base_delivery_fee=Decimal("30.00"), min_order_amount=Decimal("0.00"), **over)
    RestaurantZone.objects.create(restaurant=r, zone=z)
    for wd in range(7):
        RestaurantHours.objects.create(restaurant=r, weekday=wd, open_time="00:00", close_time="23:59")
    cat = FoodCategory.objects.create(restaurant=r, name="Main")
    item = FoodItem.objects.create(restaurant=r, category_id=cat, name="Biriyani", slug="biriyani", price=Decimal("200.00"))
    return r, z, item


def lines(item, qty=1):
    return [{"item_id": item.id, "quantity": qty, "option_ids": []}]


class CouponTests(TestCase):
    def test_coupon_applies_discount_and_increments_usage(self):
        r, z, item = make_restaurant()
        c = Coupon.objects.create(code="SAVE20", restaurant=r, discount_type=Coupon.DiscountType.PERCENT,
                                  discount_value=Decimal("20.00"))
        order = place_food_cod_order(customer=None, restaurant_slug="r", items=lines(item),
                                     contact_name="A", contact_phone="1", delivery_address="a",
                                     zone_id=z.id, coupon_code="SAVE20")
        self.assertEqual(order.discount, Decimal("40.00"))  # 20% of 200
        self.assertEqual(order.total, Decimal("190.00"))    # 200 - 40 + 30 fee
        c.refresh_from_db()
        self.assertEqual(c.used_count, 1)

    def test_invalid_coupon_rejected(self):
        r, z, item = make_restaurant()
        with self.assertRaises(ValidationError):
            place_food_cod_order(customer=None, restaurant_slug="r", items=lines(item),
                                 contact_name="A", contact_phone="1", delivery_address="a",
                                 zone_id=z.id, coupon_code="NOPE")


class ScheduleBusyTests(TestCase):
    def test_scheduled_item_rejected_outside_window(self):
        r, z, item = make_restaurant()
        now = timezone.localtime()
        # window that does NOT include now (1 minute in the future to 2 minutes)
        item.available_from = (now + timedelta(hours=2)).time()
        item.available_to = (now + timedelta(hours=3)).time()
        item.save()
        with self.assertRaises(ValidationError):
            place_food_cod_order(customer=None, restaurant_slug="r", items=lines(item),
                                 contact_name="A", contact_phone="1", delivery_address="a", zone_id=z.id)

    def test_busy_restaurant_rejects_orders(self):
        r, z, item = make_restaurant(is_accepting_orders=False)
        with self.assertRaises(ValidationError):
            place_food_cod_order(customer=None, restaurant_slug="r", items=lines(item),
                                 contact_name="A", contact_phone="1", delivery_address="a", zone_id=z.id)


class PaymentLoyaltyNotifyTests(TestCase):
    def test_online_payment_marks_collected(self):
        r, z, item = make_restaurant()
        order = place_food_cod_order(customer=None, restaurant_slug="r", items=lines(item),
                                     contact_name="A", contact_phone="1", delivery_address="a",
                                     zone_id=z.id, payment_method="BKASH")
        self.assertEqual(order.payment_method, "BKASH")
        self.assertEqual(order.payment_status, "COLLECTED")
        pay = PaymentTransaction.objects.get(order=order)
        self.assertEqual(pay.status, PaymentTransaction.Status.SUCCESS)

    def test_auth_order_awards_points_and_notification(self):
        r, z, item = make_restaurant()
        u = User.objects.create(username="cust", email="c@x.com", role="Customer")
        order = place_food_cod_order(customer=u, restaurant_slug="r", items=lines(item),
                                     contact_name="A", contact_phone="1", delivery_address="a", zone_id=z.id)
        acct = LoyaltyAccount.objects.get(user=u)
        self.assertEqual(acct.points, 4)  # 200 / 50
        self.assertTrue(Notification.objects.filter(user=u, order_code=order.order_code).exists())


class RiderDispatchTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = User.objects.create(username="adm", email="adm@x.com", role="Admin")
        self.r, self.z, self.item = make_restaurant()
        self.order = FoodOrder.objects.create(restaurant=self.r, guest_name="G", guest_phone="1",
                                              delivery_address="a", subtotal=Decimal("200"),
                                              delivery_fee=Decimal("30"), tip=Decimal("10"), total=Decimal("240"),
                                              status=FoodOrder.Status.OUT_FOR_DELIVERY)

    def test_admin_creates_rider_with_login(self):
        auth(self.client, self.admin)
        res = self.client.post("/api/food/admin/riders/", {
            "name": "Karim", "phone": "017", "vehicle_type": "BIKE",
            "owner": {"username": "rider1", "email": "rider1@x.com", "password": "pass12345"},
        }, format="json")
        self.assertEqual(res.status_code, 201, res.content)
        rider = Rider.objects.get(name="Karim")
        self.assertEqual(rider.user.role, "Rider")

    def test_assign_and_rider_delivers_credits_earning(self):
        rider_user = User.objects.create(username="r1", email="r1@x.com", role="Rider")
        rider = Rider.objects.create(user=rider_user, name="R1", is_verified=True)
        auth(self.client, self.admin)
        a = self.client.post(f"/api/food/admin/orders/{self.order.id}/assign/", {"rider_id": rider.id}, format="json")
        self.assertEqual(a.status_code, 200, a.content)
        self.order.refresh_from_db()
        self.assertEqual(self.order.rider_id, rider.id)
        # rider marks delivered
        rc = APIClient(); auth(rc, rider_user)
        d = rc.patch(f"/api/food/rider/orders/{self.order.id}/status/", {"status": "DELIVERED"}, format="json")
        self.assertEqual(d.status_code, 200, d.content)
        rider.refresh_from_db()
        self.assertEqual(rider.total_deliveries, 1)
        self.assertTrue(rider.earnings.filter(order=self.order).exists())


class CouponApiTests(TestCase):
    def test_vendor_coupon_scoped_and_validate(self):
        client = APIClient()
        owner = User.objects.create(username="ow", email="ow@x.com", role="Restaurant")
        r, z, item = make_restaurant()
        r.owner = owner; r.save()
        auth(client, owner)
        res = client.post("/api/food/vendor/coupons/", {"code": "VEND10", "discount_type": "FLAT",
                                                        "discount_value": "10.00"}, format="json")
        self.assertEqual(res.status_code, 201, res.content)
        self.assertEqual(Coupon.objects.get(code="VEND10").restaurant_id, r.id)
        # validate endpoint
        v = client.post("/api/food/coupons/validate/", {"code": "VEND10", "restaurant_slug": "r", "subtotal": "200"}, format="json")
        self.assertTrue(v.json()["data"]["valid"])
