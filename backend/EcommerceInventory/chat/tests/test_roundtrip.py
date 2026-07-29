"""End-to-end round trip: a staff reply posted through the admin endpoint
must be visible to the customer polling the customer-facing messages
endpoint -- both on the initial (no-cursor) load and on a subsequent
``after=<cursor>`` poll.

This is the seam neither test_admin_api.py nor test_customer_api.py covers:
those files are one-sided (staff-post-only, customer-read-only). Reported
symptom: "the reply from the admin panel doesn't reach the client frontend
chatbox."
"""
from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from chat.models import ChatMessage, ChatThread

User = get_user_model()


def auth(client, user):
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {str(RefreshToken.for_user(user).access_token)}")


class StaffReplyReachesCustomerTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.customer = User.objects.create(username="cust1", email="cust1@x.com", role="Customer")
        self.staff = User.objects.create(username="admin1", email="admin1@x.com", role="Admin")

        auth(self.client, self.customer)
        res = self.client.post(
            "/api/chat/threads/", {"kind": "GENERAL", "body": "hello, need help"}, format="json",
        )
        self.assertEqual(res.status_code, 201, res.content)
        self.thread_id = res.data["data"]["id"]

    def test_staff_reply_visible_on_initial_customer_poll(self):
        auth(self.client, self.staff)
        res = self.client.post(
            f"/api/chat/admin/threads/{self.thread_id}/messages/", {"body": "we're on it"}, format="json",
        )
        self.assertEqual(res.status_code, 201, res.content)

        auth(self.client, self.customer)
        res = self.client.get(f"/api/chat/threads/{self.thread_id}/messages/")
        self.assertEqual(res.status_code, 200)
        bodies = [m["body"] for m in res.data["data"]["messages"]]
        self.assertIn("we're on it", bodies)
        roles = [m["sender_role"] for m in res.data["data"]["messages"]]
        self.assertIn("STAFF", roles)

    def test_staff_reply_visible_on_after_cursor_customer_poll(self):
        auth(self.client, self.customer)
        res = self.client.get(f"/api/chat/threads/{self.thread_id}/messages/")
        cursor = res.data["data"]["latest_id"]
        self.assertIsNotNone(cursor)

        auth(self.client, self.staff)
        res = self.client.post(
            f"/api/chat/admin/threads/{self.thread_id}/messages/", {"body": "checking now"}, format="json",
        )
        self.assertEqual(res.status_code, 201, res.content)

        auth(self.client, self.customer)
        res = self.client.get(f"/api/chat/threads/{self.thread_id}/messages/?after={cursor}")
        self.assertEqual(res.status_code, 200)
        bodies = [m["body"] for m in res.data["data"]["messages"]]
        self.assertEqual(bodies, ["checking now"])
        self.assertEqual(res.data["data"]["messages"][0]["sender_role"], "STAFF")

    def test_poll_with_no_new_messages_does_not_lose_cursor(self):
        """A poll that returns zero messages must report a `latest_id` that
        preserves the caller's existing cursor rather than nulling it out --
        this is what the frontend's `latestIdRef` is trusted to store
        verbatim (see ChatWidget.js / ChatInbox.js fetchMessages)."""
        auth(self.client, self.staff)
        self.client.post(
            f"/api/chat/admin/threads/{self.thread_id}/messages/", {"body": "first reply"}, format="json",
        )

        auth(self.client, self.customer)
        res = self.client.get(f"/api/chat/threads/{self.thread_id}/messages/")
        cursor = res.data["data"]["latest_id"]
        self.assertIsNotNone(cursor)

        # Poll again immediately with that cursor -- nothing new has arrived.
        res = self.client.get(f"/api/chat/threads/{self.thread_id}/messages/?after={cursor}")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["data"]["messages"], [])
        # The bug under test: does this poll's `latest_id` come back None
        # (which would clobber a naive client's stored cursor) instead of
        # still being `cursor`?
        self.assertEqual(res.data["data"]["latest_id"], cursor)

        # And a real new staff message after that must still be found using
        # the still-correct cursor.
        auth(self.client, self.staff)
        self.client.post(
            f"/api/chat/admin/threads/{self.thread_id}/messages/", {"body": "second reply"}, format="json",
        )
        auth(self.client, self.customer)
        res = self.client.get(f"/api/chat/threads/{self.thread_id}/messages/?after={cursor}")
        self.assertEqual(res.status_code, 200)
        bodies = [m["body"] for m in res.data["data"]["messages"]]
        self.assertEqual(bodies, ["second reply"])
