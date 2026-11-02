from django.db import migrations


def update_number(apps, schema_editor):
    config = apps.get_model("core", "StoreConfiguration")
    config.objects.using(schema_editor.connection.alias).filter(
        whatsapp_chat_number__in=["", "8801842168117"]
    ).update(whatsapp_chat_number="8801353529899")


class Migration(migrations.Migration):
    dependencies = [("core", "0011_storeconfiguration_support_phone_default")]
    operations = [migrations.RunPython(update_number, migrations.RunPython.noop)]
