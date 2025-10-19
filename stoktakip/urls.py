"""
URL configuration for stoktakip project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views
from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required
from django.views.generic import TemplateView
from django.http import HttpResponse
from . import views
from . import tsc_to_zpl_converter


def redirect_to_dashboard(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    else:
        return redirect('kullanici:login')

def favicon_view(request):
    return HttpResponse(status=204)  # Empty response for favicon

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # Favicon
    path('favicon.ico', favicon_view, name='favicon'),
    
    # Ana sayfa
    path('', redirect_to_dashboard, name='home'),
    path('dashboard/', login_required(views.dashboard_view), name='dashboard'),
    path('gunluk-rapor/', login_required(views.gunluk_rapor_view), name='gunluk_rapor'),
    path('gunluk-rapor/pdf/', login_required(views.gunluk_rapor_pdf_view), name='gunluk_rapor_pdf'),
    
    # Authentication
    path('kullanici/', include('kullanici.urls', namespace='kullanici')),
    
    # App URLs
    path('urun/', include('urun.urls', namespace='urun')),
    path('satis/', include('satis.urls', namespace='satis')),
    path('musteri/', include('musteri.urls', namespace='musteri')),
    path('hediye/', include('hediye.urls', namespace='hediye')),
    path('rapor/', include('rapor.urls', namespace='rapor')),
    path('log/', include('log.urls', namespace='log')),
    path('gider/', include('gider.urls', namespace='gider')),  # Giderler modülü
    path('kasa/', include('kasa.urls', namespace='kasa')),     # Kasa yönetimi modülü
    # Downloads modülü kaldırıldı - Local Print Agent kullanılıyor
    
    # Custom Label API (TSC Design as ZPL)
    path('api/tsc-as-zpl/', tsc_to_zpl_converter.tsc_design_as_zpl, name='custom_label'),
    path('api/tsc-dynamic-zpl/', tsc_to_zpl_converter.tsc_design_dynamic_zpl, name='custom_label_dynamic'),
    
    # Ürün Etiket API'leri
    path('api/urun-etiket/<int:urun_id>/', tsc_to_zpl_converter.urun_etiket_zpl, name='urun_etiket'),
    path('api/varyant-etiket/<int:varyant_id>/', tsc_to_zpl_converter.varyant_etiket_zpl, name='varyant_etiket'),
]

# Media files için
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATICFILES_DIRS[0] if settings.STATICFILES_DIRS else '')

# Temporary debug URL
