"""GET /api/store/config/ — public storefront config, including the
Messenger deep-link field. Must default to '' (dormant) and reflect
whatever the owner sets in Django admin, with no auth required.
"""
from django.test import TestCase
from rest_framework.test import APIClient

from core.models import StoreConfiguration


class StoreConfigMessengerFieldTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_messenger_page_id_defaults_to_empty_string(self):
        res = self.client.get("/api/store/config/")
        self.assertEqual(res.status_code, 200, res.content)
        self.assertEqual(res.json()["data"]["messenger_page_id"], "")

    def test_messenger_page_id_reflects_configured_value(self):
        cfg = StoreConfiguration.get_solo()
        cfg.messenger_page_id = "fabrything"
        cfg.save()

        res = self.client.get("/api/store/config/")
        self.assertEqual(res.status_code, 200, res.content)
        self.assertEqual(res.json()["data"]["messenger_page_id"], "fabrything")

    def test_config_endpoint_requires_no_auth(self):
        res = self.client.get("/api/store/config/")
        self.assertEqual(res.status_code, 200)


class StoreConfigWhatsAppChatFieldTests(TestCase):
    """The floating WhatsApp chat button (storefront + food frontend) reads
    its number from this same public config endpoint, exactly like
    messenger_page_id -- blank means "hide the button", not a broken link."""

    def setUp(self):
        self.client = APIClient()

    def test_whatsapp_chat_number_defaults_to_empty_string(self):
        res = self.client.get("/api/store/config/")
        self.assertEqual(res.status_code, 200, res.content)
        self.assertEqual(res.json()["data"]["whatsapp_chat_number"], "")

    def test_whatsapp_chat_number_reflects_configured_value(self):
        cfg = StoreConfiguration.get_solo()
        cfg.whatsapp_chat_number = "8801842168117"
        cfg.save()

        res = self.client.get("/api/store/config/")
        self.assertEqual(res.status_code, 200, res.content)
        self.assertEqual(res.json()["data"]["whatsapp_chat_number"], "8801842168117")
