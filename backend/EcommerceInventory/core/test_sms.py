"""SMS provider unit tests — the dormant channel (core/sms.py).

The contract worth pinning is the dormancy itself: with no credentials in the
environment this module must make no network call and raise nothing, so it can
sit in the order path for months before the owner buys a gateway. Mirrors
core/test_whatsapp.py.
"""
from unittest import mock

from django.test import TestCase

from core import sms

ENV_CONFIGURED = {"SMS_API_KEY": "key", "SMS_SENDER_ID": "Fabrything"}


class SmsDormancyTests(TestCase):
    @mock.patch.dict("os.environ", {}, clear=True)
    def test_unconfigured_provider_is_inert(self):
        self.assertFalse(sms.is_configured())

    @mock.patch("core.sms.requests.post")
    @mock.patch.dict("os.environ", {}, clear=True)
    def test_send_makes_no_network_call_while_unconfigured(self, mock_post):
        self.assertFalse(sms.send_sms("8801700000001", kind="k", body="b"))
        mock_post.assert_not_called()

    @mock.patch("core.sms.requests.post")
    @mock.patch.dict("os.environ", ENV_CONFIGURED, clear=True)
    def test_blank_destination_makes_no_network_call(self, mock_post):
        self.assertFalse(sms.send_sms("", kind="k", body="b"))
        mock_post.assert_not_called()


class SmsSendTests(TestCase):
    @mock.patch("core.sms.requests.post")
    @mock.patch.dict("os.environ", ENV_CONFIGURED, clear=True)
    def test_configured_provider_posts_credentials_and_message(self, mock_post):
        mock_post.return_value = mock.Mock(ok=True, status_code=200)

        self.assertTrue(sms.send_sms("8801700000001", kind="k", body="Order FT-1"))

        _, kwargs = mock_post.call_args
        self.assertEqual(kwargs["data"]["api_key"], "key")
        self.assertEqual(kwargs["data"]["msisdn"], "8801700000001")
        self.assertEqual(kwargs["data"]["message"], "Order FT-1")

    @mock.patch("core.sms.requests.post", side_effect=TimeoutError("no route to host"))
    @mock.patch.dict("os.environ", ENV_CONFIGURED, clear=True)
    def test_network_failure_returns_false_and_never_raises(self, mock_post):
        self.assertFalse(sms.send_sms("8801700000001", kind="k", body="b"))

    @mock.patch("core.sms.requests.post")
    @mock.patch.dict("os.environ", ENV_CONFIGURED, clear=True)
    def test_gateway_rejection_returns_false(self, mock_post):
        mock_post.return_value = mock.Mock(ok=False, status_code=402)
        self.assertFalse(sms.send_sms("8801700000001", kind="k", body="b"))
