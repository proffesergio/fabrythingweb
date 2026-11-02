from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from food.models import DeliveryZone, FoodOrder, OrderSettlement, Restaurant, Rider, Village
from food.services_settlement import settle_order
from food.tests.test_settlement import make_order

User = get_user_model()


def auth(client, user):
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {RefreshToken.for_user(user).access_token}")


class SettlementApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = User.objects.create(username="setl_admin", email="setl@example.com",
                                         role="Super Admin")
        auth(self.client, self.admin)
        self.rider = Rider.objects.create(name="Karim")
        self.settlement = settle_order(make_order(rider=self.rider))

    def test_list_returns_the_money_split(self):
        res = self.client.get("/api/food/admin/settlements/")
        self.assertEqual(res.status_code, 200)
        # CommonListAPIMixin nests the page inside the standard envelope:
        # {"data": {"data": [...], "totalPages": n, ...}}. Parsing this as a
        # flat list is what broke the admin Food Orders page (commit 45ee192).
        row = res.json()["data"]["data"][0]
        self.assertEqual(row["order_code"], self.settlement.order.order_code)
        self.assertEqual(row["rider_name"], "Karim")
        self.assertEqual(Decimal(row["restaurant_payout"]), Decimal("425.00"))
        self.assertEqual(Decimal(row["platform_revenue"]), Decimal("85.00"))
        self.assertEqual(Decimal(row["rider_payout"]), Decimal("60.00"))

    def test_summary_totals_outstanding_money(self):
        res = self.client.get("/api/food/admin/settlements/summary/")
        self.assertEqual(res.status_code, 200)
        data = res.json()["data"]
        self.assertEqual(data["orders"], 1)
        self.assertEqual(Decimal(data["outstanding"]["rider_payout"]), Decimal("60.00"))
        self.assertEqual(Decimal(data["outstanding"]["restaurant_payout"]), Decimal("425.00"))
        self.assertEqual(data["counts"]["rider_payout"], 1)

    def test_marking_a_leg_paid(self):
        res = self.client.post(f"/api/food/admin/settlements/{self.settlement.id}/leg/",
                               {"leg": "rider_payout", "settled": True}, format="json")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["data"]["rider_payout_status"], "SETTLED")
        self.settlement.refresh_from_db()
        self.assertIsNotNone(self.settlement.rider_payout_at)

    def test_unknown_leg_is_rejected(self):
        res = self.client.post(f"/api/food/admin/settlements/{self.settlement.id}/leg/",
                               {"leg": "bogus"}, format="json")
        self.assertEqual(res.status_code, 400)

    def test_bulk_settles_many_at_once(self):
        second = settle_order(make_order(rider=self.rider))
        res = self.client.post("/api/food/admin/settlements/bulk/",
                               {"ids": [self.settlement.id, second.id],
                                "leg": "rider_payout", "settled": True}, format="json")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["data"]["updated"], 2)
        second.refresh_from_db()
        self.assertEqual(second.rider_payout_status, OrderSettlement.Settle.SETTLED)

    def test_filter_by_leg_status(self):
        settle_order(make_order(rider=self.rider))
        self.client.post(f"/api/food/admin/settlements/{self.settlement.id}/leg/",
                         {"leg": "rider_payout", "settled": True}, format="json")
        res = self.client.get("/api/food/admin/settlements/?leg=rider_payout&status=PENDING")
        self.assertEqual(res.json()["data"]["totalItems"], 1)

    def test_delivering_an_order_creates_its_settlement(self):
        order = make_order(rider=self.rider, status=FoodOrder.Status.OUT_FOR_DELIVERY)
        order.transition_to(FoodOrder.Status.DELIVERED)
        self.assertTrue(OrderSettlement.objects.filter(order=order).exists())


class SettlementSecurityTests(TestCase):
    """/api/food/ bypasses PermissionMiddleware — IsPlatformAdmin is the only guard."""

    def setUp(self):
        self.client = APIClient()
        self.settlement = settle_order(make_order(rider=Rider.objects.create(name="K")))

    def test_customer_cannot_read_settlements(self):
        auth(self.client, User.objects.create(username="c1", email="c1@example.com",
                                              role="Customer"))
        self.assertEqual(self.client.get("/api/food/admin/settlements/").status_code, 403)

    def test_rider_cannot_mark_their_own_payout_paid(self):
        auth(self.client, User.objects.create(username="r1", email="r1@example.com",
                                              role="Rider"))
        res = self.client.post(f"/api/food/admin/settlements/{self.settlement.id}/leg/",
                               {"leg": "rider_payout"}, format="json")
        self.assertEqual(res.status_code, 403)
        self.settlement.refresh_from_db()
        self.assertEqual(self.settlement.rider_payout_status, OrderSettlement.Settle.PENDING)

    def test_anonymous_cannot_read_settlements(self):
        self.assertIn(self.client.get("/api/food/admin/settlements/").status_code, (401, 403))


class ZoneVillageAdminTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        auth(self.client, User.objects.create(username="zone_admin",
                                              email="zone_admin@example.com",
                                              role="Super Admin"))
        self.zone = DeliveryZone.objects.create(
            name="Bancharampur Sadar", name_bn="বাঞ্ছারামপুর সদর",
            center_lat=Decimal("23.75"), center_lng=Decimal("90.78"))
        Village.objects.create(zone=self.zone, name="Ujanchar", name_bn="উজানচর")

    def test_zone_tree_nests_villages_in_both_languages(self):
        res = self.client.get("/api/food/admin/zone-tree/")
        self.assertEqual(res.status_code, 200)
        zone = res.json()["data"][0]
        self.assertEqual(zone["name_bn"], "বাঞ্ছারামপুর সদর")
        self.assertEqual(zone["display_name"], "বাঞ্ছারামপুর সদর")
        self.assertEqual(zone["village_count"], 1)
        self.assertEqual(zone["villages"][0]["name_bn"], "উজানচর")

    def test_display_name_falls_back_to_english(self):
        self.zone.name_bn = ""
        self.zone.save()
        res = self.client.get("/api/food/admin/zone-tree/")
        self.assertEqual(res.json()["data"][0]["display_name"], "Bancharampur Sadar")

    def test_admin_can_create_a_village(self):
        res = self.client.post("/api/food/admin/villages/",
                               {"zone": self.zone.id, "name": "Rupasdi",
                                "name_bn": "রূপসদী"}, format="json")
        self.assertEqual(res.status_code, 201, res.content)
        self.assertTrue(Village.objects.filter(name="Rupasdi", name_bn="রূপসদী").exists())

    def test_admin_can_correct_a_village_name(self):
        village = Village.objects.get(name="Ujanchar")
        res = self.client.patch(f"/api/food/admin/villages/{village.id}/",
                                {"name_bn": "উজানচর গ্রাম"}, format="json")
        self.assertEqual(res.status_code, 200, res.content)
        village.refresh_from_db()
        self.assertEqual(village.name_bn, "উজানচর গ্রাম")

    def test_admin_can_delete_a_village(self):
        village = Village.objects.get(name="Ujanchar")
        res = self.client.delete(f"/api/food/admin/villages/{village.id}/")
        self.assertIn(res.status_code, (200, 204))
        self.assertFalse(Village.objects.filter(id=village.id).exists())

    def test_villages_can_be_filtered_by_zone(self):
        other = DeliveryZone.objects.create(name="Other", center_lat=Decimal("23.7"),
                                            center_lng=Decimal("90.7"))
        Village.objects.create(zone=other, name="Elsewhere")
        res = self.client.get(f"/api/food/admin/villages/?zone={self.zone.id}")
        self.assertEqual(len(res.json()["data"]), 1)

    def test_customer_cannot_edit_villages(self):
        client = APIClient()
        auth(client, User.objects.create(username="c2", email="c2@example.com", role="Customer"))
        res = client.post("/api/food/admin/villages/",
                          {"zone": self.zone.id, "name": "Hack"}, format="json")
        self.assertEqual(res.status_code, 403)
