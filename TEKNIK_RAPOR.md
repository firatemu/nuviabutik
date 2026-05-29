# NuviaButik - Teknik Rapor

**Hazırlanma Tarihi:** 17 Nisan 2026  
**Proje Tipi:** Stok ve Satış Takip Sistemi  
**Versiyon:** 1.0.0

---

## 1. Genel Bakış

NuviaButik, bir butik işletmesi için geliştirilmiş kapsamlı **Django tabanlı web uygulamasıdır**. Ürün yönetimi, satış işlemleri, müşteri takibi, gider yönetimi ve raporlama gibi temel iş süreçlerini yönetir.

### 1.1 Platform Bilgileri
- **Sunucu:** 31.57.33.34
- **Domain:** nuviabutik.com, www.nuviabutik.com
- **Veritabanı:** PostgreSQL (nuviabutik_db)

---

## 2. Teknoloji Stack'i

| Katman | Teknoloji | Versiyon |
|--------|-----------|----------|
| Backend Framework | Django | 5.2.5 |
| Programlama Dili | Python | 3.13+ |
| Web Sunucusu | Gunicorn | 21.2.0 |
| HTTP Sunucusu | Nginx | - |
| Veritabanı | PostgreSQL | - |
| Cache | Redis | - |
| Frontend | Bootstrap 5 | - |
| Static Files | WhiteNoise | 6.9.0 |
| Görüntü İşleme | Pillow | 11.3.0 |
| Excel Desteği | OpenPyXL | 3.1.5 |
| PDF Üretimi | ReportLab | 4.3.3 |

---

## 3. Proje Yapısı

```
www/nuviabutik/
├── stoktakip/          # Ana Django projesi
│   ├── settings.py     # Konfigürasyon
│   ├── urls.py        # URL routing
│   ├── wsgi.py       # WSGI uygulaması
│   └── ...
├── urun/              # Ürün modülü
├── satis/             # Satış modülü
├── musteri/           # Müşteri modülü
├── kullanici/         # Kullanıcı yönetimi
├── gider/             # Gider takibi
├── kasa/              # Kasa yönetimi
├── hediye/            # Hediye çeki
├── rapor/             # Raporlama
├── log/               # Loglama
├── templates/         # HTML şablonları
├── static/            # CSS, JS, görseller
├── media/             # Yüklenen dosyalar
└── manage.py
```

---

## 4. Modül Detayları

### 4.1 Ürün Modülü (urun)

**Amaç:** Ürün ve varyant yönetimi

**Modeller:**
- `UrunKategoriUst` - Üst kategoriler (Kadın, Erkek, Çocuk)
- `UrunKategoriAlt` - Alt kategoriler
- `Renk` - Renk varyasyonları (kod + hex desteği)
- `Beden` - Beden varyasyonları (harf/rakam tipleri)
- `Marka` - Marka bilgileri
- `Urun` - Ana ürün kartı
- `UrunVaryanti` - Ürün varyantları (renk/beden kombinasyonu)
- `StokHareket` - Stok hareket takibi
- `StokDegisiklikLog` - Stok değişiklik logları
- `FiyatGecmisi` - Fiyat geçmişi
- `FiyatKampanya` - Kampanya bilgileri

**Özellikler:**
- ❌ Barkod otomatik üretimi (Code128 format)
- ❌ Peşin/Taksitli fiyat sistemi (%5 fark)
- ❌ Otomatik stok yönetimi
- ❌ Stok hareket loglama
- ❌ PRN etiket üretimi
- ❌ Kritik stok uyarıları

### 4.2 Satış Modülü (satis)

**Amaç:** Satış işlemleri ve ödeme yönetimi

**Modeller:**
- `SiparisNumarasi` - Sipariş numarası sayacı
- `Satis` - Ana satış kaydı
- `SatisDetay` - Satış kalemleri
- `Odeme` - Ödeme bilgileri (nakit, kart, hediye çeki, açık hesap)
- `SatisIptal` - İptal kayıtları
- `SatisSiparisi` - Sipariş öncesi taslak yönetimi

**Ödeme Tipleri:**
- Nakit
- Kredi Kartı (taksit desteği, 4 banka seçeneği)
- Havale/EFT
- Hediye Çeki
- Açık Hesap

**Özellikler:**
- ❌ KDV hesaplama (%18 varsayılan)
- ❌ İndirim desteği
- ❌ Otomatik sipariş/satış numarası üretimi
- ❌ Race condition korumalı sayaçlar
- ❌ Kar/zarar hesaplama
- ❌ Stok otomatik güncelleme

### 4.3 Müşteri Modülü (musteri)

**Amaç:** Müşteri yönetimi ve tahsilat takibi

**Modeller:**
- `Musteri` - Müşteri bilgileri
- `MusteriGruplar` - VIP, Toptan vb. gruplar
- `MusteriGrupUyelik` - Grup üyelikleri
- `Tahsilat` - Tahsilat kayıtları
- `TahsilatDetay` - Tahsilat detayları
- `BorcAlacakHareket` - Borç/alacak hareketleri

**Müşteri Tipleri:**
- Bireysel (TC Kimlik No)
- Kurumsal (Vergi No, Vergi Dairesi)

**Özellikler:**
- ❌ Açık hesap bakiye yönetimi
- ❌ Borç/alacak hareket takibi
- ❌ Doğum günü bilgisi
- ❌ Toplam satış istatistikleri
- ❌ Veresiye satış takibi

### 4.4 Kullanıcı Modülü (kullanici)

**Amaç:** Kimlik doğrulama ve yetkilendirme

**Modeller:**
- `CustomUser` - Özelleştirilmiş kullanıcı modeli
- `UserSession` - Oturum takibi
- `UserActivityLog` - Aktivite logları
- `UserProfile` - Profil bilgileri

**Roller:**
| Rol | İzinler |
|-----|---------|
| admin | Tüm yetkiler |
| manager | Ürün, satış, müşteri, gider, rapor görüntüleme |
| cashier | Satış, ürün görüntüleme, müşteri ekleme |
| stock_clerk | Ürün ekleme/düzenleme |
| viewer | Sadece görüntüleme |

### 4.5 Gider Modülü (gider)

**Amaç:** Gider takibi ve raporlaması

**Modeller:**
- `GiderKategori` - Gider kategorileri
- `Gider` - Gider kayıtları

**Özellikler:**
- ❌ Kategorik gider takibi
- ❌ Günlük/Haftalık/Aylık raporlar
- ❌ Gider filtreleme

### 4.6 Kasa Modülü (kasa)

**Amaç:** Kasa yönetimi ve para hareketleri

**Modeller:**
- `Kasa` - Kasa kayıtları
- `KasaHareket` - Kasa hareketleri
- `KasaVirman` - Kasa virmanları
- `KasaGiris` - Para girişleri
- `KasaCikis` - Para çıkışları

**Özellikler:**
- ❌ Çoklu kasa desteği
- ❌ Para giriş/çıkış işlemleri
- ❌ Kasa virmanları
- ❌ Günlük bakiye takibi
- ❌ Bugünkü hareket görüntüleme

### 4.7 Hediye Çeki Modülü (hediye)

**Amaç:** Hediye çeki yönetimi

**Modeller:**
- `HediyeCeki` - Hediye çekleri
- `HediyeCekiKullanim` - Kullanım kayıtları

**Özellikler:**
- ❌ Hediye çeki oluşturma
- ❌ Bakiye takibi
- ❌ Kullanım geçmişi
- ❌ İptal desteği
- ❌ Barkod ile sorgulama

### 4.8 Rapor Modülü (rapor)

**Raporlar:**
- ❌ Günlük satış raporu
- ❌ Stok raporu
- ❌ Çok satan ürünler
- ❌ Kâr/zarar analizi
- ❌ Müşteri raporu
- ❌ Satıcı raporu
- ❌ Stok hareketleri

**Export Desteği:**
- Excel (.xlsx)
- PDF

---

## 5. Veritabanı Yapısı

**Toplam Tablo Sayısı:** ~40+

**Ana Tablolar:**
- `urun_urun` - Ürünler
- `urun_urunvaryanti` - Ürün varyantları
- `urun_stokhareket` - Stok hareketleri
- `satis_satis` - Satışlar
- `satis_odeme` - Ödemeler
- `musteri_musteri` - Müşteriler
- `musteri_tahsilat` - Tahsilatlar
- `gider_gider` - Giderler
- `kasa_kasa` - Kasalar
- `kullanici_customuser` - Kullanıcılar

**İndeksler:**
- Ürün: aktif, kategori, marka, cinsiyet, urun_kodu, ad
- Varyant: urun+aktif, stok_miktari, barkod
- Satış: siparis_tarihi, durum

---

## 6. Güvenlik Değerlendirmesi

### 6.1 Mevcut Güvenlik Önlemleri
- ✅ Django authentication sistemi
- ✅ Rol bazlı yetkilendirme (RBAC)
- ✅ CSRF koruması (geçici olarak devre dışı)
- ✅ Session yönetimi (Redis ile cache)
- ✅ SQL injection koruması (Django ORM)
- ✅ XSS koruması (Django template escaping)

### 6.2 Dikkat Edilmesi Gereken Noktalar
- ⚠️ CSRF geçici olarak kapalı - üretimde aktif edilmeli
- ⚠️ SECRET_KEY çevresel değişkende tutulmalı
- ⚠️ DEBUG mode üretimde kapatılmalı
- ⚠️ Session cookie güvenlik ayarları gözden geçirilmeli

---

## 7. Performans Optimizasyonları

### 7.1 Uygulanan Optimizasyonlar
- ✅ PostgreSQL persistent connections (10 dakika)
- ✅ Connection health checks
- ✅ Query timeout (30 saniye)
- ✅ Redis cache (session + template)
- ✅ WhiteNoise static file serving
- ✅ Database indeksleri
- ✅ Compressed static files

### 7.2 Önerilen İyileştirmeler
- 🔲 Query optimization (select_related/prefetch_related)
- 🔲 View caching (per-site ve fragment)
- 🔲 Lazy loading für Bilder
- 🔲 CDN kullanımı
- 🔲 Database connection pooling (PgBouncer)

---

## 8. API & URL Yapısı

**Ana URL Grupları:**
- `/admin/` - Django admin paneli
- `/urun/` - Ürün işlemleri
- `/satis/` - Satış işlemleri
- `/musteri/` - Müşteri işlemleri
- `/gider/` - Gider işlemleri
- `/kasa/` - Kasa işlemleri
- `/hediye/` - Hediye çeki işlemleri
- `/rapor/` - Raporlar
- `/kullanici/` - Kullanıcı işlemleri

---

## 9. Dosya Yönetimi

**Upload Dizinleri:**
- `media/urun_resimleri/` - Ürün görselleri
- `media/varyant_resimleri/` - Varyant görselleri
- `media/marka_logolari/` - Marka logoları
- `media/profile_pictures/` - Profil fotoğrafları

**Görüntü İşleme:**
- Pillow ile otomatik boyutlandırma
- Cloudinary desteği (bulut depolama)

---

## 10. Deployment

### 10.1 Mevcut Kurulum
- **WSGI:** Gunicorn (port 8000)
- **HTTP:** Nginx (reverse proxy)
- **Process Manager:** systemd service
- **SSL:** Let's Encrypt desteği

### 10.2 Service Dosyası
```
/etc/systemd/system/nuviabutik.service
```

### 10.3 Nginx Konfigürasyonu
- Static files: `/static/` → `staticfiles/`
- Media files: `/media/` → `media/`
- Proxy: `/` → `127.0.0.1:8000`

---

## 11. Loglama

**Log Dosyaları:**
- `/var/log/nuviabutik_alerts.log` - Uyarılar
- `/var/log/nuviabutik_backup.log` - Yedekleme
- `/var/log/nuviabutik_health.log` - Sistem sağlığı
- `/var/log/nuviabutik_printer.log` - Yazıcı işlemleri

**Database Log Tabloları:**
- `log_logkaydi` - CRUD işlemleri
- `kullanici_useractivitylog` - Kullanıcı aktiviteleri
- `urun_stokdegisikliklog` - Stok değişiklikleri

---

## 12. Yedekleme Sistemi

**Yöntemler:**
1. **Git Backup:** Otomatik commit tabanlı
2. **Dosya Backup:** ZIP arşivleme

**Otomatik Temizlik:**
- Eski yedeklerin silinmesi

---

## 13. Bağımlılıklar

```
Django==5.2.5
gunicorn==21.2.0
psycopg2-binary==2.9.10
Pillow==11.3.0
openpyxl==3.1.5
reportlab==4.3.3
python-decouple==3.8
whitenoise==6.9.0
django-cloudinary-storage==0.3.0
cloudinary==1.44.1
redis (implicit)
```

---

## 14. Statüler

| Durum | Açıklama |
|-------|----------|
| ✅ Aktif | Üretimde çalışıyor |
| ⚠️ İncelemeli | Güvenlik açıkları olabilir |
| 🔲 Planlanan | Henüz implement edilmedi |

---

## 15. Sonuç

**Güçlü Yönler:**
- Kapsamlı iş süreci yönetimi
- Modüler ve genişletilebilir yapı
- Sağlam veritabanı tasarımı
- Stok takip ve barkod sistemi
- Çoklu ödeme yöntemi desteği

**Geliştirilmesi Gereken Alanlar:**
- Güvenlik (CSRF aktif edilmeli)
- Performans (cache ve query optimization)
- Test coverage (birim testleri yok)
- API dokumentasyonu (REST API yok)
- Monitoring (sistem sağlığı takibi)

---

*Bu rapor otomatik olarak proje analizi yapılarak oluşturulmuştur.*
