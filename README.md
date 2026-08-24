# Nuvia Otomasyon - Stok ve Satış Takip Sistemi

Modern, kapsamlı ve kullanıcı dostu **Stok ve Satış Takip Sistemi**. Django framework ile geliştirilmiş, Bootstrap 5 ile tasarlanmış web tabanlı uygulama.

## 🚀 Temel Özellikler

### 👥 Kullanıcı Yönetimi ve Yetkilendirme
- ✅ Özel kullanıcı modeli (CustomUser)
- ✅ Rol tabanlı yetkilendirme (Admin, Manager, Sales, Warehouse, Viewer)
- ✅ Kullanıcı profilleri ve aktivite takibi
- ✅ Oturum yönetimi ve güvenlik
- ✅ Kullanıcı oluşturma, düzenleme ve yetki atama

### 📦 Ürün Yönetimi
- ✅ Ürünler üst/alt kategorilerde organize edilir
- ✅ Barkod, ad, açıklama, alış/satış fiyatı, varyasyon (renk/beden), stok miktarı
- ✅ Kar marjına göre otomatik satış fiyatı hesaplama
- ✅ Ürün resmi yükleme ve otomatik boyutlandırma
- ✅ CRUD işlemleri (Ekleme, Düzenleme, Silme)

### 💰 Satış Ekranı
- ✅ Barkod okutma desteği
- ✅ Nakit, kredi kartı, taksit, iade, hediye çeki ödeme seçenekleri
- ✅ KDV hesaplama (%10 varsayılan, değiştirilebilir)
- ✅ Otomatik stok güncelleme
- ✅ Çoklu ürün satışı

### 🔍 Barkod Sorgulama
- ✅ Ayrı sayfa ile barkod sorgulama
- ✅ Ürün resmi, stok miktarı, satış fiyatı, varyasyonları görüntüleme

### 👨‍💼 Müşteri Yönetimi
- ✅ İsim, soyisim, telefon, adres bilgileri
- ✅ Bireysel/Kurumsal müşteri ayrımı
- ✅ Müşteri tahsilat takibi
- ✅ CRUD işlemleri

### 💸 Gider Yönetimi
- ✅ Kategorik gider takibi
- ✅ Günlük, haftalık, aylık gider raporları
- ✅ Gider analizi ve filtreleme

### 🎁 Hediye Çeki Sistemi
- ✅ Hediye çeki oluşturma ve yönetimi
- ✅ Kullanım takibi ve bakiye kontrolü

### 📊 Raporlama
- ✅ Günlük satış raporu
- ✅ Stok durumu raporu
- ✅ En çok satan ürünler raporu

### 💾 Yedekleme Sistemi
- ✅ Otomatik Git commit tabanlı yedekleme
- ✅ Dosya tabanlı zip arşivi yedekleme
- ✅ Eski yedeklerin otomatik temizlenmesi
- ✅ Kolay geri yükleme sistemi
- ✅ Kâr/Zarar analizi
- ✅ Minimum stok uyarısı
- ✅ Excel ve PDF export desteği

### Kullanıcı Yönetimi
- ✅ Django authentication sistemi
- ✅ Kullanıcı giriş/çıkış
- ✅ Test kullanıcısı: admin/admin

### Loglama Sistemi
- ✅ Tüm CRUD işlemleri loglanır
- ✅ Kullanıcı, tarih, saat bilgisi
- ✅ Değişiklik kayıtları
- ✅ Sistem hataları

## 🛠️ Teknolojiler

- **Backend**: Python 3.13 + Django 5.2.5
- **Frontend**: Django Templates + Bootstrap 5
- **Veritabanı**: SQLite (Development), PostgreSQL (Production)
- **Dosya İşleme**: Pillow (Resim), OpenPyXL (Excel), ReportLab (PDF)
- **Stil**: Bootstrap 5, Font Awesome, Custom CSS
- **JavaScript**: Vanilla JS, Bootstrap JS

## 📦 Kurulum

Production deploy adımları için [DEPLOY.md](DEPLOY.md) dosyasına bakın.

### Gereksinimler
- Python 3.13+
- pip
- Git

### Adım Adım Kurulum

1. **Projeyi İndirin**
```bash
git clone <repository-url>
cd NuviaOtomasyon
```

2. **Sanal Ortam Oluşturun**
```bash
python -m venv .venv
.\.venv\Scripts\activate  # Windows
source .venv/bin/activate  # Linux/Mac
```

3. **Bağımlılıkları Yükleyin**
```bash
pip install django psycopg2-binary pillow openpyxl reportlab python-decouple whitenoise
```

4. **Veritabanını Oluşturun**
```bash
python manage.py makemigrations
python manage.py migrate
```

5. **Admin Kullanıcısı Oluşturun**
```bash
python manage.py createsuperuser --username admin --email admin@example.com
# Şifre: admin (test için)
```

6. **Sunucuyu Başlatın**
```bash
python manage.py runserver
```

7. **Tarayıcıda Açın**
- Ana Site: http://127.0.0.1:8000/
- Admin Panel: http://127.0.0.1:8000/admin/

## 🎯 Kullanım

### İlk Kurulum Sonrası
1. **Kategoriler Oluşturun**
   - Üst Kategoriler: Kadın, Erkek, Çocuk
   - Alt Kategoriler: Pantolon, Gömlek, Şort, vb.

2. **Varyasyonlar Ekleyin**
   - Renkler: Siyah, Beyaz, Mavi, vb.
   - Bedenler: XS, S, M, L, XL, vb.

3. **Ürünleri Ekleyin**
   - Barkod, ad, kategori, fiyat bilgileri
   - Kar marjı belirleyin (otomatik satış fiyatı hesaplama)

4. **Müşterileri Kaydedin**
   - İletişim bilgileri ve tercihler

5. **Satış Yapmaya Başlayın**
   - Barkod okutma veya ürün arama
   - Sepete ekleme ve ödeme

### Giriş Bilgileri
- **Kullanıcı Adı**: admin
- **Şifre**: admin

## 🏗️ Proje Yapısı

```
NuviaOtomasyon/
├── stoktakip/          # Ana proje ayarları
├── urun/               # Ürün yönetimi
├── satis/              # Satış işlemleri
├── musteri/            # Müşteri yönetimi
├── rapor/              # Raporlama modülü
├── log/                # Loglama sistemi
├── templates/          # HTML şablonları
├── static/             # CSS, JS, resimler
├── media/              # Kullanıcı yüklenen dosyalar
└── manage.py           # Django yönetim scripti
```

## 📱 Responsive Tasarım

Sistem tüm cihazlarda mükemmel çalışır:
- **PC**: Tam özellikli masaüstü deneyimi
- **Tablet**: Dokunmatik optimize edilmiş arayüz
- **Telefon**: Hamburger menü ile mobil uyumlu

## 🔧 Geliştirme

### Yeni Özellik Ekleme
1. İlgili uygulamada model oluşturun
2. Migration oluşturun: `python manage.py makemigrations`
3. Veritabanına uygulayın: `python manage.py migrate`
4. View ve template dosyalarını ekleyin
5. URL yapılandırmasını güncelleyin

### Test Verisi Ekleme
```python
# Django shell ile
python manage.py shell

# Kategori ekleme
from urun.models import UrunKategoriUst, UrunKategoriAlt
ust = UrunKategoriUst.objects.create(ad="Kadın")
alt = UrunKategoriAlt.objects.create(ad="Pantolon", ust_kategori=ust)
```

## 🚀 Production Deployment

### VPS Kurulumu (Ubuntu/CentOS)
1. **Sunucu Hazırlığı**
```bash
sudo apt update && sudo apt upgrade -y
sudo apt install python3 python3-pip nginx postgresql
```

2. **PostgreSQL Yapılandırması**
```bash
sudo -u postgres createdb stoktakip
sudo -u postgres createuser stoktakip_user
```

3. **Nginx Yapılandırması**
```nginx
server {
    listen 80;
    server_name your-domain.com;
    
    location /static/ {
        alias /path/to/NuviaOtomasyon/staticfiles/;
    }
    
    location /media/ {
        alias /path/to/NuviaOtomasyon/media/;
    }
    
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

4. **Gunicorn ile Çalıştırma**
```bash
pip install gunicorn
gunicorn stoktakip.wsgi:application --bind 127.0.0.1:8000
```

## 📊 Performans

- ⚡ SQLite ile hızlı yerel geliştirme
- 🗄️ PostgreSQL ile production performansı
- 🖼️ Otomatik resim optimize edilmesi
- 📱 Responsive tasarım ile hızlı yükleme
- 🔄 AJAX ile sayfa yenilenmeden işlemler

## 🆘 Sorun Giderme

### Yaygın Sorunlar

1. **Migration Hatası**
```bash
python manage.py makemigrations --empty <app_name>
python manage.py migrate --fake-initial
```

2. **Static Files Sorunu**
```bash
python manage.py collectstatic
```

3. **Port Kullanımda**
```bash
python manage.py runserver 8001
```

## � Yedekleme Sistemi

Proje, hem Git tabanlı hem de dosya tabanlı yedekleme sistemi içerir.

### Hızlı Kullanım

```powershell
# Hızlı backup (Git + dosya)
.\backup.ps1 quick

# Mesajlı backup
.\backup.ps1 create "Önemli değişiklikler"

# Backup'ları listele
.\backup.ps1 list
```

### Detaylı Komutlar

```powershell
# Python script ile kullanım
py backup.py create [mesaj]           # Her iki yedekleme türü
py backup.py git [mesaj]              # Sadece Git commit
py backup.py file                     # Sadece dosya backup
py backup.py list                     # Backup'ları listele
py backup.py restore <dosya_adı>      # Dosya backup'ından geri yükle

# PowerShell script ile kullanım
.\backup.ps1 create [mesaj]           # Her iki yedekleme türü
.\backup.ps1 quick [mesaj]            # Hızlı backup
.\backup.ps1 git [mesaj]              # Sadece Git commit
.\backup.ps1 file                     # Sadece dosya backup
.\backup.ps1 list                     # Backup'ları listele
.\backup.ps1 restore <dosya_adı>      # Dosya backup'ından geri yükle
```

### Backup Türleri

1. **Git Backup**: Değişiklikleri Git commit'i olarak saklar
2. **Dosya Backup**: Projeyi ZIP arşivi olarak `backups/` klasörüne kaydeder

### Örnekler

```powershell
# Günlük backup
.\backup.ps1 quick "Günlük yedekleme"

# Önemli değişiklik öncesi
.\backup.ps1 create "Veritabanı güncelleme öncesi"

# Mevcut backup'ları görüntüle
.\backup.ps1 list

# Geri yükleme
.\backup.ps1 restore nuvia_backup_20250904_200929.zip
```

## �📄 Lisans

Bu proje MIT lisansı altında lisanslanmıştır.

## 👥 Katkıda Bulunma

1. Fork yapın
2. Feature branch oluşturun (`git checkout -b feature/amazing-feature`)
3. Commit yapın (`git commit -m 'Add amazing feature'`)
4. Push yapın (`git push origin feature/amazing-feature`)
5. Pull Request açın

## 📞 İletişim

Herhangi bir sorunuz için issue açabilir veya doğrudan iletişime geçebilirsiniz.

---

**Geliştirici**: GitHub Copilot ile Django Expert Developer  
**Versiyon**: 1.0.0  
**Son Güncelleme**: Ağustos 2025
