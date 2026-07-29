from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from chat.models import ChatMessage, ChatThread

User = get_user_model()


def auth(client, user):
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {str(RefreshToken.for_user(user).access_token)}")


class AdminChatInboxTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.staff = User.objects.create(username="admin1", email="admin1@x.com", role="Admin")
        self.customer = User.objects.create(username="cust1", email="cust1@x.com", role="Customer")

    def test_inbox_lists_all_customers_threads(self):
        other = User.objects.create(username="cust2", email="cust2@x.com", role="Customer")
        t1 = ChatThread.objects.create(customer=self.customer, kind="GENERAL")
        t2 = ChatThread.objects.create(customer=other, kind="EMERGENCY")

        auth(self.client, self.staff)
        res = self.client.get("/api/chat/admin/threads/")
        self.assertEqual(res.status_code, 200)
        ids = {row["id"] for row in res.data["data"]}
        self.assertEqual(ids, {t1.id, t2.id})

    def test_inbox_sorted_by_last_message_at_desc(self):
        import time

        older = ChatThread.objects.create(customer=self.customer, kind="GENERAL")
        older.last_message_at = None
        older.save()
        newer = ChatThread.objects.create(customer=self.customer, kind="GENERAL")

        from django.utils import timezone
        older.last_message_at = timezone.now() - timezone.timedelta(hours=1)
        older.save(update_fields=["last_message_at"])
        newer.last_message_at = timezone.now()
        newer.save(update_fields=["last_message_at"])

        auth(self.client, self.staff)
        res = self.client.get("/api/chat/admin/threads/")
        ids = [row["id"] for row in res.data["data"]]
        self.assertEqual(ids, [newer.id, older.id])

    def test_inbox_filters_by_status(self):
        open_thread = ChatThread.objects.create(customer=self.customer, kind="GENERAL", status="OPEN")
        closed_thread = ChatThread.objects.create(customer=self.customer, kind="GENERAL", status="CLOSED")

        auth(self.client, self.staff)
        res = self.client.get("/api/chat/admin/threads/?status=CLOSED")
        ids = [row["id"] for row in res.data["data"]]
        self.assertEqual(ids, [closed_thread.id])

    def test_inbox_filters_by_kind(self):
        general = ChatThread.objects.create(customer=self.customer, kind="GENERAL")
        emergency = ChatThread.objects.create(customer=self.customer, kind="EMERGENCY")

        auth(self.client, self.staff)
        res = self.client.get("/api/chat/admin/threads/?kind=EMERGENCY")
        ids = [row["id"] for row in res.data["data"]]
        self.assertEqual(ids, [emergency.id])

    def test_customer_role_is_rejected(self):
        auth(self.client, self.customer)
        res = self.client.get("/api/chat/admin/threads/")
        self.assertEqual(res.status_code, 403)

    def test_domain_sub_account_admin_is_rejected(self):
        # A domain ROOT admin has domain_user_id_id == its own id (see
        # Users.save()'s self-assign). A sub-account created *under* someone
        # else's domain is not platform-scoped and must not reach the inbox
        # of every customer on the platform.
        root = User.objects.create(username="root_admin", email="root@x.com", role="Admin")
        sub_admin = User.objects.create(
            username="sub_admin", email="sub@x.com", role="Admin", domain_user_id=root,
        )
        auth(self.client, sub_admin)
        res = self.client.get("/api/chat/admin/threads/")
        self.assertEqual(res.status_code, 403)

    def test_unauthenticated_is_rejected(self):
        res = self.client.get("/api/chat/admin/threads/")
        self.assertEqual(res.status_code, 401)

    def test_inbox_query_count_is_flat_regardless_of_thread_count(self):
        # The inbox must not N+1 across threads -- select_related("customer")
        # + .only() should keep this at a fixed, small query count whether
        # there are 3 threads or 30.
        for i in range(3):
            c = User.objects.create(username=f"c{i}", email=f"c{i}@x.com", role="Customer")
            ChatThread.objects.create(customer=c, kind="GENERAL")

        auth(self.client, self.staff)
        with self.assertNumQueries(2):  # JWT user fetch + one select_related threads query
            self.client.get("/api/chat/admin/threads/")

        for i in range(3, 15):
            c = User.objects.create(username=f"c{i}", email=f"c{i}@x.com", role="Customer")
            ChatThread.objects.create(customer=c, kind="GENERAL")

        with self.assertNumQueries(2):
            self.client.get("/api/chat/admin/threads/")


class AdminChatMessagesTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.staff = User.objects.create(username="admin1", email="admin1@x.com", role="Admin")
        self.customer = User.objects.create(username="cust1", email="cust1@x.com", role="Customer")
        self.thread = ChatThread.objects.create(customer=self.customer, kind="GENERAL")

    def test_staff_can_post_reply_and_it_resets_staff_unread(self):
        self.thread.staff_unread_count = 2
        self.thread.save(update_fields=["staff_unread_count"])

        auth(self.client, self.staff)
        res = self.client.post(
            f"/api/chat/admin/threads/{self.thread.id}/messages/", {"body": "we're on it"}, format="json",
        )
        self.assertEqual(res.status_code, 201, res.content)
        self.thread.refresh_from_db()
        self.assertEqual(self.thread.staff_unread_count, 0)
        self.assertEqual(self.thread.customer_unread_count, 1)
        message = ChatMessage.objects.get()
        self.assertEqual(message.sender_role, "STAFF")
        self.assertEqual(message.sender_id, self.staff.id)

    def test_staff_message_post_rejects_customer_role(self):
        auth(self.client, self.customer)
        res = self.client.post(
            f"/api/chat/admin/threads/{self.thread.id}/messages/", {"body": "hi"}, format="json",
        )
        self.assertEqual(res.status_code, 403)

    def test_staff_can_fetch_new_messages_with_after(self):
        m1 = ChatMessage.objects.create(thread=self.thread, sender=self.customer, sender_role="CUSTOMER", body="one")
        m2 = ChatMessage.objects.create(thread=self.thread, sender=self.customer, sender_role="CUSTOMER", body="two")

        auth(self.client, self.staff)
        res = self.client.get(f"/api/chat/admin/threads/{self.thread.id}/messages/?after={m1.id}")
        self.assertEqual(res.status_code, 200)
        bodies = [m["body"] for m in res.data["data"]["messages"]]
        self.assertEqual(bodies, ["two"])

    def test_mark_read_resets_staff_unread_count(self):
        self.thread.staff_unread_count = 5
        self.thread.save(update_fields=["staff_unread_count"])

        auth(self.client, self.staff)
        res = self.client.post(f"/api/chat/admin/threads/{self.thread.id}/read/")
        self.assertEqual(res.status_code, 200)
        self.thread.refresh_from_db()
        self.assertEqual(self.thread.staff_unread_count, 0)


class AdminChatStatusTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.staff = User.objects.create(username="admin1", email="admin1@x.com", role="Admin")
        self.customer = User.objects.create(username="cust1", email="cust1@x.com", role="Customer")
        self.thread = ChatThread.objects.create(customer=self.customer, kind="GENERAL", status="OPEN")

    def test_staff_can_close_thread(self):
        auth(self.client, self.staff)
        res = self.client.post(
            f"/api/chat/admin/threads/{self.thread.id}/status/", {"status": "CLOSED"}, format="json",
        )
        self.assertEqual(res.status_code, 200)
        self.thread.refresh_from_db()
        self.assertEqual(self.thread.status, "CLOSED")

    def test_staff_can_reopen_thread(self):
        self.thread.status = "CLOSED"
        self.thread.save(update_fields=["status"])

        auth(self.client, self.staff)
        res = self.client.post(
            f"/api/chat/admin/threads/{self.thread.id}/status/", {"status": "OPEN"}, format="json",
        )
        self.assertEqual(res.status_code, 200)
        self.thread.refresh_from_db()
        self.assertEqual(self.thread.status, "OPEN")

    def test_customer_cannot_close_thread(self):
        auth(self.client, self.customer)
        res = self.client.post(
            f"/api/chat/admin/threads/{self.thread.id}/status/", {"status": "CLOSED"}, format="json",
        )
        self.assertEqual(res.status_code, 403)
        self.thread.refresh_from_db()
        self.assertEqual(self.thread.status, "OPEN")


class AdminChatUpdatesTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.staff = User.objects.create(username="admin1", email="admin1@x.com", role="Admin")
        self.customer = User.objects.create(username="cust1", email="cust1@x.com", role="Customer")

    def test_badge_totals_across_all_customers(self):
        t1 = ChatThread.objects.create(customer=self.customer, kind="GENERAL", staff_unread_count=2)
        other = User.objects.create(username="cust2", email="cust2@x.com", role="Customer")
        t2 = ChatThread.objects.create(customer=other, kind="GENERAL", staff_unread_count=3)

        auth(self.client, self.staff)
        res = self.client.get("/api/chat/admin/threads/updates/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["data"]["total_unread"], 5)
        self.assertEqual(len(res.data["data"]["threads"]), 2)
