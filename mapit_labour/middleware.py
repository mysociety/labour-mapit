from logging import getLogger

from login_required.middleware import LoginRequiredMiddleware

from .models import APIKey

logger = getLogger(__name__)


class LoginOrAPIKeyRequiredMiddleware(LoginRequiredMiddleware):
    def _api_key_exists(self, request):
        if api_key := request.GET.get("api_key"):
            return APIKey.objects.filter(key=api_key).exists()

    def process_request(self, request):
        if self._api_key_exists(request):
            return None
        else:
            return self._login_required(request)
