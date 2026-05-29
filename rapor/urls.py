from django.urls import path
from . import views

app_name = 'rapor'

urlpatterns = [
    # Raporlar
    path('gunluk-satis/', views.gunluk_satis, name='gunluk_satis'),
    path('stok-raporu/', views.stok_raporu, name='stok_raporu'),
    path('stok-degeri/', views.stok_degeri, name='stok_degeri'),
    path('stok-hareketleri/<int:varyant_id>/', views.stok_hareketleri, name='stok_hareketleri'),
    path('cok-satan-urunler/', views.cok_satan_urunler, name='cok_satan_urunler'),
    path('urun-bazli-karlilik/', views.urun_bazli_karlilik, name='urun_bazli_karlilik'),
    path('fatura-bazli-karlilik/', views.fatura_bazli_karlilik, name='fatura_bazli_karlilik'),
    path(
        'fatura-bazli-karlilik/<int:pk>/',
        views.fatura_karlilik_detay,
        name='fatura_karlilik_detay',
    ),
    path('musteri-raporu/', views.musteri_raporu, name='musteri_raporu'),
    path('satici-raporu/', views.satici_raporu, name='satici_raporu'),
    
    # Rapor export
    path('export/gunluk-satis-excel/', views.gunluk_satis_excel, name='gunluk_satis_excel'),
    path('export/gunluk-satis-pdf/', views.gunluk_satis_pdf, name='gunluk_satis_pdf'),
    path('export/stok-excel/', views.stok_excel, name='stok_excel'),
    path('export/stok-pdf/', views.stok_pdf, name='stok_pdf'),
    path('export/satici-raporu-excel/', views.satici_raporu_excel, name='satici_raporu_excel'),
    path('export/satici-raporu-pdf/', views.satici_raporu_pdf, name='satici_raporu_pdf'),
]
