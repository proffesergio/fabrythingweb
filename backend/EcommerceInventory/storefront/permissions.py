from rest_framework.permissions import BasePermission

from core.helpers import isPlatformScope


class IsPlatformStaff(BasePermission):
    """Gate for /api/store/admin/banners/* (and any future storefront
    admin-only endpoint).

    `/api/store/` is listed in core.middleware.PUBLIC_API_PREFIXES -- it mixes
    public customer endpoints with admin ones under one prefix, so
    PermissionMiddleware's per-user ModuleUrls gate never runs for it. That
    makes this permission class the ONLY thing standing between banner CRUD
    and any logged-in Customer account.

    `core.helpers.isPlatformScope` alone is not enough: it is true for ANY
    domain-root user, and a self-signed-up Customer is their own domain root
    (Users.save() self-assigns domain_user_id = self on insert for every
    role -- see accounts/models.py and the identical trap documented on
    chat.permissions.IsChatStaff). The role check narrows it back down to the
    roles that actually operate the admin panel; isPlatformScope on top of
    that still excludes a domain sub-account (e.g. a Staff user created under
    someone else's domain), matching the widening rule
    ProductListView/CategoryListView already use.
    """

    message = "Staff account required."

    def has_permission(self, request, view):
        u = request.user
        if not (u and u.is_authenticated):
            return False
        return u.role in ("Admin", "Super Admin", "Staff") and isPlatformScope(u)
