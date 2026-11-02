"""`release_login` frees a username/email held by an account that shouldn't own it.

The case this was written for: someone tried to become a rider by signing up at
/auth/signup, which only ever creates `Customer` accounts. The result is a
customer account holding the username the admin now needs in order to onboard
that same person properly from the Riders tab — and `prune_orphan_logins` won't
touch it, because that command deliberately only prunes Rider/Restaurant roles.

The command must be *hard* to misuse: it deletes a login, so it refuses anything
carrying real history and reports before it acts.
"""

from io import StringIO

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from accounts.models import Users
from food.models import FoodOrder, Restaurant, Rider


def _call(*args, **kwargs):
    out = StringIO()
    call_command("release_login", *args, stdout=out, stderr=out, **kwargs)
    return out.getvalue()


class ReleaseLoginTests(TestCase):
    def setUp(self):
        self.user = Users.objects.create_user(
            username="riderbills", email="riderbills@example.com", password="pass12345",
            role="Customer", country="Bangladesh")

    def test_dry_run_by_default_reports_but_deletes_nothing(self):
        output = _call("riderbills")

        self.assertIn("riderbills", output)
        self.assertIn("Dry run", output)
        self.assertTrue(Users.objects.filter(username="riderbills").exists())

    def test_apply_deletes_and_frees_the_username(self):
        _call("riderbills", "--apply")

        self.assertFalse(Users.objects.filter(username="riderbills").exists())
        # The whole point: the admin can now onboard the rider under that name.
        Users.objects.create_user(
            username="riderbills", email="riderbills@example.com", password="pass12345",
            role="Rider", country="Bangladesh")

    def test_accepts_an_email_as_well_as_a_username(self):
        _call("riderbills@example.com", "--apply")
        self.assertFalse(Users.objects.filter(username="riderbills").exists())

    def test_unknown_identifier_is_an_error(self):
        with self.assertRaises(CommandError):
            _call("nobody")

    def test_refuses_an_admin_account(self):
        Users.objects.create_user(username="boss", email="boss@example.com",
                                  password="pass12345", role="Super Admin",
                                  country="Bangladesh")
        with self.assertRaises(CommandError):
            _call("boss", "--apply")
        self.assertTrue(Users.objects.filter(username="boss").exists())

    def test_refuses_an_account_that_already_owns_a_rider(self):
        """That is a real rider — deleting the login orphans the Rider row.
        Use the admin panel, not this."""
        rider_user = Users.objects.create_user(
            username="realrider", email="realrider@example.com", password="pass12345",
            role="Rider", country="Bangladesh")
        Rider.objects.create(name="Real", user=rider_user)

        with self.assertRaises(CommandError):
            _call("realrider", "--apply")
        self.assertTrue(Users.objects.filter(username="realrider").exists())

    def test_refuses_an_account_that_owns_a_restaurant(self):
        owner = Users.objects.create_user(
            username="vendor", email="vendor@example.com", password="pass12345",
            role="Restaurant", country="Bangladesh")
        Restaurant.objects.create(name="Kitchen", slug="kitchen", owner=owner)

        with self.assertRaises(CommandError):
            _call("vendor", "--apply")
        self.assertTrue(Users.objects.filter(username="vendor").exists())

    def test_refuses_an_account_with_order_history(self):
        """Deleting this would take real orders with it."""
        restaurant = Restaurant.objects.create(name="K", slug="k")
        FoodOrder.objects.create(
            customer=self.user, restaurant=restaurant,
            guest_name="Bills", guest_phone="017", delivery_address="somewhere",
            subtotal=100, delivery_fee=30, total=130)

        with self.assertRaises(CommandError):
            _call("riderbills", "--apply")
        self.assertTrue(Users.objects.filter(username="riderbills").exists())

    def test_lists_what_would_be_deleted_alongside_the_account(self):
        """An empty signup cart is fine to take; the operator should still see it."""
        from storefront.models import Cart

        Cart.objects.create(user=self.user)
        output = _call("riderbills")
        self.assertIn("Cart", output)
