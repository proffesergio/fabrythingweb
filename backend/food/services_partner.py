"""Restaurant self-signup — "Become a Partner".

Distinct from `services_admin.create_restaurant_with_owner`, which is an admin
creating a live restaurant. Here the *owner* applies, the restaurant is born
PENDING, and it is invisible to customers until an admin approves it
(`PublicRestaurantListView` already filters to ACTIVE, so that is free).

The whole thing is one `transaction.atomic` block, and that is not decoration.
Both rider and restaurant onboarding have been bitten by the same trap: a User
created before the thing it belongs to, a later failure, and the orphan User
committed anyway — owning the username forever, with no row in the admin panel
to delete, so every retry fails with "already exists". See
`accounts/management/commands/release_login.py` for the cleanup that exists
because of it.
"""
from django.contrib.auth import get_user_model
from django.db import transaction
from rest_framework.exceptions import ValidationError

from food.models import Restaurant, RestaurantZone, DeliveryZone
from food.services_admin import _unique_restaurant_slug

User = get_user_model()


def _norm(value):
    return (value or "").strip()


def existing_application(email, phone):
    """A pending application already owned by this person, if any.

    Re-applying must *update* the first application rather than mint a second
    login: the second attempt would fail on the unique username anyway, and the
    applicant would be stuck with no way to correct a typo.
    """
    email, phone = _norm(email).lower(), _norm(phone)
    qs = Restaurant.objects.filter(status=Restaurant.Status.PENDING, owner__isnull=False)
    if email:
        found = qs.filter(owner__email__iexact=email).first()
        if found:
            return found
    if phone:
        return qs.filter(phone=phone).first()
    return None


def _validate(data):
    required = {"name": "Restaurant name", "owner_name": "Your name",
                "phone": "Phone number", "email": "Email", "password": "Password"}
    for field, label in required.items():
        if not _norm(data.get(field)):
            raise ValidationError({field: [f"{label} is required."]})
    if len(_norm(data.get("password"))) < 6:
        raise ValidationError({"password": ["Password must be at least 6 characters."]})


@transaction.atomic
def apply_as_partner(data):
    """Create a PENDING restaurant plus its owner login. Returns the Restaurant.

    Raises ValidationError with field-keyed messages, so the form can attribute
    each one to an input (the envelope exposes them as `field_errors`).
    """
    _validate(data)
    email = _norm(data["email"]).lower()
    phone = _norm(data["phone"])

    # An applicant correcting their details resubmits rather than duplicates.
    already = existing_application(email, phone)
    if already:
        return update_application(already, data)

    if User.objects.filter(email__iexact=email).exists():
        raise ValidationError({"email": [
            "An account already uses this email. Sign in instead, or use another address."]})

    username = email.split("@")[0][:30] or phone
    base, i = username, 2
    while User.objects.filter(username=username).exists():
        username = f"{base}{i}"[:30]
        i += 1

    owner = User.objects.create_user(
        username=username, email=email, password=data["password"],
        first_name=_norm(data.get("owner_name")), phone=phone,
        role="Restaurant", country="Bangladesh",
    )

    name = _norm(data["name"])
    restaurant = Restaurant.objects.create(
        name=name, slug=_unique_restaurant_slug(name), owner=owner,
        name_bn=_norm(data.get("name_bn")), address=_norm(data.get("address")),
        cuisine_type=_norm(data.get("cuisine_type")), phone=phone,
        description=_norm(data.get("description")),
        pickup_lat=data.get("pickup_lat") or None,
        pickup_lng=data.get("pickup_lng") or None,
        # PENDING is the approval gate: customers cannot see this restaurant and
        # cannot order from it until an admin flips it to ACTIVE.
        status=Restaurant.Status.PENDING,
    )
    _assign_zones(restaurant, data.get("zone_ids"))
    return restaurant


def update_application(restaurant, data):
    """Let an applicant correct a still-pending application."""
    if restaurant.status != Restaurant.Status.PENDING:
        raise ValidationError("This restaurant has already been reviewed.")
    for field, key in [("name", "name"), ("name_bn", "name_bn"), ("address", "address"),
                       ("cuisine_type", "cuisine_type"), ("description", "description")]:
        if data.get(key) is not None:
            setattr(restaurant, field, _norm(data.get(key)))
    if data.get("phone"):
        restaurant.phone = _norm(data["phone"])
    if data.get("pickup_lat") and data.get("pickup_lng"):
        restaurant.pickup_lat = data["pickup_lat"]
        restaurant.pickup_lng = data["pickup_lng"]
    restaurant.save()
    _assign_zones(restaurant, data.get("zone_ids"))
    return restaurant


def _assign_zones(restaurant, zone_ids):
    for zid in zone_ids or []:
        zone = DeliveryZone.objects.filter(id=zid, is_active=True).first()
        if zone:
            RestaurantZone.objects.get_or_create(restaurant=restaurant, zone=zone)


@transaction.atomic
def approve_partner(restaurant, *, commission_percentage=None, min_commission_amount=None):
    """Admin approval: the moment the commission terms are agreed and the
    restaurant becomes visible to customers."""
    if commission_percentage is not None:
        restaurant.commission_percentage = commission_percentage
    if min_commission_amount is not None:
        restaurant.min_commission_amount = min_commission_amount
    restaurant.status = Restaurant.Status.ACTIVE
    restaurant.save(update_fields=["status", "commission_percentage",
                                   "min_commission_amount", "updated_at"])
    return restaurant


@transaction.atomic
def reject_partner(restaurant, reason=""):
    """Decline an application. The login is kept (so the owner can be told, and
    can re-apply) but the restaurant is marked REJECTED, not deleted — deleting
    it would strand the User exactly as the orphan-login trap does."""
    restaurant.status = Restaurant.Status.REJECTED
    if reason:
        restaurant.description = (restaurant.description + f"\n\n[Rejected: {reason}]").strip()
    restaurant.save(update_fields=["status", "description", "updated_at"])
    return restaurant
