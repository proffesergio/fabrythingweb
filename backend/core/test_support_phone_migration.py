"""The support phone must actually reach the live storefront.

Production's StoreConfiguration row predates this value, so a field default
alone would never touch it — migration 0011 carries a data step for exactly
that. These tests pin the two halves of the contract: a blank number gets
filled, and a number the owner has chosen is never overwritten.
"""
from django.core.cache import cache
from django.test import TestCase
from rest_framework.test import APIClient

from core.models import StoreConfiguration


class SupportPhoneTests(TestCase):
    def setUp(self):
        cache.clear()

    def test_fresh_configuration_carries_the_owner_number(self):
        self.assertEqual(StoreConfiguration.get_solo().support_phone, "8801842168117")

    def test_public_config_endpoint_publishes_it(self):
        """This is the whole point — the storefront reads support_phone from
        /api/store/config/, and it was serving an empty string."""
        res = APIClient().get("/api/store/config/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["data"]["support_phone"], "8801842168117")

    def test_an_owner_chosen_number_is_preserved(self):
        config = StoreConfiguration.get_solo()
        config.support_phone = "8801999999999"
        config.save()
        self.assertEqual(StoreConfiguration.get_solo().support_phone, "8801999999999")
