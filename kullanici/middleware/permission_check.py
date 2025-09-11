from django.utils.deprecation import MiddlewareMixin
from django.shortcuts import redirect
from django.urls import reverse
from django.http import JsonResponse


class PermissionCheckMiddleware(MiddlewareMixin):
    """Yetki kontrolü middleware'i"""
    
    def process_request(self, request):
        # Login gerektirmeyen sayfalar
        allowed_paths = [
            '/kullanici/login/',
            '/admin/',
            '/favicon.ico',
            '/urun/barkod/',  # Barkod sorgulama sayfası
        ]
        
        # Eğer kullanıcı login olmamışsa ve izin verilen sayfalarda değilse
        if not request.user.is_authenticated:
            # İzin verilen sayfalarda değilse login'e yönlendir
            if not any(request.path.startswith(path) for path in allowed_paths):
                # AJAX istekleri için farklı response
                is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
                if is_ajax or request.content_type == 'application/json':
                    return JsonResponse({'error': 'Authentication required'}, status=401)
                else:
                    return redirect(reverse('kullanici:login'))
