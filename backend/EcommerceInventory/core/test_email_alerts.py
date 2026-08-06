"""Email order alerts — the *active* admin notification channel.

WhatsApp (core/whatsapp.py) and SMS (core/sms.py) both ship dormant, waiting
on credentials the owner does not have yet. Email is what actually reaches the
owner today, so the contract that matters here is: a placed order always
produces an email attempt, and a broken mailbox can never lose the order.
"""
from unittest.mock import patch

from django.core import mail
from django.core.cache import cache
from django.test import TestCase, override_settings

from core.email_alerts import send_email_alert, send_email_alert_on_commit
from core.models import StoreConfiguration


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class SendEmailAlertTests(TestCase):
    def setUp(self):
        mail.outbox = []

    def test_sends_to_the_given_address(self):
        sent = send_email_alert(
            "owner@example.com", kind="store_order_admin",
            subject="New order FT-1", body="Someone bought something.")

        self.assertTrue(sent)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["owner@example.com"])
        self.assertIn("FT-1", mail.outbox[0].subject)

    def test_blank_destination_is_a_no_op_not_an_error(self):
        self.assertFalse(send_email_alert("", kind="k", subject="s", body="b"))
        self.assertEqual(len(mail.outbox), 0)

    def test_never_raises_when_the_mail_backend_explodes(self):
        """The whole point of the contract: order placement calls this, so a
        dead SMTP host must degrade to a logged failure, never a 500 that
        loses a real customer's order."""
        with patch("core.email_alerts.send_mail", side_effect=OSError("smtp down")):
            self.assertFalse(
                send_email_alert("owner@example.com", kind="k", subject="s", body="b"))

    def test_on_commit_variant_defers_until_after_commit(self):
        """Mirrors send_whatsapp_on_commit: order placement runs inside an
        atomic block holding select_for_update row locks, and SMTP is a
        blocking network call. Sending before commit would pin those locks."""
        with self.captureOnCommitCallbacks(execute=True):
            send_email_alert_on_commit(
                "owner@example.com", kind="k", subject="s", body="b")
            self.assertEqual(len(mail.outbox), 0)  # not yet — still in the block
        self.assertEqual(len(mail.outbox), 1)


class AlertEmailConfigurationTests(TestCase):
    def setUp(self):
        # get_solo() caches the singleton in Django's cache, which — unlike the
        # DB row — is not rolled back between tests, so a mutation in one test
        # leaks into the next.
        cache.clear()

    def test_store_configuration_defaults_to_the_owner_mailbox(self):
        self.assertEqual(StoreConfiguration.get_solo().alert_email, "fabrything@gmail.com")

    def test_alert_email_is_admin_editable_without_a_redeploy(self):
        config = StoreConfiguration.get_solo()
        config.alert_email = "someone.else@example.com"
        config.save()  # save() drops the singleton cache key
        self.assertEqual(StoreConfiguration.get_solo().alert_email, "someone.else@example.com")
