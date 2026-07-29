"""Customer message -> admin WhatsApp nudge (chat/services.py), reusing the
same dormant-until-configured core.whatsapp provider food/services_dispatch.py
alerts through. Mirrors food/tests/test_whatsapp_alerts.py's approach: patch
the env + the HTTP call, never the network.
"""
from datetime import timedelta
from unittest import mock

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from chat.models import ChatMessage, ChatThread
from core.models import StoreConfiguration, WhatsAppAlertLog

User = get_user_model()

ENV_CONFIGURED = {
    "WHATSAPP_ACCESS_TOKEN": "tok",
    "WHATSAPP_PHONE_NUMBER_ID": "123",
}


def auth(client, user):
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {str(RefreshToken.for_user(user).access_token)}")


class ChatWhatsAppNotifyTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.customer = User.objects.create(username="cust1", email="cust1@x.com", role="Customer")
        config = StoreConfiguration.get_solo()
        config.whatsapp_admin_number = "8801700000009"
        config.save()

    @mock.patch("core.whatsapp.requests.post")
    @mock.patch.dict("os.environ", ENV_CONFIGURED, clear=True)
    def test_new_thread_notifies_admin_on_whatsapp(self, mock_post):
        mock_post.return_value = mock.Mock(ok=True, status_code=200, text="")
        auth(self.client, self.customer)

        with self.captureOnCommitCallbacks(execute=True):
            res = self.client.post(
                "/api/chat/threads/", {"kind": "EMERGENCY", "body": "need help fast"}, format="json",
            )
        self.assertEqual(res.status_code, 201, res.content)

        alert = WhatsAppAlertLog.objects.get(kind="chat_customer_message")
        self.assertEqual(alert.recipient, "8801700000009")
        self.assertTrue(alert.success)

    @mock.patch("core.whatsapp.requests.post")
    @mock.patch.dict("os.environ", ENV_CONFIGURED, clear=True)
    def test_does_not_notify_when_staff_replied_recently(self, mock_post):
        mock_post.return_value = mock.Mock(ok=True, status_code=200, text="")
        thread = ChatThread.objects.create(customer=self.customer, kind="GENERAL")
        staff_msg = ChatMessage.objects.create(
            thread=thread, sender=None, sender_role="STAFF", body="on it",
        )
        # created_at is auto_now_add -- Django ignores any value passed to
        # create() for it, so backdating requires a raw UPDATE after the fact.
        ChatMessage.objects.filter(pk=staff_msg.pk).update(
            created_at=timezone.now() - timedelta(minutes=2),
        )

        auth(self.client, self.customer)
        with self.captureOnCommitCallbacks(execute=True):
            res = self.client.post(
                f"/api/chat/threads/{thread.id}/messages/", {"body": "thanks!"}, format="json",
            )
        self.assertEqual(res.status_code, 201, res.content)
        mock_post.assert_not_called()
        self.assertEqual(WhatsAppAlertLog.objects.filter(kind="chat_customer_message").count(), 0)

    @mock.patch("core.whatsapp.requests.post")
    @mock.patch.dict("os.environ", ENV_CONFIGURED, clear=True)
    def test_notifies_again_once_staff_reply_goes_stale(self, mock_post):
        mock_post.return_value = mock.Mock(ok=True, status_code=200, text="")
        thread = ChatThread.objects.create(customer=self.customer, kind="GENERAL")
        staff_msg = ChatMessage.objects.create(
            thread=thread, sender=None, sender_role="STAFF", body="on it",
        )
        ChatMessage.objects.filter(pk=staff_msg.pk).update(
            created_at=timezone.now() - timedelta(minutes=30),
        )

        auth(self.client, self.customer)
        with self.captureOnCommitCallbacks(execute=True):
            res = self.client.post(
                f"/api/chat/threads/{thread.id}/messages/", {"body": "still there?"}, format="json",
            )
        self.assertEqual(res.status_code, 201, res.content)
        mock_post.assert_called_once()

    @mock.patch("core.whatsapp.requests.post")
    @mock.patch.dict("os.environ", {}, clear=True)
    def test_unconfigured_provider_does_not_fail_the_message_post(self, mock_post):
        auth(self.client, self.customer)
        with self.captureOnCommitCallbacks(execute=True):
            res = self.client.post(
                "/api/chat/threads/", {"kind": "GENERAL", "body": "hello"}, format="json",
            )
        self.assertEqual(res.status_code, 201, res.content)
        mock_post.assert_not_called()

    @mock.patch("core.whatsapp.requests.post", side_effect=RuntimeError("boom"))
    @mock.patch.dict("os.environ", ENV_CONFIGURED, clear=True)
    def test_whatsapp_send_failure_does_not_fail_the_message_post(self, mock_post):
        # core.whatsapp.send_whatsapp already swallows this internally, but
        # this pins the outer guarantee: even if something in the notify path
        # blew up entirely, the message must already be committed.
        auth(self.client, self.customer)
        with self.captureOnCommitCallbacks(execute=True):
            res = self.client.post(
                "/api/chat/threads/", {"kind": "GENERAL", "body": "hello"}, format="json",
            )
        self.assertEqual(res.status_code, 201, res.content)
        self.assertEqual(ChatThread.objects.count(), 1)
        self.assertEqual(ChatMessage.objects.count(), 1)

    def test_no_admin_number_configured_skips_silently(self):
        config = StoreConfiguration.get_solo()
        config.whatsapp_admin_number = ""
        config.save()

        auth(self.client, self.customer)
        with self.captureOnCommitCallbacks(execute=True):
            res = self.client.post(
                "/api/chat/threads/", {"kind": "GENERAL", "body": "hello"}, format="json",
            )
        self.assertEqual(res.status_code, 201, res.content)
        self.assertEqual(WhatsAppAlertLog.objects.count(), 0)
