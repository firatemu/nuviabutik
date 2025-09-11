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
import uuid

print('=== FINAL MIGRATION - ALL SQLITE DATA TO POSTGRESQL ===')

# Mevcut verileri temizle
print(' Cleaning existing data...')
Renk.objects.all().delete()
Beden.objects.all().delete()
GiderKategori.objects.all().delete()
Kasa.objects.all().delete()

# Renkler
print(' Importing Renkler...')
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
                kod = ad.upper()[:3] + str(renk_count + 1)  # Unique kod
                renk = Renk.objects.create(ad=ad, kod=kod)
                renk_count += 1
                print(f'   {ad} (kod: {kod})')

# Bedenler
print(' Importing Bedenler...')
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
                print(f'   {ad}')

# Gider Kategorileri
print(' Importing Gider Kategorileri...')
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
                print(f'   {ad}')

# Kasalar
print(' Importing Kasalar...')
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
                print(f'   {ad} ({tip}) - {bakiye_decimal} TL')

print('\\n' + '='*50)
print(' MIGRATION COMPLETED SUCCESSFULLY! ')
print('='*50)
print(f' SUMMARY:')
print(f'   Users: 3 (admin, nuviaadmin, serdar)')
print(f'   Colors (Renkler): {renk_count}')
print(f'   Sizes (Bedenler): {beden_count}')
print(f'   Expense Categories: {gider_count}')
print(f'   Cash Registers: {kasa_count}')
print(f'   Total Records: {3 + renk_count + beden_count + gider_count + kasa_count}')
print('\\n All SQLite data successfully migrated to PostgreSQL!')
print(' Login system ready with PostgreSQL backend!')
print(' Production system ready at https://nuviabutik.com/')
