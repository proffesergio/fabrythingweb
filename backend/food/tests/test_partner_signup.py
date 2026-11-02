"""Become a Partner: self-signup behind an approval gate."""
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db import transaction
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from food.models import DeliveryZone, Restaurant, RestaurantZone
from food.services_partner import apply_as_partner

User = get_user_model()

APPLICATION = {
    "name": "Karim's Kitchen", "owner_name": "Karim Mia", "phone": "01712345678",
    "email": "Karim@Example.com", "password": "secret123",
    "address": "Bancharampur bazar", "cuisine_type": "Bengali",
}


class ApplyTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def _apply(self, **over):
        payload = {**APPLICATION, **over}
        return self.client.post("/api/food/partner/apply/", payload, format="json")

    def test_an_owner_can_apply_without_an_account(self):
        """Public by design — the approval gate is PENDING, not authentication."""
        res = self._apply()
        self.assertEqual(res.status_code, 201, res.content)
        d = res.json()["data"]
        self.assertEqual(d["restaurant"]["status"], "PENDING")
        self.assertTrue(d["access"])

    def test_the_new_restaurant_is_invisible_to_customers(self):
        self._apply()
        rows = self.client.get("/api/food/restaurants/").json()["data"]["data"]
        self.assertEqual(rows, [])

    def test_the_owner_login_can_reach_the_vendor_panel_immediately(self):
        """The application is worth something at once: the owner can build a menu
        while they wait, instead of filling in a form that vanishes."""
        access = self._apply().json()["data"]["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
        res = self.client.get("/api/food/vendor/restaurant/")
        self.assertEqual(res.status_code, 200, res.content)
        self.assertEqual(res.json()["data"]["status"], "PENDING")

    def test_the_owner_gets_the_Restaurant_role(self):
        self._apply()
        owner = User.objects.get(email="karim@example.com")
        self.assertEqual(owner.role, "Restaurant")

    def test_email_is_stored_lowercased_so_it_cannot_be_duplicated_by_case(self):
        self._apply()
        self.assertTrue(User.objects.filter(email="karim@example.com").exists())

    def test_selected_zones_are_attached(self):
        z = DeliveryZone.objects.create(name="Z", center_lat="23.8", center_lng="90.4", radius_km="5")
        self._apply(zone_ids=[z.id])
        r = Restaurant.objects.get(slug__startswith="karim")
        self.assertEqual(list(r.zones.values_list("id", flat=True)), [z.id])

    def test_a_pin_dropped_on_the_form_is_kept_for_distance_pricing(self):
        self._apply(pickup_lat="23.770000", pickup_lng="90.780000")
        r = Restaurant.objects.get(slug__startswith="karim")
        self.assertEqual(r.pickup_lat, Decimal("23.770000"))


class ValidationTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def _apply(self, **over):
        return self.client.post("/api/food/partner/apply/", {**APPLICATION, **over}, format="json")

    def test_missing_fields_are_attributed_to_their_input(self):
        # The envelope exposes these as field_errors so the form can show each
        # message under the right box.
        res = self._apply(name="")
        self.assertEqual(res.status_code, 400)
        self.assertIn("name", res.json()["field_errors"])

    def test_a_short_password_is_refused(self):
        res = self._apply(password="123")
        self.assertEqual(res.status_code, 400)
        self.assertIn("password", res.json()["field_errors"])

    def test_an_email_already_owned_by_another_account_is_refused(self):
        User.objects.create_user(username="someone", email="karim@example.com",
                                 password="x", role="Customer")
        res = self._apply()
        self.assertEqual(res.status_code, 400)
        self.assertIn("email", res.json()["field_errors"])

    def test_reapplying_corrects_the_first_application_instead_of_duplicating(self):
        """A typo must not strand the applicant. A second login would fail on the
        unique username anyway, leaving them with no way to fix it."""
        self._apply()
        res = self._apply(name="Karim's Kitchen & Grill", cuisine_type="Kebab")
        self.assertEqual(res.status_code, 201)
        self.assertEqual(Restaurant.objects.count(), 1)
        self.assertEqual(User.objects.filter(role="Restaurant").count(), 1)
        self.assertEqual(Restaurant.objects.get().name, "Karim's Kitchen & Grill")

    def test_two_different_owners_both_get_a_login(self):
        self._apply()
        res = self._apply(email="other@example.com", phone="01799999999", name="Other Place")
        self.assertEqual(res.status_code, 201)
        self.assertEqual(Restaurant.objects.count(), 2)
        self.assertEqual(User.objects.filter(role="Restaurant").count(), 2)

    def test_a_clashing_username_is_made_unique_rather_than_failing(self):
        User.objects.create_user(username="karim", email="taken@example.com",
                                 password="x", role="Customer")
        res = self._apply()
        self.assertEqual(res.status_code, 201)
        self.assertNotEqual(res.json()["data"]["username"], "karim")


class AtomicityTests(TestCase):
    """The orphan-login trap: a User committed without the restaurant it belongs
    to owns the username forever, with no row in the admin panel to delete."""

    def test_a_failure_after_the_user_is_created_leaves_no_orphan(self):
        before = User.objects.count()
        with self.assertRaises(Exception):
            with transaction.atomic():
                apply_as_partner({**APPLICATION, "zone_ids": "not-a-list-of-ids"})
                raise RuntimeError("simulated failure after the owner exists")
        self.assertEqual(User.objects.count(), before)
        self.assertEqual(Restaurant.objects.count(), 0)


class ApprovalTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.client.post("/api/food/partner/apply/", APPLICATION, format="json")
        self.restaurant = Restaurant.objects.get()
        self.admin = User.objects.create_user(username="boss", email="boss@example.com",
                                              password="x", role="Admin")

    def _auth_admin(self):
        token = RefreshToken.for_user(self.admin).access_token
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

    def _decide(self, **body):
        self._auth_admin()
        return self.client.post(f"/api/food/admin/partner/{self.restaurant.id}/decision/",
                                body, format="json")

    def test_the_queue_lists_who_applied_and_how_to_reach_them(self):
        self._auth_admin()
        rows = self.client.get("/api/food/admin/partner/applications/").json()["data"]
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["owner_email"], "karim@example.com")
        self.assertEqual(rows[0]["phone"], "01712345678")

    def test_approval_makes_the_restaurant_visible_to_customers(self):
        self._decide(decision="approve")
        self.client.credentials()
        rows = self.client.get("/api/food/restaurants/").json()["data"]["data"]
        self.assertEqual(len(rows), 1)

    def test_approval_is_where_the_commission_terms_are_set(self):
        self._decide(decision="approve", commission_percentage="10.00",
                     min_commission_amount="20.00")
        self.restaurant.refresh_from_db()
        self.assertEqual(self.restaurant.commission_percentage, Decimal("10.00"))
        self.assertEqual(self.restaurant.min_commission_amount, Decimal("20.00"))

    def test_rejection_keeps_the_login_so_the_owner_can_be_told(self):
        self._decide(decision="reject", reason="Not in our delivery area yet")
        self.restaurant.refresh_from_db()
        self.assertEqual(self.restaurant.status, "REJECTED")
        self.assertTrue(User.objects.filter(email="karim@example.com").exists())

    def test_a_nonsense_decision_is_refused(self):
        self.assertEqual(self._decide(decision="maybe").status_code, 400)

    def test_the_queue_is_admin_only(self):
        self.client.credentials()
        self.assertIn(self.client.get("/api/food/admin/partner/applications/").status_code,
                      (401, 403))

    def test_a_restaurant_owner_cannot_approve_themselves(self):
        owner = self.restaurant.owner
        token = RefreshToken.for_user(owner).access_token
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        res = self.client.post(f"/api/food/admin/partner/{self.restaurant.id}/decision/",
                               {"decision": "approve"}, format="json")
        self.assertIn(res.status_code, (401, 403))
        self.restaurant.refresh_from_db()
        self.assertEqual(self.restaurant.status, "PENDING")
