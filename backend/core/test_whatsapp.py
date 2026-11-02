"""core.whatsapp — the Meta WhatsApp Cloud API provider.

Ships dormant: WHATSAPP_ACCESS_TOKEN / WHATSAPP_PHONE_NUMBER_ID are read from
the environment and everything is a no-op until both are set. These tests
never touch the network — requests.post is always patched.
"""
from unittest import mock

from django.test import TestCase, override_settings

from core.models import WhatsAppAlertLog
from core.whatsapp import is_configured, send_whatsapp, send_whatsapp_on_commit

ENV_CONFIGURED = {
    "WHATSAPP_ACCESS_TOKEN": "super-secret-token-do-not-leak",
    "WHATSAPP_PHONE_NUMBER_ID": "1234567890",
}


class UnconfiguredProviderTests(TestCase):
    """No env vars set — the state the project ships in."""

    @mock.patch.dict("os.environ", {}, clear=True)
    def test_is_configured_false_with_no_env(self):
        self.assertFalse(is_configured())

    @mock.patch("core.whatsapp.requests.post")
    @mock.patch.dict("os.environ", {}, clear=True)
    def test_send_whatsapp_returns_false_and_never_calls_the_network(self, mock_post):
        result = send_whatsapp(
            "8801700000000", kind="test", template_name="tpl",
            params=["a", "b"],
        )
        self.assertFalse(result)
        mock_post.assert_not_called()

    @mock.patch("core.whatsapp.requests.post")
    @mock.patch.dict("os.environ", {}, clear=True)
    def test_send_whatsapp_does_not_raise_when_unconfigured(self, mock_post):
        # Must never raise — an unconfigured provider must never break checkout.
        try:
            send_whatsapp("8801700000000", kind="test", template_name="tpl", params=[])
        except Exception as exc:  # pragma: no cover - failure path
            self.fail(f"send_whatsapp raised while unconfigured: {exc}")

    @mock.patch("core.whatsapp.requests.post")
    @mock.patch.dict("os.environ", {}, clear=True)
    def test_send_whatsapp_writes_no_log_row_when_unconfigured(self, mock_post):
        send_whatsapp("8801700000000", kind="test", template_name="tpl", params=[])
        self.assertEqual(WhatsAppAlertLog.objects.count(), 0)

    @mock.patch("core.whatsapp.requests.post")
    @mock.patch.dict("os.environ", ENV_CONFIGURED, clear=True)
    def test_send_whatsapp_returns_false_with_blank_recipient_even_when_configured(self, mock_post):
        result = send_whatsapp("", kind="test", template_name="tpl", params=[])
        self.assertFalse(result)
        mock_post.assert_not_called()
        self.assertEqual(WhatsAppAlertLog.objects.count(), 0)


class ConfiguredProviderTests(TestCase):
    """WHATSAPP_ACCESS_TOKEN / WHATSAPP_PHONE_NUMBER_ID present."""

    @mock.patch("core.whatsapp.requests.post")
    @mock.patch.dict("os.environ", ENV_CONFIGURED, clear=True)
    def test_is_configured_true(self, mock_post):
        self.assertTrue(is_configured())

    @mock.patch("core.whatsapp.requests.post")
    @mock.patch.dict("os.environ", ENV_CONFIGURED, clear=True)
    def test_posts_to_the_right_url_with_auth_header_and_template_payload(self, mock_post):
        mock_post.return_value = mock.Mock(ok=True, status_code=200, text="")

        result = send_whatsapp(
            "8801700000000", kind="store_order_admin", template_name="store_new_order_admin",
            params=["ORD-1", "Karim", "01700000000", "2", "500.00 BDT"],
            language_code="en", related_order="ORD-1",
        )

        self.assertTrue(result)
        mock_post.assert_called_once()
        call = mock_post.call_args
        url = call.args[0] if call.args else call.kwargs["url"]
        self.assertEqual(
            url, "https://graph.facebook.com/v20.0/1234567890/messages"
        )
        headers = call.kwargs["headers"]
        self.assertEqual(headers["Authorization"], "Bearer super-secret-token-do-not-leak")
        payload = call.kwargs["json"]
        self.assertEqual(payload["messaging_product"], "whatsapp")
        self.assertEqual(payload["to"], "8801700000000")
        self.assertEqual(payload["type"], "template")
        self.assertEqual(payload["template"]["name"], "store_new_order_admin")
        self.assertEqual(payload["template"]["language"], {"code": "en"})
        body_params = payload["template"]["components"][0]["parameters"]
        self.assertEqual([p["text"] for p in body_params],
                         ["ORD-1", "Karim", "01700000000", "2", "500.00 BDT"])
        self.assertEqual(call.kwargs["timeout"], 5)

    @mock.patch("core.whatsapp.requests.post")
    @mock.patch.dict("os.environ", ENV_CONFIGURED, clear=True)
    def test_custom_api_version_is_honoured(self, mock_post):
        mock_post.return_value = mock.Mock(ok=True, status_code=200, text="")
        with mock.patch.dict("os.environ", {"WHATSAPP_API_VERSION": "v21.0"}):
            send_whatsapp("8801700000000", kind="k", template_name="t", params=[])
        call = mock_post.call_args
        url = call.args[0] if call.args else call.kwargs["url"]
        self.assertIn("v21.0", url)

    @mock.patch("core.whatsapp.requests.post")
    @mock.patch.dict("os.environ", ENV_CONFIGURED, clear=True)
    def test_success_is_recorded_in_the_attempt_log_without_the_token(self, mock_post):
        mock_post.return_value = mock.Mock(ok=True, status_code=200, text="")
        send_whatsapp("8801700000000", kind="store_order_admin", template_name="tpl",
                      params=["ORD-1"], related_order="ORD-1")

        log = WhatsAppAlertLog.objects.get()
        self.assertEqual(log.recipient, "8801700000000")
        self.assertEqual(log.kind, "store_order_admin")
        self.assertEqual(log.related_order, "ORD-1")
        self.assertTrue(log.success)
        self.assertEqual(log.error, "")
        self.assertNotIn("super-secret-token-do-not-leak", log.payload_summary)
        self.assertNotIn("super-secret-token-do-not-leak", log.error)

    @mock.patch("core.whatsapp.requests.post")
    @mock.patch.dict("os.environ", ENV_CONFIGURED, clear=True)
    def test_http_failure_is_recorded_and_does_not_raise(self, mock_post):
        mock_post.return_value = mock.Mock(ok=False, status_code=401, text="Invalid OAuth token")
        result = send_whatsapp("8801700000000", kind="k", template_name="t", params=[])

        self.assertFalse(result)
        log = WhatsAppAlertLog.objects.get()
        self.assertFalse(log.success)
        self.assertIn("401", log.error)
        self.assertNotIn("super-secret-token-do-not-leak", log.error)

    @mock.patch("core.whatsapp.requests.post", side_effect=TimeoutError("timed out"))
    @mock.patch.dict("os.environ", ENV_CONFIGURED, clear=True)
    def test_network_timeout_is_swallowed_and_recorded(self, mock_post):
        result = send_whatsapp("8801700000000", kind="k", template_name="t", params=[])

        self.assertFalse(result)
        log = WhatsAppAlertLog.objects.get()
        self.assertFalse(log.success)
        self.assertIn("timed out", log.error)

    @mock.patch("core.whatsapp.requests.post", side_effect=ConnectionError("boom"))
    @mock.patch.dict("os.environ", ENV_CONFIGURED, clear=True)
    def test_generic_network_error_never_raises(self, mock_post):
        try:
            result = send_whatsapp("8801700000000", kind="k", template_name="t", params=[])
        except Exception as exc:  # pragma: no cover - failure path
            self.fail(f"send_whatsapp raised on network error: {exc}")
        self.assertFalse(result)


class SendOnCommitTests(TestCase):
    @mock.patch("core.whatsapp.requests.post")
    @mock.patch.dict("os.environ", ENV_CONFIGURED, clear=True)
    def test_defers_send_until_after_commit(self, mock_post):
        mock_post.return_value = mock.Mock(ok=True, status_code=200, text="")
        with self.captureOnCommitCallbacks(execute=False) as callbacks:
            send_whatsapp_on_commit("8801700000000", kind="k", template_name="t", params=[])
            # Not sent yet — still inside the transaction / before commit ran.
            mock_post.assert_not_called()
        self.assertEqual(len(callbacks), 1)

    @mock.patch("core.whatsapp.requests.post")
    @mock.patch.dict("os.environ", ENV_CONFIGURED, clear=True)
    def test_runs_after_commit_executes(self, mock_post):
        mock_post.return_value = mock.Mock(ok=True, status_code=200, text="")
        with self.captureOnCommitCallbacks(execute=True):
            send_whatsapp_on_commit("8801700000000", kind="k", template_name="t", params=[])
        mock_post.assert_called_once()
