"""
Hediye çeki satış entegrasyonu için test scripti
"""
import os
import sys
import django
from datetime import timedelta

# Django setup
sys.path.insert(0, '/var/www/nuviabutik')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'stoktakip.settings')
django.setup()

from decimal import Decimal
from django.utils import timezone
from django.contrib.auth.models import User
from hediye.models import HediyeCeki, HediyeCekiKullanim
from satis.models import Satis, Odeme
from satis.services.checkout import complete_checkout, parse_request_payload
from satis.services.exceptions import CheckoutError
from musteri.models import Musteri
from urun.models import Urun, UrunVaryanti

def setup_test_environment():
    """Test ortamını kur"""
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
    
    # Test ürünü oluştur veya al
    urun, created = Urun.objects.get_or_create(
        barkod='TEST0001',
        defaults={
            'ad': 'Test Ürünü',
            'pesin_fiyat': Decimal('100.00'),
            'aktif': True
        }
    )
    
    # Stok ekle
    if not urun.toplam_stok > 0:
        # Varyant oluştur
        varyant, _ = UrunVaryanti.objects.get_or_create(
            urun=urun,
            varyasyon_adi='Standart',
            defaults={
                'stok_miktari': 100,
                'aktif': True
            }
        )
    
    return user, musteri, urun

def test_karma_odeme_hediye_ceki():
    """Karma ödeme ile hediye çeki kullanımını test et"""
    print("=" * 60)
    print("Hediye Çeki Satış Entegrasyon Testi")
    print("=" * 60)
    
    # Test ortamını kur
    user, musteri, urun = setup_test_environment()
    
    # Test hediye çeki oluştur
    test_kod = f"TEST{timezone.now().strftime('%Y%m%d%H%M%S')}"
    hediye_ceki = HediyeCeki.objects.create(
        kod=test_kod,
        tutar=Decimal('150.00'),
        kalan_tutar=Decimal('150.00'),
        gecerlilik_tarihi=timezone.now().date() + timezone.timedelta(days=30),
        durum='aktif',
        aktif=True,
        musteri=musteri,
        olusturan=user,
        aciklama='Test için oluşturuldu'
    )
    
    print(f"\n🎫 Test hediye çeki oluşturuldu:")
    print(f"   Kod: {hediye_ceki.kod}")
    print(f"   Tutar: {hediye_ceki.tutar} ₺")
    print(f"   Kalan Bakiye: {hediye_ceki.kalan_tutar} ₺")
    
    # Test sepeti oluştur
    sepet_data = [
        {
            'id': urun.id,
            'varyant_id': None,
            'ad': urun.ad,
            'barkod': urun.barkod,
            'fiyat': float(urun.pesin_fiyat),
            'miktar': 1,
            'indirim': 0,
            'toplam': float(urun.pesin_fiyat)
        }
    ]
    
    # Ödeme detayları (karma: hediye çeki + nakit)
    odeme_detaylari = {
        'tip': 'karma',
        'karma_detay': {
            'nakit': 50.00,
            'hediye_ceki': 50.00,  # 50 ₺ hediye çeki kullan
            'kart': 0,
            'havale': 0
        },
        'karma_kart_banka': None,
        'karma_kart_taksit': 1
    }
    
    data = {
        'sepet': sepet_data,
        'musteri_id': musteri.id,
        'odeme_detaylari': odeme_detaylari,
        'hediye_ceki': {
            'kod': hediye_ceki.kod
        },
        'satici_id': user.id,
        'genel_indirim': 0
    }
    
    print(f"\n🛒 Test sepeti:")
    print(f"   Ürün: {urun.ad} (1 adet)")
    print(f"   Fiyat: {urun.pesin_fiyat} ₺")
    print(f"   Toplam: 100.00 ₺")
    
    print(f"\n💰 Ödeme detayları:")
    print(f"   Hediye Çeki: 50.00 ₺")
    print(f"   Nakit: 50.00 ₺")
    print(f"   Toplam: 100.00 ₺")
    
    # Satışı tamamla
    try:
        result = complete_checkout(
            user=user,
            sepet_data=sepet_data,
            musteri_id=musteri.id,
            odeme_detaylari=odeme_detaylari,
            data=data
        )
        
        print(f"\n✅ Satış başarıyla tamamlandı!")
        print(f"   Satış ID: {result['satis_id']}")
        print(f"   Sipariş No: {result['siparis_no']}")
        print(f"   Toplam Tutar: {result['toplam']} ₺")
        
        # Satışı kontrol et
        satis = Satis.objects.get(id=result['satis_id'])
        odemeler = Odeme.objects.filter(satis=satis)
        
        print(f"\n📋 Ödeme kayıtları:")
        for odeme in odemeler:
            print(f"   {odeme.get_odeme_tipi_display()}: {odeme.tutar} ₺")
            if odeme.odeme_tipi == 'hediye_ceki':
                print(f"      Hediye Çeki Kodu: {odeme.hediye_ceki_kodu}")
        
        # Hediye çeki kontrol et
        hediye_ceki.refresh_from_db()
        print(f"\n🎫 Hediye çeki güncellemesi:")
        print(f"   Önceki Bakiye: 150.00 ₺")
        print(f"   Kullanılan: 50.00 ₺")
        print(f"   Kalan Bakiye: {hediye_ceki.kalan_tutar} ₺")
        print(f"   Durum: {hediye_ceki.get_durum_display()}")
        
        # Kullanım kaydı kontrol et
        kullanimlar = HediyeCekiKullanim.objects.filter(hediye_ceki=hediye_ceki)
        print(f"\n📝 Kullanım kayıtları:")
        for kullanim in kullanimlar:
            print(f"   Tutar: {kullanim.kullanilan_tutar} ₺")
            print(f"   Tarih: {kullanim.kullanim_tarihi}")
            print(f"   Satış ID: {kullanim.satis_id}")
            print(f"   Açıklama: {kullanim.aciklama}")
        
        # Assertions
        assert hediye_ceki.kalan_tutar == Decimal('100.00'), "Bakiye 100 ₺ olmalı"
        assert hediye_ceki.durum == 'aktif', "Durum hala aktif olmalı"
        assert kullanimlar.count() == 1, "1 kullanım kaydı olmalı"
        
        hediye_ceki_odeme = odemeler.filter(odeme_tipi='hediye_ceki').first()
        assert hediye_ceki_odeme is not None, "Hediye çeki ödeme kaydı olmalı"
        assert hediye_ceki_odeme.tutar == Decimal('50.00'), "Ödeme tutarı 50 ₺ olmalı"
        
        print(f"\n" + "=" * 60)
        print("✅ TÜM TESTLER BAŞARILI!")
        print("=" * 60)
        
        return True
        
    except CheckoutError as e:
        print(f"\n❌ Checkout hatası: {e}")
        return False
    except Exception as e:
        print(f"\n❌ Beklenmeyen hata: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    try:
        success = test_karma_odeme_hediye_ceki()
        if success:
            print(f"\n✅ Hediye çeki entegrasyonu başarıyla çalışıyor!")
            sys.exit(0)
        else:
            print(f"\n❌ Test başarısız!")
            sys.exit(1)
    except Exception as e:
        print(f"\n❌ Test başarısız: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)