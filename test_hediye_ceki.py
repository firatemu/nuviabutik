#!/usr/bin/env python
"""Test script for hediye çeki functionality"""
import os
import sys
import django

# Add project to path
sys.path.insert(0, '/var/www/nuviabutik')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'stoktakip.settings')
django.setup()

from decimal import Decimal
from django.utils import timezone
from django.contrib.auth.models import User
from hediye.models import HediyeCeki, HediyeCekiKullanim
from satis.models import Satis, Odeme
from musteri.models import Musteri

def test_hediye_ceki_kullanimi():
    """Hediye çeki kullanımını test et"""
    print("=" * 50)
    print("Hediye Çeki Kullanım Testi")
    print("=" * 50)

    # Test kullanıcısı oluştur veya al
    user, created = User.objects.get_or_create(
        username='test_user',
        defaults={
            'first_name': 'Test',
            'last_name': 'User',
            'is_active': True
        }
    )
    
    # Test müşterisi oluştur veya al
    musteri, created = Musteri.objects.get_or_create(
        ad='Test',
        soyad='Müşteri',
        defaults={
            'telefon': '5551234567',
            'aktif': True
        }
    )

    # Test hediye çeki oluştur
    test_kod = f"TEST{timezone.now().strftime('%Y%m%d%H%M%S')}"
    hediye_ceki = HediyeCeki.objects.create(
        kod=test_kod,
        tutar=Decimal('100.00'),
        kalan_tutar=Decimal('100.00'),
        gecerlilik_tarihi=timezone.now().date() + timezone.timedelta(days=30),
        durum='aktif',
        aktif=True,
        musteri=musteri,
        olusturan=user,
        aciklama='Test için oluşturuldu'
    )

    print(f"\n✅ Test hediye çeki oluşturuldu:")
    print(f"   Kod: {hediye_ceki.kod}")
    print(f"   Tutar: {hediye_ceki.tutar} ₺")
    print(f"   Kalan Bakiye: {hediye_ceki.kalan_tutar} ₺")
    print(f"   Durum: {hediye_ceki.get_durum_display()}")
    print(f"   Kullanılabilir: {hediye_ceki.kullanilabilir_mi}")

    # Kullanılabilirlik kontrolü
    assert hediye_ceki.kullanilabilir_mi == True, "Hediye çeki kullanılabilir olmalı"
    assert hediye_ceki.kalan_tutar == Decimal('100.00'), "Bakiye 100 ₺ olmalı"

    # Kısmi kullanım testi (50 ₺)
    print(f"\n🔄 50 ₺ kısmi kullanım testi...")
    kalan_bakiye = hediye_ceki.kullan(Decimal('50.00'))
    hediye_ceki.refresh_from_db()

    print(f"   Kullanılan: 50.00 ₺")
    print(f"   Kalan Bakiye: {hediye_ceki.kalan_tutar} ₺")
    print(f"   Durum: {hediye_ceki.get_durum_display()}")

    assert hediye_ceki.kalan_tutar == Decimal('50.00'), "Bakiye 50 ₺ olmalı"
    assert hediye_ceki.durum == 'aktif', "Durum hala aktif olmalı"

    # Kullanım kaydı kontrolü
    kullanim_sayisi = HediyeCekiKullanim.objects.filter(hediye_ceki=hediye_ceki).count()
    assert kullanim_sayisi == 1, "1 kullanım kaydı olmalı"
    print(f"   Kullanım kayıtları: {kullanim_sayisi}")

    # Kalan bakiyenin tam kullanımı
    print(f"\n🔄 Kalan 50 ₺ tam kullanım testi...")
    kalan_bakiye = hediye_ceki.kullan(Decimal('50.00'))
    hediye_ceki.refresh_from_db()

    print(f"   Kullanılan: 50.00 ₺")
    print(f"   Kalan Bakiye: {hediye_ceki.kalan_tutar} ₺")
    print(f"   Durum: {hediye_ceki.get_durum_display()}")

    assert hediye_ceki.kalan_tutar == Decimal('0.00'), "Bakiye 0 ₺ olmalı"
    assert hediye_ceki.durum == 'kullanilmis', "Durum kullanılmış olmalı"

    # Toplam kullanım kaydı kontrolü
    kullanim_sayisi = HediyeCekiKullanim.objects.filter(hediye_ceki=hediye_ceki).count()
    assert kullanim_sayisi == 2, "2 kullanım kaydı olmalı"
    print(f"   Toplam kullanım kayıtları: {kullanim_sayisi}")

    # Bakiye yetersizlik testi
    print(f"\n🧪 Bakiye yetersizlik testi...")
    try:
        hediye_ceki.kullan(Decimal('1.00'))
        print("   ❌ Hata: ValueError fırlatmalıydı")
        assert False, "Hata fırlatmalıydı"
    except ValueError as e:
        print(f"   ✅ Doğru şekilde hata fırlatıldı: {e}")

    print(f"\n" + "=" * 50)
    print("✅ TÜM TESTLER BAŞARILI!")
    print("=" * 50)

    # Test sonuçlarını göster
    print(f"\n📊 Test Sonuçları:")
    print(f"   Hediye Çeki Kodu: {hediye_ceki.kod}")
    print(f"   Orijinal Tutar: 100.00 ₺")
    print(f"   Toplam Kullanılan: 100.00 ₺")
    print(f"   Kalan Bakiye: {hediye_ceki.kalan_tutar} ₺")
    print(f"   Kullanım Durumu: {hediye_ceki.get_durum_display()}")
    print(f"   Kullanım Kayıtları: {kullanim_sayisi} adet")

    return hediye_ceki

if __name__ == '__main__':
    try:
        test_hediye_ceki = test_hediye_ceki_kullanimi()
        print(f"\n✅ Test başarılı! Test hediye çeki: {test_hediye_ceki.kod}")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Test başarısız: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)