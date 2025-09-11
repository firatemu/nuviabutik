# NuviaButik.com Quick Start Guide

## 🚀 Sunucuya Upload Edilecek Dosyalar

### 1. Temel Dosyalar
```bash
# Tüm proje dosyalarını upload edin
scp -r * root@31.57.33.34:/var/www/nuviabutik/
```

### 2. Önemli Konfigürasyon Dosyaları
- `production_settings.py` - Production Django ayarları
- `gunicorn.conf.py` - Gunicorn konfigürasyonu
- `nginx_nuviabutik.conf` - Nginx konfigürasyonu
- `nuviabutik.service` - Systemd service dosyası
- `.env.production` - Environment template

### 3. Deployment Scripts
- `deploy.sh` - Sunucu kurulum scripti
- `setup_initial_data.sh` - İlk veri yükleme scripti

## 📋 Sunucuda Yapılacak İşlemler

### 1. Sunucu Hazırlığı
```bash
ssh root@31.57.33.34
chmod +x deploy.sh
./deploy.sh
```

### 2. Proje Upload
```bash
cd /var/www/nuviabutik
# Git kullanıyorsanız:
git clone https://github.com/azemyazilim/NuviaOtomasyon.git .

# Veya manuel upload:
# Local bilgisayardan: scp -r * root@31.57.33.34:/var/www/nuviabutik/
```

### 3. Python Environment
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 4. Environment Ayarları
```bash
cp .env.production .env
nano .env
# Bu değerleri güncelleyin:
# SECRET_KEY=your-secret-key
# DB_PASSWORD=your-secure-password
```

### 5. Database Setup
```bash
# PostgreSQL şifresini değiştirin
sudo -u postgres psql -c "ALTER USER nuviabutik_user PASSWORD 'your-secure-password';"

# Django migrasyonları
python manage.py migrate --settings=production_settings
python manage.py collectstatic --noinput --settings=production_settings
python manage.py createsuperuser --settings=production_settings
```

### 6. İlk Verileri Yükle
```bash
chmod +x setup_initial_data.sh
./setup_initial_data.sh
```

### 7. Web Server Ayarları
```bash
# Nginx konfigürasyonu
cp nginx_nuviabutik.conf /etc/nginx/sites-available/nuviabutik.com
ln -s /etc/nginx/sites-available/nuviabutik.com /etc/nginx/sites-enabled/
nginx -t
systemctl restart nginx

# Systemd service
cp nuviabutik.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable nuviabutik
systemctl start nuviabutik
```

### 8. SSL Sertifikası
```bash
certbot --nginx -d nuviabutik.com -d www.nuviabutik.com
```

## ✅ Test Listesi

1. [ ] Sunucu ayarları tamamlandı
2. [ ] Django uygulaması çalışıyor
3. [ ] Database bağlantısı OK
4. [ ] Static files yükleniyor
5. [ ] Admin paneli erişilebilir
6. [ ] SSL sertifikası kuruldu
7. [ ] Domain doğru yönlendiriliyor

## 🔗 Önemli URL'ler

- **Ana Site**: https://nuviabutik.com
- **Admin Panel**: https://nuviabutik.com/admin/
- **Dashboard**: https://nuviabutik.com/dashboard/

## 🛠️ Sorun Giderme

### Log Kontrolleri
```bash
# Django app logs
tail -f /var/log/django/nuviabutik.log

# Gunicorn logs
tail -f /var/log/gunicorn/nuviabutik_error.log

# Nginx logs
tail -f /var/log/nginx/error.log

# Service status
systemctl status nuviabutik
```

### Yaygın Hatalar
- **502 Bad Gateway**: Gunicorn servisini kontrol edin
- **Static files 404**: collectstatic komutunu tekrar çalıştırın
- **Database error**: PostgreSQL servisini ve .env dosyasını kontrol edin

---

**NuviaButik.com** başarıyla deploy edildi! 🎉
