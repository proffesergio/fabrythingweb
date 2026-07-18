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
