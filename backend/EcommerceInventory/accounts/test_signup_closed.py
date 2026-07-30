"""The public admin signup hole is closed.

/api/auth/signup/ (accounts.controllers.AuthController.SignupAPIView) had no
permission_classes/authentication_classes and called create_user() with no
role, which minted "Admin" (the model's old default) for anyone who posted to
it -- verified against production, which returned 201 with a role="Admin"
JWT. The route is removed entirely rather than gated, since nothing
legitimate called it (the storefront customer signup is the separate,
still-public /api/store/auth/signup/).
"""
from django.test import TestCase
from django.urls import reverse, NoReverseMatch

from accounts.models import Users


class AdminSignupRouteIsGoneTests(TestCase):
    def test_signup_route_returns_404(self):
        response = self.client.post("/api/auth/signup/", {
            "username": "attacker", "email": "attacker@example.com", "password": "hunter22",
        })
        self.assertEqual(response.status_code, 404)

    def test_signup_route_is_not_even_registered(self):
        with self.assertRaises(NoReverseMatch):
            reverse("signup")

    def test_no_admin_account_created_by_the_attempt(self):
        self.client.post("/api/auth/signup/", {
            "username": "attacker2", "email": "attacker2@example.com", "password": "hunter22",
        })
        self.assertFalse(Users.objects.filter(username="attacker2").exists())


class StorefrontCustomerSignupStillWorksTests(TestCase):
    """The owner was explicit: customers must keep signing up. This is a
    completely different endpoint/view (storefront.views.CustomerSignupView)
    and must be untouched by closing the admin hole."""

    def test_store_signup_returns_201_with_customer_role(self):
        response = self.client.post("/api/store/auth/signup/", {
            "username": "newcustomer", "email": "newcustomer@example.com", "password": "hunter22",
        })
        self.assertEqual(response.status_code, 201, response.content)
        self.assertIn("access", response.json())

        user = Users.objects.get(username="newcustomer")
        self.assertEqual(user.role, "Customer")
