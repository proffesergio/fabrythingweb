from rest_framework.permissions import BasePermission


class IsRestaurantOwner(BasePermission):
    message = "Restaurant account required."

    def has_permission(self, request, view):
        u = request.user
        return bool(u and u.is_authenticated and u.role == "Restaurant" and getattr(u, "restaurant", None))


class IsPlatformAdmin(BasePermission):
    """Gate for /api/food/admin/* endpoints.

    /api/food/ is listed in core.middleware.PUBLIC_API_PREFIXES so that the
    public read API (AllowAny) and vendor JWT-authenticated endpoints aren't
    forced through PermissionMiddleware's module-permission lookup. That means
    PermissionMiddleware never gates these admin routes either — IsAuthenticated
    alone would let ANY authenticated user (Customer, Rider, Restaurant vendor)
    approve/suspend restaurants or edit delivery zones. This permission is the
    only gate standing between those endpoints and any logged-in user, so it
    must be applied on every admin viewset alongside IsAuthenticated.
    """

    message = "Platform admin account required."

    def has_permission(self, request, view):
        u = request.user
        return bool(u and u.is_authenticated and u.role in ("Admin", "Super Admin"))
