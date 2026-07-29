from rest_framework.permissions import BasePermission

from core.helpers import isPlatformScope


class IsChatStaff(BasePermission):
    """Gate for /api/chat/admin/* endpoints.

    /api/chat/ is listed in core.middleware.PUBLIC_API_PREFIXES (same reason
    as /api/food/: it mixes customer- and staff-authenticated endpoints under
    one prefix, so PermissionMiddleware's per-user ModuleUrls gate is bypassed
    entirely for it). That means this permission class is the ONLY thing
    standing between the admin chat inbox and any logged-in Customer/Rider/
    Restaurant account — IsAuthenticated alone would let anyone read/reply to
    every customer's thread.

    `core.helpers.isPlatformScope` alone is not enough: it is true for ANY
    domain-root user (a plain Customer who self-signed up is their own domain
    root — see accounts/test_dynamic_form_scope.py), not just staff. The role
    check narrows it back down to the roles that actually operate the admin
    panel; isPlatformScope on top of that excludes a domain sub-account
    (a Staff/Admin user created *under* someone else's domain) that should only
    ever act within its own tenant, matching the widening rule
    ProductListView/CategoryListView already use.
    """

    message = "Staff account required."

    def has_permission(self, request, view):
        u = request.user
        if not (u and u.is_authenticated):
            return False
        return u.role in ("Admin", "Super Admin", "Staff") and isPlatformScope(u)
