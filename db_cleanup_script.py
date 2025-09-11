#!/usr/bin/env python
"""
Veritabanı Temizlik Scripti
Kullanıcılar, Beden, Renkler, Kasalar, Gider Kategorileri dışında tüm verileri temizler
"""

import os
import sys
import django

# Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'stoktakip.settings')
django.setup()

from django.db import transaction
from kullanici.models import CustomUser
from urun.models import UrunVaryanti, Urun, UrunKategoriUst, Marka, Beden, Renk
from satis.models import Satis, SatisDetay, Odeme
from musteri.models import Musteri, Tahsilat, TahsilatDetay, BorcAlacakHareket
from kasa.models import Kasa, KasaHareket
from gider.models import Gider, GiderKategori
from hediye.models import HediyeCeki
from log.models import AktiviteLog

def confirm_deletion():
    """Kullanıcıdan onay al"""
    print("\n" + "="*60)
    print("🚨 VERİTABANI TEMİZLİK İŞLEMİ")
    print("="*60)
    print("\nAşağıdaki veriler SİLİNECEK:")
    print("❌ Tüm ürünler ve varyantlar")
    print("❌ Tüm satışlar ve ödemeler") 
    print("❌ Tüm müşteriler ve tahsilatlar")
    print("❌ Tüm kasa hareketleri")
    print("❌ Tüm giderler")
    print("❌ Tüm hediye çekleri")
    print("❌ Tüm log kayıtları")
    print("❌ Ürün kategorileri ve markalar")
    
    print("\nAşağıdaki veriler KORUNACAK:")
    print("✅ Kullanıcılar (Users)")
    print("✅ Bedenler (Beden)")
    print("✅ Renkler (Renk)")
    print("✅ Kasalar (Kasa - sadece tanımlar)")
    print("✅ Gider Kategorileri (GiderKategori)")
    
    print("\n" + "="*60)
    response = input("Bu işlemi yapmak istediğinizden emin misiniz? (EVET/hayır): ")
    return response.upper() == 'EVET'

def get_stats_before():
    """Temizlik öncesi istatistikler"""
    stats = {
        'users': CustomUser.objects.count(),
        'urunler': Urun.objects.count(),
        'varyantlar': UrunVaryanti.objects.count(),
        'satislar': Satis.objects.count(),
        'musteriler': Musteri.objects.count(),
        'giderler': Gider.objects.count(),
        'hediye_cekleri': HediyeCeki.objects.count(),
        'kasa_hareketleri': KasaHareket.objects.count(),
        'log_entries': AktiviteLog.objects.count(),
        'bedenler': Beden.objects.count(),
        'renkler': Renk.objects.count(),
        'kasalar': Kasa.objects.count(),
        'gider_kategorileri': GiderKategori.objects.count(),
    }
    return stats

def clean_database():
    """Veritabanını temizle"""
    try:
        with transaction.atomic():
            print("\n🧹 Veritabanı temizliği başlatılıyor...")
            
            # 1. Log kayıtları
            log_count = AktiviteLog.objects.count()
            AktiviteLog.objects.all().delete()
            print(f"✅ {log_count} log kaydı silindi")
            
            # 2. Hediye çekleri
            hediye_count = HediyeCeki.objects.count()
            HediyeCeki.objects.all().delete()
            print(f"✅ {hediye_count} hediye çeki silindi")
            
            # 3. Satış detayları (önce detaylar sonra ana kayıtlar)
            satis_detay_count = SatisDetay.objects.count()
            SatisDetay.objects.all().delete()
            print(f"✅ {satis_detay_count} satış detayı silindi")
            
            # 4. Ödemeler
            odeme_count = Odeme.objects.count()
            Odeme.objects.all().delete()
            print(f"✅ {odeme_count} ödeme kaydı silindi")
            
            # 5. Satışlar
            satis_count = Satis.objects.count()
            Satis.objects.all().delete()
            print(f"✅ {satis_count} satış kaydı silindi")
            
            # 6. Müşteri tahsilat detayları ve hareketleri
            tahsilat_detay_count = TahsilatDetay.objects.count()
            TahsilatDetay.objects.all().delete()
            print(f"✅ {tahsilat_detay_count} tahsilat detayı silindi")
            
            # 7. Borç-alacak hareketleri
            borc_alacak_count = BorcAlacakHareket.objects.count() 
            BorcAlacakHareket.objects.all().delete()
            print(f"✅ {borc_alacak_count} borç-alacak hareketi silindi")
            
            # 8. Müşteri tahsilatları
            tahsilat_count = Tahsilat.objects.count()
            Tahsilat.objects.all().delete()
            print(f"✅ {tahsilat_count} müşteri tahsilat kaydı silindi")
            
            # 9. Müşteriler
            musteri_count = Musteri.objects.count()
            Musteri.objects.all().delete()
            print(f"✅ {musteri_count} müşteri kaydı silindi")
            
            # 10. Kasa hareketleri (kasaları değil, sadece hareketleri)
            kasa_hareket_count = KasaHareket.objects.count()
            KasaHareket.objects.all().delete()
            print(f"✅ {kasa_hareket_count} kasa hareketi silindi")
            
            # 11. Giderler (kategorileri değil, sadece giderleri)
            gider_count = Gider.objects.count()
            Gider.objects.all().delete()
            print(f"✅ {gider_count} gider kaydı silindi")
            
            # 12. Ürün varyantları
            varyant_count = UrunVaryanti.objects.count()
            UrunVaryanti.objects.all().delete()
            print(f"✅ {varyant_count} ürün varyantı silindi")
            
            # 13. Ürünler
            urun_count = Urun.objects.count()
            Urun.objects.all().delete()
            print(f"✅ {urun_count} ürün silindi")
            
            # 14. Ürün kategorileri
            kategori_count = UrunKategoriUst.objects.count()
            UrunKategoriUst.objects.all().delete()
            print(f"✅ {kategori_count} ürün kategorisi silindi")
            
            # 15. Markalar
            marka_count = Marka.objects.count()
            Marka.objects.all().delete()
            print(f"✅ {marka_count} marka silindi")
            
            print("\n🎉 Veritabanı temizliği tamamlandı!")
            
    except Exception as e:
        print(f"\n❌ Hata oluştu: {str(e)}")
        raise

def get_stats_after():
    """Temizlik sonrası istatistikler"""
    stats = {
        'users': CustomUser.objects.count(),
        'bedenler': Beden.objects.count(),
        'renkler': Renk.objects.count(),
        'kasalar': Kasa.objects.count(),
        'gider_kategorileri': GiderKategori.objects.count(),
    }
    return stats

def main():
    print("🗄️ NUVIA OTOMASYON - VERİTABANI TEMİZLİK ARACI")
    
    # Onay al
    if not confirm_deletion():
        print("\n❌ İşlem iptal edildi.")
        return
    
    # Önceki istatistikler
    stats_before = get_stats_before()
    print(f"\n📊 TEMİZLİK ÖNCESİ İSTATİSTİKLER:")
    for key, value in stats_before.items():
        print(f"   {key}: {value}")
    
    # Temizlik yap
    try:
        clean_database()
        
        # Sonraki istatistikler
        stats_after = get_stats_after()
        print(f"\n📊 TEMİZLİK SONRASI KALAN VERİLER:")
        for key, value in stats_after.items():
            print(f"   {key}: {value}")
            
        print(f"\n✨ Veritabanı başarıyla temizlendi!")
        print(f"💾 Kullanıcılar, bedenler, renkler, kasalar ve gider kategorileri korundu.")
        
    except Exception as e:
        print(f"\n💥 Kritik hata: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
