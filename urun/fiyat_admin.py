"""
Admin Panel - Fiyat Yönetimi
"""

from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .fiyat_models import FiyatGecmisi, FiyatKampanya, FiyatUyari


@admin.register(FiyatGecmisi)
class FiyatGecmisiAdmin(admin.ModelAdmin):
    list_display = [
        'urun_link',
        'eski_satis_goster',
        'yeni_satis_goster',
        'degisiklik_goster',
        'neden_badge',
        'degistiren',
        'degisiklik_tarihi',
    ]
    list_filter = [
        'neden',
        'degisiklik_tarihi',
        'degistiren',
        'geri_alindi',
    ]
    search_fields = [
        'urun__ad',
        'urun__urun_kodu',
        'aciklama',
    ]
    readonly_fields = [
        'urun',
        'eski_alis_fiyati',
        'yeni_alis_fiyati',
        'eski_satis_fiyati',
        'yeni_satis_fiyati',
        'degisiklik_yuzdesi',
        'degisiklik_miktari',
        'degistiren',
        'degisiklik_tarihi',
        'ip_adresi',
    ]
    fieldsets = (
        ('Ürün Bilgisi', {
            'fields': ('urun',)
        }),
        ('Fiyat Değişikliği', {
            'fields': (
                ('eski_alis_fiyati', 'yeni_alis_fiyati'),
                ('eski_satis_fiyati', 'yeni_satis_fiyati'),
                ('degisiklik_yuzdesi', 'degisiklik_miktari'),
            )
        }),
        ('Değişiklik Detayları', {
            'fields': (
                'neden',
                'aciklama',
                ('degistiren', 'ip_adresi'),
                'degisiklik_tarihi',
            )
        }),
        ('Kampanya Bilgileri', {
            'fields': (
                ('gecerlilik_baslangic', 'gecerlilik_bitis'),
                'otomatik_geri_al',
                'geri_alindi',
            ),
            'classes': ('collapse',),
        }),
    )

    date_hierarchy = 'degisiklik_tarihi'

    def urun_link(self, obj):
        url = reverse('admin:urun_urun_change', args=[obj.urun.pk])
        return format_html('<a href="{}">{}</a>', url, obj.urun.ad)
    urun_link.short_description = 'Ürün'

    def eski_satis_goster(self, obj):
        return f"{obj.eski_satis_fiyati:.2f} ₺"
    eski_satis_goster.short_description = 'Eski Fiyat'

    def yeni_satis_goster(self, obj):
        return f"{obj.yeni_satis_fiyati:.2f} ₺"
    yeni_satis_goster.short_description = 'Yeni Fiyat'

    def degisiklik_goster(self, obj):
        if obj.artis_mi:
            renk = 'red'
            icon = '▲'
        else:
            renk = 'green'
            icon = '▼'

        return format_html(
            '<span style="color: {}; font-weight: bold;">{} {}%</span>',
            renk,
            icon,
            abs(obj.degisiklik_yuzdesi)
        )
    degisiklik_goster.short_description = 'Değişim'

    def neden_badge(self, obj):
        renkler = {
            'zam': 'red',
            'indirim': 'green',
            'kampanya': 'blue',
            'sezon_sonu': 'purple',
            'maliyet': 'orange',
            'duzeltme': 'gray',
        }
        renk = renkler.get(obj.neden, 'gray')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; '
            'border-radius: 3px; font-size: 11px;">{}</span>',
            renk,
            obj.get_neden_display()
        )
    neden_badge.short_description = 'Neden'

    def has_add_permission(self, request):
        return False  # Manuel ekleme yapılmasın

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser  # Sadece superuser silebilir


@admin.register(FiyatKampanya)
class FiyatKampanyaAdmin(admin.ModelAdmin):
    list_display = [
        'ad',
        'kampanya_turu_badge',
        'deger_goster',
        'durum_badge',
        'tarih_araligi',
        'etkilenen_urun_sayisi',
        'aktif_mi_goster',
        'islemler',
    ]
    list_filter = [
        'durum',
        'kampanya_turu',
        'baslangic_tarihi',
        'otomatik_geri_al',
    ]
    search_fields = ['ad', 'aciklama']
    filter_horizontal = ['kategoriler', 'markalar', 'urunler']

    fieldsets = (
        ('Kampanya Bilgileri', {
            'fields': (
                'ad',
                'aciklama',
                'durum',
            )
        }),
        ('Kampanya Türü ve Değeri', {
            'fields': (
                'kampanya_turu',
                'deger',
            )
        }),
        ('Tarih Aralığı', {
            'fields': (
                'baslangic_tarihi',
                'bitis_tarihi',
                'otomatik_geri_al',
            )
        }),
        ('Hedef Ürünler - Kategoriler', {
            'fields': (
                'kategoriler',
                'markalar',
                'cinsiyet',
            )
        }),
        ('Hedef Ürünler - Fiyat Aralığı', {
            'fields': (
                'min_fiyat',
                'max_fiyat',
            )
        }),
        ('Hedef Ürünler - Belirli Ürünler', {
            'fields': ('urunler',),
            'description': 'Belirli ürünler seçerseniz, diğer filtreler dikkate alınmaz.'
        }),
        ('İstatistikler', {
            'fields': (
                'etkilenen_urun_sayisi',
                'geri_alindi',
            ),
            'classes': ('collapse',),
        }),
    )

    readonly_fields = ['etkilenen_urun_sayisi', 'geri_alindi']

    def kampanya_turu_badge(self, obj):
        renkler = {
            'indirim_yuzde': 'green',
            'indirim_tutar': 'green',
            'zam_yuzde': 'red',
            'sabit_fiyat': 'blue',
        }
        renk = renkler.get(obj.kampanya_turu, 'gray')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; '
            'border-radius: 3px; font-size: 11px;">{}</span>',
            renk,
            obj.get_kampanya_turu_display()
        )
    kampanya_turu_badge.short_description = 'Tür'

    def deger_goster(self, obj):
        if obj.kampanya_turu in ['indirim_yuzde', 'zam_yuzde']:
            return f"%{obj.deger}"
        else:
            return f"{obj.deger} ₺"
    deger_goster.short_description = 'Değer'

    def durum_badge(self, obj):
        renkler = {
            'taslak': 'gray',
            'beklemede': 'orange',
            'aktif': 'green',
            'tamamlandi': 'blue',
            'iptal': 'red',
        }
        renk = renkler.get(obj.durum, 'gray')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; '
            'border-radius: 3px; font-size: 11px;">{}</span>',
            renk,
            obj.get_durum_display()
        )
    durum_badge.short_description = 'Durum'

    def tarih_araligi(self, obj):
        return format_html(
            '{}<br>→ {}',
            obj.baslangic_tarihi.strftime('%d.%m.%Y %H:%M'),
            obj.bitis_tarihi.strftime('%d.%m.%Y %H:%M')
        )
    tarih_araligi.short_description = 'Tarih Aralığı'

    def aktif_mi_goster(self, obj):
        if obj.aktif_mi:
            return format_html('<span style="color: green;">✓ Aktif</span>')
        elif obj.bitti_mi:
            return format_html('<span style="color: gray;">Bitti</span>')
        else:
            return format_html('<span style="color: orange;">Bekliyor</span>')
    aktif_mi_goster.short_description = 'Aktiflik'

    def islemler(self, obj):
        if obj.durum == 'taslak':
            return format_html(
                '<a class="button" href="{}">Uygula</a>',
                reverse('admin:fiyat_kampanya_uygula', args=[obj.pk])
            )
        elif obj.durum == 'aktif' and obj.otomatik_geri_al and not obj.geri_alindi:
            return format_html(
                '<a class="button" href="{}">Geri Al</a>',
                reverse('admin:fiyat_kampanya_geri_al', args=[obj.pk])
            )
        return '-'
    islemler.short_description = 'İşlemler'


@admin.register(FiyatUyari)
class FiyatUyariAdmin(admin.ModelAdmin):
    list_display = [
        'urun_link',
        'uyari_turu_badge',
        'mesaj_kisaltma',
        'okundu_goster',
        'olusturma_tarihi',
    ]
    list_filter = [
        'uyari_turu',
        'okundu',
        'olusturma_tarihi',
    ]
    search_fields = ['urun__ad', 'mesaj']
    readonly_fields = [
        'urun',
        'uyari_turu',
        'mesaj',
        'fiyat_gecmisi',
        'olusturma_tarihi',
    ]

    date_hierarchy = 'olusturma_tarihi'

    def urun_link(self, obj):
        url = reverse('admin:urun_urun_change', args=[obj.urun.pk])
        return format_html('<a href="{}">{}</a>', url, obj.urun.ad)
    urun_link.short_description = 'Ürün'

    def uyari_turu_badge(self, obj):
        renkler = {
            'buyuk_artis': 'red',
            'buyuk_dusus': 'orange',
            'minimum_altinda': 'red',
            'maksimum_ustunde': 'red',
            'kar_marji_dusuk': 'orange',
        }
        renk = renkler.get(obj.uyari_turu, 'gray')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; '
            'border-radius: 3px; font-size: 11px;">⚠ {}</span>',
            renk,
            obj.get_uyari_turu_display()
        )
    uyari_turu_badge.short_description = 'Uyarı'

    def mesaj_kisaltma(self, obj):
        return obj.mesaj[:50] + '...' if len(obj.mesaj) > 50 else obj.mesaj
    mesaj_kisaltma.short_description = 'Mesaj'

    def okundu_goster(self, obj):
        if obj.okundu:
            return format_html('<span style="color: green;">✓ Okundu</span>')
        else:
            return format_html('<span style="color: red;">✗ Okunmadı</span>')
    okundu_goster.short_description = 'Durum'

    def has_add_permission(self, request):
        return False  # Otomatik oluşuyor

    actions = ['okundu_isaretle']

    def okundu_isaretle(self, request, queryset):
        updated = queryset.update(okundu=True)
        self.message_user(
            request, f'{updated} uyarı okundu olarak işaretlendi.')
    okundu_isaretle.short_description = 'Seçilenleri okundu olarak işaretle'

