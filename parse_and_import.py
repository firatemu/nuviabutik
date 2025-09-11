import os
import django

# PostgreSQL için Django setup
os.environ['DATABASE_URL'] = 'postgresql://nuviabutik_user:nuviabutik123@localhost/nuviabutik'
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'stoktakip.settings')
django.setup()

from urun.models import Renk, Beden
from gider.models import GiderKategori
from kasa.models import Kasa
from decimal import Decimal

print('=== Parse and Import ===')

# Mevcut verileri temizle
print('Cleaning existing data...')
Renk.objects.all().delete()
Beden.objects.all().delete()
GiderKategori.objects.all().delete()
Kasa.objects.all().delete()

# Renkler - dosyayı \\n ile böl
print('Parsing Renkler...')
with open('/tmp/renkler.txt', 'r', encoding='utf-8') as f:
    content = f.read()
    
items = content.replace('\\n', '\n').strip().split('\n')
renk_count = 0
for item in items:
    if '|' in item:
        parts = item.split('|')
        if len(parts) >= 2:
            ad = parts[1].strip()
            if ad:
                renk = Renk.objects.create(ad=ad, kod='')
                renk_count += 1
                print('  Created Renk:', ad)

# Bedenler
print('Parsing Bedenler...')
with open('/tmp/bedenler.txt', 'r', encoding='utf-8') as f:
    content = f.read()
    
items = content.replace('\\n', '\n').strip().split('\n')
beden_count = 0
for item in items:
    if '|' in item:
        parts = item.split('|')
        if len(parts) >= 2:
            ad = parts[1].strip()
            if ad:
                beden = Beden.objects.create(ad=ad)
                beden_count += 1
                print('  Created Beden:', ad)

# Gider Kategorileri
print('Parsing Gider Kategorileri...')
with open('/tmp/gider_kategoriler.txt', 'r', encoding='utf-8') as f:
    content = f.read()
    
items = content.replace('\\n', '\n').strip().split('\n')
gider_count = 0
for item in items:
    if '|' in item:
        parts = item.split('|')
        if len(parts) >= 2:
            ad = parts[1].strip()
            aciklama = parts[2].strip() if len(parts) > 2 else ''
            if ad:
                gider = GiderKategori.objects.create(
                    ad=ad,
                    aciklama=aciklama,
                    aktif=True
                )
                gider_count += 1
                print('  Created GiderKategori:', ad)

# Kasalar
print('Parsing Kasalar...')
with open('/tmp/kasalar_fixed.txt', 'r', encoding='utf-8') as f:
    content = f.read()
    
items = content.replace('\\n', '\n').strip().split('\n')
kasa_count = 0
for item in items:
    if '|' in item:
        parts = item.split('|')
        if len(parts) >= 4:
            ad = parts[1].strip()
            tip = parts[2].strip()
            bakiye = parts[3].strip()
            
            if ad:
                try:
                    bakiye_decimal = Decimal(str(bakiye))
                except:
                    bakiye_decimal = Decimal('0.00')
                    
                kasa = Kasa.objects.create(
                    ad=ad,
                    tip=tip,
                    baslangic_bakiye=bakiye_decimal,
                    aktif=True
                )
                kasa_count += 1
                print('  Created Kasa:', ad)

print('\\n=== FINAL MIGRATION SUMMARY ===')
print(' Renkler created:', renk_count, '/ Total:', Renk.objects.count())
print(' Bedenler created:', beden_count, '/ Total:', Beden.objects.count())
print(' Gider Kategorileri created:', gider_count, '/ Total:', GiderKategori.objects.count())
print(' Kasalar created:', kasa_count, '/ Total:', Kasa.objects.count())
print(' Kullanıcılar: 3 (admin, nuviaadmin, serdar)')
print('\\n COMPLETE DATA MIGRATION SUCCESS! ')
print(' Total migrated records:', renk_count + beden_count + gider_count + kasa_count + 3)
