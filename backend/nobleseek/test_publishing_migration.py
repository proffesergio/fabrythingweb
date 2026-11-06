"""Existing editorial rows survive the NEWS/BLOG schema upgrade unchanged."""
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase


class PublishingMigrationTests(TransactionTestCase):
    def test_existing_articles_become_news_and_settings_preserve_ingestion(self):
        old_target = [("nobleseek", "0003_flatpage_poll_pushcampaign_pushdevice_and_more")]
        new_target = [("nobleseek", "0004_article_content_type_publishingsettings")]
        executor = MigrationExecutor(connection)
        executor.migrate(old_target)
        try:
            old_apps = executor.loader.project_state(old_target).apps
            article = old_apps.get_model("nobleseek", "Article").objects.create(
                headline="Existing n8n story", slug="existing-n8n-story",
                body_html="<p>Existing content</p>", status="PUBLISHED")
            executor = MigrationExecutor(connection)
            executor.migrate(new_target)
            apps = executor.loader.project_state(new_target).apps
            stored = apps.get_model("nobleseek", "Article").objects.get(pk=article.pk)
            self.assertEqual(stored.content_type, "NEWS")
            self.assertEqual(stored.status, "PUBLISHED")
            self.assertEqual(stored.body_html, "<p>Existing content</p>")
            settings = apps.get_model("nobleseek", "PublishingSettings").objects.get(pk=1)
            self.assertFalse(settings.ingestion_paused)
            self.assertEqual(settings.daily_article_limit, 0)
            self.assertFalse(settings.require_review_for_automation)
            self.assertEqual(settings.news_site_url, "https://www.fabrything.com")
        finally:
            MigrationExecutor(connection).migrate(new_target)
