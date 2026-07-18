from rest_framework.permissions import BasePermission


class IsRestaurantOwner(BasePermission):
    message = "Restaurant account required."

    def has_permission(self, request, view):
        u = request.user
        return bool(u and u.is_authenticated and u.role == "Restaurant" and getattr(u, "restaurant", None))
