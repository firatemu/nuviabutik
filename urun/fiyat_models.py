"""
Fiyat Geçmişi ve Yönetim Modelleri
NuviaButik - Fiyat Takip Sistemi
"""

from django.db import models
from django.conf import settings
from decimal import Decimal
from django.utils import timezone
from datetime import timedelta


class FiyatGecmisi(models.Model):
    """Ürün fiyat değişiklik geçmişi"""

    DEGISIKLIK_NEDENI = [
        ('zam', 'Fiyat Zammı'),
        ('indirim', 'İndirim'),
        ('kampanya', 'Kampanya'),
        ('sezon_sonu', 'Sezon Sonu İndirimi'),
        ('maliyet', 'Maliyet Artışı'),
        ('duzeltme', 'Fiyat Düzeltme'),
        ('toplu_guncelleme', 'Toplu Güncelleme'),
        ('enflasyon', 'Enflasyon Zammı'),
        ('diger', 'Diğer'),
    ]

    urun = models.ForeignKey(
        'Urun',
        on_delete=models.CASCADE,
        related_name='fiyat_gecmisi',
        verbose_name="Ürün"
    )

    # Fiyat bilgileri
    eski_alis_fiyati = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name="Eski Alış Fiyatı"
    )
    yeni_alis_fiyati = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name="Yeni Alış Fiyatı"
    )
    eski_satis_fiyati = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name="Eski Satış Fiyatı"
    )
    yeni_satis_fiyati = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name="Yeni Satış Fiyatı"
    )

    # Değişiklik bilgileri
    degisiklik_yuzdesi = models.DecimalField(
        max_digits=7,
        decimal_places=2,
        verbose_name="Değişim Yüzdesi (%)",
        help_text="Satış fiyatındaki değişim yüzdesi"
    )
    degisiklik_miktari = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name="Değişim Miktarı (TL)"
    )

    # Neden ve açıklama
    neden = models.CharField(
        max_length=20,
        choices=DEGISIKLIK_NEDENI,
        default='diger',
        verbose_name="Değişiklik Nedeni"
    )
    aciklama = models.TextField(
        blank=True,
        null=True,
        verbose_name="Açıklama"
    )

    # Kullanıcı ve tarih
    degistiren = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Değiştiren Kullanıcı"
    )
    degisiklik_tarihi = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Değişiklik Tarihi"
    )
    ip_adresi = models.GenericIPAddressField(
        null=True,
        blank=True,
        verbose_name="IP Adresi"
    )

    # Geçerlilik tarihleri (kampanyalar için)
    gecerlilik_baslangic = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Geçerlilik Başlangıç"
    )
    gecerlilik_bitis = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Geçerlilik Bitiş"
    )

    # Otomatik geri alma (kampanya bitiminde)
    otomatik_geri_al = models.BooleanField(
        default=False,
        verbose_name="Otomatik Geri Al",
        help_text="Kampanya bitiminde eski fiyata geri dön"
    )
    geri_alindi = models.BooleanField(
        default=False,
        verbose_name="Geri Alındı"
    )

    class Meta:
        verbose_name = "Fiyat Geçmişi"
        verbose_name_plural = "Fiyat Geçmişleri"
        ordering = ['-degisiklik_tarihi']
        indexes = [
            models.Index(fields=['urun', '-degisiklik_tarihi']),
            models.Index(fields=['degistiren', '-degisiklik_tarihi']),
            models.Index(fields=['neden']),
            models.Index(fields=['gecerlilik_bitis']),
        ]

    def __str__(self):
        return f"{self.urun.ad} - {self.eski_satis_fiyati}₺ → {self.yeni_satis_fiyati}₺"

    @property
    def artis_mi(self):
        """Fiyat artışı mı yoksa düşüş mü?"""
        return self.yeni_satis_fiyati > self.eski_satis_fiyati

    @property
    def degisiklik_turu(self):
        """Değişiklik türü string"""
        return "Artış" if self.artis_mi else "Düşüş"

    @property
    def kampanya_aktif_mi(self):
        """Kampanya hala aktif mi?"""
        if not self.gecerlilik_baslangic or not self.gecerlilik_bitis:
            return False
        simdi = timezone.now()
        return self.gecerlilik_baslangic <= simdi <= self.gecerlilik_bitis

    @property
    def kampanya_bitti_mi(self):
        """Kampanya bitti mi?"""
        if not self.gecerlilik_bitis:
            return False
        return timezone.now() > self.gecerlilik_bitis

    def save(self, *args, **kwargs):
        # Değişim yüzdesini hesapla
        if self.eski_satis_fiyati > 0:
            degisim = ((self.yeni_satis_fiyati - self.eski_satis_fiyati) /
                       self.eski_satis_fiyati) * 100
            self.degisiklik_yuzdesi = round(degisim, 2)

        # Değişim miktarını hesapla
        self.degisiklik_miktari = self.yeni_satis_fiyati - self.eski_satis_fiyati

        super().save(*args, **kwargs)

    @classmethod
    def kaydet(cls, urun, yeni_alis, yeni_satis, neden='diger', aciklama=None,
               kullanici=None, ip_adresi=None, baslangic=None, bitis=None,
               otomatik_geri_al=False):
        """Fiyat değişikliğini kaydet"""

        return cls.objects.create(
            urun=urun,
            eski_alis_fiyati=urun.alis_fiyati,
            yeni_alis_fiyati=yeni_alis,
            eski_satis_fiyati=urun.satis_fiyati,
            yeni_satis_fiyati=yeni_satis,
            neden=neden,
            aciklama=aciklama,
            degistiren=kullanici,
            ip_adresi=ip_adresi,
            gecerlilik_baslangic=baslangic,
            gecerlilik_bitis=bitis,
            otomatik_geri_al=otomatik_geri_al
        )


class FiyatKampanya(models.Model):
    """Toplu fiyat kampanyaları"""

    KAMPANYA_TURU = [
        ('indirim_yuzde', 'Yüzde İndirim'),
        ('indirim_tutar', 'Tutar İndirim'),
        ('zam_yuzde', 'Yüzde Zam'),
        ('sabit_fiyat', 'Sabit Fiyat'),
    ]

    DURUM = [
        ('taslak', 'Taslak'),
        ('beklemede', 'Beklemede'),
        ('aktif', 'Aktif'),
        ('tamamlandi', 'Tamamlandı'),
        ('iptal', 'İptal Edildi'),
    ]

    # Kampanya bilgileri
    ad = models.CharField(
        max_length=200,
        verbose_name="Kampanya Adı"
    )
    aciklama = models.TextField(
        blank=True,
        null=True,
        verbose_name="Açıklama"
    )

    # Kampanya türü ve değeri
    kampanya_turu = models.CharField(
        max_length=20,
        choices=KAMPANYA_TURU,
        default='indirim_yuzde',
        verbose_name="Kampanya Türü"
    )
    deger = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name="Değer",
        help_text="İndirim/Zam yüzdesi veya tutarı"
    )

    # Tarih aralığı
    baslangic_tarihi = models.DateTimeField(
        verbose_name="Başlangıç Tarihi"
    )
    bitis_tarihi = models.DateTimeField(
        verbose_name="Bitiş Tarihi"
    )

    # Hedef ürünler (filtreler)
    kategoriler = models.ManyToManyField(
        'UrunKategoriUst',
        blank=True,
        verbose_name="Kategoriler"
    )
    markalar = models.ManyToManyField(
        'Marka',
        blank=True,
        verbose_name="Markalar"
    )
    urunler = models.ManyToManyField(
        'Urun',
        blank=True,
        verbose_name="Belirli Ürünler"
    )
    cinsiyet = models.CharField(
        max_length=10,
        blank=True,
        null=True,
        choices=[('kadin', 'Kadın'), ('erkek', 'Erkek')],
        verbose_name="Cinsiyet Filtresi"
    )

    # Minimum/Maksimum fiyat filtresi
    min_fiyat = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Minimum Fiyat"
    )
    max_fiyat = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Maksimum Fiyat"
    )

    # Durum
    durum = models.CharField(
        max_length=20,
        choices=DURUM,
        default='taslak',
        verbose_name="Durum"
    )

    # Otomatik geri alma
    otomatik_geri_al = models.BooleanField(
        default=True,
        verbose_name="Otomatik Geri Al",
        help_text="Kampanya bitiminde eski fiyatlara dön"
    )
    geri_alindi = models.BooleanField(
        default=False,
        verbose_name="Geri Alındı"
    )

    # İstatistikler
    etkilenen_urun_sayisi = models.PositiveIntegerField(
        default=0,
        verbose_name="Etkilenen Ürün Sayısı"
    )

    # Oluşturan
    olusturan = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        verbose_name="Oluşturan"
    )
    olusturma_tarihi = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Oluşturma Tarihi"
    )
    guncelleme_tarihi = models.DateTimeField(
        auto_now=True,
        verbose_name="Güncelleme Tarihi"
    )

    class Meta:
        verbose_name = "Fiyat Kampanyası"
        verbose_name_plural = "Fiyat Kampanyaları"
        ordering = ['-baslangic_tarihi']

    def __str__(self):
        return f"{self.ad} ({self.get_durum_display()})"

    @property
    def aktif_mi(self):
        """Kampanya şu an aktif mi?"""
        simdi = timezone.now()
        return (self.durum == 'aktif' and
                self.baslangic_tarihi <= simdi <= self.bitis_tarihi)

    @property
    def bitti_mi(self):
        """Kampanya bitti mi?"""
        return timezone.now() > self.bitis_tarihi

    def hedef_urunleri_getir(self):
        """Kampanya hedefindeki ürünleri getir"""
        from .models import Urun

        # Başlangıç queryset
        urunler = Urun.objects.filter(aktif=True)

        # Belirli ürünler seçilmişse
        if self.urunler.exists():
            return self.urunler.filter(aktif=True)

        # Kategori filtresi
        if self.kategoriler.exists():
            urunler = urunler.filter(kategori__in=self.kategoriler.all())

        # Marka filtresi
        if self.markalar.exists():
            urunler = urunler.filter(marka__in=self.markalar.all())

        # Cinsiyet filtresi
        if self.cinsiyet:
            urunler = urunler.filter(cinsiyet=self.cinsiyet)

        # Fiyat aralığı
        if self.min_fiyat:
            urunler = urunler.filter(satis_fiyati__gte=self.min_fiyat)
        if self.max_fiyat:
            urunler = urunler.filter(satis_fiyati__lte=self.max_fiyat)

        return urunler

    def yeni_fiyat_hesapla(self, eski_fiyat):
        """Kampanyaya göre yeni fiyat hesapla"""
        if self.kampanya_turu == 'indirim_yuzde':
            # Yüzde indirim
            return eski_fiyat * (1 - (self.deger / 100))

        elif self.kampanya_turu == 'indirim_tutar':
            # Tutar indirim
            yeni = eski_fiyat - self.deger
            return max(yeni, Decimal('0.01'))  # Minimum 0.01 TL

        elif self.kampanya_turu == 'zam_yuzde':
            # Yüzde zam
            return eski_fiyat * (1 + (self.deger / 100))

        elif self.kampanya_turu == 'sabit_fiyat':
            # Sabit fiyat
            return self.deger

        return eski_fiyat

    def uygula(self, kullanici=None):
        """Kampanyayı uygula"""
        from .models import Urun

        if self.durum == 'aktif':
            return False, "Kampanya zaten aktif!"

        # Hedef ürünleri al
        urunler = self.hedef_urunleri_getir()
        basarili = 0

        for urun in urunler:
            try:
                # Yeni fiyat hesapla
                yeni_satis = self.yeni_fiyat_hesapla(urun.satis_fiyati)

                # Fiyat geçmişine kaydet
                FiyatGecmisi.kaydet(
                    urun=urun,
                    yeni_alis=urun.alis_fiyati,  # Alış fiyatı değişmiyor
                    yeni_satis=yeni_satis,
                    neden='kampanya',
                    aciklama=f"Kampanya: {self.ad}",
                    kullanici=kullanici,
                    baslangic=self.baslangic_tarihi,
                    bitis=self.bitis_tarihi,
                    otomatik_geri_al=self.otomatik_geri_al
                )

                # Ürün fiyatını güncelle
                urun.satis_fiyati = yeni_satis
                urun.save()

                basarili += 1

            except Exception as e:
                print(f"Hata ({urun.id}): {str(e)}")
                continue

        # Kampanya durumunu güncelle
        self.durum = 'aktif'
        self.etkilenen_urun_sayisi = basarili
        self.save()

        return True, f"{basarili} ürün güncellendi"

    def geri_al(self, kullanici=None):
        """Kampanyayı geri al (eski fiyatlara dön)"""
        if self.geri_alindi:
            return False, "Kampanya zaten geri alınmış!"

        # Bu kampanya ile değiştirilen fiyat geçmişlerini bul
        gecmisler = FiyatGecmisi.objects.filter(
            aciklama__contains=f"Kampanya: {self.ad}",
            geri_alindi=False
        )

        basarili = 0
        for gecmis in gecmisler:
            try:
                urun = gecmis.urun

                # Eski fiyata geri dön
                FiyatGecmisi.kaydet(
                    urun=urun,
                    yeni_alis=urun.alis_fiyati,
                    yeni_satis=gecmis.eski_satis_fiyati,
                    neden='diger',
                    aciklama=f"Kampanya geri alındı: {self.ad}",
                    kullanici=kullanici
                )

                # Ürün fiyatını güncelle
                urun.satis_fiyati = gecmis.eski_satis_fiyati
                urun.save()

                # Geçmiş kaydını işaretle
                gecmis.geri_alindi = True
                gecmis.save()

                basarili += 1

            except Exception as e:
                print(f"Hata ({gecmis.id}): {str(e)}")
                continue

        # Kampanya durumunu güncelle
        self.geri_alindi = True
        self.durum = 'tamamlandi'
        self.save()

        return True, f"{basarili} ürün eski fiyatına döndürüldü"


class FiyatUyari(models.Model):
    """Fiyat değişiklik uyarıları"""

    UYARI_TURU = [
        ('buyuk_artis', 'Büyük Fiyat Artışı'),
        ('buyuk_dusus', 'Büyük Fiyat Düşüşü'),
        ('minimum_altinda', 'Minimum Fiyatın Altında'),
        ('maksimum_ustunde', 'Maksimum Fiyatın Üstünde'),
        ('kar_marji_dusuk', 'Kar Marjı Çok Düşük'),
    ]

    urun = models.ForeignKey(
        'Urun',
        on_delete=models.CASCADE,
        related_name='fiyat_uyarilari',
        verbose_name="Ürün"
    )
    uyari_turu = models.CharField(
        max_length=20,
        choices=UYARI_TURU,
        verbose_name="Uyarı Türü"
    )
    mesaj = models.TextField(verbose_name="Mesaj")
    okundu = models.BooleanField(default=False, verbose_name="Okundu")
    olusturma_tarihi = models.DateTimeField(auto_now_add=True)

    fiyat_gecmisi = models.ForeignKey(
        FiyatGecmisi,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="İlgili Fiyat Değişikliği"
    )

    class Meta:
        verbose_name = "Fiyat Uyarısı"
        verbose_name_plural = "Fiyat Uyarıları"
        ordering = ['-olusturma_tarihi']

    def __str__(self):
        return f"{self.urun.ad} - {self.get_uyari_turu_display()}"

