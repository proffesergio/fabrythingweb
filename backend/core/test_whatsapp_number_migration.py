from importlib import import_module
from types import SimpleNamespace
from django.apps import apps
from django.core.cache import cache
from django.db import connection
from django.test import TestCase
from core.models import StoreConfiguration


class WhatsAppNumberMigrationTests(TestCase):
    def setUp(self):
        cache.clear()

    def test_updates_old_and_blank_numbers_but_preserves_custom_number(self):
        migrate = import_module('core.migrations.0012_update_whatsapp_chat_number').update_number
        config = StoreConfiguration.get_solo()
        for old, expected in [('', '8801353529899'), ('8801842168117', '8801353529899'),
                              ('8801999999999', '8801999999999')]:
            StoreConfiguration.objects.filter(pk=config.pk).update(whatsapp_chat_number=old)
            migrate(apps, SimpleNamespace(connection=connection))
            config.refresh_from_db()
            self.assertEqual(config.whatsapp_chat_number, expected)
