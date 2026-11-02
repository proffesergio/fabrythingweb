"""`/api/health/` must answer without a token and report schema drift.

The endpoint exists because a database whose schema lags the deployed code is
invisible from outside: DEBUG=False renders a body-less "Server Error (500)" and
every affected endpoint looks equally broken whether the cause is a missing
migration or a genuine bug.
"""

from django.test import TestCase


class HealthEndpointTests(TestCase):
    def test_reachable_without_authentication(self):
        response = self.client.get("/api/health/")
        self.assertNotEqual(response.status_code, 401,
                            "PermissionMiddleware must not gate the health check")
        self.assertIn(response.status_code, (200, 503))

    def test_reports_ok_on_a_fully_migrated_database(self):
        """The test DB is migrated by the runner, so nothing should be pending."""
        response = self.client.get("/api/health/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")
        self.assertEqual(response.json()["pending_migrations"], [])

    def test_does_not_leak_connection_details(self):
        body = self.client.get("/api/health/").content.decode().lower()
        for secret in ("password", "sslmode", "neon.tech", "@"):
            self.assertNotIn(secret, body)
