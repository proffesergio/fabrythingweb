from django.http import JsonResponse
from accounts.models import ModuleUrls, UserPermissions
from rest_framework_simplejwt.authentication import JWTAuthentication
import re
from django.db.models import Q


# Public API paths that must NEVER be gated behind a JWT by this middleware.
# These are the endpoints a visitor reaches *before* they have a token:
#   - the whole storefront (it enforces its own auth via DRF permission_classes)
#   - login / signup (you cannot present a token before you have logged in)
PUBLIC_API_PREFIXES = (
    '/api/store/',
    '/api/auth/login',
    '/api/auth/signup',
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

        # Skip Permission Logic for Super Admin and Top Domain Level User
        if user.role == "Super Admin" or user.domain_user_id.id == user.id:
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
