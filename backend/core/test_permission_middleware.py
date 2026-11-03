"""Authorization must complete before a legacy admin view executes."""
from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.test import RequestFactory, SimpleTestCase, TestCase
from django.http import HttpResponse

from accounts.models import Modules, ModuleUrls
from core.middleware import PermissionMiddleware, urlToSkip


class PermissionMiddlewareOrderTests(SimpleTestCase):
    def setUp(self):
        self.request = RequestFactory().post("/api/products/admin/123/quick-update/")
        self.user = SimpleNamespace(id=2, role="Staff", domain_user_id_id=1)
        self.next_view = Mock(return_value=HttpResponse("mutation ran"))

    def _call(self, permission):
        with (
            patch("core.middleware.urlToSkip", return_value=[]),
            patch("core.middleware.JWTAuthentication.authenticate", return_value=(self.user, object())),
            patch("core.middleware.find_matching_module", return_value=SimpleNamespace(module=SimpleNamespace(id=5))),
            patch("core.middleware.UserPermissions.objects.filter") as filtered,
        ):
            filtered.return_value.first.return_value = permission
            response = PermissionMiddleware(self.next_view)(self.request)
        return response

    def test_denied_user_never_executes_view(self):
        response = self._call(SimpleNamespace(is_permission=False))
        self.assertEqual(response.status_code, 403)
        self.next_view.assert_not_called()

    def test_allowed_user_executes_view_once(self):
        response = self._call(SimpleNamespace(is_permission=True))
        self.assertEqual(response.status_code, 200)
        self.next_view.assert_called_once_with(self.request)


class PermissionSkipTests(TestCase):
    def test_only_unassigned_urls_skip_permissions(self):
        module = Modules.objects.create(module_name="Products")
        ModuleUrls.objects.create(url="/api/products/", module=module)
        ModuleUrls.objects.create(url="/api/public-exception/", module=None)

        self.assertEqual(urlToSkip(), ["/api/public-exception/"])
