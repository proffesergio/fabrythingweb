"""Activate the Messenger button for the real Facebook page.

The page username is `fabrything` (public — it is the m.me/ handle printed on
the site's own footer), so this is configuration, not a secret. Set only when
the field is still blank, so an admin who later changes it in the panel does
not get overwritten if this migration is ever re-run against a fresh clone.
"""
from django.db import migrations

PAGE_USERNAME = "fabrything"


def set_page_id(apps, schema_editor):
    StoreConfiguration = apps.get_model("core", "StoreConfiguration")
    StoreConfiguration.objects.filter(messenger_page_id="").update(
        messenger_page_id=PAGE_USERNAME
    )


def unset_page_id(apps, schema_editor):
    StoreConfiguration = apps.get_model("core", "StoreConfiguration")
    StoreConfiguration.objects.filter(messenger_page_id=PAGE_USERNAME).update(
        messenger_page_id=""
    )


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0004_storeconfiguration_messenger_page_id"),
    ]

    operations = [
        migrations.RunPython(set_page_id, unset_page_id),
    ]
