#!/bin/bash

# Initial data setup for NuviaButik.com after deployment
# Run this script after successful deployment to populate initial data

set -e

PROJECT_DIR="/var/www/nuviabutik"
VENV_PYTHON="$PROJECT_DIR/venv/bin/python"
MANAGE_PY="$PROJECT_DIR/manage.py"
SETTINGS="--settings=production_settings"

echo "🎯 Setting up initial data for NuviaButik.com..."

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Change to project directory
cd $PROJECT_DIR

print_status "Creating default sizes (bedenler)..."
sudo -u www-data $VENV_PYTHON $MANAGE_PY shell $SETTINGS << 'EOF'
from urun.models import Beden

# Erkek giyim bedenleri
erkek_bedenler = ['XS', 'S', 'M', 'L', 'XL', 'XXL', 'XXXL']
for beden in erkek_bedenler:
    Beden.objects.get_or_create(ad=beden, kategori='erkek')

# Kadın giyim bedenleri  
kadin_bedenler = ['XS', 'S', 'M', 'L', 'XL', 'XXL', 'XXXL', '34', '36', '38', '40', '42', '44', '46']
for beden in kadin_bedenler:
    Beden.objects.get_or_create(ad=beden, kategori='kadin')

# Ayakkabı bedenleri
ayakkabi_bedenler = ['36', '37', '38', '39', '40', '41', '42', '43', '44', '45', '46']
for beden in ayakkabi_bedenler:
    Beden.objects.get_or_create(ad=beden, kategori='ayakkabi')

print(f"Toplam {Beden.objects.count()} beden oluşturuldu.")
EOF

print_status "Creating default colors (renkler)..."
sudo -u www-data $VENV_PYTHON $MANAGE_PY shell $SETTINGS << 'EOF'
from urun.models import Renk

# Temel renkler
renkler = [
    'Siyah', 'Beyaz', 'Gri', 'Lacivert', 'Mavi', 'Kırmızı', 'Yeşil', 
    'Sarı', 'Turuncu', 'Mor', 'Pembe', 'Kahverengi', 'Bej', 'Krem', 'Bordo'
]

for renk in renkler:
    Renk.objects.get_or_create(ad=renk)

print(f"Toplam {Renk.objects.count()} renk oluşturuldu.")
EOF

print_status "Creating default cash registers (kasalar)..."
sudo -u www-data $VENV_PYTHON $MANAGE_PY shell $SETTINGS << 'EOF'
from kasa.models import Kasa

# Varsayılan kasalar
kasalar = [
    {'ad': 'Ana Kasa', 'aciklama': 'Mağaza ana kasası'},
    {'ad': 'Online Satış', 'aciklama': 'Online satışlar için kasa'},
    {'ad': 'Kredi Kartı', 'aciklama': 'Kredi kartı ödemeleri'},
    {'ad': 'Nakit', 'aciklama': 'Nakit ödemeler'}
]

for kasa_data in kasalar:
    Kasa.objects.get_or_create(
        ad=kasa_data['ad'],
        defaults={'aciklama': kasa_data['aciklama'], 'aktif': True}
    )

print(f"Toplam {Kasa.objects.count()} kasa oluşturuldu.")
EOF

print_status "Creating default expense categories (gider kategorileri)..."
sudo -u www-data $VENV_PYTHON $MANAGE_PY shell $SETTINGS << 'EOF'
from gider.models import GiderKategori

# Gider kategorileri
kategoriler = [
    'Kira', 'Elektrik', 'Su', 'Doğalgaz', 'Telefon', 'İnternet',
    'Personel Maaşı', 'SGK Primleri', 'Vergi', 'Muhasebe',
    'Temizlik', 'Güvenlik', 'Sigorta', 'Reklam', 'Pazarlama',
    'Malzeme', 'Ofis Giderleri', 'Yakıt', 'Nakliye', 'Diğer'
]

for kategori in kategoriler:
    GiderKategori.objects.get_or_create(ad=kategori, aktif=True)

print(f"Toplam {GiderKategori.objects.count()} gider kategorisi oluşturuldu.")
EOF

print_status "Setting up admin user permissions..."
sudo -u www-data $VENV_PYTHON $MANAGE_PY shell $SETTINGS << 'EOF'
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission

User = get_user_model()

# Create admin group if not exists
admin_group, created = Group.objects.get_or_create(name='Admin')
if created:
    # Add all permissions to admin group
    permissions = Permission.objects.all()
    admin_group.permissions.set(permissions)
    print("Admin grubu oluşturuldu ve tüm yetkiler verildi.")

# Create cashier group
cashier_group, created = Group.objects.get_or_create(name='Kasiyer')
if created:
    # Add specific permissions for cashiers
    cashier_permissions = Permission.objects.filter(
        codename__in=[
            'view_satis', 'add_satis', 'change_satis',
            'view_musteri', 'add_musteri', 'change_musteri',
            'view_urun', 'view_urunvaryanti',
            'view_kasa', 'add_kasahareket'
        ]
    )
    cashier_group.permissions.set(cashier_permissions)
    print("Kasiyer grubu oluşturuldu ve gerekli yetkiler verildi.")

print("Kullanıcı grupları hazırlandı.")
EOF

print_status "Creating initial data completed successfully!"
print_warning "Don't forget to:"
echo "1. Change default admin password"
echo "2. Configure email settings in .env"
echo "3. Set up backup system"
echo "4. Configure monitoring"

print_status "Your NuviaButik.com is ready for business! 🎉"
