"""Customer-facing custom-print endpoints.

Every request-scoped view here filters by ``customer=request.user`` -- a
customer may only ever read or act on their OWN print requests. Getting this
wrong is exactly the kind of cross-tenant bug this project has shipped
before (see chat/views.py's docstring and accounts/test_dynamic_form_scope.py);
printing/tests/test_customer_api.py pins it explicitly for both read and write.
"""
import os

from django.shortcuts import get_object_or_404
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication

from core.helpers import renderResponse
from core.storage import save_file
from printing.permissions import IsPrintStaff
from printing.models import (
    PrintArea, PrintablePreset, PrintProof, PrintRequest,
    PrintRosterLine, PrintShowcaseItem,
)
from printing.serializers import (
    PrintShowcaseItemSerializer,
    PrintablePresetSerializer, PrintAreaSerializer, PrintRequestCreateSerializer,
    PrintRequestDetailSerializer, PrintRequestListSerializer, PrintRosterLineSerializer,
    ProofDecisionSerializer, QuoteRequestSerializer,
)
from printing.services import approve_proof, compute_quote, create_print_request, request_revision

MAX_REFERENCE_IMAGES = 10

# Roster lines and reference images may only be added/edited while the
# request is still in the design conversation -- once approved, production
# has priced and locked the job, so mutating "who gets which shirt" after
# the fact would silently disagree with what was quoted.
MUTABLE_ROSTER_STATUSES = {
    PrintRequest.Status.SUBMITTED, PrintRequest.Status.IN_DESIGN,
    PrintRequest.Status.PROOF_READY, PrintRequest.Status.REVISION_REQUESTED,
}


class PrintablePresetListView(APIView):
    """Public: the garment options the storefront's "Custom Printing" form
    offers. No auth required, same as the rest of the public catalog."""

    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        presets = PrintablePreset.objects.filter(is_active=True).select_related("product")
        return renderResponse(data=PrintablePresetSerializer(presets, many=True).data, message="Presets retrieved")


class PrintAreaListView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        areas = PrintArea.objects.filter(is_active=True)
        return renderResponse(data=PrintAreaSerializer(areas, many=True).data, message="Print areas retrieved")


class PrintQuoteView(APIView):
    """Live price preview before submitting a request -- runs the exact same
    printing.services.compute_quote used at approval time, so the estimate
    shown on the form can never disagree with what staff ends up quoting."""

    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        serializer = QuoteRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return renderResponse(data=serializer.errors, message="Validation error", status=400)
        v = serializer.validated_data

        preset = None
        if v.get("preset"):
            preset = get_object_or_404(PrintablePreset, pk=v["preset"], is_active=True)
        areas = list(PrintArea.objects.filter(pk__in=v.get("print_areas") or [], is_active=True))

        quote = compute_quote(preset=preset, print_areas=areas, quantity=v["quantity"])
        return renderResponse(data={k: str(val) for k, val in quote.items()}, message="Quote computed")


class PrintRequestListCreateView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        requests_qs = PrintRequest.objects.filter(customer=request.user).prefetch_related("print_areas")
        return renderResponse(
            data=PrintRequestListSerializer(requests_qs, many=True).data, message="Print requests retrieved",
        )

    def post(self, request):
        serializer = PrintRequestCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return renderResponse(data=serializer.errors, message="Validation error", status=400)
        v = serializer.validated_data

        from catalog.models import Products

        product = Products.objects.filter(pk=v["product"]).first() if v.get("product") else None
        preset = PrintablePreset.objects.filter(pk=v["preset"], is_active=True).first() if v.get("preset") else None

        print_request = create_print_request(
            request.user,
            product=product,
            preset=preset,
            color=v.get("color", ""),
            size=v.get("size", ""),
            quantity=v["quantity"],
            brief=v["brief"],
            reference_images=v.get("reference_images", []),
            print_area_ids=v.get("print_areas", []),
            roster_lines=v.get("roster_lines", []),
        )
        data = PrintRequestDetailSerializer(print_request).data
        return renderResponse(data=data, message="Print request submitted", status=201)


class PrintRequestDetailView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        print_request = get_object_or_404(PrintRequest, pk=pk, customer=request.user)
        return renderResponse(data=PrintRequestDetailSerializer(print_request).data, message="Print request retrieved")


class PrintReferenceImageUploadView(APIView):
    """Direct multipart upload tied to a specific request -- reuses
    core.storage.save_file (content-addressed, survives Render's ephemeral
    disk) rather than adding a new upload mechanism."""

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    parser_classes = (MultiPartParser, FormParser)

    def post(self, request, pk):
        print_request = get_object_or_404(PrintRequest, pk=pk, customer=request.user)

        file_obj = request.FILES.get("image")
        if not file_obj:
            return renderResponse(data="No image file provided.", message="Validation error", status=400)
        if len(print_request.reference_images) >= MAX_REFERENCE_IMAGES:
            return renderResponse(
                data=f"A print request may have at most {MAX_REFERENCE_IMAGES} reference images.",
                message="Validation error", status=400,
            )

        unique_name = os.urandom(24).hex() + "_" + file_obj.name.replace(" ", "_")
        url = save_file(unique_name, file_obj.read(), file_obj.content_type)

        print_request.reference_images = [*print_request.reference_images, url]
        print_request.save(update_fields=["reference_images", "updated_at"])
        return renderResponse(data={"reference_images": print_request.reference_images}, message="Image uploaded", status=201)


class PrintRosterLineListCreateView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def _get_owned_request(self, request, pk):
        return get_object_or_404(PrintRequest, pk=pk, customer=request.user)

    def get(self, request, pk):
        print_request = self._get_owned_request(request, pk)
        lines = print_request.roster_lines.all()
        return renderResponse(data=PrintRosterLineSerializer(lines, many=True).data, message="Roster retrieved")

    def post(self, request, pk):
        print_request = self._get_owned_request(request, pk)
        if print_request.status not in MUTABLE_ROSTER_STATUSES:
            return renderResponse(
                data="Roster can no longer be changed once the request is approved.",
                message="Validation error", status=400,
            )
        serializer = PrintRosterLineSerializer(data=request.data)
        if not serializer.is_valid():
            return renderResponse(data=serializer.errors, message="Validation error", status=400)
        line = PrintRosterLine.objects.create(print_request=print_request, **serializer.validated_data)
        return renderResponse(data=PrintRosterLineSerializer(line).data, message="Roster line added", status=201)


class PrintRosterLineDetailView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def _get_owned_line(self, request, pk, line_pk):
        print_request = get_object_or_404(PrintRequest, pk=pk, customer=request.user)
        line = get_object_or_404(PrintRosterLine, pk=line_pk, print_request=print_request)
        return print_request, line

    def patch(self, request, pk, line_pk):
        print_request, line = self._get_owned_line(request, pk, line_pk)
        if print_request.status not in MUTABLE_ROSTER_STATUSES:
            return renderResponse(
                data="Roster can no longer be changed once the request is approved.",
                message="Validation error", status=400,
            )
        serializer = PrintRosterLineSerializer(line, data=request.data, partial=True)
        if not serializer.is_valid():
            return renderResponse(data=serializer.errors, message="Validation error", status=400)
        serializer.save()
        return renderResponse(data=serializer.data, message="Roster line updated")

    def delete(self, request, pk, line_pk):
        print_request, line = self._get_owned_line(request, pk, line_pk)
        if print_request.status not in MUTABLE_ROSTER_STATUSES:
            return renderResponse(
                data="Roster can no longer be changed once the request is approved.",
                message="Validation error", status=400,
            )
        line.delete()
        return renderResponse(data=None, message="Roster line removed")


class PrintProofDecisionView(APIView):
    """Customer decides on the LATEST proof only -- approve locks in the
    price (PrintRequest.transition_to snapshots it), revision loops the
    request back to IN_DESIGN for another round."""

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request, pk, proof_pk):
        print_request = get_object_or_404(PrintRequest, pk=pk, customer=request.user)
        proof = get_object_or_404(PrintProof, pk=proof_pk, print_request=print_request)

        serializer = ProofDecisionSerializer(data=request.data)
        if not serializer.is_valid():
            return renderResponse(data=serializer.errors, message="Validation error", status=400)
        v = serializer.validated_data

        if v["decision"] == PrintProof.Decision.APPROVED:
            approve_proof(print_request, proof)
        else:
            request_revision(print_request, proof, feedback=v["feedback"])

        print_request.refresh_from_db()
        return renderResponse(data=PrintRequestDetailSerializer(print_request).data, message="Decision recorded")


class PrintShowcaseListView(APIView):
    """GET /api/print/showcase/ -- public. What we can print, for the Custom
    Printing page. Active items only, in display order."""
    authentication_classes = []
    permission_classes = []

    def get(self, request):
        items = PrintShowcaseItem.objects.filter(is_active=True)
        return renderResponse(
            data=PrintShowcaseItemSerializer(items, many=True).data,
            message="Showcase retrieved")


class AdminPrintShowcaseListCreateView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsPrintStaff]

    def get(self, request):
        items = PrintShowcaseItem.objects.all()
        return renderResponse(
            data=PrintShowcaseItemSerializer(items, many=True).data,
            message="Showcase items retrieved")

    def post(self, request):
        serializer = PrintShowcaseItemSerializer(data=request.data)
        if not serializer.is_valid():
            return renderResponse(data=serializer.errors, message="Validation error", status=400)
        serializer.save()
        return renderResponse(data=serializer.data, message="Showcase item created", status=201)


class AdminPrintShowcaseDetailView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsPrintStaff]

    def _get(self, pk):
        return PrintShowcaseItem.objects.filter(pk=pk).first()

    def patch(self, request, pk):
        item = self._get(pk)
        if not item:
            return renderResponse(data=None, message="Not found", status=404)
        serializer = PrintShowcaseItemSerializer(item, data=request.data, partial=True)
        if not serializer.is_valid():
            return renderResponse(data=serializer.errors, message="Validation error", status=400)
        serializer.save()
        return renderResponse(data=serializer.data, message="Showcase item updated")

    def delete(self, request, pk):
        item = self._get(pk)
        if not item:
            return renderResponse(data=None, message="Not found", status=404)
        item.delete()
        return renderResponse(data=None, message="Showcase item deleted")
