"""Web-to-press storefront + admin endpoints.

Customer surface filters every order by ``customer=request.user`` (same
cross-tenant rule as printing/views.py). Staff surface is gated by
IsPrintStaff. Payment callbacks never raise raw tracebacks — failures return
the {data, message} envelope with actionable text (spec: graceful payment
error handling).
"""
import os

from django.shortcuts import get_object_or_404
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet
from rest_framework_simplejwt.authentication import JWTAuthentication

from core.helpers import renderResponse
from core.storage import save_file
from food.views_vendor import EnvelopeModelViewSetMixin
from printing.models import (
    CorporateAccount, FinishingOption, PaperStock, PressOrder, PressProduct,
    PressShippingRate, PressShopConfig, PressSizePreset, Quotation,
)
from printing.permissions import IsPrintStaff
from printing.serializers_press import (
    AdminPaymentSerializer, AdminPressOrderDetailSerializer,
    AdminPressOrderListSerializer, CorporateAccountSerializer,
    FinishingOptionSerializer, PaperStockSerializer, PressCheckoutSerializer,
    PressOrderDetailSerializer, PressOrderListSerializer,
    PressProductSerializer, PressProductWriteSerializer,
    PressQuoteRequestSerializer, PressShippingRateSerializer,
    PressShopConfigSerializer, PressSizePresetSerializer,
    QuotationCreateSerializer, QuotationSerializer,
    AdminPressStatusSerializer,
)
from printing.services_press import (
    compute_press_quote, convert_currency, create_press_order, create_quotation,
    handle_payment_callback, init_payment, shipping_quote,
)

MAX_ARTWORK_FILES = 10


def _resolve_quote_inputs(v):
    product = get_object_or_404(PressProduct, pk=v["product"], is_active=True)
    paper = None
    if v.get("paper_stock"):
        paper = get_object_or_404(PaperStock, pk=v["paper_stock"], is_active=True)
    finishings = list(FinishingOption.objects.filter(pk__in=v.get("finishing_ids") or [], is_active=True))
    return product, paper, finishings


def _quote_payload(product, paper, finishings, v):
    quote = compute_press_quote(
        product=product, width=v["width"], height=v["height"], unit=v.get("unit", "in"),
        paper_stock=paper, finishing_options=finishings,
        quantity=v.get("quantity", 1), sides=v.get("sides", "4/0"),
    )
    weight_kg = float(product.weight_per_unit_kg or 0) * v.get("quantity", 1)
    ship = shipping_quote(
        weight_kg=weight_kg, zone=v.get("shipping_zone", "INSIDE_DHAKA_HOME"),
        courier=v.get("shipping_courier", "") or "",
    )
    total_bdt = quote["total_bdt"] + ship["fee_bdt"]
    payload = {k: str(val) for k, val in quote.items()}
    payload.update({
        "shipping_fee_bdt": str(ship["fee_bdt"]),
        "shipping_courier": ship["courier"],
        "weight_kg": str(weight_kg),
        "grand_total_bdt": str(total_bdt),
        "grand_total_charged": str(convert_currency(total_bdt, v.get("currency", "BDT"))),
    })
    return payload


# ── Public catalogue + live calculator ─────────────────────────────────────

class PressProductListView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        products = PressProduct.objects.filter(is_active=True).prefetch_related("size_presets")
        category = request.query_params.get("category")
        if category:
            products = products.filter(category=category)
        return renderResponse(data=PressProductSerializer(products, many=True).data, message="Press products retrieved")


class PressProductDetailView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request, slug):
        product = get_object_or_404(PressProduct, slug=slug, is_active=True)
        return renderResponse(data=PressProductSerializer(product).data, message="Press product retrieved")


class PressPaperListView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        return renderResponse(
            data=PaperStockSerializer(PaperStock.objects.filter(is_active=True), many=True).data,
            message="Paper stocks retrieved")


class PressFinishingListView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        qs = FinishingOption.objects.filter(is_active=True)
        kind = request.query_params.get("kind")
        if kind:
            qs = qs.filter(kind=kind)
        return renderResponse(data=FinishingOptionSerializer(qs, many=True).data, message="Finishing options retrieved")


class PressQuoteView(APIView):
    """Reactive calculator: instant, non-blocking (pure arithmetic, no I/O
    beyond three indexed lookups) and identical to checkout pricing."""

    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        serializer = PressQuoteRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return renderResponse(data=serializer.errors, message="Validation error", status=400)
        v = serializer.validated_data
        product, paper, finishings = _resolve_quote_inputs(v)
        return renderResponse(data=_quote_payload(product, paper, finishings, v), message="Quote computed")


class PressConfigView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        config = PressShopConfig.get_solo()
        return renderResponse(data=PressShopConfigSerializer(config).data, message="Press config retrieved")


# ── Customer checkout + orders ─────────────────────────────────────────────

class PressCheckoutView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = PressCheckoutSerializer(data=request.data)
        if not serializer.is_valid():
            return renderResponse(data=serializer.errors, message="Validation error", status=400)
        v = serializer.validated_data
        product, paper, finishings = _resolve_quote_inputs(v)

        quotation = None
        if v.get("quotation_id"):
            quotation = Quotation.objects.filter(pk=v["quotation_id"], customer=request.user).first()

        from rest_framework.exceptions import ValidationError
        try:
            order = create_press_order(
                request.user, product=product,
                width=v["width"], height=v["height"], unit=v.get("unit", "in"),
                paper_stock=paper, finishing_ids=[f.id for f in finishings],
                quantity=v.get("quantity", 1), sides=v.get("sides", "4/0"),
                currency=v.get("currency", "BDT"), payment_method=v.get("payment_method", "SSLCOMMERZ"),
                shipping_zone=v.get("shipping_zone", "INSIDE_DHAKA_HOME"),
                shipping_courier=v.get("shipping_courier", "") or "",
                shipping_address=v.get("shipping_address", {}),
                artwork_files=[{"url": f["url"], "name": f.get("name", ""), "size": f.get("size", 0),
                                "content_type": f.get("content_type", "")} for f in v.get("artwork_files", [])],
                artwork_meta=[{"name": f.get("name", ""), "size": f.get("size", 0),
                               "width_px": f.get("width_px"), "height_px": f.get("height_px")}
                              for f in v.get("artwork_files", [])],
                size_name=v.get("size_name", ""), po_number=v.get("po_number", ""),
                is_corporate=v.get("is_corporate", False), quotation=quotation,
            )
        except ValidationError as exc:
            detail = exc.detail[0] if isinstance(exc.detail, list) else str(exc.detail)
            return renderResponse(data=detail, message="Validation error", status=400)

        data = PressOrderDetailSerializer(order).data
        if order.payment_method in ("SSLCOMMERZ", "BKASH", "NAGAD", "ROCKET") and order.payment_status == "PENDING":
            data["payment"] = init_payment(order)
            data["payment_hint"] = (
                "Complete payment with SSLCommerz, bKash, Nagad or Rocket to move "
                "your order into artwork review."
            )
        elif order.payment_method == "COD":
            data["payment_hint"] = "Cash on Delivery selected — pay the courier on arrival."
        return renderResponse(data=data, message="Press order placed", status=201)


class PressOrderListView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = PressOrder.objects.filter(customer=request.user).select_related("product", "paper_stock")
        return renderResponse(data=PressOrderListSerializer(qs, many=True).data, message="Press orders retrieved")


class PressOrderDetailView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        order = get_object_or_404(PressOrder, pk=pk, customer=request.user)
        return renderResponse(data=PressOrderDetailSerializer(order).data, message="Press order retrieved")


class PressArtworkUploadView(APIView):
    """Chunked-upload friendly: each file arrives in its own multipart POST
    (client chunks >8MB), validated for type/size and appended to the order."""

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    parser_classes = (MultiPartParser, FormParser)

    def post(self, request, pk):
        from printing.services_press import validate_artwork

        order = get_object_or_404(PressOrder, pk=pk, customer=request.user)
        if order.status not in (PressOrder.Status.PENDING_PAYMENT, PressOrder.Status.ARTWORK_REVIEW):
            return renderResponse(
                data="Artwork can only be added while the order is awaiting payment or review.",
                message="Validation error", status=400,
            )
        file_obj = request.FILES.get("file") or request.FILES.get("artwork")
        if not file_obj:
            return renderResponse(data="No file provided.", message="Validation error", status=400)
        if len(order.artwork_files) >= MAX_ARTWORK_FILES:
            return renderResponse(
                data=f"A press order may have at most {MAX_ARTWORK_FILES} artwork files.",
                message="Validation error", status=400,
            )
        config = PressShopConfig.get_solo()
        if file_obj.size > int(config.max_upload_mb or 100) * 1024 * 1024:
            return renderResponse(
                data=f"File exceeds the {config.max_upload_mb}MB limit.",
                message="Validation error", status=400,
            )
        unique_name = os.urandom(24).hex() + "_" + file_obj.name.replace(" ", "_")
        url = save_file(unique_name, file_obj.read(), file_obj.content_type)
        entry = {"url": url, "name": file_obj.name, "size": file_obj.size,
                 "content_type": file_obj.content_type}
        order.artwork_files = [*order.artwork_files, entry]
        order.artwork_validation = validate_artwork(
            [{"name": file_obj.name, "size": file_obj.size}], width=order.width,
            height=order.height, unit=order.size_unit, product=order.product,
        )
        order.save(update_fields=["artwork_files", "artwork_validation", "updated_at"])
        return renderResponse(
            data={"artwork_files": order.artwork_files, "artwork_validation": order.artwork_validation},
            message="Artwork uploaded", status=201)


class PressPaymentInitView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        order = get_object_or_404(PressOrder, pk=pk, customer=request.user)
        if order.payment_status == "PAID":
            return renderResponse(data="Order is already paid.", message="Validation error", status=400)
        if order.payment_method == "COD":
            return renderResponse(data="COD orders need no online payment.", message="Validation error", status=400)
        return renderResponse(data=init_payment(order), message="Payment initialised")


class PressPaymentCallbackView(APIView):
    """Simulated gateway return (success=true/false + txn id). Real provider
    webhooks land here with the same contract."""

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        order = get_object_or_404(PressOrder, pk=pk, customer=request.user)
        success = str(request.data.get("success", "")).lower() in ("1", "true", "yes", "paid", "success")
        txn_id = str(request.data.get("txn_id", "") or "")
        from rest_framework.exceptions import ValidationError
        try:
            handle_payment_callback(order, success=success, txn_id=txn_id)
        except ValidationError as exc:
            detail = exc.detail[0] if isinstance(exc.detail, list) else str(exc.detail)
            return renderResponse(data=detail, message="Payment failed", status=400)
        order.refresh_from_db()
        return renderResponse(data=PressOrderDetailSerializer(order).data, message="Payment recorded")


class PressQuotationListCreateView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = Quotation.objects.filter(customer=request.user).select_related("product")
        return renderResponse(data=QuotationSerializer(qs, many=True).data, message="Quotations retrieved")

    def post(self, request):
        serializer = QuotationCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return renderResponse(data=serializer.errors, message="Validation error", status=400)
        v = serializer.validated_data
        product, paper, finishings = _resolve_quote_inputs(v)
        quotation = create_quotation(
            request.user, product=product, width=v["width"], height=v["height"],
            unit=v.get("unit", "in"), paper_stock=paper,
            finishing_ids=[f.id for f in finishings], quantity=v.get("quantity", 1),
            sides=v.get("sides", "4/0"), currency=v.get("currency", "BDT"),
            po_number=v.get("po_number", ""),
        )
        return renderResponse(data=QuotationSerializer(quotation).data, message="Quotation created", status=201)


# ── Staff ──────────────────────────────────────────────────────────────────

class AdminPressOrderQueueView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsPrintStaff]

    def get(self, request):
        qs = PressOrder.objects.select_related("customer", "product", "paper_stock")
        status = request.query_params.get("status")
        if status in PressOrder.Status.values:
            qs = qs.filter(status=status)
        return renderResponse(data=AdminPressOrderListSerializer(qs, many=True).data, message="Press queue retrieved")


class AdminPressOrderDetailView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsPrintStaff]

    def get(self, request, pk):
        order = get_object_or_404(PressOrder, pk=pk)
        return renderResponse(data=AdminPressOrderDetailSerializer(order).data, message="Press order retrieved")

    def patch(self, request, pk):
        order = get_object_or_404(PressOrder, pk=pk)
        notes = request.data.get("staff_notes")
        if notes is None:
            return renderResponse(data="staff_notes is required.", message="Validation error", status=400)
        order.staff_notes = notes
        order.save(update_fields=["staff_notes", "updated_at"])
        return renderResponse(data=AdminPressOrderDetailSerializer(order).data, message="Notes updated")


class AdminPressStatusView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsPrintStaff]

    def post(self, request, pk):
        order = get_object_or_404(PressOrder, pk=pk)
        serializer = AdminPressStatusSerializer(data=request.data)
        if not serializer.is_valid():
            return renderResponse(data=serializer.errors, message="Validation error", status=400)
        from rest_framework.exceptions import ValidationError
        try:
            order.transition_to(serializer.validated_data["status"])
        except ValidationError as exc:
            detail = exc.detail[0] if isinstance(exc.detail, list) else str(exc.detail)
            return renderResponse(data=detail, message="Validation error", status=400)
        return renderResponse(data=AdminPressOrderDetailSerializer(order).data, message="Status updated")


class AdminPressPaymentView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsPrintStaff]

    def post(self, request, pk):
        order = get_object_or_404(PressOrder, pk=pk)
        serializer = AdminPaymentSerializer(data=request.data)
        if not serializer.is_valid():
            return renderResponse(data=serializer.errors, message="Validation error", status=400)
        order.payment_status = serializer.validated_data["payment_status"]
        if serializer.validated_data.get("payment_txn_id"):
            order.payment_txn_id = serializer.validated_data["payment_txn_id"]
        order.save(update_fields=["payment_status", "payment_txn_id", "updated_at"])
        if order.payment_status == "PAID" and order.status == PressOrder.Status.PENDING_PAYMENT:
            order.transition_to(PressOrder.Status.ARTWORK_REVIEW)
        return renderResponse(data=AdminPressOrderDetailSerializer(order).data, message="Payment updated")


class AdminPressExportView(APIView):
    """Production handoff grouped by Order ID: hi-res artwork URLs untouched
    (no recompression), trim/bleed geometry, stock, finishing and price."""

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsPrintStaff]

    def get(self, request, pk):
        order = get_object_or_404(
            PressOrder.objects.select_related("product", "paper_stock").prefetch_related("finishing_options"), pk=pk,
        )
        trim_w, trim_h = order.width, order.height
        bleed_mm = "3"
        data = {
            "press_order_id": order.id,
            "status": order.status,
            "product": {"id": order.product_id, "name": order.product.name, "category": order.product.category},
            "spec": {
                "size_name": order.size_name, "width": str(trim_w), "height": str(trim_h),
                "unit": order.size_unit, "sides": order.sides, "quantity": order.quantity,
                "bleed": f"+{bleed_mm}mm all sides",
                "paper_stock": order.paper_stock.name if order.paper_stock else None,
                "finishing": [{"name": f.name, "kind": f.kind} for f in order.finishing_options.all()],
            },
            "artwork_files": order.artwork_files,
            "artwork_validation": order.artwork_validation,
            "price_breakdown": order.price_breakdown,
            "total_bdt": str(order.total_bdt),
            "payment": {"method": order.payment_method, "status": order.payment_status, "txn_id": order.payment_txn_id},
            "shipping": {"zone": order.shipping_zone, "courier": order.shipping_courier,
                         "fee_bdt": str(order.shipping_fee_bdt), "address": order.shipping_address},
            "corporate": {"is_corporate": order.is_corporate, "po_number": order.po_number},
        }
        return renderResponse(data=data, message="Export data retrieved")


class AdminPressProductViewSet(EnvelopeModelViewSetMixin, ModelViewSet):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsPrintStaff]
    serializer_class = PressProductWriteSerializer
    queryset = PressProduct.objects.all()
    pagination_class = None
    entity_name = "Press product"


class AdminPressSizeViewSet(EnvelopeModelViewSetMixin, ModelViewSet):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsPrintStaff]
    serializer_class = PressSizePresetSerializer
    queryset = PressSizePreset.objects.all()
    pagination_class = None
    entity_name = "Press size"


class AdminPaperStockViewSet(EnvelopeModelViewSetMixin, ModelViewSet):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsPrintStaff]
    serializer_class = PaperStockSerializer
    queryset = PaperStock.objects.all()
    pagination_class = None
    entity_name = "Paper stock"


class AdminFinishingViewSet(EnvelopeModelViewSetMixin, ModelViewSet):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsPrintStaff]
    serializer_class = FinishingOptionSerializer
    queryset = FinishingOption.objects.all()
    pagination_class = None
    entity_name = "Finishing option"


class AdminPressShippingViewSet(EnvelopeModelViewSetMixin, ModelViewSet):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsPrintStaff]
    serializer_class = PressShippingRateSerializer
    queryset = PressShippingRate.objects.all()
    pagination_class = None
    entity_name = "Shipping rate"


class AdminPressShopConfigView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsPrintStaff]
    parser_classes = (JSONParser, MultiPartParser, FormParser)

    def get(self, request):
        return renderResponse(
            data=PressShopConfigSerializer(PressShopConfig.get_solo()).data, message="Press config retrieved")

    def put(self, request):
        config = PressShopConfig.get_solo()
        serializer = PressShopConfigSerializer(config, data=request.data, partial=True)
        if not serializer.is_valid():
            return renderResponse(data=serializer.errors, message="Validation error", status=400)
        serializer.save()
        return renderResponse(data=serializer.data, message="Press config updated")


class AdminCorporateViewSet(EnvelopeModelViewSetMixin, ModelViewSet):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsPrintStaff]
    serializer_class = CorporateAccountSerializer
    queryset = CorporateAccount.objects.select_related("customer").all()
    pagination_class = None
    entity_name = "Corporate account"


class AdminQuotationQueueView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsPrintStaff]

    def get(self, request):
        qs = Quotation.objects.select_related("customer", "product")
        status = request.query_params.get("status")
        if status in Quotation.Status.values:
            qs = qs.filter(status=status)
        return renderResponse(data=QuotationSerializer(qs, many=True).data, message="Quotations retrieved")

    def patch(self, request, pk=None):
        quotation = get_object_or_404(Quotation, pk=request.data.get("id", pk))
        status = request.data.get("status")
        if status not in Quotation.Status.values:
            return renderResponse(data="Unknown status.", message="Validation error", status=400)
        quotation.status = status
        quotation.save(update_fields=["status", "updated_at"])
        return renderResponse(data=QuotationSerializer(quotation).data, message="Quotation updated")
