import re

from django.conf import settings
from django.core.exceptions import PermissionDenied
from login_required.middleware import LoginRequiredMiddleware

from .models import APIKey

ALLOWED_PATHS = [
    re.compile(url) for url in getattr(settings, "API_KEY_AUTH_ALLOWED_PATHS", [])
]


class LoginOrAPIKeyRequiredMiddleware(LoginRequiredMiddleware):
    def _api_key_exists_and_allowed(self, request):
        if not any(url.match(request.path) for url in ALLOWED_PATHS):
            return False

        if request.user.is_authenticated:
            return False

        if APIKey.objects.filter(
            key=request.GET.get("api_key"), user__is_active=True
        ).exists():
            return True
        else:
            raise PermissionDenied

    def process_request(self, request):
        if self._api_key_exists_and_allowed(request):
            return None
        else:
            return super().process_request(request)
