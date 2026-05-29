"""
Django Signals - Fiyat Değişiklik Takibi
Otomatik fiyat geçmişi kaydı
"""

from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from decimal import Decimal


def get_client_ip(request):
    """Request'ten IP adresini al"""
    if not request:
        return None
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


@receiver(pre_save, sender='urun.Urun')
def urun_fiyat_degisiklik_takip(sender, instance, **kwargs):
    """Ürün kaydedilmeden önce fiyat değişikliğini kontrol et"""

    # Yeni kayıt mı kontrol et
    if instance.pk is None:
        return

    try:
        # Eski kaydı al
        eski_urun = sender.objects.get(pk=instance.pk)

        # Fiyat değişikliği var mı?
        alis_degisti = eski_urun.alis_fiyati != instance.alis_fiyati
        satis_degisti = eski_urun.satis_fiyati != instance.satis_fiyati

        if alis_degisti or satis_degisti:
            # Değişiklik bilgisini instance'a ekle (post_save'de kullanmak için)
            instance._fiyat_degisti = True
            instance._eski_alis = eski_urun.alis_fiyati
            instance._eski_satis = eski_urun.satis_fiyati

            # Kullanıcı bilgisini sakla (eğer varsa)
            if hasattr(instance, '_current_user'):
                instance._degistiren_user = instance._current_user
            if hasattr(instance, '_current_ip'):
                instance._degistiren_ip = instance._current_ip

    except sender.DoesNotExist:
        pass


@receiver(post_save, sender='urun.Urun')
def urun_fiyat_degisiklik_kaydet(sender, instance, created, **kwargs):
    """Ürün kaydedildikten sonra fiyat değişikliğini kaydet"""

    # Yeni kayıt ise geçmiş oluşturma
    if created:
        return

    # Fiyat değişikliği var mı kontrol et
    if not hasattr(instance, '_fiyat_degisti') or not instance._fiyat_degisti:
        return

    # Circular import'u önlemek için burada import
    from .fiyat_models import FiyatGecmisi, FiyatUyari

    try:
        # Kullanıcı bilgisini al
        kullanici = getattr(instance, '_degistiren_user', None)
        ip_adresi = getattr(instance, '_degistiren_ip', None)

        # Fiyat geçmişine kaydet
        gecmis = FiyatGecmisi.kaydet(
            urun=instance,
            yeni_alis=instance.alis_fiyati,
            yeni_satis=instance.satis_fiyati,
            neden='duzeltme',  # Varsayılan
            aciklama="Otomatik kayıt",
            kullanici=kullanici,
            ip_adresi=ip_adresi
        )

        # Uyarı kontrolü
        _fiyat_uyari_kontrol(instance, gecmis)

    except Exception as e:
        print(f"Fiyat geçmişi kaydedilemedi: {str(e)}")

    finally:
        # Temporary attribute'leri temizle
        if hasattr(instance, '_fiyat_degisti'):
            delattr(instance, '_fiyat_degisti')
        if hasattr(instance, '_eski_alis'):
            delattr(instance, '_eski_alis')
        if hasattr(instance, '_eski_satis'):
            delattr(instance, '_eski_satis')
        if hasattr(instance, '_degistiren_user'):
            delattr(instance, '_degistiren_user')
        if hasattr(instance, '_degistiren_ip'):
            delattr(instance, '_degistiren_ip')


def _fiyat_uyari_kontrol(urun, fiyat_gecmisi):
    """Fiyat değişikliği için uyarı oluştur"""
    from .fiyat_models import FiyatUyari

    # Büyük artış uyarısı (%30'dan fazla)
    if fiyat_gecmisi.degisiklik_yuzdesi > 30:
        FiyatUyari.objects.create(
            urun=urun,
            uyari_turu='buyuk_artis',
            mesaj=f"Fiyat %{fiyat_gecmisi.degisiklik_yuzdesi:.1f} arttı! "
                  f"({fiyat_gecmisi.eski_satis_fiyati}₺ → {fiyat_gecmisi.yeni_satis_fiyati}₺)",
            fiyat_gecmisi=fiyat_gecmisi
        )

    # Büyük düşüş uyarısı (%30'dan fazla)
    elif fiyat_gecmisi.degisiklik_yuzdesi < -30:
        FiyatUyari.objects.create(
            urun=urun,
            uyari_turu='buyuk_dusus',
            mesaj=f"Fiyat %{abs(fiyat_gecmisi.degisiklik_yuzdesi):.1f} düştü! "
                  f"({fiyat_gecmisi.eski_satis_fiyati}₺ → {fiyat_gecmisi.yeni_satis_fiyati}₺)",
            fiyat_gecmisi=fiyat_gecmisi
        )

    # Kar marjı düşük (%10'dan az)
    if urun.alis_fiyati > 0:
        kar_marji = ((urun.satis_fiyati - urun.alis_fiyati) /
                     urun.alis_fiyati) * 100
        if kar_marji < 10:
            FiyatUyari.objects.create(
                urun=urun,
                uyari_turu='kar_marji_dusuk',
                mesaj=f"Kar marjı çok düşük: %{kar_marji:.1f}! "
                      f"Alış: {urun.alis_fiyati}₺, Satış: {urun.satis_fiyati}₺",
                fiyat_gecmisi=fiyat_gecmisi
            )

