# NuviaButik.com Production Deployment Kılavuzu

## 🚀 Sunucu Bilgileri
- **Domain**: nuviabutik.com
- **IP**: 31.57.33.34
- **Platform**: Ubuntu Server (önerilen)
- **Web Server**: Nginx
- **Application Server**: Gunicorn
- **Database**: PostgreSQL
- **SSL**: Let's Encrypt

## 📋 Ön Gereksinimler

### Sunucu Gereksinimleri
- Ubuntu 20.04 LTS veya 22.04 LTS
- En az 2GB RAM
- En az 20GB disk alanı
- Root erişimi veya sudo yetkisi

### Domain Ayarları
DNS kayıtlarınızı aşağıdaki gibi yapılandırın:
```
A     nuviabutik.com          31.57.33.34
A     www.nuviabutik.com      31.57.33.34
```

## 🛠️ Adım Adım Kurulum

### 1. Sunucu Hazırlığı
```bash
# Sunucuya SSH ile bağlanın
ssh root@31.57.33.34

# Deployment script'ini çalıştırın
chmod +x deploy.sh
sudo ./deploy.sh
```

### 2. Django Projesi Yükleme
```bash
# Proje dizinini oluşturun
sudo mkdir -p /var/www/nuviabutik
cd /var/www/nuviabutik

# Projenizi yükleyin (Git kullanarak)
sudo git clone https://github.com/azemyazilim/NuviaOtomasyon.git .

# Veya SCP/SFTP ile dosyaları kopyalayın
# scp -r /path/to/your/project/* root@31.57.33.34:/var/www/nuviabutik/
```

### 3. Python Ortamı Kurulumu
```bash
# Virtual environment oluşturun
sudo python3 -m venv /var/www/nuviabutik/venv

# Virtual environment'ı aktif edin
source /var/www/nuviabutik/venv/bin/activate

# Requirements'ları yükleyin
sudo /var/www/nuviabutik/venv/bin/pip install -r requirements.txt

# Dosya sahipliklerini ayarlayın
sudo chown -R www-data:www-data /var/www/nuviabutik
```

### 4. Environment Dosyası Ayarlama
```bash
# Production environment dosyasını kopyalayın
sudo cp .env.production .env

# Environment dosyasını düzenleyin
sudo nano .env
```

Aşağıdaki değerleri güncelleyin:
```env
SECRET_KEY=generate-a-strong-secret-key-here
DEBUG=False
DB_PASSWORD=your-secure-database-password
```

### 5. Veritabanı Ayarlama
```bash
# Veritabanı şifresini değiştirin
sudo -u postgres psql -c "ALTER USER nuviabutik_user PASSWORD 'your-secure-password';"

# Migrasyonları çalıştırın
sudo -u www-data /var/www/nuviabutik/venv/bin/python manage.py migrate --settings=production_settings

# Static dosyaları toplayın
sudo -u www-data /var/www/nuviabutik/venv/bin/python manage.py collectstatic --noinput --settings=production_settings

# Süper kullanıcı oluşturun
sudo -u www-data /var/www/nuviabutik/venv/bin/python manage.py createsuperuser --settings=production_settings
```

### 6. Nginx Konfigürasyonu
```bash
# Nginx config dosyasını kopyalayın
sudo cp nginx_nuviabutik.conf /etc/nginx/sites-available/nuviabutik.com

# Site'ı aktif edin
sudo ln -s /etc/nginx/sites-available/nuviabutik.com /etc/nginx/sites-enabled/

# Nginx'i test edin ve restart edin
sudo nginx -t
sudo systemctl restart nginx
```

### 7. Systemd Service Kurulumu
```bash
# Service dosyasını kopyalayın
sudo cp nuviabutik.service /etc/systemd/system/

# Service'i aktif edin
sudo systemctl daemon-reload
sudo systemctl enable nuviabutik
sudo systemctl start nuviabutik

# Durumu kontrol edin
sudo systemctl status nuviabutik
```

### 8. SSL Sertifikası (Let's Encrypt)
```bash
# SSL sertifikası alın
sudo certbot --nginx -d nuviabutik.com -d www.nuviabutik.com

# Otomatik renewal'ı test edin
sudo certbot renew --dry-run
```

### 9. Son Kontroller
```bash
# Servislerin durumunu kontrol edin
sudo systemctl status nginx
sudo systemctl status nuviabutik
sudo systemctl status postgresql

# Log dosyalarını kontrol edin
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/gunicorn/nuviabutik_error.log
```

## 🔧 Güncelleme İşlemleri

### Kod Güncellemesi
```bash
cd /var/www/nuviabutik

# Değişiklikleri çekin
sudo git pull origin main

# Requirements'ları güncelleyin
sudo /var/www/nuviabutik/venv/bin/pip install -r requirements.txt

# Migrasyonları çalıştırın
sudo -u www-data /var/www/nuviabutik/venv/bin/python manage.py migrate --settings=production_settings

# Static dosyaları güncelleyin
sudo -u www-data /var/www/nuviabutik/venv/bin/python manage.py collectstatic --noinput --settings=production_settings

# Uygulamayı restart edin
sudo systemctl restart nuviabutik
```

## 🔍 Sorun Giderme

### Log Dosyaları
```bash
# Django application logs
sudo tail -f /var/log/django/nuviabutik.log

# Gunicorn logs
sudo tail -f /var/log/gunicorn/nuviabutik_error.log
sudo tail -f /var/log/gunicorn/nuviabutik_access.log

# Nginx logs
sudo tail -f /var/log/nginx/error.log
sudo tail -f /var/log/nginx/access.log

# System service logs
sudo journalctl -u nuviabutik -f
```

### Yaygın Sorunlar
1. **Static dosyalar yüklenmiyor**: `collectstatic` komutunu tekrar çalıştırın
2. **Database connection error**: PostgreSQL servisini ve .env dosyasını kontrol edin
3. **Permission denied**: Dosya sahipliklerini kontrol edin (`chown -R www-data:www-data`)
4. **502 Bad Gateway**: Gunicorn servisinin çalıştığını kontrol edin

## 🔐 Güvenlik Önerileri

### 1. Firewall Ayarları
```bash
sudo ufw allow OpenSSH
sudo ufw allow 'Nginx Full'
sudo ufw deny 8000  # Django development server'ı kapat
sudo ufw enable
```

### 2. PostgreSQL Güvenliği
```bash
# PostgreSQL'e sadece local erişim
sudo nano /etc/postgresql/*/main/postgresql.conf
# listen_addresses = 'localhost'
```

### 3. Nginx Security Headers
SSL yapılandırması tamamlandıktan sonra güvenlik başlıklarını aktif edin.

### 4. Regular Backups
```bash
# Veritabanı backup scripti
sudo crontab -e
# Her gün saat 2'de backup al
0 2 * * * pg_dump nuviabutik_db > /backup/nuviabutik_$(date +\%Y\%m\%d).sql
```

## 📞 Destek

Kurulum sırasında sorun yaşarsanız:
1. Log dosyalarını kontrol edin
2. Service durumlarını kontrol edin
3. Firewall ayarlarını kontrol edin
4. DNS ayarlarının doğru olduğundan emin olun

## ✅ Go-Live Checklist

- [ ] Domain DNS ayarları yapıldı
- [ ] Sunucu kurulumu tamamlandı
- [ ] Django uygulaması deploy edildi
- [ ] Veritabanı ayarlandı
- [ ] Nginx konfigüre edildi
- [ ] SSL sertifikası kuruldu
- [ ] Backup sistemi kuruldu
- [ ] Monitoring sistemi kuruldu
- [ ] Test işlemleri tamamlandı
