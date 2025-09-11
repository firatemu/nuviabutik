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

print('=== Safe Import to PostgreSQL ===')

# Renkler import (sadece ad field'a göre)
print('Importing Renkler...')
renk_count = 0
with open('/tmp/renkler.txt', 'r', encoding='utf-8') as f:
    for line in f:
        parts = line.strip().replace('\\n', '').split('|')
        if len(parts) >= 2:
            ad = parts[1]
            renk, created = Renk.objects.get_or_create(ad=ad)
            if created:
                renk_count += 1
                print('  Created Renk:', ad)

# Bedenler import
print('Importing Bedenler...')
beden_count = 0
with open('/tmp/bedenler.txt', 'r', encoding='utf-8') as f:
    for line in f:
        parts = line.strip().replace('\\n', '').split('|')
        if len(parts) >= 2:
            ad = parts[1]
            beden, created = Beden.objects.get_or_create(ad=ad)
            if created:
                beden_count += 1
                print('  Created Beden:', ad)

# Gider Kategorileri import
print('Importing Gider Kategorileri...')
gider_count = 0
with open('/tmp/gider_kategoriler.txt', 'r', encoding='utf-8') as f:
    for line in f:
        parts = line.strip().replace('\\n', '').split('|')
        if len(parts) >= 2:
            ad = parts[1]
            aciklama = parts[2] if len(parts) > 2 else ''
            gider, created = GiderKategori.objects.get_or_create(
                ad=ad,
                defaults={
                    'aciklama': aciklama,
                    'aktif': True
                }
            )
            if created:
                gider_count += 1
                print('  Created GiderKategori:', ad)

# Kasalar import
print('Importing Kasalar...')
kasa_count = 0
with open('/tmp/kasalar_fixed.txt', 'r', encoding='utf-8') as f:
    for line in f:
        parts = line.strip().replace('\\n', '').split('|')
        if len(parts) >= 4:
            ad, tip, bakiye = parts[1], parts[2], parts[3]
            try:
                bakiye_decimal = Decimal(str(bakiye))
            except:
                bakiye_decimal = Decimal('0.00')
                
            kasa, created = Kasa.objects.get_or_create(
                ad=ad,
                defaults={
                    'tip': tip,
                    'baslangic_bakiye': bakiye_decimal,
                    'aktif': True
                }
            )
            if created:
                kasa_count += 1
                print('  Created Kasa:', ad)

print('\\n=== Safe Import Summary ===')
print('New Renkler created:', renk_count, '/ Total:', Renk.objects.count())
print('New Bedenler created:', beden_count, '/ Total:', Beden.objects.count())
print('New Gider Kategorileri created:', gider_count, '/ Total:', GiderKategori.objects.count())
print('New Kasalar created:', kasa_count, '/ Total:', Kasa.objects.count())
print('\\n Safe data migration completed successfully!')
