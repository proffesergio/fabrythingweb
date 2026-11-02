from decimal import Decimal
from io import StringIO
from django.test import TestCase
from django.core.management import call_command
from rest_framework.test import APIClient
from food.models import DeliveryZone, Village, RestaurantZone
from food.services import place_food_cod_order
from food.tests.test_phase_features import make_restaurant, lines


class VillageOrderTests(TestCase):
    def test_village_resolves_zone_and_stores_pin(self):
        r, z, item = make_restaurant()
        village = Village.objects.create(zone=z, name="Bancharampur", name_bn="বাঞ্ছারামপুর")
        order = place_food_cod_order(
            customer=None, restaurant_slug="r", items=lines(item),
            contact_name="A", contact_phone="1", delivery_address="House 3",
            village_id=village.id, delivery_lat="23.7772", delivery_lng="90.7886")
        order.refresh_from_db()
        self.assertEqual(order.village_id, village.id)
        self.assertEqual(order.zone_id, z.id)                 # union inferred from village
        self.assertEqual(order.delivery_lat, Decimal("23.777200"))
        self.assertEqual(order.delivery_fee, Decimal("30.00"))  # from restaurant zone/base

    def test_village_outside_service_area_rejected(self):
        r, z, item = make_restaurant()
        other = DeliveryZone.objects.create(name="Faraway", center_lat="24.0",
                                            center_lng="91.0", radius_km="3")
        v = Village.objects.create(zone=other, name="Nowhere")
        with self.assertRaises(Exception):
            place_food_cod_order(customer=None, restaurant_slug="r", items=lines(item),
                                 contact_name="A", contact_phone="1", delivery_address="x",
                                 village_id=v.id)


class ZoneVillageApiTests(TestCase):
    def test_zone_endpoint_nests_active_villages(self):
        z = DeliveryZone.objects.create(name="Bancharampur", center_lat="23.7", center_lng="90.7", radius_km="4")
        Village.objects.create(zone=z, name="Alipur", name_bn="আলীপুর")
        Village.objects.create(zone=z, name="Hidden", is_active=False)
        res = APIClient().get("/api/food/zones/")
        self.assertEqual(res.status_code, 200)
        zone = next(x for x in res.data["data"] if x["name"] == "Bancharampur")
        names = [v["name"] for v in zone["villages"]]
        self.assertIn("Alipur", names)
        self.assertNotIn("Hidden", names)          # inactive villages hidden


class SeedBancharampurTests(TestCase):
    def test_seed_creates_unions_and_villages(self):
        call_command("seed_bancharampur", stdout=StringIO())
        self.assertEqual(DeliveryZone.objects.filter(is_active=True).count(), 13)
        self.assertEqual(Village.objects.count(), 121)
        banch = DeliveryZone.objects.get(name="Bancharampur")
        self.assertEqual(banch.name_bn, "বাঞ্ছারামপুর")
        self.assertTrue(banch.villages.filter(name="Alipur").exists())

    def test_exclusive_deactivates_other_zones(self):
        DeliveryZone.objects.create(name="OldTown", center_lat="1", center_lng="1", radius_km="3")
        call_command("seed_bancharampur", "--exclusive", stdout=StringIO())
        self.assertFalse(DeliveryZone.objects.get(name="OldTown").is_active)
        self.assertEqual(DeliveryZone.objects.filter(is_active=True).count(), 13)
