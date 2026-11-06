from django.db import migrations, models


def seed_settings(apps, schema_editor):
    apps.get_model("nobleseek", "PublishingSettings").objects.using(
        schema_editor.connection.alias).get_or_create(pk=1)


class Migration(migrations.Migration):
    dependencies = [
        ("nobleseek", "0003_flatpage_poll_pushcampaign_pushdevice_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="article", name="content_type",
            field=models.CharField(choices=[("NEWS", "News"), ("BLOG", "Blog")],
                                   db_index=True, default="NEWS", max_length=4)),
        migrations.CreateModel(
            name="PublishingSettings",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("news_site_url", models.URLField(default="https://www.fabrything.com", max_length=500)),
                ("ingestion_paused", models.BooleanField(default=False)),
                ("daily_article_limit", models.PositiveIntegerField(default=0, help_text="0 disables the limit")),
                ("require_review_for_automation", models.BooleanField(default=False)),
                ("estimated_text_bytes_per_article", models.PositiveIntegerField(default=20000)),
                ("estimated_image_bytes_per_article", models.PositiveIntegerField(default=300000)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"constraints": [models.CheckConstraint(check=models.Q(pk=1), name="ns_publishing_singleton")]},
        ),
        migrations.RunPython(seed_settings, migrations.RunPython.noop),
    ]
