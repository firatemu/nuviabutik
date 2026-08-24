from django.utils.deprecation import MiddlewareMixin
from django.shortcuts import redirect
from django.urls import reverse
from django.http import JsonResponse


class PermissionCheckMiddleware(MiddlewareMixin):
    """Global login gate — static/media and auth pages are public."""

    ALLOWED_PREFIXES = (
        '/kullanici/login/',
        '/admin/login/',
        '/admin/logout/',
        '/static/',
        '/media/',
        '/favicon.ico',
    )

    def process_request(self, request):
        if request.user.is_authenticated:
            return None

        path = request.path
        if any(path.startswith(prefix) for prefix in self.ALLOWED_PREFIXES):
            return None

        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        is_json = 'application/json' in (request.content_type or '')
        if is_ajax or is_json:
            return JsonResponse(
                {'success': False, 'message': 'Oturum açmanız gerekiyor.'},
                status=401,
            )
        return redirect(reverse('kullanici:login'))
