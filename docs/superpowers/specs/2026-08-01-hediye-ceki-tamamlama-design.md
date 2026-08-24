# Hediye Çeki Tamamlama Entegrasyonu

**Tarih:** 2026-08-01  
**Proje:** NuviaButik Satış Sistemi  
**Amaç:** Satış ekranındaki hediye çeki fonksiyonelliğinin backend entegrasyonunu tamamlamak

## 📋 Proje Kapsamı

### Mevcut Durum
- ✅ Frontend hediye çeki arayüzü tamamen çalışıyor
- ✅ Hediye çeki kodu sorgulama API'si mevcut (`/satis/hediye-ceki-sorgula/`)
- ✅ Hediye çeki modelleri tamamlanmış (`HediyeCeki`, `HediyeCekiKullanim`)
- ❌ Checkout servisi hediye çeki işlemini gerçekleştirmiyor
- ❌ Hediye çeki bakiyesinden düşme ve kullanım kaydı oluşturma eksik

### Hedef Durum
- ✅ Hediye çeki ile ödeme yapılan satışlar tamamlanabiliyor
- ✅ Hediye çeki bakiyesinden doğru tutar düşülüyor
- ✅ Hediye çeki kullanım kayıtları tutuluyor
- ✅ Ödeme kayıtlarına hediye çeki dahil ediliyor
- ✅ Kısmi kullanım destekleniyor

## 🎯 Kullanım Senaryoları

### Ana Senaryo: Hediye Çeki ile Karma Ödeme
1. Kullanıcı sepeti doldurur
2. Karma ödeme seçer
3. Hediye çeki kodunu girer ve sorgular
4. Sistem bakiyeyi gösterir
5. Kullanıcı kullanmak istediği tutarı girer (bakiye kadar veya daha az)
6. Diğer ödeme yöntemlerini (nakit, kart, havale) tamamlar
7. Satışı tamamlar
8. Sistem hediye çeki bakiyesinden düşer ve kullanım kaydı oluşturur

### Alternatif Senaryo: Tam Bakiye Kullanımı
- Kullanıcı hediye çeki bakiyesinin tamamını kullanır
- Çek durumu 'kullanilmis' olarak güncellenir
- Kullanılma tarihi kaydedilir

### Alternatif Senaryo: Kısmi Kullanım
- Kullanıcı hediye çeki bakiyesinin bir kısmını kullanır
- Kalan bakiye çekte tutulur
- Çek durumu 'aktif' olarak kalır

## 🏗️ Mimari

### Veri Akışı

```
Frontend → Backend API → Checkout Servisi → Hediye Çeki İşlemleri
     ↓              ↓              ↓                  ↓
  UI Form     Request Data   Business Logic    Database Updates
```

### Bileşenler

#### 1. Frontend (Zaten Tamamlandı)
- `satis-ekrani.js`: Hediye çeki arayüzü mantığı
- `satis_ekrani.html`: Hediye çeki UI elementleri

#### 2. Backend API
- `satis/views.py`: `satis_tamamla()` view'ı
- `satis/services/checkout.py`: `complete_checkout()` fonksiyonu

#### 3. Veritabanı Modelleri (Zaten Mevcut)
- `hediye.models.HediyeCeki`: Hediye çeki ana modeli
- `hediye.models.HediyeCekiKullanim`: Kullanım geçmişi
- `satis.models.Odeme`: Ödeme kayıtları

## 🔧 Teknik Detaylar

### Checkout Servisi Değişiklikleri

#### 1. Parametre Çıkarma
```python
def complete_checkout(user, sepet_data, musteri_id, odeme_detaylari, data=None, session=None):
    # Mevcut parametreler...
    
    # Hediye çeki bilgilerini çıkar
    hediye_ceki_kodu = data.get('hediye_ceki', {}).get('kod')
    hediye_ceki_tutar = odeme_detaylari.get('karma_detay', {}).get('hediye_ceki', 0)
```

#### 2. Hediye Çeki Validasyonu
```python
if hediye_ceki_kodu and hediye_ceki_tutar > 0:
    from hediye.models import HediyeCeki
    from django.utils import timezone
    
    try:
        hediye_ceki = HediyeCeki.objects.get(kod=hediye_ceki_kodu, aktif=True)
        
        # Validasyon kontrolleri
        if not hediye_ceki.kullanilabilir_mi:
            raise CheckoutError("Hediye çeki kullanılamaz durumda")
        
        if hediye_ceki.kalan_tutar < hediye_ceki_tutar:
            raise CheckoutError("Hediye çeki bakiyesi yetersiz")
            
    except HediyeCeki.DoesNotExist:
        raise CheckoutError("Hediye çeki bulunamadı")
```

#### 3. Bakiye Düşme İşlemi
```python
# Satış oluşturulduktan sonra
if hediye_ceki_kodu and hediye_ceki_tutar > 0:
    hediye_ceki.kullan(hediye_ceki_tutar)
```

#### 4. Kullanım Kaydı Oluşturma
```python
from hediye.models import HediyeCekiKullanim

HediyeCekiKullanim.objects.create(
    hediye_ceki=hediye_ceki,
    kullanilan_tutar=hediye_ceki_tutar,
    satis_id=satis.id,
    kullanan=user,
    aciklama=f"Satış #{satis.siparis_no}"
)
```

#### 5. Ödeme Kaydı Entegrasyonu
```python
# Mevcut ödeme kaydı oluşturma mantığına ekle
if hediye_ceki_tutar > 0:
    Odeme.objects.create(
        satis=satis,
        odeme_tipi='hediye_ceki',
        tutar=hediye_ceki_tutar,
        odeme_tarihi=timezone.now(),
        aciklama=f"Hediye Çeki: {hediye_ceki_kodu}"
    )
```

## 🛡️ Hata Yönetimi

### Hata Senaryoları ve Mesajları

| Senaryo | Mesaj | HTTP Status |
|---------|-------|-------------|
| Hediye çeki bulunamadı | "Hediye çeki bulunamadı" | 400 |
| Bakiye yetersiz | "Hediye çeki bakiyesi yetersiz" | 400 |
| Çek kullanılamaz durumda | "Hediye çeki kullanılamaz durumda" | 400 |
| Süresi dolmuş | "Hediye çeki süresi dolmuş" | 400 |
| Kod boş | "Hediye çeki kodu gerekli" | 400 |

### Hata Yakalama
```python
try:
    # Hediye çeki işlemleri
    pass
except ValueError as e:
    raise CheckoutError(str(e))
except Exception as e:
    logger.error(f"Hediye çeki hatası: {e}")
    raise CheckoutError("Hediye çeki işleminde hata oluştu")
```

## 🔄 İşlem Akışı

### Normal Akış
1. Frontend satış verilerini backend'e gönderir
2. `complete_checkout()` parametreleri alır
3. Sepet ve ödeme validasyonları yapılır
4. Hediye çeki validasyonu yapılır (varsa)
5. Satış ve satış detayları oluşturulur
6. Ödeme kayıtları oluşturulur
7. Hediye çeki bakiyesinden düşülür (varsa)
8. Hediye çeki kullanım kaydı oluşturulur (varsa)
9. Stok düşümleri yapılır
10. Başarı response'u döndürülür

### Hata Akışı
Herhangi bir adımda hata oluşursa:
1. İşlem transaction rollback edilir
2. Anlamlı hata mesajı döndürülür
3. Frontend kullanıcıya hatayı gösterir

## 📊 Test Senaryoları

### Birim Testler
- [ ] Hediye çeki validasyonu
- [ ] Bakiye düşme işlemi
- [ ] Kullanım kaydı oluşturma
- [ ] Ödeme kaydı entegrasyonu

### Entegrasyon Testleri
- [ ] Normal hediye çeki ile satış
- [ ] Kısmi bakiye kullanımı
- [ ] Tam bakiye kullanımı
- [ ] Yetersiz bakiye durumu
- [ ] Geçersiz kod durumu
- [ ] Karma ödeme (hediye çeki + diğer yöntemler)

### Edge Case Testler
- [ ] Aynı hediye çeki birden fazla kullanım denemesi
- [ ] Çok küçük tutarlı kullanım (0.01 ₺)
- [ ] Tam bakiye sınırında kullanım

## 🔐 Güvenlik

### Güvenlik Önlemleri
- Hediye çeki kodu doğrulaması backend'de tekrarlanır
- Bakiye kontrolü işlem öncesi yapılır
- Transaction güvenliği ile veri bütünlüğü sağlanır
- Kullanıcı yetkilendirmesi kontrol edilir

## 📈 Performans

### Performans İyileştirmeleri
- Hediye çeki sorgusu için indeksler mevcut (kod alanı)
- Kullanım kaydı sorguları optimize edilmiş
- Transaction süresi minimize edilmiş

## 🎯 Başarı Kriterleri

### Fonksiyonel Gereksinimler
- ✅ Hediye çeki ile ödeme yapılabilir
- ✅ Bakiye doğru şekilde düşülür
- ✅ Kullanım kayıtları tutulur
- ✅ Kısmi kullanım desteklenir
- ✅ Hatalar doğru şekilde yönetilir

### Teknik Gereksinimler
- ✅ Mevcut frontend kodlarını değiştirmeden çalışır
- ✅ Mevcut veritabanı yapısını korur
- ✅ Transaction güvenliği sağlar
- ✅ Hata loglama yapar

## 🚀 Deployment Planı

### Adım 1: Kod Değişiklikleri
- `satis/services/checkout.py` güncellemesi
- Testler

### Adım 2: Test
- Yerel test ortamında doğrulama
- Hata senaryoları testleri

### Adım 3: Deployment
- Canlıya alma
- İzleme

## 📝 Notlar

### Varsayımlar
- Frontend hediye çeki kodunu `data.hediye_ceki.kod` olarak gönderiyor
- Hediye çeki tutarı `odeme_detaylari.karma_detay.hediye_ceki` olarak geliyor
- Mevcut `HediyeCeki.kullan()` metodu güvenilir çalışıyor

### Riskler
- Hediye çeki model yapısının değişme riski düşük
- Frontend ile backend arayüz uyumsuzluğu riski düşük (mevcut JSON yapısı)
- Performans etkisi minimal (tek ek veritabanı sorgusu)

### Gelecek İyileştirmeler
- Hediye çeki kullanım raporları
- Müşteri bazlı hediye çeki analitiği
- Hediye çeki oluşturma otomasyonu