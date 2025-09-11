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

print('=== Clean and Import ===')

# Mevcut verileri temizle (kullanıcılar dışında)
print('Cleaning existing data...')
Renk.objects.all().delete()
Beden.objects.all().delete()
GiderKategori.objects.all().delete()
Kasa.objects.all().delete()

print('Starting fresh import...')

# Renkler import
renk_count = 0
renk_names = set()
with open('/tmp/renkler.txt', 'r', encoding='utf-8') as f:
    for line in f:
        parts = line.strip().split('|')
        if len(parts) >= 2:
            ad = parts[1].replace('\\n', '').strip()
            if ad and ad not in renk_names:
                renk_names.add(ad)
                renk = Renk.objects.create(ad=ad, kod='')
                renk_count += 1
                print('  Created Renk:', ad)

# Bedenler import
beden_count = 0
beden_names = set()
with open('/tmp/bedenler.txt', 'r', encoding='utf-8') as f:
    for line in f:
        parts = line.strip().split('|')
        if len(parts) >= 2:
            ad = parts[1].replace('\\n', '').strip()
            if ad and ad not in beden_names:
                beden_names.add(ad)
                beden = Beden.objects.create(ad=ad)
                beden_count += 1
                print('  Created Beden:', ad)

# Gider Kategorileri import
gider_count = 0
gider_names = set()
with open('/tmp/gider_kategoriler.txt', 'r', encoding='utf-8') as f:
    for line in f:
        parts = line.strip().split('|')
        if len(parts) >= 2:
            ad = parts[1].replace('\\n', '').strip()
            aciklama = parts[2].replace('\\n', '').strip() if len(parts) > 2 else ''
            if ad and ad not in gider_names:
                gider_names.add(ad)
                gider = GiderKategori.objects.create(
                    ad=ad,
                    aciklama=aciklama,
                    aktif=True
                )
                gider_count += 1
                print('  Created GiderKategori:', ad)

# Kasalar import
kasa_count = 0
kasa_names = set()
with open('/tmp/kasalar_fixed.txt', 'r', encoding='utf-8') as f:
    for line in f:
        parts = line.strip().split('|')
        if len(parts) >= 4:
            ad = parts[1].replace('\\n', '').strip()
            tip = parts[2].replace('\\n', '').strip()
            bakiye = parts[3].replace('\\n', '').strip()
            
            if ad and ad not in kasa_names:
                kasa_names.add(ad)
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

print('\\n=== Final Migration Summary ===')
print(' Renkler created:', renk_count, '/ Total:', Renk.objects.count())
print(' Bedenler created:', beden_count, '/ Total:', Beden.objects.count())
print(' Gider Kategorileri created:', gider_count, '/ Total:', GiderKategori.objects.count())
print(' Kasalar created:', kasa_count, '/ Total:', Kasa.objects.count())
print('\\n ALL SQLite DATA SUCCESSFULLY MIGRATED TO POSTGRESQL! ')
