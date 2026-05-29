from django.contrib import admin
from .models import UrunKategoriUst, Renk, Beden, Marka, Urun, UrunVaryanti, StokHareket, StokDegisiklikLog


@admin.register(UrunKategoriUst)
class UrunKategoriUstAdmin(admin.ModelAdmin):
    list_display = ['ad', 'aktif', 'olusturma_tarihi']
    list_filter = ['aktif', 'olusturma_tarihi']
    search_fields = ['ad']
    ordering = ['ad']


@admin.register(Renk)
class RenkAdmin(admin.ModelAdmin):
    list_display = ['ad', 'kod', 'hex_kod', 'sira', 'aktif']
    list_filter = ['aktif']
    search_fields = ['ad', 'kod']
    ordering = ['sira', 'ad']
    list_editable = ['sira', 'aktif']


@admin.register(Beden)
class BedenAdmin(admin.ModelAdmin):
    list_display = ['ad', 'kod', 'tip', 'sira', 'aktif']
    list_filter = ['tip', 'aktif']
    search_fields = ['ad', 'kod']
    ordering = ['tip', 'sira', 'ad']
    list_editable = ['sira', 'aktif']


@admin.register(Marka)
class MarkaAdmin(admin.ModelAdmin):
    list_display = ['ad', 'aktif', 'olusturma_tarihi']
    list_filter = ['aktif', 'olusturma_tarihi']
    search_fields = ['ad']
    ordering = ['ad']


class UrunVaryantiInline(admin.TabularInline):
    model = UrunVaryanti
    extra = 0
    readonly_fields = ['barkod', 'olusturma_tarihi',
                       'stok_durumu', 'son_degisiklik']
    fields = ['renk', 'beden', 'stok_miktari', 'barkod', 'aktif']

    def get_readonly_fields(self, request, obj=None):
        readonly_fields = list(self.readonly_fields)

        # Eğer obj varsa (düzenleme modunda)
        if obj:
            for varyant in obj.varyantlar.all():
                if varyant.stok_kaydedildi:
                    # Stok kaydedilmişse stok_miktari readonly yap
                    readonly_fields.append('stok_miktari')
                    break

        return readonly_fields

    def stok_durumu(self, obj):
        if obj and obj.pk:
            return obj.stok_durumu
        return "Yeni kayıt - Düzenlenebilir"
    stok_durumu.short_description = "Stok Durumu"

    def son_degisiklik(self, obj):
        if obj and obj.pk:
            son_log = obj.stok_loglari.first()
            if son_log:
                return f"{son_log.olusturma_tarihi.strftime('%d.%m %H:%M')} ({son_log.get_islem_tipi_display()})"
            return "Henüz değişiklik yok"
        return "Yeni kayıt"
    son_degisiklik.short_description = "Son Değişiklik"


@admin.register(Urun)
class UrunAdmin(admin.ModelAdmin):
    list_display = ['urun_kodu', 'ad', 'kategori', 'marka', 'varyasyonlu',
                    'pesin_fiyat_gorsel', 'taksitli_fiyat_gorsel', 'fark_gorsel',
                    'toplam_stok', 'aktif']
    list_filter = ['kategori', 'marka', 'varyasyonlu', 'aktif', 'cinsiyet']
    search_fields = ['ad', 'urun_kodu']
    ordering = ['-olusturma_tarihi']
    readonly_fields = ['urun_kodu', 'taksitli_fiyat', 'fiyat_farki_goster',
                       'olusturma_tarihi', 'guncelleme_tarihi']
    inlines = [UrunVaryantiInline]

    fieldsets = (
        ('Temel Bilgiler', {
            'fields': ('urun_kodu', 'ad', 'aciklama', 'kategori', 'marka', 'cinsiyet', 'birim')
        }),
        ('Varyasyon', {
            'fields': ('varyasyonlu',)
        }),
        ('Fiyat Bilgileri', {
            'fields': (
                'alis_fiyati',
                'kar_orani',
                ('pesin_fiyat', 'taksit_orani'),
                'taksitli_fiyat',
                'fiyat_farki_goster'
            ),
            'description': 'Taksitli fiyat otomatik hesaplanır (Peşin + Taksit Oranı)'
        }),
        ('Ürün Resmi', {
            'fields': ('resim',)
        }),
        ('Durum', {
            'fields': ('aktif', 'stok_takibi', 'kritik_stok_seviyesi')
        }),
        ('Tarih Bilgileri', {
            'fields': ('olusturma_tarihi', 'guncelleme_tarihi'),
            'classes': ('collapse',)
        }),
    )

    def pesin_fiyat_gorsel(self, obj):
        """Peşin fiyat - liste görünümü"""
        from django.utils.html import format_html
        return format_html(
            '<span style="font-weight: bold; color: green;">{}₺</span>',
            f'{float(obj.pesin_fiyat):.2f}'
        )
    pesin_fiyat_gorsel.short_description = 'Peşin Fiyat'
    pesin_fiyat_gorsel.admin_order_field = 'pesin_fiyat'

    def taksitli_fiyat_gorsel(self, obj):
        """Taksitli fiyat - liste görünümü"""
        from django.utils.html import format_html
        return format_html(
            '<span style="font-weight: bold; color: #ff9800;">{}₺</span>',
            f'{float(obj.taksitli_fiyat):.2f}'
        )
    taksitli_fiyat_gorsel.short_description = 'Taksitli Fiyat'
    taksitli_fiyat_gorsel.admin_order_field = 'taksitli_fiyat'

    def fark_gorsel(self, obj):
        """Fiyat farkı - liste görünümü"""
        from django.utils.html import format_html
        fark = float(obj.fiyat_farki)
        yuzde = float(obj.fiyat_farki_yuzdesi)
        return format_html(
            '<span style="color: #2196F3; font-size: 11px;">+{}₺<br>(%{})</span>',
            f'{fark:.2f}',
            f'{yuzde:.1f}'
        )
    fark_gorsel.short_description = 'Fark'

    def fiyat_farki_goster(self, obj):
        """Fiyat farkı detay - form görünümü"""
        from django.utils.html import format_html
        if obj.pesin_fiyat > 0:
            fark = float(obj.fiyat_farki)
            yuzde = float(obj.fiyat_farki_yuzdesi)
            return format_html(
                '<div style="background: #f0f0f0; padding: 10px; border-radius: 5px;">'
                '<strong>Fark:</strong> {}₺ '
                '<span style="color: #2196F3;">(+%{})</span>'
                '</div>',
                f'{fark:.2f}',
                f'{yuzde:.2f}'
            )
        return '-'
    fiyat_farki_goster.short_description = 'Peşin/Taksitli Farkı'


@admin.register(UrunVaryanti)
class UrunVaryantiAdmin(admin.ModelAdmin):
    list_display = ['urun', 'varyasyon_adi', 'barkod',
                    'stok_miktari', 'stok_durumu_admin', 'aktif']
    list_filter = ['urun__kategori', 'renk',
                   'beden', 'aktif', 'stok_kaydedildi']
    search_fields = ['urun__ad', 'barkod']
    ordering = ['urun', 'renk', 'beden']
    readonly_fields = ['barkod', 'stok_durumu',
                       'olusturma_tarihi', 'guncelleme_tarihi']

    fieldsets = (
        ('Ürün Bilgileri', {
            'fields': ('urun', 'renk', 'beden')
        }),
        ('Stok Bilgileri', {
            'fields': ('stok_miktari', 'stok_kaydedildi', 'stok_durumu'),
            'description': 'Stok miktarı sadece ilk oluşturulduğunda değiştirilebilir. Sonrasında Stok Hareket sistemi kullanılmalıdır.'
        }),
        ('Ek Bilgiler', {
            'fields': ('barkod', 'ek_aciklama', 'resim', 'aktif'),
            'classes': ('collapse',)
        }),
        ('Tarih Bilgileri', {
            'fields': ('olusturma_tarihi', 'guncelleme_tarihi'),
            'classes': ('collapse',)
        }),
    )

    def get_readonly_fields(self, request, obj=None):
        readonly_fields = list(self.readonly_fields)

        # Eğer obje varsa ve stok kaydedilmişse
        if obj and obj.stok_kaydedildi:
            readonly_fields.append('stok_miktari')
            readonly_fields.append('stok_kaydedildi')

        return readonly_fields

    def stok_durumu_admin(self, obj):
        if obj.stok_kaydedildi:
            return "🔒 Korumalı"
        else:
            return "🔓 Düzenlenebilir"
    stok_durumu_admin.short_description = "Stok Durumu"

    def save_model(self, request, obj, form, change):
        try:
            # Yeni kayıt için ilk stok ayarlama
            if not change and 'stok_miktari' in form.cleaned_data:
                stok_miktari = form.cleaned_data['stok_miktari']
                obj.save()  # Önce kaydet
                # İlk stok hareketini oluştur
                if stok_miktari > 0:
                    obj.ilk_stok_ayarla(
                        stok_miktari, request.user, "Admin panelinden ilk stok girişi")
            else:
                super().save_model(request, obj, form, change)
        except ValueError as e:
            from django.contrib import messages
            messages.error(request, str(e))

    actions = ['reset_stock_protection']

    def reset_stock_protection(self, request, queryset):
        """Seçili varyantların stok korumasını kaldır (Dikkatli kullanın!)"""
        count = 0
        for varyant in queryset:
            if varyant.stok_kaydedildi:
                varyant.stok_kaydedildi = False
                varyant.save()
                count += 1

        self.message_user(
            request, f"{count} adet varyantın stok koruması kaldırıldı.")
    reset_stock_protection.short_description = "⚠️ Stok korumasını kaldır (DİKKAT!)"

    def save_model(self, request, obj, form, change):
        # Kullanıcı bilgisini set et
        obj.set_current_user(request.user, self.get_client_ip(request))

        try:
            # Yeni kayıt için ilk stok ayarlama
            if not change and 'stok_miktari' in form.cleaned_data:
                stok_miktari = form.cleaned_data['stok_miktari']
                obj.save()  # Önce kaydet
                # İlk stok hareketini oluştur
                if stok_miktari > 0:
                    obj.ilk_stok_ayarla(
                        stok_miktari, request.user, "Admin panelinden ilk stok girişi")
            else:
                super().save_model(request, obj, form, change)
        except ValueError as e:
            from django.contrib import messages
            messages.error(request, str(e))

    def get_client_ip(self, request):
        """İstemci IP adresini al"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


@admin.register(StokHareket)
class StokHareketAdmin(admin.ModelAdmin):
    list_display = ['varyant', 'hareket_tipi', 'miktar',
                    'onceki_stok', 'yeni_stok', 'kullanici', 'olusturma_tarihi']
    list_filter = ['hareket_tipi', 'olusturma_tarihi', 'kullanici']
    search_fields = ['varyant__urun__ad', 'varyant__barkod', 'aciklama']
    ordering = ['-olusturma_tarihi']
    readonly_fields = ['olusturma_tarihi']

    def has_add_permission(self, request):
        return False  # Stok hareketleri sadece sistem tarafından oluşturulmalı


@admin.register(StokDegisiklikLog)
class StokDegisiklikLogAdmin(admin.ModelAdmin):
    list_display = ['varyant', 'islem_tipi', 'eski_miktar', 'yeni_miktar',
                    'miktar_degisimi_display', 'kullanici', 'olusturma_tarihi']
    list_filter = ['islem_tipi', 'olusturma_tarihi', 'kullanici']
    search_fields = ['varyant__urun__ad', 'varyant__barkod', 'aciklama']
    ordering = ['-olusturma_tarihi']
    readonly_fields = ['varyant', 'islem_tipi', 'eski_miktar',
                       'yeni_miktar', 'kullanici', 'ip_adresi', 'olusturma_tarihi']

    date_hierarchy = 'olusturma_tarihi'

    def has_add_permission(self, request):
        return False  # Loglar sadece sistem tarafından oluşturulmalı

    def has_change_permission(self, request, obj=None):
        return False  # Loglar değiştirilemez

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser  # Sadece superuser silebilir

    def miktar_degisimi_display(self, obj):
        degisim = obj.miktar_degisimi()
        if degisim > 0:
            return f"+{degisim}"
        elif degisim < 0:
            return str(degisim)
        else:
            return "0"
    miktar_degisimi_display.short_description = "Değişim"

    fieldsets = (
        ('Stok Değişiklik Bilgileri', {
            'fields': ('varyant', 'islem_tipi', 'eski_miktar', 'yeni_miktar')
        }),
        ('Kullanıcı Bilgileri', {
            'fields': ('kullanici', 'ip_adresi')
        }),
        ('Açıklama', {
            'fields': ('aciklama',)
        }),
        ('Tarih', {
            'fields': ('olusturma_tarihi',)
        }),
    )
