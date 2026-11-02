"""Staff-facing custom-print endpoints.

Gated by IsPrintStaff (core.helpers.isPlatformStaff), not by a per-user
ModuleUrls row -- /api/print/ sits in core.middleware.PUBLIC_API_PREFIXES for
the same reason /api/food/ and /api/chat/ do (it mixes customer- and
staff-authenticated endpoints under one prefix), so IsPrintStaff is the only
thing standing between these views and any logged-in Customer/Rider/
Restaurant account.
"""
import os

from django.shortcuts import get_object_or_404
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.viewsets import ModelViewSet
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication

from core.helpers import renderResponse
from core.storage import save_file
from food.views_vendor import EnvelopeModelViewSetMixin
from printing.models import PrintArea, PrintablePreset, PrintPricingConfig, PrintProof, PrintRequest
from printing.permissions import IsPrintStaff
from printing.serializers import (
    AdminPriceSerializer, AdminPrintRequestDetailSerializer, AdminPrintRequestListSerializer,
    AdminProofCreateSerializer, AdminStatusSerializer, PrintablePresetWriteSerializer, PrintAreaSerializer,
    PrintPricingConfigSerializer,
)
from printing.services import attach_proof, set_price


class AdminPrintRequestQueueView(APIView):
    """`?status=<Status>` filters; always newest first (PrintRequest's
    default ordering)."""

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsPrintStaff]

    def get(self, request):
        qs = PrintRequest.objects.select_related("customer", "product", "preset").prefetch_related("print_areas")

        status = request.query_params.get("status")
        if status in PrintRequest.Status.values:
            qs = qs.filter(status=status)

        return renderResponse(data=AdminPrintRequestListSerializer(qs, many=True).data, message="Queue retrieved")


class AdminPrintRequestDetailView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsPrintStaff]

    def get(self, request, pk):
        print_request = get_object_or_404(PrintRequest, pk=pk)
        return renderResponse(
            data=AdminPrintRequestDetailSerializer(print_request).data, message="Print request retrieved",
        )

    def patch(self, request, pk):
        """Staff-only free-text notes -- everything else about a request
        (price, status, artwork) has its own dedicated, audited action."""
        print_request = get_object_or_404(PrintRequest, pk=pk)
        notes = request.data.get("staff_notes")
        if notes is None:
            return renderResponse(data="staff_notes is required.", message="Validation error", status=400)
        print_request.staff_notes = notes
        print_request.save(update_fields=["staff_notes", "updated_at"])
        return renderResponse(data=AdminPrintRequestDetailSerializer(print_request).data, message="Notes updated")


class AdminPrintProofCreateView(APIView):
    """Attach a new artwork version. Accepts either a direct multipart file
    (goes straight through core.storage.save_file) or a JSON body with an
    already-uploaded ``image`` URL (e.g. via POST /api/uploads/) -- both end
    up calling printing.services.attach_proof, the single place that
    advances the request's status and posts the chat system message."""

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsPrintStaff]
    parser_classes = (MultiPartParser, FormParser, JSONParser)

    def post(self, request, pk):
        print_request = get_object_or_404(PrintRequest, pk=pk)

        file_obj = request.FILES.get("image")
        if file_obj:
            unique_name = os.urandom(24).hex() + "_" + file_obj.name.replace(" ", "_")
            image_url = save_file(unique_name, file_obj.read(), file_obj.content_type)
            note = request.data.get("note", "")
        else:
            serializer = AdminProofCreateSerializer(data=request.data)
            if not serializer.is_valid():
                return renderResponse(data=serializer.errors, message="Validation error", status=400)
            image_url = serializer.validated_data["image"]
            note = serializer.validated_data.get("note", "")

        proof = attach_proof(print_request, staff_user=request.user, image=image_url, note=note)
        print_request.refresh_from_db()
        return renderResponse(
            data=AdminPrintRequestDetailSerializer(print_request).data, message=f"Proof v{proof.version} attached", status=201,
        )


class AdminPrintPriceView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsPrintStaff]

    def post(self, request, pk):
        print_request = get_object_or_404(PrintRequest, pk=pk)
        serializer = AdminPriceSerializer(data=request.data)
        if not serializer.is_valid():
            return renderResponse(data=serializer.errors, message="Validation error", status=400)
        v = serializer.validated_data

        from rest_framework.exceptions import ValidationError
        try:
            set_price(print_request, unit_price=v["unit_price"], total_price=v.get("total_price"))
        except ValidationError as exc:
            return renderResponse(data=str(exc.detail[0]) if isinstance(exc.detail, list) else str(exc.detail),
                                   message="Validation error", status=400)

        return renderResponse(data=AdminPrintRequestDetailSerializer(print_request).data, message="Price updated")


class AdminPrintStatusView(APIView):
    """Advance (or cancel) a request. Legality is enforced in exactly one
    place -- PrintRequest.transition_to -- so an illegal jump (e.g. straight
    from SUBMITTED to COMPLETED) 400s here regardless of what this view
    allows through."""

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsPrintStaff]

    def post(self, request, pk):
        print_request = get_object_or_404(PrintRequest, pk=pk)
        serializer = AdminStatusSerializer(data=request.data)
        if not serializer.is_valid():
            return renderResponse(data=serializer.errors, message="Validation error", status=400)

        from rest_framework.exceptions import ValidationError
        try:
            print_request.transition_to(serializer.validated_data["status"])
        except ValidationError as exc:
            return renderResponse(data=str(exc.detail[0]) if isinstance(exc.detail, list) else str(exc.detail),
                                   message="Validation error", status=400)

        return renderResponse(data=AdminPrintRequestDetailSerializer(print_request).data, message="Status updated")


class AdminPrintExportView(APIView):
    """Print-ready artwork + placement/spec data for production -- the
    full-resolution image URL(s) and everything the printer needs, no PDF
    generation (per SP6 spec)."""

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsPrintStaff]

    def get(self, request, pk):
        print_request = get_object_or_404(
            PrintRequest.objects.prefetch_related("proofs", "print_areas", "roster_lines"), pk=pk,
        )
        latest_proof = print_request.proofs.order_by("-version").first()
        approved_proof = print_request.proofs.filter(decision=PrintProof.Decision.APPROVED).order_by("-version").first()

        data = {
            "print_request_id": print_request.id,
            "status": print_request.status,
            "garment": {
                "product_id": print_request.product_id,
                "product_name": print_request.product.name if print_request.product else None,
                "preset_id": print_request.preset_id,
                "preset_name": print_request.preset.name if print_request.preset else None,
                "color": print_request.color,
                "size": print_request.size,
                "quantity": print_request.quantity,
            },
            "print_areas": [{"id": a.id, "name": a.name, "price": str(a.price)} for a in print_request.print_areas.all()],
            "artwork": {
                "approved_image_url": approved_proof.image if approved_proof else None,
                "approved_version": approved_proof.version if approved_proof else None,
                "latest_image_url": latest_proof.image if latest_proof else None,
                "latest_version": latest_proof.version if latest_proof else None,
            },
            "reference_images": print_request.reference_images,
            "roster_lines": [
                {"player_name": l.player_name, "number": l.number, "size": l.size, "quantity": l.quantity}
                for l in print_request.roster_lines.all()
            ],
            "agreed_unit_price": str(print_request.agreed_unit_price) if print_request.agreed_unit_price is not None else None,
            "agreed_total_price": str(print_request.agreed_total_price) if print_request.agreed_total_price is not None else None,
            "brief": print_request.brief,
        }
        return renderResponse(data=data, message="Export data retrieved")


class AdminPrintAreaViewSet(EnvelopeModelViewSetMixin, ModelViewSet):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsPrintStaff]
    serializer_class = PrintAreaSerializer
    queryset = PrintArea.objects.all()
    pagination_class = None
    entity_name = "Print area"


class AdminPrintablePresetViewSet(EnvelopeModelViewSetMixin, ModelViewSet):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsPrintStaff]
    serializer_class = PrintablePresetWriteSerializer
    queryset = PrintablePreset.objects.all()
    pagination_class = None
    entity_name = "Printable preset"


class AdminPrintPricingConfigView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsPrintStaff]

    def get(self, request):
        config = PrintPricingConfig.get_solo()
        return renderResponse(data=PrintPricingConfigSerializer(config).data, message="Pricing config retrieved")

    def put(self, request):
        config = PrintPricingConfig.get_solo()
        serializer = PrintPricingConfigSerializer(config, data=request.data, partial=True)
        if not serializer.is_valid():
            return renderResponse(data=serializer.errors, message="Validation error", status=400)
        serializer.save()
        return renderResponse(data=serializer.data, message="Pricing config updated")
