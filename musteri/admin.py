from django.contrib import admin
from .models import Musteri, Tahsilat, TahsilatDetay, MusteriGruplar


@admin.register(Musteri)
class MusteriAdmin(admin.ModelAdmin):
    list_display = ['ad', 'soyad', 'telefon', 'tip', 'acik_hesap_bakiye', 'acik_hesap_limit', 'aktif']
    list_filter = ['tip', 'aktif', 'kayit_tarihi']
    search_fields = ['ad', 'soyad', 'telefon', 'email', 'firma_adi']
    list_editable = ['acik_hesap_limit', 'aktif']
    fieldsets = (
        ('Kişisel Bilgiler', {
            'fields': ('ad', 'soyad', 'telefon', 'email', 'dogum_tarihi')
        }),
        ('Adres Bilgileri', {
            'fields': ('adres', 'il', 'ilce', 'posta_kodu')
        }),
        ('Müşteri Tipi', {
            'fields': ('tip',)
        }),
        ('Kurumsal Bilgiler', {
            'fields': ('firma_adi', 'vergi_no', 'vergi_dairesi'),
            'classes': ('collapse',)
        }),
        ('Bireysel Bilgiler', {
            'fields': ('tc_no',),
            'classes': ('collapse',)
        }),
        ('Açık Hesap Bilgileri', {
            'fields': ('acik_hesap_bakiye', 'acik_hesap_limit'),
            'description': 'Müşterinin açık hesap (veresiye) bilgileri'
        }),
        ('Diğer', {
            'fields': ('notlar', 'aktif')
        })
    )
    readonly_fields = ['acik_hesap_bakiye']  # Bakiye otomatik hesaplanır


@admin.register(Tahsilat)
class TahsilatAdmin(admin.ModelAdmin):
    list_display = ['tahsilat_no', 'musteri', 'tutar', 'tahsilat_tipi', 'durum', 'tahsilat_tarihi']
    list_filter = ['tahsilat_tipi', 'durum', 'tahsilat_tarihi']
    search_fields = ['tahsilat_no', 'musteri__ad', 'musteri__soyad']
    readonly_fields = ['tahsilat_no', 'olusturma_tarihi']
    date_hierarchy = 'tahsilat_tarihi'


@admin.register(MusteriGruplar)
class MusteriGruplarAdmin(admin.ModelAdmin):
    list_display = ['ad', 'aciklama', 'indirim_orani', 'aktif']
    list_filter = ['aktif']
    search_fields = ['ad']
    list_editable = ['aktif']


# Register your models here.
