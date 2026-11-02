from unittest import mock
from django.test import TestCase
from django.contrib.auth import get_user_model
from food.models import DeviceToken, Notification
from food.services import notify
from food import services_push

User = get_user_model()


class PushTests(TestCase):
    def setUp(self):
        self.u = User.objects.create(username="c1", role="Customer")
        DeviceToken.objects.create(user=self.u, expo_token="ExponentPushToken[a]",
                                   app="customer", platform="android", enabled=True)
        DeviceToken.objects.create(user=self.u, expo_token="ExponentPushToken[off]",
                                   app="customer", platform="android", enabled=False)

    @mock.patch("food.services_push._post_to_expo")
    def test_send_expo_push_posts_only_given_tokens(self, post):
        post.return_value = [{"status": "ok"}]
        services_push.send_expo_push(["ExponentPushToken[a]"], "Hi", "Body", {"k": "v"})
        self.assertEqual(post.call_count, 1)
        messages = post.call_args[0][0]
        self.assertEqual(messages[0]["to"], "ExponentPushToken[a]")
        self.assertEqual(messages[0]["title"], "Hi")

    @mock.patch("food.services_push._post_to_expo")
    def test_device_not_registered_disables_token(self, post):
        post.return_value = [{"status": "error", "details": {"error": "DeviceNotRegistered"}}]
        services_push.send_expo_push(["ExponentPushToken[a]"], "Hi", "Body")
        self.assertFalse(DeviceToken.objects.get(expo_token="ExponentPushToken[a]").enabled)

    @mock.patch("food.services_push.send_expo_push")
    def test_notify_creates_notification_and_pushes_enabled_only(self, send):
        # send_expo_push is deferred via transaction.on_commit (see food/services.py
        # notify()), so the callback only fires once the surrounding transaction
        # commits. captureOnCommitCallbacks(execute=True) commits+runs it here.
        with self.captureOnCommitCallbacks(execute=True):
            notify(self.u, "Order update", "On the way", "ORD123")
        self.assertTrue(Notification.objects.filter(user=self.u, title="Order update").exists())
        send.assert_called_once()
        tokens = send.call_args[0][0]
        self.assertEqual(tokens, ["ExponentPushToken[a]"])  # disabled token excluded

    @mock.patch("food.services_push.send_expo_push")
    def test_notify_creates_notification_even_if_push_never_fires(self, send):
        # Without draining on_commit callbacks, the Notification row still
        # exists (it's created eagerly) even though the deferred push does not.
        notify(self.u, "Order update", "On the way", "ORD123")
        self.assertTrue(Notification.objects.filter(user=self.u, title="Order update").exists())
        send.assert_not_called()
