"""Auth session tests: refresh-token renewal for the admin panel/apps."""
from django.test import TestCase
from rest_framework_simplejwt.tokens import RefreshToken

from accounts.models import Users


def make_admin(username="owner", role="Super Admin"):
    return Users.objects.create_user(
        username=username, email=f"{username}@x.com", password="pw123456",
        address="Dhaka", role=role)


class RefreshTests(TestCase):
    def test_login_issues_refresh_pair(self):
        u = make_admin()
        r = self.client.post("/api/auth/login/",
                             {"username": u.username, "password": "pw123456"},
                             content_type="application/json")
        assert r.status_code == 200, r.content[:200]
        assert r.json()["access"]
        assert r.json()["refresh"]

    def test_refresh_rotates_access(self):
        u = make_admin()
        rt = str(RefreshToken.for_user(u))
        r = self.client.post("/api/auth/refresh/", {"refresh": rt},
                             content_type="application/json")
        assert r.status_code == 200, r.content[:200]
        assert r.json()["access"]

    def test_refresh_rejects_garbage(self):
        r = self.client.post("/api/auth/refresh/", {"refresh": "nope"},
                             content_type="application/json")
        assert r.status_code == 401
