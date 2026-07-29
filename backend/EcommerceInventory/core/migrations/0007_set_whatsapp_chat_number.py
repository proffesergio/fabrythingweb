"""Activate the floating WhatsApp chat button with the owner's real number.

Same create-only pattern as 0005_set_messenger_page_id: set only when the
field is still blank, so an admin who later changes it in the panel does not
get overwritten if this migration is ever re-run against a fresh clone.
"""
from django.db import migrations

WHATSAPP_NUMBER = "8801842168117"


def set_whatsapp_number(apps, schema_editor):
    StoreConfiguration = apps.get_model("core", "StoreConfiguration")
    StoreConfiguration.objects.filter(whatsapp_chat_number="").update(
        whatsapp_chat_number=WHATSAPP_NUMBER
    )


def unset_whatsapp_number(apps, schema_editor):
    StoreConfiguration = apps.get_model("core", "StoreConfiguration")
    StoreConfiguration.objects.filter(whatsapp_chat_number=WHATSAPP_NUMBER).update(
        whatsapp_chat_number=""
    )


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0006_storeconfiguration_whatsapp_chat_number"),
    ]

    operations = [
        migrations.RunPython(set_whatsapp_number, unset_whatsapp_number),
    ]
