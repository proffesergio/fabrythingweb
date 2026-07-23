from django.db.models import (Prefetch, Count, Q, F, Exists, OuterRef, FloatField, Value,
                              BooleanField, ExpressionWrapper)
from django.db.models.functions import ACos, Cos, Sin, Radians, Least, Greatest, Cast
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView
from rest_framework.generics import ListAPIView
from core.helpers import renderResponse, CustomPageNumberPagination, CommonListAPIMixin
from rest_framework.exceptions import ValidationError
from food.models import (Restaurant, FoodCategory, FoodItem, FoodItemOptionGroup,
                         DeliveryZone, FoodOrder, RestaurantZone, Village)
from food.serializers import RestaurantListSerializer, RestaurantDetailSerializer, DeliveryZoneSerializer
from food.pricing import delivery_quote
from food.services import served_zones, DELIVERY_BUFFER_MINUTES

EARTH_RADIUS_KM = 6371.0


def _lang(request):
    return "bn" if request.GET.get("lang") == "bn" else "en"


def _float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _haversine_expr(lat, lng):
    """Great-circle km from (lat, lng) to each restaurant's pickup pin, as a DB
    expression so the result stays a QuerySet (orderable, filterable, paginable).

    Uses the spherical law of cosines — the same distance as food.geo.haversine_km
    to well under a metre at town scale, but expressible with the math functions
    Django ships for both SQLite and Postgres.

    The ACos argument is clamped to [-1, 1]: floating-point drift can push it a
    hair outside that range for a restaurant sitting exactly on the pin, and
    ACos(1.0000000001) is a domain error that surfaces as a 500.
    """
    r_lat = Radians(Cast(F("pickup_lat"), FloatField()))
    r_lng = Radians(Cast(F("pickup_lng"), FloatField()))
    p_lat, p_lng = Radians(Value(lat)), Radians(Value(lng))

    cos_angle = (Cos(p_lat) * Cos(r_lat) * Cos(r_lng - p_lng)) + (Sin(p_lat) * Sin(r_lat))
    clamped = Least(Greatest(cos_angle, Value(-1.0)), Value(1.0))
    return ACos(clamped) * Value(EARTH_RADIUS_KM)


class PublicRestaurantListView(ListAPIView):
    permission_classes = [AllowAny]
    serializer_class = RestaurantListSerializer
    pagination_class = CustomPageNumberPagination

    def get_queryset(self):
        p = self.request.GET
        # `hours` feeds is_open_now for every row — without the prefetch that is
        # one query per restaurant.
        qs = (Restaurant.objects.filter(status=Restaurant.Status.ACTIVE)
              .prefetch_related("hours"))

        zone = p.get("zone")
        # `all=true` (the Browse page) keeps every restaurant in the list and only
        # uses `zone` to mark which ones deliver to you, rather than filtering.
        browse_all = p.get("all") == "true"
        # A restaurant with no RestaurantZone rows is unconfigured, not restricted,
        # and delivers everywhere — see food.services.served_zones. It must stay in
        # the zone-filtered list, or checkout would accept an order for a
        # restaurant the customer was never shown.
        unzoned = ~Exists(RestaurantZone.objects.filter(restaurant=OuterRef("pk")))
        if zone and not browse_all:
            qs = qs.filter(Q(zones__id=zone) | unzoned).distinct()

        if p.get("search"):
            qs = qs.filter(name__icontains=p["search"])
        if p.get("cuisine"):
            qs = qs.filter(cuisine_type__icontains=p["cuisine"])

        # Skip restaurants already shown in another row (the "you may also like"
        # row must not repeat the "nearest" row).
        exclude = [i for i in (p.get("exclude") or "").split(",") if i.strip().isdigit()]
        if exclude:
            qs = qs.exclude(id__in=exclude)

        sort = p.get("sort")
        if sort == "popular":
            # Delivered orders only — cancelled ones are not a popularity signal.
            qs = qs.annotate(order_count=Count(
                "orders", filter=Q(orders__status=FoodOrder.Status.DELIVERED))
            ).order_by("-order_count", "name")
        else:
            qs = qs.order_by("name")

        if zone:
            in_zone = Exists(RestaurantZone.objects.filter(restaurant=OuterRef("pk"), zone_id=zone))
            qs = qs.annotate(delivers_to_zone=ExpressionWrapper(
                in_zone | unzoned, output_field=BooleanField()))

        # Distance is annotated in SQL rather than sorted in Python: this must stay
        # a real QuerySet, because CommonListAPIMixin.common_list_decorator calls
        # .filter()/.order_by() on whatever get_queryset returns.
        lat, lng = _float(p.get("lat")), _float(p.get("lng"))
        if lat is not None and lng is not None:
            qs = qs.annotate(distance_km=_haversine_expr(lat, lng))
            if sort == "distance":
                # Restaurants with no pickup pin have a NULL distance; they sort
                # last rather than jumping to the front on a NULLS-FIRST backend.
                qs = qs.order_by(F("distance_km").asc(nulls_last=True), "name")

        return qs

    def get_serializer_context(self):
        return {"lang": _lang(self.request)}

    # Wrap the paginated list in the project's standard renderResponse envelope
    # ({"data": {"data": [...], "totalPages": ..., ...}, "message": ...}) —
    # the same convention every other public list endpoint in this codebase uses
    # (see storefront.views.CustomerOrderListView / AdminOrderListView).
    @CommonListAPIMixin.common_list_decorator(RestaurantListSerializer)
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)


def _detail_prefetch():
    opt_groups = Prefetch(
        "option_groups",
        queryset=FoodItemOptionGroup.objects.prefetch_related("options"),
    )
    items = Prefetch("items", queryset=FoodItem.objects.prefetch_related(opt_groups))
    cats = Prefetch("categories", queryset=FoodCategory.objects.prefetch_related(items))
    # `zones` feeds served_zone_ids; prefetching keeps the detail endpoint's query
    # count flat instead of adding one per request.
    zones = Prefetch("zones", queryset=DeliveryZone.objects.filter(is_active=True))
    # `hours` feeds is_open_now (see RestaurantListSerializer).
    return cats, zones, "hours"


class PublicRestaurantDetailView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, slug):
        restaurant = (
            Restaurant.objects.filter(status=Restaurant.Status.ACTIVE, slug=slug)
            .prefetch_related(*_detail_prefetch())
            .first()
        )
        if not restaurant:
            return renderResponse(data={}, message="Restaurant not found", status=404)
        data = RestaurantDetailSerializer(restaurant, context={"lang": _lang(request)}).data
        return renderResponse(data=data, message="Restaurant detail")


class PublicZoneListView(ListAPIView):
    permission_classes = [AllowAny]
    serializer_class = DeliveryZoneSerializer
    pagination_class = None

    def get_queryset(self):
        return DeliveryZone.objects.filter(is_active=True).prefetch_related("villages").order_by("name")

    def list(self, request, *args, **kwargs):
        # Wrap in the project's standard {"data": [...]} envelope so the frontend's
        # res.data.data access works (every other food endpoint uses renderResponse).
        serializer = self.get_serializer(self.get_queryset(), many=True)
        return renderResponse(data=serializer.data, message="Zones")


class DeliveryQuoteView(APIView):
    """What this delivery will cost, before the customer commits to it.

    Checkout calls this whenever the destination changes. It is the *same*
    function the order endpoint prices with (food.pricing.delivery_quote), so
    the number shown can never disagree with the number charged — the class of
    bug that made a zone dropdown offer areas the order endpoint then rejected.

    Out-of-range is a 200 with `deliverable: false` and a reason, not a 400: the
    customer is asking a question, not placing an order, and the UI needs to
    explain the refusal rather than swallow it.
    """
    permission_classes = [AllowAny]

    def get(self, request):
        p = request.GET
        restaurant = Restaurant.objects.filter(slug=p.get("restaurant"),
                                               status=Restaurant.Status.ACTIVE).first()
        if not restaurant:
            return renderResponse(data={}, message="Restaurant not available", status=404)

        zone, village = None, None
        if p.get("village"):
            village = Village.objects.filter(id=p["village"], is_active=True).select_related("zone").first()
            zone = village.zone if village else None
        if p.get("zone"):
            zone = DeliveryZone.objects.filter(id=p["zone"], is_active=True).first() or zone
        if zone and not served_zones(restaurant).filter(id=zone.id).exists():
            return renderResponse(
                data={"deliverable": False,
                      "reason": "This restaurant does not deliver to the selected area."},
                message="Delivery quote")

        lat, lng = _float(p.get("lat")), _float(p.get("lng"))
        try:
            quote = delivery_quote(restaurant, zone=zone, village=village, lat=lat, lng=lng)
        except ValidationError as exc:
            return renderResponse(
                data={"deliverable": False, "reason": exc.detail[0] if isinstance(exc.detail, list)
                      else str(exc.detail)},
                message="Delivery quote")

        return renderResponse(data={
            "deliverable": True,
            "fee": str(quote["fee"]),
            "distance_km": str(quote["distance_km"]) if quote["distance_km"] is not None else None,
            # How we located the customer: a "zone"-sourced distance can be a
            # couple of km out, and the UI nudges for a pin when it sees that.
            "distance_source": quote["distance_source"],
            "priced_by": quote["priced_by"],
            "eta_minutes": restaurant.avg_prep_minutes + DELIVERY_BUFFER_MINUTES,
        }, message="Delivery quote")
