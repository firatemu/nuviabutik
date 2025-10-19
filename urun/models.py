from django.db import models
from barcode import Code128
from django.contrib.auth.models import User
from barcode.writer import ImageWriter
import io
import base64
from PIL import Image
from datetime import datetime
import os
from django.conf import settings
from decimal import Decimal
from django.core.validators import MinValueValidator, MaxValueValidator
import uuid


class UrunKategoriUst(models.Model):
    """Üst kategori modeli"""
    ad = models.CharField(max_length=100, unique=True, verbose_name="Kategori Adı")
    aciklama = models.TextField(blank=True, null=True, verbose_name="Açıklama")
    aktif = models.BooleanField(default=True, verbose_name="Aktif")
    olusturma_tarihi = models.DateTimeField(auto_now_add=True)
    guncelleme_tarihi = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Üst Kategori"
        verbose_name_plural = "Üst Kategoriler"
        ordering = ['ad']

    def __str__(self):
        return self.ad


class Renk(models.Model):
    """Renk varyasyon modeli"""
    ad = models.CharField(max_length=50, unique=True, verbose_name="Renk Adı")
    kod = models.CharField(max_length=1, unique=True, verbose_name="Renk Kodu (1 harf)")
    hex_kod = models.CharField(max_length=7, blank=True, null=True, verbose_name="Hex Renk Kodu")
    sira = models.PositiveIntegerField(default=1, verbose_name="Sıra")
    aktif = models.BooleanField(default=True, verbose_name="Aktif")
    olusturma_tarihi = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Renk"
        verbose_name_plural = "Renkler"
        ordering = ['sira', 'ad']

    def __str__(self):
        return f"{self.ad} ({self.kod})"


class Beden(models.Model):
    """Beden varyasyon modeli"""
    ad = models.CharField(max_length=20, unique=True, verbose_name="Beden Adı")
    kod = models.CharField(max_length=1, unique=True, verbose_name="Beden Kodu (1 karakter)")
    tip = models.CharField(max_length=20, choices=[
        ('harf', 'Harf (XS, S, M, L, XL, XXL)'),
        ('rakam', 'Rakam (36, 38, 40, 42)')
    ], default='harf', verbose_name="Beden Tipi")
    sira = models.PositiveIntegerField(default=1, verbose_name="Sıra")
    aktif = models.BooleanField(default=True, verbose_name="Aktif")
    olusturma_tarihi = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Beden"
        verbose_name_plural = "Bedenler"
        ordering = ['tip', 'sira', 'ad']

    def __str__(self):
        return f"{self.ad} ({self.kod})"


class Marka(models.Model):
    """Ürün markaları için model"""
    ad = models.CharField(max_length=100, unique=True, verbose_name="Marka Adı")
    aciklama = models.TextField(blank=True, null=True, verbose_name="Açıklama")
    logo = models.ImageField(upload_to='marka_logolari/', blank=True, null=True, verbose_name="Marka Logosu")
    aktif = models.BooleanField(default=True, verbose_name="Aktif")
    olusturma_tarihi = models.DateTimeField(auto_now_add=True)
    guncelleme_tarihi = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Marka"
        verbose_name_plural = "Markalar"
        ordering = ['ad']

    def __str__(self):
        return self.ad


class Urun(models.Model):
    """Ana ürün modeli"""
    CINSIYET_SECENEKLERI = [
        ('kadin', 'Kadın'),
        ('erkek', 'Erkek'),
    ]
    
    BIRIM_SECENEKLERI = [
        ('adet', 'Adet'),
        ('takim', 'Takım'),
        ('cift', 'Çift'),
        ('kg', 'Kilogram'),
        ('gr', 'Gram'),
        ('lt', 'Litre'),
        ('ml', 'Mililitre'),
        ('m', 'Metre'),
        ('cm', 'Santimetre'),
    ]
    
    # Benzersiz ürün kodu
    urun_kodu = models.CharField(max_length=5, unique=True, verbose_name="Ürün Kodu (5 hane)", blank=True, null=True)
    ad = models.CharField(max_length=200, verbose_name="Ürün Adı")
    aciklama = models.TextField(blank=True, null=True, verbose_name="Açıklama")
    kategori = models.ForeignKey(UrunKategoriUst, on_delete=models.CASCADE, verbose_name="Kategori")
    marka = models.ForeignKey(Marka, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Marka")
    cinsiyet = models.CharField(max_length=10, choices=CINSIYET_SECENEKLERI, default='kadin', verbose_name="Cinsiyet")
    birim = models.CharField(max_length=10, choices=BIRIM_SECENEKLERI, default='adet', verbose_name="Birim")
    
    # Varyasyon kontrolü
    varyasyonlu = models.BooleanField(default=False, verbose_name="Varyasyonlu Ürün")
    
    # Temel fiyat bilgileri
    alis_fiyati = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, verbose_name="Alış Fiyatı")
    kar_orani = models.DecimalField(max_digits=5, decimal_places=2, default=50.00, verbose_name="Kar Oranı (%)")
    satis_fiyati = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, verbose_name="Satış Fiyatı")
    
    # Ürün resmi
    resim = models.ImageField(upload_to='urun_resimleri/', blank=True, null=True, verbose_name="Ana Ürün Resmi")
    
    # Durum bilgisi
    aktif = models.BooleanField(default=True, verbose_name="Aktif")
    stok_takibi = models.BooleanField(default=True, verbose_name="Stok Takibi Yapılsın")
    kritik_stok_seviyesi = models.PositiveIntegerField(default=5, verbose_name="Kritik Stok Seviyesi")
    
    # Tarih bilgileri
    olusturma_tarihi = models.DateTimeField(auto_now_add=True)
    guncelleme_tarihi = models.DateTimeField(auto_now=True)
    olusturan = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Oluşturan")

    class Meta:
        verbose_name = "Ürün"
        verbose_name_plural = "Ürünler"
        ordering = ['-olusturma_tarihi']
        indexes = [
            models.Index(fields=['aktif', 'kategori']),
            models.Index(fields=['marka', 'aktif']),
            models.Index(fields=['cinsiyet', 'aktif']),
            models.Index(fields=['urun_kodu']),
            models.Index(fields=['ad']),
            models.Index(fields=['-olusturma_tarihi']),
        ]

    def save(self, *args, **kwargs):
        # Ürün kodu otomatik oluştur
        if not self.urun_kodu:
            # Son ürün kodunu bul ve 1 artır
            son_urun = Urun.objects.filter(urun_kodu__isnull=False).order_by('-urun_kodu').first()
            if son_urun and son_urun.urun_kodu.isdigit():
                yeni_kod = str(int(son_urun.urun_kodu) + 1).zfill(5)
            else:
                yeni_kod = '00001'
            self.urun_kodu = yeni_kod
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.urun_kodu} - {self.ad}"

    @property
    def toplam_stok(self):
        """Toplam stok miktarını hesapla"""
        if self.varyasyonlu:
            return sum(v.stok_miktari for v in self.varyantlar.filter(aktif=True))
        else:
            varyant = self.varyantlar.first()
            return varyant.stok_miktari if varyant else 0

    @property
    def ozellik_kodu(self):
        """Barkod için özellik kodunu oluştur"""
        if not self.varyasyonlu:
            return "00"  # Varyasyonsuz ürün
        
        # Varyantları kontrol et
        varyant = self.varyantlar.first()
        if not varyant:
            return "00"
        
        renk_var = varyant.renk is not None
        beden_var = varyant.beden is not None
        
        if renk_var and beden_var:
            return "03"  # Renk + Beden
        elif renk_var:
            return "01"  # Sadece renk
        elif beden_var:
            return "02"  # Sadece beden
        else:
            return "00"  # Varyasyonsuz



# PRN Etiket Template
PRN_TEMPLATE = """SIZE 56 mm, 40 mm
GAP 3 mm, 0 mm
SET RIBBON OFF
DIRECTION 0,0
REFERENCE 0,0
OFFSET 0 mm
SET PEEL OFF
SET CUTTER OFF
SET TEAR ON
CLS
BITMAP 162,34,15,56,1,ÿÿÿÿÿÿÿÿÿÿÿÿÿüÿÿÿÿÿÿÿÿÿÿÿÿÿüÿÿÿÿÿÿÿÿÿÿÿÿÿüÿÿÿÿÿÿÿÿÿÿÿÿÿüÿÿÿÿÿÿÿÿÿÿÿÿÿüÿÿÿÿÿÿÿÿÿÿÿÿÿüÿÿÿÿÿÿÿÿÿÿÿÿÿüÿÿÿÿÿÿÿÿÿÿÿÿÿüÿÿÿÿÿÿÿÿÿÿÿÿÿüÿÿÿÿÿÿÿÿÿÿÿÿÿüÿüÿÿ€üÿ€ÿğ<ÿà ÿş üÿ€ÿÀÿÀ ?ü üÿ€ÿ€ÿ€ ø üÿ€ÿ  ÿ  ğ üÿ€ş  ÿ ğàüÿ€şàşøà? üÿ€üğÿÃüÀ?€üÿ€üøÿÿüÀ€üÿ€üøÿÿşøÀ|ÿ€øüÿÿşÿÿÀ|ÿ€øüÿÿşÿÿÀ|ÿ€øüş  ÿÿÀ|ÿ€øüş  ÿÿÀ|ÿ€øüş  ÿÿÀ|ÿ€øüş  ÿÿÀ|ÿ€øüşşÿÿÀ|ÿ øüşşÿÿÀ|ÿ øüÿşø€üş üøÿüÀ€üü üøÿüà? ü  üğÿ€pàü  şàÿ€ ğ ü  ş  ÿÀ ğ ü @ÿ ÿà ?ø ü Àÿ€ÿø ÿş üÀÿÀÿşÿÿ€ÿÿƒÿÿğ?ÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿüÿÿÿÿÿÿÿÿÿÿÿÿÿüÿÿÿÿÿÿÿÿÿÿÿÿÿüÿÿÿÿÿÿÿÿÿÿÿÿÿüÿÿÿÿÿÿÿÿÿÿÿÿÿüÿÿÿÿÿÿÿÿÿÿÿÿÿüÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿ
BITMAP 170,98,17,40,1,ÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿ€Ãƒÿà?şÿÁàğàáş Â ÿ€øÿÁğÀ?€!ü À  ğ Áğ  ø À > à Áğ  şÀp<Àğ?ÁğÿÿÀø<ÁÀø?Áğ~ÿÿƒÁüÀñüÁğ~ÁÿÿƒÁü?àÿüÁğ|Áø Áü?àÿüÁğ`Áø Áü?àÿüÁğ <Áø Áü?àÿüÁğüÁø?ƒÁü?àÿüÁğüÁø?ƒÁüÀñüğüÁüÀøÁÁø?ğ~|üÀp<àğ8ğ<ş À > à xğ > ş À  ğ xø ? ÿ€?Á ÿ€øğ!ü €AÿÀÁƒÿà?şøaşÿàÁÿÿÿÁÿÿÿÿÿÿÿÿÿÿÿÿÁÿÿÿÁÿÿÿÿÿÿÿÿÿÿÿÿÁÿÿÿÁÿÿÿÿÿÿÿÿÿÿÿÿÁÿÿÿÁÿÿÿÿÿÿÿÿÿÿÿÿÁÿÿÿÁÿÿÿÿÿÿÿÿÿÿÿÿÁÿÿÿÁÿÿÿÿÿÿÿÿÿÿÿÿÁÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿ
BITMAP 18,250,50,48,1,ÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿŸÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿ‡ÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿ ?ÿ ğÿÿÿÿÿÿÿÿ€ÿÿøÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿàÿÿÿÿÿ   ?ü ş   ÿüÿà?ÿş ÿÿÀ ÿø  ÿàÿğÿğÿÿ€ ÿğÿ   ?ğ ÿ   ?üÿà?ÿø  ÿÿ  ÿà  ÿğÿğÿğÿş  ?ğÿ   ?à  ÿÀ  üÿà?ÿğ  ş  ÿ€  ÿğÿğÿàÿü  ğÿ   ?À  ğ  üÿà?ÿà  ?ü  ÿ   ÿğÿàÿàÿø  ğÿ   ?€  ğ  üÿà?ÿÀ  ?ø  ş   ÿøÿà>ÿàÿğ  ğÿ   ?€? ?àğüÿà?ÿÀ€ğøş   ÿøÿà>ÿÀÿğàğÿÿÿà?€À?à üüÿà?ÿÀ?ààş şÿğÿøÿÀ>ÿÀÿğøğÿÿÿà? ÿà?À >üÿà?ÿ€ğàÿ üÿğÿüÿÀ~ÿÀÿàüğÿÿÿà?ÿà€` üÿà?ÿ€ÿğÀ?ÿ€|ÿğÿü   ~ÿ€€ÿà?üğ ÿÿÿà?ÿğ€x üÿà?ÿ€ÿøÀ?ÿ€|ÿğÿü   ~ÿ€€ÿà?şğ ÿÿà?ÿğ€şÿ€üÿà?ÿ€ÿøÀÿÀ|ÿğÿş   şÿÀÿà?şğ ÿÿà?ÿğ€ÿÿ€üÿà?ÿ€ÿøÀÿÀ|ÿğÿş   şÿÀà?şğ ?ÿÿà?ÿğÿÿÀ|ÿà?ÿ€ÿø€ÿÿà>ÿğÿş   şÿÀà?şğ0?ÿÿà?ÿğÿÿÀ|ÿà?ÿ€ÿø€ÿÿà> ÿğÿÿ  şÿÀà?şğ0ÿÿà?ÿğÿÿÀ|ÿà?ÿ€ÿø€ÿÿà?   ÿÿÿşşà?à?şğ8À  ?ÿğÿÿÀ|ÿà?ÿ€ÿø€ÿÿà?€  ÿÿÿşşà?à?şğ8À  ?ÿğÿÿÀ|ÿà?ÿ€ÿø€ÿÿà?À  ÿÿ€şşşà?à?şğ<À  ?ÿğÿÿÀ|ÿà?ÿ€ÿø€ÿÿà?ğ  ÿÿ€şşüğà?şğ<À  ?ÿğÿÿÀ|ÿà?ÿ€ÿø€ÿÿà?À  ÿÿÀşşüğà?şğ>À  ?ÿğÿÿÀ|ÿà?ÿ€ÿø€ÿÿà?€  ÿÿÀ|şüğà?şğ?À  ?ÿğÿÿÀ|ÿà?ÿ€ÿø€ÿÿà? ÿğÿÿÀ|şøøà?şğ?ÿÿà?ÿğÿÿÀ|ÿà?ÿ€ÿø€ÿÿà?ÿğÿÿà|şøøà?şğ?€ÿÿà?ÿğ€ÿÿ€üÿà?ÿ€ÿøÀÿÀ~ÿğÿÿà8şøøà?şğ?€ÿÿà?ÿğ€ÿÿ€üÿà?ÿ€ÿøÀÿÀ~ÿğÿÿà8şğøà?şğ?Àÿÿà?ÿğ€ÿ üÿà?ÿ€ÿøÀ?ÿ€~ÿğÿÿğ8şğüà?şğ?àÿÿà?ÿğ€ÿ üÿà?ÿ€ÿøÀ?ÿ€~ÿğÿÿğşğüà?şğ?àÿÿà?ÿğÀ?şüÿà?ÿ€ÿøàÿ şÿğÿÿğşàüà?şğ?ğÿÿà?ÿğÀüüÿà?ÿ€ÿøàş ş ÿğÿÿø?şà?şà?şğ?ğ€  ?ÿğàğü€  €ÿøğøÿ   ÿÿø ?şà?şà?şğ?ø€  ?ÿğğ  ü€  €ÿøø  ÿ   ÿÿø ?şÀ?şà?şğ?ü€  ?ÿğø  ü€  €ÿøü  ÿ€  ÿÿü şÀÿà?şğ?ü€  ?ÿğü  ü€  €ÿøş  ÿÀ  ÿÿü şÀÿà?şğ?ş€  ?ÿğş  ?ü€  €ÿøÿ  ÿà  ÿÿş ş€ÿ à?şğ?ş€  ?ÿğÿ€ ÿü€  €ÿøÿÀ ÿü  ÿÿş ÿş€ÿÿ€à?şğ?ÿÿÿÿÿÿÿÿÿÿğÿÿÿÿÿÿÿÿÿÿÿÿøÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿÿ
CODEPAGE 1254
TEXT 410,245,"ARIALR.TTF",180,9,9,"{product_name}"
TEXT 287,25,"ARIALR.TTF",180,6,6,"Fiyat Güncelleme Tarih:"
TEXT 350,75,"ARIALR.TTF",180,8,8,"{price} TL"
BARCODE 408,214,"128M",79,0,180,3,6,"{barcode}"
TEXT 109,25,"ARIALR.TTF",180,6,6,"{date}"
PRINT 1,1"""


class UrunVaryanti(models.Model):
    """Ürün varyantları - her renk/beden kombinasyonu için ayrı kayıt"""
    urun = models.ForeignKey(Urun, on_delete=models.CASCADE, related_name='varyantlar', verbose_name="Ürün")
    renk = models.ForeignKey(Renk, on_delete=models.CASCADE, null=True, blank=True, verbose_name="Renk")
    beden = models.ForeignKey(Beden, on_delete=models.CASCADE, null=True, blank=True, verbose_name="Beden")
    
    # Barkod - otomatik oluşturulacak
    barkod = models.CharField(max_length=20, unique=True, verbose_name="Barkod", blank=True)
    
    # Stok bilgisi
    stok_miktari = models.PositiveIntegerField(default=1, verbose_name="Stok Miktarı")
    def ilk_stok_ayarla(self, miktar, kullanici, aciklama="İlk stok girişi"):
        """
        Sadece yeni oluşturulan varyantlar için stok ayarlama
        Bu metod sadece stok_kaydedildi=False olan varyantlarda çalışır
        """
        if self.stok_kaydedildi:
            raise ValueError("Bu ürünün stoğu zaten kaydedilmiş. Artık sadece Stok Hareket sistemi kullanılabilir!")
        
        # Stok miktarını ayarla
        self.stok_miktari = miktar
        
        # İlk stok hareketini kaydet
        from .models import StokHareket  # Circular import'u önlemek için burada import
        StokHareket.stok_hareketi_olustur(
            varyant=self,
            hareket_tipi='giris',
            miktar=miktar,
            kullanici=kullanici,
            aciklama=aciklama
        )
        
        # Stok kaydedildi olarak işaretle
        self.stok_kaydedildi = True
        self.save(ilk_kayit=True)
        
        return True
    def set_current_user(self, user, ip_address=None):
        """Stok loglama için kullanıcı bilgisi set et"""
        self._current_user = user
        self._current_ip = ip_address

    @property
    def stok_loglari_ozet(self):
        """Son 10 stok değişiklik logu"""
        return self.stok_loglari.all()[:10]

    def stok_gecmisi(self, limit=50):
        """Stok değişiklik geçmişi"""
        return self.stok_loglari.all()[:limit]


    def stok_degistirilebilir_mi(self):
        """Stoğun değiştirilebilir olup olmadığını kontrol et"""
        return not self.stok_kaydedildi

    @property 
    def stok_durumu(self):
        """Stok durumu bilgisi"""
        if not self.stok_kaydedildi:
            return "Stok henüz kaydedilmedi - Düzenlenebilir"
        else:
            return "Stok kaydedildi - Sadece Stok Hareket sistemi ile değiştirilebilir"

    stok_kaydedildi = models.BooleanField(default=False, verbose_name="Stok Kaydedildi Mi?")
    
    # Ek bilgiler
    ek_aciklama = models.TextField(blank=True, null=True, verbose_name="Ek Açıklama")
    resim = models.ImageField(upload_to='varyant_resimleri/', blank=True, null=True, verbose_name="Varyant Resmi")
    
    # Durum
    aktif = models.BooleanField(default=True, verbose_name="Aktif")
    olusturma_tarihi = models.DateTimeField(auto_now_add=True)
    guncelleme_tarihi = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Ürün Varyantı"
        verbose_name_plural = "Ürün Varyantları"
        ordering = ['urun', 'renk', 'beden']
        unique_together = ['urun', 'renk', 'beden']
        indexes = [
            models.Index(fields=['urun', 'aktif']),
            models.Index(fields=['stok_miktari']),
            models.Index(fields=['barkod']),
            models.Index(fields=['urun', 'renk', 'beden']),
        ]

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        # stok_hareket_guncelleme parametresini önce çıkar
        stok_hareket_guncelleme = kwargs.pop('stok_hareket_guncelleme', False)
        ilk_kayit = kwargs.pop('ilk_kayit', False)

        # Yeni kayıt mı kontrol et
        # Eski stok miktarını tanımla
        old_stock = None
        if not is_new:
            try:
                original = UrunVaryanti.objects.get(pk=self.pk)
                old_stock = original.stok_miktari
            except UrunVaryanti.DoesNotExist:
                old_stock = None

        # Stok değişiklik kontrolü (sadece stok hareket sistemi dışındaki değişiklikler için)
        if not stok_hareket_guncelleme and not is_new:
            original = UrunVaryanti.objects.get(pk=self.pk)
            
            # Eğer stok değiştirilmeye çalışılıyorsa ve bu varyant kilitliyse
            if original.stok_miktari != self.stok_miktari and original.stok_kaydedildi:
                self.stok_miktari = original.stok_miktari  # Eski değeri geri yükle
                raise ValueError("Bu varyasyonun stoğu kilitlenmiştir! Sadece Stok Hareket sistemi ile değiştirilebilir.")

        # Barkod otomatik oluştur
        if not self.barkod:
            self.barkod = self.olustur_barkod()
        
        super().save(*args, **kwargs)
        
        # YENİ MANTIK 2: Stok miktarı güncellendiğinde bu varyantı hemen kilitle
        if not stok_hareket_guncelleme:
            # Yeni varyant için: İlk kez stok giriliyorsa kilitle
            if is_new and self.stok_miktari > 0:
                self.stok_kaydedildi = True
            # Mevcut varyant için: Stok değiştirilmişse ve henüz kaydedilmemişse kilitle
            elif not is_new and old_stock is not None and old_stock != self.stok_miktari and not original.stok_kaydedildi:
                self.stok_kaydedildi = True
                UrunVaryanti.objects.filter(pk=self.pk).update(stok_kaydedildi=True)

    def olustur_barkod(self):
        "Code 128 formatında barkod oluştur"
        # 1. Özellik kodu (2 hane)
        ozellik_kodu = self.urun.ozellik_kodu
        # 2. Varyant kodu (2 hane)
        renk_kodu = self.renk.kod if self.renk else "0"
        beden_kodu = self.beden.kod if self.beden else "0"
        varyant_kodu = f"{renk_kodu}{beden_kodu}"
        
        # 3. Ürün numarası (5 hane)
        urun_numarasi = self.urun.urun_kodu
        
        # 4. Fiyat (4 hane)
        fiyat_kodu = str(int(self.urun.satis_fiyati)).zfill(4)
        
        # Barkod birleştir
        # Code 128 için veri hazırla
        code128_data = f"NUV{ozellik_kodu}{varyant_kodu}{urun_numarasi}{fiyat_kodu}"
        
        return code128_data
    def barkod_gorseli_olustur(self, format='PNG'):
        """Code 128 barkod görselini oluştur"""
        try:
            # Barkod verisini al
            barkod_data = self.olustur_barkod()
            
            # Code 128 barkod oluştur
            code128 = Code128(barkod_data, writer=ImageWriter())
            
            # Görsel buffer'ı oluştur
            buffer = io.BytesIO()
            
            # Barkod görselini oluştur
            code128.write(buffer, options={
                'module_width': 0.2,
                'module_height': 15.0,
                'quiet_zone': 6.5,
                'font_size': 10,
                'text_distance': 5.0,
                'background': 'white',
                'foreground': 'black',
            })
            
            # Buffer'ı sıfırla
            buffer.seek(0)
            
            if format.upper() == 'BASE64':
                # Base64 formatında döndür
                image_data = buffer.getvalue()
                base64_data = base64.b64encode(image_data).decode('utf-8')
                return f"data:image/png;base64,{base64_data}"
            else:
                # PIL Image olarak döndür
                image = Image.open(buffer)
                return image
                
        except Exception as e:
            # Barkod görseli oluşturulurken hata meydana geldi
            return None

    def barkod_gorseli_kaydet(self, dosya_yolu):
        """Barkod görselini dosyaya kaydet"""
        try:
            image = self.barkod_gorseli_olustur()
            if image:
                image.save(dosya_yolu)
                return True
            return False
        except Exception as e:
            # Barkod görseli kaydedilirken hata meydana geldi
            return False

    def etiket_olustur(self, custom_date=None):
        """Ürün varyantı için PRN etiket oluştur"""
        try:
            # Tarih
            if custom_date:
                date_str = custom_date
            else:
                date_str = datetime.now().strftime("%d.%m.%Y")
            
            # Ürün adı ve varyasyon
            product_name = f"{self.urun.ad}"
            if self.varyasyon_adi != "Standart":
                product_name += f" {self.varyasyon_adi}"
            
            # Barkod
            barcode = self.olustur_barkod()
            
            # Fiyat
            price = float(self.urun.satis_fiyati)
            
            # PRN içeriği oluştur
            prn_content = PRN_TEMPLATE.format(
                product_name=product_name[:30],  # Etiket boyutu limiti
                barcode=barcode,
                price=f"{price:.2f}",
                date=date_str
            )
            
            return prn_content
            
        except Exception as e:
            # Etiket oluşturulurken hata meydana geldi
            return None

    def etiket_kaydet(self, file_path, custom_date=None):
        """PRN etiket dosyasını kaydet"""
        try:
            prn_content = self.etiket_olustur(custom_date)
            if prn_content:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(prn_content)
                return True
            return False
        except Exception as e:
            # Etiket kaydedilirken hata meydana geldi
            return False

    def toplu_etiket_olustur(self, miktar=1):
        """Aynı üründen birden fazla etiket oluştur"""
        etiketler = []
        for i in range(miktar):
            etiket = self.etiket_olustur()
            if etiket:
                etiketler.append(etiket)
        return etiketler

    @classmethod
    def toplu_etiket_yazdir(cls, varyant_list, output_dir="labels"):
        """Birden fazla varyant için etiket oluştur"""
        os.makedirs(output_dir, exist_ok=True)
        created_files = []
        
        for i, varyant in enumerate(varyant_list, 1):
            # Dosya adını oluştur
            safe_name = "".join(c for c in varyant.urun.ad if c.isalnum() or c in (' ', '-', '_')).strip()
            file_name = f"label_{i:03d}_{safe_name[:20]}.prn"
            file_path = os.path.join(output_dir, file_name)
            
            # Etiket oluştur
            success = varyant.etiket_kaydet(file_path)
            if success:
                created_files.append(file_path)
        
        return created_files


    @property
    def varyasyon_adi(self):
        """Varyasyon adını oluştur"""
        parts = []
        if self.renk:
            parts.append(self.renk.ad)
        if self.beden:
            parts.append(self.beden.ad)
        return " - ".join(parts) if parts else "Standart"

    def __str__(self):
        return f"{self.urun.ad} ({self.varyasyon_adi})"

    @classmethod
    def barkod_cozumle(cls, barkod):
        """Code 128 formatında barkod çözümleme algoritması"""
        # Code 128 formatı: NUV + 13 karakterlik veri
        if not barkod or len(barkod) < 16:
            return None

        try:
            # NUV prefix kontrolü
            if not barkod.startswith('NUV'):
                # Eski format için backward compatibility
                if len(barkod) == 13:
                    return cls._legacy_barkod_cozumle(barkod)
                return None
            
            # NUV prefix'ini çıkar
            veri = barkod[3:]  # NUV'dan sonraki kısım
            
            if len(veri) != 13:
                return None
                
            # Barkodu parçalara ayır
            ozellik_kodu = veri[:2]
            varyant_kodu = veri[2:4]
            urun_numarasi = veri[4:9]
            fiyat_kodu = veri[9:13]
            
            # Renk ve beden kodlarını ayır
            renk_kodu = varyant_kodu[0]
            beden_kodu = varyant_kodu[1]
            
            return {
                'ozellik_kodu': ozellik_kodu,
                'renk_kodu': renk_kodu if renk_kodu != '0' else None,
                'beden_kodu': beden_kodu if beden_kodu != '0' else None,
                'urun_numarasi': urun_numarasi,
                'fiyat_kodu': fiyat_kodu,
                'format': 'code128'
            }
            
        except Exception:
            return None

    @classmethod
    def _legacy_barkod_cozumle(cls, barkod):
        """Eski 13 karakter formatı için backward compatibility"""
        if len(barkod) != 13:
            return None

        try:
            # Barkodu parçalara ayır
            ozellik_kodu = barkod[:2]
            varyant_kodu = barkod[2:4]
            urun_numarasi = barkod[4:9]
            fiyat_kodu = barkod[9:13]
            
            # Renk ve beden kodlarını ayır
            renk_kodu = varyant_kodu[0]
            beden_kodu = varyant_kodu[1]
            
            return {
                'ozellik_kodu': ozellik_kodu,
                'renk_kodu': renk_kodu if renk_kodu != '0' else None,
                'beden_kodu': beden_kodu if beden_kodu != '0' else None,
                'urun_numarasi': urun_numarasi,
                'fiyat_kodu': fiyat_kodu,
                'format': 'legacy'
            }
            
        except Exception:
            return None

    



class StokDegisiklikLog(models.Model):
    """Stok değişiklik logları"""
    
    ISLEM_TIPLERI = [
        ('ilk_kayit', 'İlk Kayıt'),
        ('admin_degisiklik', 'Admin Değişiklik'),
        ('sistem_degisiklik', 'Sistem Değişiklik'),
        ('sistem_kilitleme', 'Sistem Kilitleme (Yeni Varyasyon)'),
        ('stok_hareket', 'Stok Hareket'),
        ('koruma_kaldirma', 'Koruma Kaldırma'),
    ]
    
    varyant = models.ForeignKey('UrunVaryanti', on_delete=models.CASCADE, related_name='stok_loglari')
    islem_tipi = models.CharField(max_length=20, choices=ISLEM_TIPLERI, verbose_name="İşlem Tipi")
    eski_miktar = models.PositiveIntegerField(verbose_name="Eski Miktar")
    yeni_miktar = models.PositiveIntegerField(verbose_name="Yeni Miktar")
    kullanici = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Kullanıcı")
    ip_adresi = models.GenericIPAddressField(null=True, blank=True, verbose_name="IP Adresi")
    aciklama = models.TextField(blank=True, null=True, verbose_name="Açıklama")
    olusturma_tarihi = models.DateTimeField(auto_now_add=True, verbose_name="Oluşturma Tarihi")
    
    class Meta:
        verbose_name = "Stok Değişiklik Logu"
        verbose_name_plural = "Stok Değişiklik Logları"
        ordering = ['-olusturma_tarihi']
    
    def __str__(self):
        return f"{self.varyant} - {self.get_islem_tipi_display()} ({self.eski_miktar}→{self.yeni_miktar})"
    
    def miktar_degisimi(self):
        return self.yeni_miktar - self.eski_miktar
    
    @classmethod
    def log_olustur(cls, varyant, islem_tipi, eski_miktar, yeni_miktar, kullanici=None, ip_adresi=None, aciklama=None):
        """Stok değişiklik logu oluştur"""
        return cls.objects.create(
            varyant=varyant,
            islem_tipi=islem_tipi,
            eski_miktar=eski_miktar,
            yeni_miktar=yeni_miktar,
            kullanici=kullanici,
            ip_adresi=ip_adresi,
            aciklama=aciklama
        )


class StokHareket(models.Model):
    """Stok hareket takip modeli"""
    HAREKET_TIPLERI = [
        ('giris', 'Stok Girişi'),
        ('cikis', 'Stok Çıkışı'),
        ('duzeltme', 'Stok Düzeltmesi'),
        ('sayim_eksik', 'Sayım Eksiği'),
        ('sayim_fazla', 'Sayım Fazlası'),
        ('transfer', 'Transfer'),
        ('fire', 'Fire'),
    ]
    
    varyant = models.ForeignKey('UrunVaryanti', on_delete=models.CASCADE, verbose_name="Ürün Varyantı")
    hareket_tipi = models.CharField(max_length=20, choices=HAREKET_TIPLERI, verbose_name="Hareket Tipi")
    miktar = models.IntegerField(verbose_name="Miktar")
    onceki_stok = models.IntegerField(verbose_name="Önceki Stok")
    yeni_stok = models.IntegerField(verbose_name="Yeni Stok")
    aciklama = models.TextField(blank=True, null=True, verbose_name="Açıklama")
    referans_id = models.CharField(max_length=100, blank=True, null=True, verbose_name="Referans ID")  # Satış ID vs.
    kullanici = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, verbose_name="Kullanıcı")
    olusturma_tarihi = models.DateTimeField(auto_now_add=True, verbose_name="Oluşturma Tarihi")
    
    class Meta:
        verbose_name = "Stok Hareket"
        verbose_name_plural = "Stok Hareketleri"
        ordering = ['-olusturma_tarihi']
    
    def __str__(self):
        return f"{self.varyant} - {self.get_hareket_tipi_display()} ({self.miktar})"
    
    @classmethod
    def stok_hareketi_olustur(cls, varyant, hareket_tipi, miktar, kullanici, aciklama=None, referans_id=None):
        """Stok hareketi oluşturur"""
        onceki_stok = varyant.stok_miktari
        
        if hareket_tipi == 'giris':
            yeni_stok = onceki_stok + miktar
        elif hareket_tipi == 'cikis':
            yeni_stok = onceki_stok - miktar
        elif hareket_tipi == 'sayim_eksik':
            yeni_stok = onceki_stok - miktar
        elif hareket_tipi == 'sayim_fazla':
            yeni_stok = onceki_stok + miktar
        else:
            yeni_stok = miktar  # Düzeltme vb. için direkt miktar
        
        # Stok hareketini kaydet
        hareket = cls.objects.create(
            varyant=varyant,
            hareket_tipi=hareket_tipi,
            miktar=miktar,
            onceki_stok=onceki_stok,
            yeni_stok=yeni_stok,
            aciklama=aciklama,
            referans_id=referans_id,
            kullanici=kullanici
        )
        
        # Varyantın stok miktarını güncelle (güvenli güncelleme)
        varyant.stok_miktari = yeni_stok
        varyant.save(stok_hareket_guncelleme=True)
        
        return hareket
