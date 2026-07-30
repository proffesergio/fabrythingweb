from django.http import JsonResponse
from accounts.models import ModuleUrls, UserPermissions
from rest_framework_simplejwt.authentication import JWTAuthentication
import re
from django.db.models import Q


# Public API paths that must NEVER be gated behind a JWT by this middleware.
# These are the endpoints a visitor reaches *before* they have a token:
#   - the whole storefront (it enforces its own auth via DRF permission_classes)
#   - the public food-delivery read API (restaurants/zones; AllowAny via DRF)
#   - login / signup (you cannot present a valid access token before you have
#     logged in) — refresh is handled under /api/store/, already public above
#   - the deploy health check (it must answer even when the DB is unreachable,
#     which is precisely when you most need it)
#   - served images (core.views.serve_media_blob): this is <img src="..."/>
#     content — a product card's image tag never carries a bearer token, so
#     gating it behind a JWT would just make every image on the storefront
#     403. The URL is content-addressed (the sha256 of the bytes), so there
#     is nothing sensitive to protect by requiring auth here.
#   - the live chat API (/api/chat/): same shape as /api/food/ above — it
#     mixes customer-authenticated and staff-authenticated endpoints under one
#     prefix, each enforcing its own JWTAuthentication + permission class
#     (IsAuthenticated / chat.permissions.IsChatStaff). Gating it behind this
#     middleware's per-user ModuleUrls lookup instead would require seeding a
#     module row before ANY customer could open a chat thread.
#   - the custom print-on-demand API (/api/print/): same shape again --
#     public preset/print-area/quote lookups, customer-authenticated request
#     endpoints and staff-authenticated admin endpoints all under one prefix,
#     each enforcing its own JWTAuthentication + permission class
#     (IsAuthenticated / printing.permissions.IsPrintStaff).
PUBLIC_API_PREFIXES = (
    '/api/store/',
    '/api/food/',
    '/api/chat/',
    '/api/print/',
    '/api/auth/login',
    '/api/auth/signup',
    '/api/health/',
    '/api/media/',
)


class PermissionMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        current_url = request.path
        # Only the JSON API is permission-gated here. Everything else — the Django
        # admin (/admin/), static/media, and the SPA catch-all — authenticates on
        # its own (or is public) and must not be turned into a 401 by this middleware.
        if not current_url.startswith('/api/'):
            return self.get_response(request)
        # Public, token-less endpoints (storefront + login/signup) bypass the gate.
        if any(current_url.startswith(prefix) for prefix in PUBLIC_API_PREFIXES):
            return self.get_response(request)
        if current_url in urlToSkip():
            return self.get_response(request)

        jwt_auth = JWTAuthentication()
        try:
            user, token = jwt_auth.authenticate(request)
            if not user:
                return JsonResponse({"message": "Unauthorized"}, status=401)
        except:
            return JsonResponse({"message": "Unauthorized"}, status=401)

        response = self.get_response(request)

        # Skip Permission Logic for Super Admin and Top Domain Level User.
        # `domain_user_id` is nullable and was NULL on every account created before
        # accounts migration 0003 backfilled it — dereferencing `.id` on that turned
        # a routine request into a blank 500. Compare the raw FK column instead: a
        # NULL simply means "not a top-level account" and falls through to the normal
        # module-permission check below.
        if user.role == "Super Admin" or user.domain_user_id_id == user.id:
            return response

        module = find_matching_module(current_url)

        if not module:
            return JsonResponse({"message": "Module not Exist"}, status=400)

        permission = UserPermissions.objects.filter(
            user=user.id, module=module.module
        ).first()
        if not permission or permission.is_permission == False:
            return JsonResponse({"message": "Permission Denied"}, status=403)

        return response


def urlToSkip():
    return list(ModuleUrls.objects.values_list("url", flat=True))


def find_matching_module(url):
    regex_pattern = re.sub(r"\d+", r"[^/]+", re.escape(url))

    match_patter = ModuleUrls.objects.filter(
        Q(url__iregex=f"^{regex_pattern}$")
    ).first()
    return match_patter
