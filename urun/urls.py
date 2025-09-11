from django.urls import path
from . import views

app_name = 'urun'

urlpatterns = [
    # Ürün listesi ve ekleme
    path('', views.urun_listesi, name='liste'),
    path('ekle/', views.urun_ekle, name='ekle'),
    path('<int:urun_id>/', views.urun_detay, name='detay'),
    path('<int:urun_id>/duzenle/', views.urun_duzenle, name='duzenle'),
    path('<int:urun_id>/sil/', views.urun_sil, name='sil'),
    
    # Varyasyon yönetimi
    path('<int:urun_id>/varyasyon/', views.varyasyon_yonet, name='varyasyon_yonet'),
    path('<int:urun_id>/varyasyon/olustur/', views.varyasyon_olustur, name='varyasyon_olustur'),
    path('varyant/<int:varyant_id>/duzenle/', views.varyant_duzenle, name='varyant_duzenle'),
    path('varyant/<int:varyant_id>/sil/', views.varyant_sil, name='varyant_sil'),
    path('<int:urun_id>/varyant/toplu-stok/', views.varyant_toplu_stok_guncelle, name='varyant_toplu_stok'),
    
    # Barkod sorgulama
    path('barkod/', views.barkod_sorgula, name='barkod_sorgula'),
    
    # Kategori yönetimi
    path('kategori/', views.kategori_yonetimi, name='kategori'),
    path('kategori/ust-ekle/', views.ust_kategori_ekle, name='ust_kategori_ekle'),
    path('kategori/ust-sil/<int:kategori_id>/', views.ust_kategori_sil, name='ust_kategori_sil'),
    
    # Marka yönetimi
    path('marka/', views.marka_listesi, name='marka_listesi'),
    path('marka/ekle/', views.marka_ekle, name='marka_ekle'),
    path('marka/<int:pk>/duzenle/', views.marka_duzenle, name='marka_duzenle'),
    path('marka/<int:pk>/sil/', views.marka_sil, name='marka_sil'),
    
    # Stok raporları
    path('en-cok-satanlar/', views.en_cok_satanlar, name='en_cok_satanlar'),
    path('kar-zarar/', views.kar_zarar_raporu, name='kar_zarar_raporu'),
    
    # Stok hareket yönetimi
    path('stok/', views.stok_yonetimi_ana, name='stok_yonetimi'),
    path('stok/sayim-eksigi/', views.sayim_eksigi_view, name='sayim_eksigi'),
    path('stok/sayim-fazlasi/', views.sayim_fazlasi_view, name='sayim_fazlasi'),
    path('stok/hareketler/', views.stok_hareket_listesi, name='stok_hareket_listesi'),
    
    # Fiyat yönetimi
    path('fiyat-guncelleme/', views.fiyat_guncelleme, name='fiyat_guncelleme'),
]
