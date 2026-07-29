from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from chat.models import ChatMessage, ChatThread

User = get_user_model()


def auth(client, user):
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {str(RefreshToken.for_user(user).access_token)}")


class ChatThreadCreateListTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.customer = User.objects.create(username="cust1", email="cust1@x.com", role="Customer")

    def test_create_thread_with_first_message(self):
        auth(self.client, self.customer)
        res = self.client.post(
            "/api/chat/threads/",
            {"kind": "EMERGENCY", "body": "Need an urgent delivery please!"},
            format="json",
        )
        self.assertEqual(res.status_code, 201, res.content)
        thread = ChatThread.objects.get()
        self.assertEqual(thread.customer_id, self.customer.id)
        self.assertEqual(thread.kind, "EMERGENCY")
        self.assertEqual(thread.status, "OPEN")
        self.assertIsNotNone(thread.last_message_at)
        # Customer just sent it -- caught up on their own side; staff has one unread.
        self.assertEqual(thread.customer_unread_count, 0)
        self.assertEqual(thread.staff_unread_count, 1)
        self.assertEqual(ChatMessage.objects.count(), 1)
        message = ChatMessage.objects.get()
        self.assertEqual(message.sender_role, "CUSTOMER")
        self.assertEqual(message.body, "Need an urgent delivery please!")

    def test_create_thread_defaults_to_general_kind(self):
        auth(self.client, self.customer)
        res = self.client.post("/api/chat/threads/", {"body": "hello"}, format="json")
        self.assertEqual(res.status_code, 201, res.content)
        self.assertEqual(ChatThread.objects.get().kind, "GENERAL")

    def test_create_thread_rejects_blank_body(self):
        auth(self.client, self.customer)
        res = self.client.post("/api/chat/threads/", {"kind": "GENERAL", "body": ""}, format="json")
        self.assertEqual(res.status_code, 400)
        self.assertEqual(ChatThread.objects.count(), 0)

    def test_create_thread_rejects_overlong_body(self):
        auth(self.client, self.customer)
        res = self.client.post(
            "/api/chat/threads/", {"kind": "GENERAL", "body": "x" * 4001}, format="json",
        )
        self.assertEqual(res.status_code, 400)
        self.assertEqual(ChatThread.objects.count(), 0)

    def test_create_thread_rejects_invalid_kind(self):
        auth(self.client, self.customer)
        res = self.client.post(
            "/api/chat/threads/", {"kind": "NOT_A_KIND", "body": "hi"}, format="json",
        )
        self.assertEqual(res.status_code, 400)

    def test_list_only_returns_my_own_threads(self):
        other = User.objects.create(username="cust2", email="cust2@x.com", role="Customer")
        mine = ChatThread.objects.create(customer=self.customer, kind="GENERAL")
        ChatThread.objects.create(customer=other, kind="GENERAL")

        auth(self.client, self.customer)
        res = self.client.get("/api/chat/threads/")
        self.assertEqual(res.status_code, 200)
        ids = [row["id"] for row in res.data["data"]]
        self.assertEqual(ids, [mine.id])

    def test_requires_authentication(self):
        res = self.client.get("/api/chat/threads/")
        self.assertEqual(res.status_code, 401)


class ChatThreadMessagesTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.customer = User.objects.create(username="cust1", email="cust1@x.com", role="Customer")
        self.thread = ChatThread.objects.create(customer=self.customer, kind="GENERAL")

    def test_post_message_updates_counters_and_last_message_at(self):
        auth(self.client, self.customer)
        res = self.client.post(
            f"/api/chat/threads/{self.thread.id}/messages/", {"body": "hi there"}, format="json",
        )
        self.assertEqual(res.status_code, 201, res.content)
        self.thread.refresh_from_db()
        self.assertEqual(self.thread.staff_unread_count, 1)
        self.assertEqual(self.thread.customer_unread_count, 0)
        self.assertIsNotNone(self.thread.last_message_at)

    def test_cannot_post_to_a_closed_thread(self):
        self.thread.status = ChatThread.Status.CLOSED
        self.thread.save(update_fields=["status"])
        auth(self.client, self.customer)
        res = self.client.post(
            f"/api/chat/threads/{self.thread.id}/messages/", {"body": "still here?"}, format="json",
        )
        self.assertEqual(res.status_code, 400)
        self.assertEqual(self.thread.messages.count(), 0)

    def test_get_messages_with_no_after_returns_recent_history_oldest_first(self):
        m1 = ChatMessage.objects.create(thread=self.thread, sender=self.customer, sender_role="CUSTOMER", body="one")
        m2 = ChatMessage.objects.create(thread=self.thread, sender=self.customer, sender_role="CUSTOMER", body="two")

        auth(self.client, self.customer)
        res = self.client.get(f"/api/chat/threads/{self.thread.id}/messages/")
        self.assertEqual(res.status_code, 200)
        bodies = [m["body"] for m in res.data["data"]["messages"]]
        self.assertEqual(bodies, ["one", "two"])
        self.assertEqual(res.data["data"]["latest_id"], m2.id)

    def test_after_message_id_returns_only_new_messages(self):
        m1 = ChatMessage.objects.create(thread=self.thread, sender=self.customer, sender_role="CUSTOMER", body="one")
        m2 = ChatMessage.objects.create(thread=self.thread, sender=self.customer, sender_role="CUSTOMER", body="two")
        m3 = ChatMessage.objects.create(thread=self.thread, sender=self.customer, sender_role="CUSTOMER", body="three")

        auth(self.client, self.customer)
        res = self.client.get(f"/api/chat/threads/{self.thread.id}/messages/?after={m1.id}")
        self.assertEqual(res.status_code, 200)
        bodies = [m["body"] for m in res.data["data"]["messages"]]
        # Only messages strictly newer than the cursor -- never the whole history.
        self.assertEqual(bodies, ["two", "three"])

    def test_after_timestamp_returns_only_new_messages(self):
        from urllib.parse import quote

        m1 = ChatMessage.objects.create(thread=self.thread, sender=self.customer, sender_role="CUSTOMER", body="one")
        # `+` (the UTC offset separator in isoformat()) must be percent-encoded
        # in a query string or it decodes back to a space -- a real client
        # (encodeURIComponent) does this automatically; the test must too.
        cutoff = quote(m1.created_at.isoformat())
        m2 = ChatMessage.objects.create(thread=self.thread, sender=self.customer, sender_role="CUSTOMER", body="two")

        auth(self.client, self.customer)
        res = self.client.get(f"/api/chat/threads/{self.thread.id}/messages/?after={cutoff}")
        self.assertEqual(res.status_code, 200)
        bodies = [m["body"] for m in res.data["data"]["messages"]]
        self.assertEqual(bodies, ["two"])

    def test_mark_read_resets_customer_unread_count(self):
        self.thread.customer_unread_count = 3
        self.thread.save(update_fields=["customer_unread_count"])

        auth(self.client, self.customer)
        res = self.client.post(f"/api/chat/threads/{self.thread.id}/read/")
        self.assertEqual(res.status_code, 200)
        self.thread.refresh_from_db()
        self.assertEqual(self.thread.customer_unread_count, 0)


class ChatCrossCustomerAccessTests(TestCase):
    """The rule this project has already gotten wrong once: a customer may
    only ever read or post to their OWN threads."""

    def setUp(self):
        self.client = APIClient()
        self.owner = User.objects.create(username="owner", email="owner@x.com", role="Customer")
        self.attacker = User.objects.create(username="attacker", email="attacker@x.com", role="Customer")
        self.thread = ChatThread.objects.create(customer=self.owner, kind="GENERAL")
        ChatMessage.objects.create(thread=self.thread, sender=self.owner, sender_role="CUSTOMER", body="private")

    def test_other_customer_cannot_read_messages(self):
        auth(self.client, self.attacker)
        res = self.client.get(f"/api/chat/threads/{self.thread.id}/messages/")
        self.assertEqual(res.status_code, 404)

    def test_other_customer_cannot_post_messages(self):
        auth(self.client, self.attacker)
        res = self.client.post(
            f"/api/chat/threads/{self.thread.id}/messages/", {"body": "snooping"}, format="json",
        )
        self.assertEqual(res.status_code, 404)
        self.assertEqual(self.thread.messages.count(), 1)

    def test_other_customer_cannot_mark_read(self):
        auth(self.client, self.attacker)
        res = self.client.post(f"/api/chat/threads/{self.thread.id}/read/")
        self.assertEqual(res.status_code, 404)

    def test_other_customer_thread_not_in_list(self):
        auth(self.client, self.attacker)
        res = self.client.get("/api/chat/threads/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["data"], [])


class ChatUpdatesBadgeTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.customer = User.objects.create(username="cust1", email="cust1@x.com", role="Customer")

    def test_badge_reflects_unread_and_updates_after_read(self):
        thread = ChatThread.objects.create(customer=self.customer, kind="GENERAL")
        ChatMessage.objects.create(thread=thread, sender=None, sender_role="STAFF", body="hi")
        thread.staff_unread_count = 0
        thread.customer_unread_count = 1
        thread.save(update_fields=["staff_unread_count", "customer_unread_count"])

        auth(self.client, self.customer)
        res = self.client.get("/api/chat/threads/updates/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["data"]["total_unread"], 1)
        self.assertEqual(len(res.data["data"]["threads"]), 1)

        self.client.post(f"/api/chat/threads/{thread.id}/read/")

        res = self.client.get("/api/chat/threads/updates/")
        self.assertEqual(res.data["data"]["total_unread"], 0)
        self.assertEqual(res.data["data"]["threads"], [])
