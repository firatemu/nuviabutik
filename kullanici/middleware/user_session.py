from django.utils.deprecation import MiddlewareMixin
from django.contrib.auth import logout
from django.shortcuts import redirect
from django.urls import reverse
from django.utils import timezone
from kullanici.models import UserSession


class UserSessionMiddleware(MiddlewareMixin):
    """Kullanıcı oturum yönetimi middleware'i"""
    
    def process_request(self, request):
        if request.user.is_authenticated:
            session_key = request.session.session_key
            
            if session_key:
                try:
                    user_session = UserSession.objects.get(
                        user=request.user,
                        session_key=session_key,
                        is_active=True
                    )
                    # Oturum hala aktif
                except UserSession.DoesNotExist:
                    # Oturum bulunamadı, kullanıcıyı çıkart
                    logout(request)
                    return redirect(reverse('kullanici:login'))
