"""Become a Partner — public application, and the admin's approve/reject."""
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.tokens import RefreshToken

from core.helpers import renderResponse
from food.models import Restaurant
from food.permissions import IsPlatformAdmin
from food.serializers import RestaurantListSerializer
from food.services_partner import apply_as_partner, approve_partner, reject_partner


class PartnerApplyView(APIView):
    """POST api/food/partner/apply/ — a restaurant owner applies to join.

    Public by design: the whole point is to stop being the data-entry bottleneck
    on every new partner. The approval gate is `Restaurant.Status.PENDING`, not
    authentication.

    Returns tokens on success so the owner lands straight in their vendor panel
    and can start building a menu while they wait — the application is worth
    something to them immediately, instead of being a form that vanishes.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        try:
            restaurant = apply_as_partner(request.data)
        except ValidationError as exc:
            # Hand the field-keyed dict to renderResponse so it emits
            # `field_errors` and the form can show each message under the input
            # it belongs to. DRF's default handler would flatten it to a toast.
            detail = exc.detail
            if isinstance(detail, dict):
                return renderResponse(data={k: [str(m) for m in v] for k, v in detail.items()},
                                      message="Please check the form", status=400)
            msgs = detail if isinstance(detail, list) else [detail]
            return renderResponse(data=[str(m) for m in msgs],
                                  message="Please check the form", status=400)
        refresh = RefreshToken.for_user(restaurant.owner)
        return renderResponse(
            data={
                "restaurant": {"id": restaurant.id, "name": restaurant.name,
                               "slug": restaurant.slug, "status": restaurant.status},
                "access": str(refresh.access_token),
                "refresh": str(refresh),
                "username": restaurant.owner.username,
            },
            message="Application received", status=201)


class AdminPartnerApplicationsView(APIView):
    """GET api/food/admin/partner/applications/ — the approval queue."""
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsPlatformAdmin]

    def get(self, request):
        pending = (Restaurant.objects.filter(status=Restaurant.Status.PENDING)
                   .select_related("owner").prefetch_related("hours", "zones")
                   .order_by("-created_at"))
        rows = RestaurantListSerializer(pending, many=True, context={"lang": "en"}).data
        for row, r in zip(rows, pending):
            # The reviewer needs to know who they are approving, and how to call
            # them — none of which the customer-facing serializer carries.
            row["owner_name"] = r.owner.first_name if r.owner else ""
            row["owner_email"] = r.owner.email if r.owner else ""
            row["owner_username"] = r.owner.username if r.owner else ""
            row["phone"] = r.phone
            row["address"] = r.address
            row["applied_at"] = r.created_at
        return renderResponse(data=rows, message="Partner applications")


class AdminPartnerDecisionView(APIView):
    """POST api/food/admin/partner/<pk>/decision/ — approve or reject.

    Approval is where the commission terms are set, so the rate and floor are
    accepted here rather than left at defaults nobody agreed to.
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsPlatformAdmin]

    def post(self, request, pk):
        restaurant = Restaurant.objects.filter(pk=pk).first()
        if not restaurant:
            return renderResponse(data={}, message="Restaurant not found", status=404)

        decision = (request.data.get("decision") or "").lower()
        if decision == "approve":
            approve_partner(
                restaurant,
                commission_percentage=request.data.get("commission_percentage"),
                min_commission_amount=request.data.get("min_commission_amount"))
            return renderResponse(data={"status": restaurant.status}, message="Partner approved")
        if decision == "reject":
            reject_partner(restaurant, request.data.get("reason", ""))
            return renderResponse(data={"status": restaurant.status}, message="Application rejected")
        return renderResponse(data={}, message="decision must be 'approve' or 'reject'", status=400)
