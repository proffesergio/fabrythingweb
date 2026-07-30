"""UserController.CreateUserView (POST /api/auth/users/create/) is the
replacement for the closed public /api/auth/signup/: a logged-in back-office
user creates another account and sets its role directly. This is the ONLY way
left to mint an Admin/Staff/Super Admin account.
"""
from django.test import TestCase
from rest_framework.test import APIRequestFactory, force_authenticate

from accounts.controllers.UserController import CreateUserView
from accounts.models import Users


class CreateUserViewTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.super_admin = Users.objects.create_user(
            username="cu-super", email="cu-super@x.com", password="x",
            role="Super Admin", country="Bangladesh")
        self.super_admin.domain_user_id = self.super_admin
        self.super_admin.save()

        self.admin = Users.objects.create_user(
            username="cu-admin", email="cu-admin@x.com", password="x",
            role="Admin", country="Bangladesh")
        # Make the admin a domain root so isPlatformStaff is True for it.
        self.admin.domain_user_id = self.admin
        self.admin.save()

        self.customer = Users.objects.create_user(
            username="cu-customer", email="cu-customer@x.com", password="x",
            role="Customer", country="Bangladesh")

    def _post(self, user, body):
        request = self.factory.post("/api/auth/users/create/", body, format="json")
        if user is not None:
            force_authenticate(request, user=user)
        return CreateUserView.as_view()(request)

    def test_anonymous_cannot_create_a_user(self):
        res = self._post(None, {
            "username": "hacker", "email": "hacker@x.com", "password": "x", "role": "Admin"})
        self.assertEqual(res.status_code, 401)
        self.assertFalse(Users.objects.filter(username="hacker").exists())

    def test_customer_cannot_create_a_user(self):
        res = self._post(self.customer, {
            "username": "sneaky", "email": "sneaky@x.com", "password": "x", "role": "Admin"})
        self.assertEqual(res.status_code, 403)
        self.assertFalse(Users.objects.filter(username="sneaky").exists())

    def test_admin_can_create_a_staff_user(self):
        res = self._post(self.admin, {
            "username": "new-staff", "email": "new-staff@x.com", "password": "x", "role": "Staff"})
        self.assertEqual(res.status_code, 201, res.data)
        created = Users.objects.get(username="new-staff")
        self.assertEqual(created.role, "Staff")
        # Joins the creator's tenant.
        self.assertEqual(created.domain_user_id_id, self.admin.domain_user_id_id)
        self.assertEqual(created.added_by_user_id_id, self.admin.id)

    def test_admin_cannot_create_a_super_admin(self):
        res = self._post(self.admin, {
            "username": "escalated", "email": "escalated@x.com", "password": "x", "role": "Super Admin"})
        self.assertEqual(res.status_code, 403)
        self.assertFalse(Users.objects.filter(username="escalated").exists())

    def test_super_admin_can_create_a_super_admin(self):
        res = self._post(self.super_admin, {
            "username": "new-super", "email": "new-super@x.com", "password": "x", "role": "Super Admin"})
        self.assertEqual(res.status_code, 201, res.data)
        created = Users.objects.get(username="new-super")
        self.assertEqual(created.role, "Super Admin")
        # A new Super Admin is its own domain root, not folded into the creator's tenant.
        self.assertEqual(created.domain_user_id_id, created.id)

    def test_invalid_role_rejected(self):
        res = self._post(self.super_admin, {
            "username": "badrole", "email": "badrole@x.com", "password": "x", "role": "Emperor"})
        self.assertEqual(res.status_code, 400)
        self.assertFalse(Users.objects.filter(username="badrole").exists())

    def test_duplicate_username_rejected(self):
        res = self._post(self.super_admin, {
            "username": "cu-admin", "email": "someoneelse@x.com", "password": "x", "role": "Staff"})
        self.assertEqual(res.status_code, 400)

    def test_missing_fields_rejected(self):
        res = self._post(self.super_admin, {"username": "incomplete"})
        self.assertEqual(res.status_code, 400)
