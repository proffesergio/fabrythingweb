"""The module URL editor must preserve explicit skip semantics."""
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from accounts.models import ModuleUrls, Modules, Users
from core.middleware import urlToSkip


class ModuleUrlEditorTests(TestCase):
    def test_super_admin_can_change_assigned_url_to_skip(self):
        admin = Users.objects.create_user(
            username="module-editor", email="module-editor@example.com",
            password="test-password", role="Super Admin")
        module = Modules.objects.create(module_name="Products")
        entry = ModuleUrls.objects.create(url="/api/products/", module=module)
        client = APIClient()
        token = RefreshToken.for_user(admin).access_token
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

        response = client.post(
            "/api/moduleUrls/",
            [{"id": entry.id, "url": entry.url, "module": 0}],
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        entry.refresh_from_db()
        self.assertIsNone(entry.module_id)
        self.assertIn(entry.url, urlToSkip())
