#!/bin/bash
# NuviaButik.com tam sunucu kurulum scripti
# Ubuntu 20.04/22.04 için uygundur
# root olarak çalıştırın

set -e

# 1. Sistem güncellemesi ve temel paketler
apt update && apt upgrade -y
apt install -y python3 python3-pip python3-venv python3-dev \
    postgresql postgresql-contrib nginx git curl wget unzip build-essential libpq-dev \
    ufw fail2ban

# 2. PostgreSQL database ve kullanıcı oluşturma
systemctl start postgresql
systemctl enable postgresql
sudo -u postgres psql -c "CREATE DATABASE nuviabutik_db;" || echo "Database zaten var."
sudo -u postgres psql -c "CREATE USER nuviabutik_user WITH PASSWORD 'NuviaButik2025!';" || echo "Kullanıcı zaten var."
sudo -u postgres psql -c "ALTER ROLE nuviabutik_user SET client_encoding TO 'utf8';"
sudo -u postgres psql -c "ALTER ROLE nuviabutik_user SET default_transaction_isolation TO 'read committed';"
sudo -u postgres psql -c "ALTER ROLE nuviabutik_user SET timezone TO 'UTC';"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE nuviabutik_db TO nuviabutik_user;"


# 3. Proje dizinleri (root kullanıcısı için)
mkdir -p /var/www/nuviabutik
mkdir -p /var/log/django
mkdir -p /var/log/gunicorn
mkdir -p /var/run/gunicorn
# root kullanıcısı için chown gerekmez


# 4. Proje dosyalarını klonlama (root için)
cd /var/www/nuviabutik
if [ ! -d .git ]; then
    git clone https://github.com/azemyazilim/NuviaOtomasyon.git .
fi

# 5. Python virtual environment ve paketler
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt


# 6. Environment dosyası
if [ ! -f .env ]; then
    cp .env.production .env
fi

# 7. Django migrasyonları ve setup
python manage.py migrate --settings=production_settings
python manage.py collectstatic --noinput --settings=production_settings
python manage.py createsuperuser --settings=production_settings --noinput || echo "Süper kullanıcı zaten var."
chmod +x setup_initial_data.sh
./setup_initial_data.sh

# 8. Nginx ve Gunicorn konfigürasyonu
cp nginx_nuviabutik.conf /etc/nginx/sites-available/nuviabutik.com
ln -sf /etc/nginx/sites-available/nuviabutik.com /etc/nginx/sites-enabled/
nginx -t && systemctl restart nginx
cp nuviabutik.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable nuviabutik
systemctl start nuviabutik


# 9. SSL sertifikası (Let's Encrypt)
if ! command -v certbot &> /dev/null; then
    apt install -y certbot python3-certbot-nginx
fi
certbot --nginx -d nuviabutik.com -d www.nuviabutik.com || echo "SSL kurulumu manuel yapılmalı."

# 10. Son kontroller
systemctl status nginx --no-pager
systemctl status nuviabutik --no-pager
systemctl status postgresql --no-pager


# Log dosyalarını göster
ls -lh /var/log/django/
ls -lh /var/log/gunicorn/
ls -lh /var/log/nginx/

echo "\n🚀 Tüm kurulum adımları tamamlandı! NuviaButik.com yayında!"
