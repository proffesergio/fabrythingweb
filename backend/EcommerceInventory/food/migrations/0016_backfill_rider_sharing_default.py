from django.db import migrations


def backfill_is_sharing_location(apps, schema_editor):
    # 0014 added is_sharing_location with default=False, so Django backfilled
    # every pre-existing Rider row to False. 0015 only changed the schema
    # default for *future* inserts and never touched existing rows. Riders
    # created after 0015 already get True from the schema default; this
    # one-time backfill exists solely to bring the pre-existing population in
    # line with the corrected "default True" design.
    Rider = apps.get_model("food", "Rider")
    Rider.objects.update(is_sharing_location=True)


class Migration(migrations.Migration):

    dependencies = [
        ("food", "0015_alter_rider_is_sharing_location"),
    ]

    operations = [
        migrations.RunPython(backfill_is_sharing_location, migrations.RunPython.noop),
    ]
