import hashlib
import hmac
import json
import os
from datetime import timedelta
from typing import ClassVar

from catalog.models import Products
from core import whatsapp
from core.helpers import renderResponse
from core.models import StoreConfiguration
from django.db import transaction
from django.db.models import Count
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from rest_framework import serializers
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication
from storefront.permissions import IsPlatformStaff

from .alerts import record_delivery
from .capacity import capacity_report
from .images import enqueue_product, restore_job
from .models import ImageCleanupJob, OperationsPolicy, OrderAlert, WorkerHeartbeat


class PolicySerializer(serializers.ModelSerializer):
    whatsapp_admin_number = serializers.RegexField(
        r"^[1-9][0-9]{7,14}$", required=False, allow_blank=True
    )
    whatsapp_template = serializers.RegexField(r"^[a-z0-9_]{1,100}$", required=False)
    whatsapp_language = serializers.RegexField(
        r"^[a-z]{2,3}(?:_[A-Z]{2})?$", required=False
    )
    database_budget_bytes = serializers.IntegerField(
        min_value=1, max_value=10**18, allow_null=True, required=False
    )
    object_budget_bytes = serializers.IntegerField(
        min_value=1, max_value=10**18, allow_null=True, required=False
    )

    class Meta:
        model = OperationsPolicy
        fields: ClassVar[list] = [
            "auto_clean_images",
            "database_budget_bytes",
            "object_budget_bytes",
            "budget_note",
            "whatsapp_enabled",
            "whatsapp_template",
            "whatsapp_language",
            "whatsapp_admin_number",
            "updated_at",
        ]
        read_only_fields: ClassVar[list] = ["updated_at"]

    def update(self, instance, validated_data):
        number = validated_data.pop("whatsapp_admin_number", None)
        if number is not None:
            config = StoreConfiguration.get_solo()
            config.whatsapp_admin_number = number
            config.save(update_fields=["whatsapp_admin_number", "updated_at"])
        return super().update(instance, validated_data)


class StaffView(APIView):
    authentication_classes: ClassVar[list] = [JWTAuthentication]
    permission_classes: ClassVar[list] = [IsAuthenticated, IsPlatformStaff]


def policy_data():
    data = PolicySerializer(OperationsPolicy.current()).data
    data["whatsapp_admin_number"] = StoreConfiguration.get_solo().whatsapp_admin_number
    return data


class OperationsView(StaffView):
    def get(self, request):
        worker = (
            WorkerHeartbeat.objects.filter(name="store-operations")
            .values("status", "detail", "updated_at")
            .first()
        )
        if worker:
            worker["stale"] = worker["updated_at"] < timezone.now() - timedelta(
                minutes=5
            )
        alert_worker = (
            WorkerHeartbeat.objects.filter(name="store-orders")
            .values("status", "detail", "updated_at")
            .first()
        )
        if alert_worker:
            alert_worker["stale"] = alert_worker[
                "updated_at"
            ] < timezone.now() - timedelta(minutes=5)
        jobs = list(
            ImageCleanupJob.objects.select_related("product").order_by("-created_at")[
                :50
            ]
        )
        alerts = list(
            OrderAlert.objects.select_related("order").order_by("-created_at")[:30]
        )
        counts = dict(
            ImageCleanupJob.objects.values("status")
            .annotate(n=Count("id"))
            .values_list("status", "n")
        )
        return renderResponse(
            data={
                "policy": policy_data(),
                "capacity": capacity_report(),
                "worker": worker,
                "queue_counts": counts,
                "jobs": [
                    {
                        "id": j.pk,
                        "product_id": j.product_id,
                        "product_name": j.product.name,
                        "slot": j.slot,
                        "original_url": j.backup_url or j.original_url,
                        "output_url": j.output_url,
                        "status": j.status,
                        "attempts": j.attempts,
                        "error": j.error,
                        "created_at": j.created_at,
                    }
                    for j in jobs
                ],
                "whatsapp": {
                    "configured": whatsapp.is_configured(),
                    "worker": alert_worker,
                    "webhook_configured": bool(
                        os.getenv("WHATSAPP_APP_SECRET")
                        and os.getenv("WHATSAPP_VERIFY_TOKEN")
                    ),
                    "alerts": [
                        {
                            "id": a.pk,
                            "order_number": a.order.order_number,
                            "status": a.status,
                            "attempts": a.attempts,
                            "error": a.error,
                            "created_at": a.created_at,
                        }
                        for a in alerts
                    ],
                },
                "measured_at": timezone.now(),
            },
            message="Store operations",
        )

    @transaction.atomic
    def patch(self, request):
        policy = OperationsPolicy.objects.select_for_update().get(
            pk=OperationsPolicy.current().pk
        )
        serializer = PolicySerializer(policy, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return renderResponse(data=policy_data(), message="Operations settings saved")


class QueueImagesView(StaffView):
    def post(self, request):
        field = serializers.ListField(
            child=serializers.IntegerField(min_value=1), min_length=1, max_length=100
        )
        ids = set(field.run_validation(request.data.get("product_ids")))
        products = list(Products.objects.filter(pk__in=ids))
        if len(products) != len(ids):
            raise serializers.ValidationError(
                "Some products no longer exist. Refresh the selection."
            )
        with transaction.atomic():
            jobs = [job.pk for product in products for job in enqueue_product(product)]
        return renderResponse(
            data={"job_ids": jobs, "products": len(products)},
            message="Product photos queued",
            status=202,
        )


class ImageActionView(StaffView):
    def post(self, request, pk, action):
        if action == "restore":
            get_object_or_404(ImageCleanupJob, pk=pk)
            try:
                restore_job(pk)
            except ValueError as exc:
                raise serializers.ValidationError(str(exc))
        elif action == "retry":
            with transaction.atomic():
                job = get_object_or_404(
                    ImageCleanupJob.objects.select_for_update(), pk=pk
                )
                if job.status not in ("failed", "review"):
                    raise serializers.ValidationError(
                        "Only failed or review jobs may be retried."
                    )
                job.status, job.attempts, job.error = "queued", 0, ""
                job.save()
        else:
            raise serializers.ValidationError("Unsupported image action.")
        return renderResponse(data={"id": pk}, message="Image action saved")


@csrf_exempt
def whatsapp_webhook(request):
    """Only signed Meta callbacks can promote accepted messages to delivered."""
    verify_token = os.getenv("WHATSAPP_VERIFY_TOKEN", "")
    if request.method == "GET":
        supplied = request.GET.get("hub.verify_token", "")
        if (
            verify_token
            and request.GET.get("hub.mode") == "subscribe"
            and hmac.compare_digest(supplied, verify_token)
        ):
            return HttpResponse(
                request.GET.get("hub.challenge", ""), content_type="text/plain"
            )
        return HttpResponse(status=403)
    if request.method != "POST":
        return HttpResponse(status=405)
    secret = os.getenv("WHATSAPP_APP_SECRET", "")
    if not secret or int(request.META.get("CONTENT_LENGTH") or 0) > 256_000:
        return HttpResponse(status=403)
    body = request.body
    if len(body) > 256_000:
        return HttpResponse(status=413)
    signature = "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(
        signature, request.headers.get("X-Hub-Signature-256", "")
    ):
        return HttpResponse(status=403)
    try:
        data = json.loads(body)
        for entry in data.get("entry", [])[:100]:
            for change in entry.get("changes", [])[:100]:
                for item in change.get("value", {}).get("statuses", [])[:100]:
                    status = item.get("status")
                    if status not in (
                        "sent",
                        "delivered",
                        "read",
                        "failed",
                    ) or not item.get("id"):
                        continue
                    if len(str(item["id"])) <= 255:
                        record_delivery(item["id"], status)
    except (ValueError, TypeError, AttributeError):
        return HttpResponse(status=400)
    return HttpResponse(status=200)
