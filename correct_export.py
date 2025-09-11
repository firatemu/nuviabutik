import os
import django

# SQLite için Django setup
os.environ.pop('DATABASE_URL', None)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'stoktakip.settings')
django.setup()

from kullanici.models import CustomUser
from urun.models import Renk, Beden
from gider.models import GiderKategori
from kasa.models import Kasa

print('=== Correct Data Export ===')

# Renkler
print('Exporting Renk records:', Renk.objects.count())
with open('/tmp/renkler.txt', 'w', encoding='utf-8') as f:
    for renk in Renk.objects.all():
        f.write(f'{renk.id}|{renk.ad}\\n')

# Bedenler  
print('Exporting Beden records:', Beden.objects.count())
with open('/tmp/bedenler.txt', 'w', encoding='utf-8') as f:
    for beden in Beden.objects.all():
        f.write(f'{beden.id}|{beden.ad}\\n')

# Gider Kategorileri (field adı: ad)
print('Exporting GiderKategori records:', GiderKategori.objects.count())
with open('/tmp/gider_kategoriler.txt', 'w', encoding='utf-8') as f:
    for gider in GiderKategori.objects.all():
        f.write(f'{gider.id}|{gider.ad}|{gider.aciklama or }\\n')

# Kasa (field adı: ad, bakiye property)
print('Exporting Kasa records:', Kasa.objects.count())
with open('/tmp/kasalar.txt', 'w', encoding='utf-8') as f:
 for kasa in Kasa.objects.all():
 bakiye = getattr(kasa, 'bakiye', kasa.baslangic_bakiye)
 f.write(f'{kasa.id}|{kasa.ad}|{kasa.tip}|{bakiye}\\n')

print('\\nExport files created:')
print(' /tmp/renkler.txt')
print(' /tmp/bedenler.txt') 
print(' /tmp/gider_kategoriler.txt')
print(' /tmp/kasalar.txt')
