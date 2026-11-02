from rest_framework.permissions import BasePermission

from core.helpers import isPlatformStaff


class IsAnalyticsStaff(BasePermission):
    """Gate for /api/store/admin/analytics/* endpoints.

    Same shape as printing.permissions.IsPrintStaff: these routes sit under
    /api/store/ (a PUBLIC_API_PREFIXES entry, so PermissionMiddleware lets
    them through) and each enforces its own staff check here instead.
    Delegates to core.helpers.isPlatformStaff — never role-name matching.
    """

    message = "Staff account required."

    def has_permission(self, request, view):
        u = request.user
        if not (u and u.is_authenticated):
            return False
        return isPlatformStaff(u)
