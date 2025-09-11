from django.http import HttpResponseForbidden
from django.shortcuts import redirect
from django.urls import reverse
from django.contrib import messages


class AdminAccessMiddleware:
    """
    Admin paneline sadece superuser kullanıcılarının erişimini sağlayan middleware
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Admin paneli URL'lerini kontrol et
        if request.path.startswith('/admin/'):
            # Login sayfasını kontrol etme
            if request.path in ['/admin/login/', '/admin/logout/']:
                response = self.get_response(request)
                return response

            # Kullanıcı giriş yapmış mı kontrol et
            if not request.user.is_authenticated:
                return redirect('/admin/login/')

            # Sadece superuser kullanıcılarına izin ver (kullanıcı adı kısıtlaması kaldırıldı)
            if not request.user.is_superuser:
                messages.error(request, 'Admin paneline erişim yetkiniz bulunmamaktadır.')
                return redirect('/')  # Ana sayfaya yönlendir

        response = self.get_response(request)
        return response
