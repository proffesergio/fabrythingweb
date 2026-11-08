from decimal import Decimal

from django.db import migrations, models


def update_inside_dhaka_rate(apps, schema_editor):
    apps.get_model("core", "StoreConfiguration").objects.update(
        fixed_shipping_rate=Decimal("70.00")
    )


class Migration(migrations.Migration):
    dependencies = [("core", "0012_update_whatsapp_chat_number")]

    operations = [
        migrations.AlterField(
            model_name="storeconfiguration",
            name="fixed_shipping_rate",
            field=models.DecimalField(
                max_digits=8, decimal_places=2, default=Decimal("70.00"),
                help_text="Base shipping charge for deliveries inside Dhaka.",
            ),
        ),
        migrations.AddField(
            model_name="storeconfiguration",
            name="outside_dhaka_shipping_rate",
            field=models.DecimalField(
                max_digits=8, decimal_places=2, default=Decimal("120.00"),
                help_text="Base shipping charge for deliveries outside Dhaka.",
            ),
        ),
        migrations.RunPython(update_inside_dhaka_rate, migrations.RunPython.noop),
    ]
