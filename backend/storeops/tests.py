import hashlib
import hmac
import io
import json
from datetime import timedelta
from unittest.mock import Mock, patch

from accounts.models import Users
from catalog.models import Products
from core.models import StoreConfiguration
from django.core.cache import cache
from django.db import transaction
from django.test import TestCase, TransactionTestCase
from django.utils import timezone
from orders.models import Order
from PIL import Image, ImageDraw
from rest_framework.test import APIClient

from .alerts import enqueue_order_alert, process_one_alert, record_delivery
from .capacity import capacity_item, capacity_report, ensure_write_capacity
from .images import (
    ReviewRequired,
    claim_image,
    enqueue_product,
    normalize_image,
    process_one_image,
    read_source,
    restore_job,
)
from .models import (
    CapacitySnapshot,
    ImageCleanupJob,
    ImageWorkerLease,
    OperationsPolicy,
    OrderAlert,
)

ENV = {"WHATSAPP_ACCESS_TOKEN": "private-test-token", "WHATSAPP_PHONE_NUMBER_ID": "123"}


def product(**kwargs):
    return Products.objects.create(
        name="Test shirt",
        sku="TEST",
        description="Cotton shirt",
        initial_buying_price=100,
        initial_selling_price=200,
        **kwargs,
    )


def photo():
    stream = io.BytesIO()
    Image.new("RGB", (80, 80), "red").save(stream, "PNG")
    return stream.getvalue()


def mask(image):
    result = image.convert("RGBA")
    alpha = Image.new("L", image.size, 0)
    ImageDraw.Draw(alpha).rectangle((15, 15, 65, 65), fill=255)
    result.putalpha(alpha)
    return result


class AutocommitImageQueueTests(TransactionTestCase):
    @patch(
        "storeops.images.enqueue_product", side_effect=RuntimeError("queue unavailable")
    )
    def test_failed_queue_does_not_leave_a_half_created_product(self, enqueue):
        with self.assertRaises(RuntimeError):
            product(image=["https://example.com/a.png"])
        self.assertFalse(Products.objects.exists())


class ImageQueueTests(TestCase):
    def test_new_products_enqueue_once_without_running_model_or_network(self):
        with patch("storeops.images.read_source") as read:
            p = product(image=["https://example.com/shirt.png"])
            enqueue_product(p)
        self.assertEqual(ImageCleanupJob.objects.count(), 1)
        read.assert_not_called()

    def test_product_rollback_also_rolls_back_job(self):
        with self.assertRaises(ValueError), transaction.atomic():
            product(image=["https://example.com/shirt.png"])
            raise ValueError()
        self.assertFalse(ImageCleanupJob.objects.exists())

    def test_auto_switch_disables_new_jobs(self):
        OperationsPolicy.objects.create(pk=1, auto_clean_images=False)
        product(image=["https://example.com/shirt.png"])
        self.assertFalse(ImageCleanupJob.objects.exists())

    def test_normalization_keeps_product_and_white_canvas(self):
        content = normalize_image(photo(), remover=mask)
        with Image.open(io.BytesIO(content)) as image:
            self.assertEqual(image.size, (1200, 1200))
            self.assertEqual(image.format, "WEBP")
            self.assertTrue(all(c > 245 for c in image.getpixel((0, 0))[:3]))
            self.assertGreater(image.getpixel((600, 600))[0], 200)

    def test_empty_or_full_foreground_is_held_for_review(self):
        for alpha in (0, 255):

            def uncertain(image, mask_alpha=alpha):
                output = image.convert("RGBA")
                output.putalpha(mask_alpha)
                return output

            with self.assertRaises(ReviewRequired):
                normalize_image(photo(), remover=uncertain)

    def test_oversized_content_rejected_before_decode(self):
        with self.assertRaises(ReviewRequired):
            normalize_image(b"x" * (5 * 1024 * 1024 + 1))

    def test_claim_is_global_single_image_even_for_different_jobs(self):
        product(image=["https://example.com/a.png", "https://example.com/b.png"])
        self.assertIsNotNone(claim_image())
        self.assertIsNone(claim_image())

    def test_expired_claim_can_recover_with_new_token(self):
        product(image=["https://example.com/a.png"])
        original = claim_image()
        ImageWorkerLease.objects.update(until=timezone.now() - timedelta(minutes=1))
        ImageCleanupJob.objects.update(
            lease_until=timezone.now() - timedelta(minutes=1)
        )
        recovered = claim_image()
        self.assertNotEqual(original.lease_token, recovered.lease_token)
        self.assertEqual(recovered.attempts, 2)

    @patch("storeops.images.save_file", side_effect=["/original.png", "/clean.webp"])
    @patch("storeops.images.normalize_image", return_value=b"webp")
    @patch("storeops.images.read_source", side_effect=lambda url: photo())
    def test_success_applies_and_restore_preserves_original(
        self, read, normalize, save
    ):
        p = product(image=["https://example.com/a.png"])
        self.assertTrue(process_one_image())
        p.refresh_from_db()
        self.assertEqual(p.image, ["/clean.webp"])
        job = ImageCleanupJob.objects.get()
        self.assertEqual(job.status, "completed")
        restore_job(job.pk)
        p.refresh_from_db()
        self.assertEqual(p.image, ["/original.png"])
        with self.assertRaises(ValueError):
            restore_job(job.pk)

    @patch("storeops.images.save_file", side_effect=["/original.png", "/clean.webp"])
    @patch("storeops.images.normalize_image", return_value=b"webp")
    def test_editor_change_is_never_overwritten(self, normalize, save):
        p = product(image=["https://example.com/a.png"])

        def change(url):
            Products.objects.filter(pk=p.pk).update(
                image=["https://example.com/manual.png"]
            )
            return photo()

        with patch("storeops.images.read_source", side_effect=change):
            process_one_image()
        p.refresh_from_db()
        self.assertEqual(p.image, ["https://example.com/manual.png"])
        self.assertEqual(ImageCleanupJob.objects.get().status, "stale")

    @patch("catalog.supplier_security.supplier_get_bytes", return_value=b"bytes")
    def test_remote_media_path_is_not_treated_as_local(self, fetch):
        read_source("https://example.com/api/media/" + "a" * 64 + "/")
        fetch.assert_called_once()


class AlertQueueTests(TestCase):
    def setUp(self):
        cache.clear()
        config = StoreConfiguration.get_solo()
        config.whatsapp_admin_number = "8801353529899"
        config.save()
        self.order = Order.objects.create(
            subtotal=200,
            total_amount=270,
            shipping_amount=70,
            contact_name="Test",
            contact_phone="01700000000",
            shipping_address={},
        )

    def test_enqueue_is_idempotent_and_has_no_http(self):
        with patch("storeops.alerts.requests.post") as post:
            enqueue_order_alert(self.order, ["test"])
            enqueue_order_alert(self.order, ["test"])
        self.assertEqual(OrderAlert.objects.count(), 1)
        post.assert_not_called()

    @patch.dict("os.environ", {}, clear=True)
    @patch("storeops.alerts.requests.post")
    def test_missing_provider_retains_queue_without_attempt(self, post):
        job = enqueue_order_alert(self.order, [])
        self.assertFalse(process_one_alert())
        job.refresh_from_db()
        self.assertEqual(job.attempts, 0)
        post.assert_not_called()

    @patch.dict("os.environ", ENV, clear=True)
    @patch("storeops.alerts.requests.post")
    def test_success_is_accepted_until_signed_delivery_callback(self, post):
        post.return_value = Mock(
            ok=True, json=lambda: {"messages": [{"id": "wamid.test"}]}
        )
        job = enqueue_order_alert(self.order, ["test"])
        process_one_alert()
        process_one_alert()
        job.refresh_from_db()
        self.assertEqual(job.status, "accepted")
        self.assertEqual(job.provider_id, "wamid.test")
        post.assert_called_once()

    @patch.dict("os.environ", ENV, clear=True)
    @patch(
        "storeops.alerts.requests.post", side_effect=TimeoutError("private-test-token")
    )
    def test_timeout_is_unknown_and_never_blindly_retried(self, post):
        job = enqueue_order_alert(self.order, [])
        process_one_alert()
        process_one_alert()
        job.refresh_from_db()
        self.assertEqual(job.status, "unknown")
        self.assertNotIn("private-test-token", job.error)
        post.assert_called_once()

    @patch.dict("os.environ", ENV, clear=True)
    @patch("storeops.alerts.requests.post")
    def test_expired_sending_lease_is_ambiguous(self, post):
        job = enqueue_order_alert(self.order, [])
        job.status, job.lease_until = "sending", timezone.now() - timedelta(seconds=1)
        job.save()
        process_one_alert()
        job.refresh_from_db()
        self.assertEqual(job.status, "unknown")
        post.assert_not_called()

    @patch.dict("os.environ", {"WHATSAPP_APP_SECRET": "test-secret"}, clear=True)
    def test_delivery_webhook_requires_signature_and_never_regresses(self):
        job = enqueue_order_alert(self.order, [])
        job.status, job.provider_id = "accepted", "wamid.test"
        job.save()

        def payload(status):
            return json.dumps(
                {
                    "entry": [
                        {
                            "changes": [
                                {
                                    "value": {
                                        "statuses": [
                                            {"id": "wamid.test", "status": status}
                                        ]
                                    }
                                }
                            ]
                        }
                    ]
                }
            ).encode()

        url = "/api/store/webhooks/whatsapp/"
        self.assertEqual(
            self.client.post(
                url, payload("delivered"), content_type="application/json"
            ).status_code,
            403,
        )
        for status in ("delivered", "sent"):
            body = payload(status)
            signature = (
                "sha256=" + hmac.new(b"test-secret", body, hashlib.sha256).hexdigest()
            )
            self.assertEqual(
                self.client.post(
                    url,
                    body,
                    content_type="application/json",
                    HTTP_X_HUB_SIGNATURE_256=signature,
                ).status_code,
                200,
            )
        job.refresh_from_db()
        self.assertEqual(job.status, "delivered")

    @patch.dict("os.environ", ENV, clear=True)
    @patch("storeops.alerts.requests.post")
    def test_fast_delivery_callback_before_send_response_is_retained(self, post):
        record_delivery("wamid.fast", "read")
        post.return_value = Mock(
            ok=True, json=lambda: {"messages": [{"id": "wamid.fast"}]}
        )
        job = enqueue_order_alert(self.order, [])
        process_one_alert()
        job.refresh_from_db()
        self.assertEqual(job.status, "read")

    @patch.dict("os.environ", ENV, clear=True)
    @patch("storeops.alerts.requests.post")
    def test_rate_limit_retries_only_after_backoff(self, post):
        post.return_value = Mock(ok=False, status_code=429)
        job = enqueue_order_alert(self.order, [])
        process_one_alert()
        process_one_alert()
        job.refresh_from_db()
        self.assertEqual(job.status, "queued")
        self.assertGreater(job.available_at, timezone.now())
        post.assert_called_once()


class CapacityTests(TestCase):
    def setUp(self):
        cache.clear()

    def test_unknown_limits_are_not_reported_as_free_space(self):
        self.assertIsNone(capacity_item(1000, None)["remaining_bytes"])
        self.assertIsNone(capacity_item(1000, 5000, complete=False)["remaining_bytes"])
        self.assertEqual(capacity_item(900, 1000)["status"], "critical")

    def test_snapshot_absence_remains_unknown(self):
        report = capacity_report()
        self.assertIsNone(report["database"]["used_bytes"])
        self.assertTrue(report["stale"])

    @patch("storeops.capacity.storage.use_s3", return_value=False)
    @patch("storeops.capacity.database_size", return_value={"size_bytes": 96})
    def test_headroom_guard_blocks_image_writes(self, size, s3):
        OperationsPolicy.objects.create(pk=1, database_budget_bytes=100)
        with self.assertRaises(RuntimeError):
            ensure_write_capacity(1)

    @patch("storeops.capacity.database_size", return_value={"size_bytes": 200})
    def test_projection_requires_at_least_one_day_of_measured_growth(self, size):
        OperationsPolicy.objects.create(pk=1, database_budget_bytes=1000)
        CapacitySnapshot.objects.create(
            database_bytes=100, created_at=timezone.now() - timedelta(days=2)
        )
        CapacitySnapshot.objects.create(database_bytes=200)
        self.assertAlmostEqual(
            capacity_report()["database"]["projected_days_remaining"], 16, delta=0.1
        )


class WorkerCommandTests(TestCase):
    @patch(
        "storeops.management.commands.run_store_operations.process_one_alert",
        return_value=False,
    )
    @patch("storeops.management.commands.run_store_operations.process_one_image")
    @patch("storeops.management.commands.run_store_operations.take_snapshot")
    def test_alerts_only_never_initializes_image_work_or_inventory(
        self, snapshot, image, alert
    ):
        from django.core.management import call_command

        call_command("run_store_operations", alerts_only=True, stdout=io.StringIO())
        image.assert_not_called()
        snapshot.assert_not_called()
        alert.assert_called_once()


class PermissionTests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient()

    def test_anonymous_and_customer_cannot_access_or_mutate(self):
        url = "/api/store/admin/operations/"
        self.assertEqual(self.client.get(url).status_code, 401)
        user = Users.objects.create(
            username="customer", email="customer@test.invalid", role="Customer"
        )
        self.client.force_authenticate(user)
        self.assertEqual(self.client.get(url).status_code, 403)
        self.assertEqual(
            self.client.patch(
                url, {"auto_clean_images": False}, format="json"
            ).status_code,
            403,
        )
        self.assertEqual(
            self.client.post(
                url + "images/", {"product_ids": [1]}, format="json"
            ).status_code,
            403,
        )

    def test_platform_staff_can_save_policy_but_not_invalid_destinations(self):
        user = Users.objects.create(
            username="admin", email="admin@test.invalid", role="Admin"
        )
        self.client.force_authenticate(user)
        url = "/api/store/admin/operations/"
        self.assertEqual(self.client.get(url).status_code, 200)
        self.assertEqual(
            self.client.patch(
                url, {"whatsapp_admin_number": "+8801invalid"}, format="json"
            ).status_code,
            400,
        )
        response = self.client.patch(
            url,
            {"auto_clean_images": False, "whatsapp_admin_number": "8801353529899"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(OperationsPolicy.current().auto_clean_images)
        self.assertNotIn("private-test-token", response.content.decode())
