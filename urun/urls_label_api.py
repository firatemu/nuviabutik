# urun/urls.py - Etiket API endpoint ekle

from django.urls import path
from . import views

app_name = 'urun'

urlpatterns = [
    # ... mevcut URL'ler ...
    
    # Etiket API'leri
    path('api/getlabel/<int:urun_id>/', views.get_label_api, name='get_label_api'),
    path('api/getlabel/variant/<int:variant_id>/', views.get_variant_label_api, name='get_variant_label_api'),
]