from typing import ClassVar

from django.db import migrations


def set_destination(apps, schema_editor):
    # Owner explicitly chose the existing store WhatsApp destination on Nov13.
    StoreConfiguration = apps.get_model("core", "StoreConfiguration")
    config, _ = StoreConfiguration.objects.get_or_create(pk=1)
    if not config.whatsapp_admin_number:
        config.whatsapp_admin_number = config.whatsapp_chat_number or "8801353529899"
        config.save(update_fields=["whatsapp_admin_number"])


class Migration(migrations.Migration):
    dependencies: ClassVar[list] = [
        ("storeops", "0001_initial"),
        ("core", "0013_regional_shipping_rates"),
    ]
    operations: ClassVar[list] = [
        migrations.RunPython(set_destination, migrations.RunPython.noop)
    ]
