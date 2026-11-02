from rest_framework.permissions import BasePermission

from core.helpers import isPlatformStaff


class IsPrintStaff(BasePermission):
    """Gate for /api/print/admin/* endpoints.

    /api/print/ sits in core.middleware.PUBLIC_API_PREFIXES for the same
    reason /api/food/ and /api/chat/ do: it mixes customer- and
    staff-authenticated endpoints under one prefix, so this permission class
    -- not PermissionMiddleware's per-user ModuleUrls gate -- is the only
    thing standing between the admin print queue and any logged-in
    Customer/Rider/Restaurant account.

    Delegates to core.helpers.isPlatformStaff, NOT isPlatformScope alone --
    isPlatformScope is True for any self-signed-up Customer (they are their
    own domain root), which is exactly the privilege-escalation this project
    already shipped once (see chat.permissions.IsChatStaff and
    accounts/test_dynamic_form_scope.py).
    """

    message = "Staff account required."

    def has_permission(self, request, view):
        u = request.user
        if not (u and u.is_authenticated):
            return False
        return isPlatformStaff(u)
