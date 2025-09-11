import os
import django

# SQLite için Django setup
os.environ.pop('DATABASE_URL', None)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'stoktakip.settings')
django.setup()

from urun.models import Renk, Beden
from gider.models import GiderKategori
from kasa.models import Kasa

print('=== Final Data Export ===')

# Renkler
print('Exporting Renk records:', Renk.objects.count())
with open('/tmp/renkler.txt', 'w', encoding='utf-8') as f:
    for renk in Renk.objects.all():
        f.write(str(renk.id) + '|' + renk.ad + '\\n')

# Bedenler  
print('Exporting Beden records:', Beden.objects.count())
with open('/tmp/bedenler.txt', 'w', encoding='utf-8') as f:
    for beden in Beden.objects.all():
        f.write(str(beden.id) + '|' + beden.ad + '\\n')

# Gider Kategorileri
print('Exporting GiderKategori records:', GiderKategori.objects.count())
with open('/tmp/gider_kategoriler.txt', 'w', encoding='utf-8') as f:
    for gider in GiderKategori.objects.all():
        aciklama = gider.aciklama if gider.aciklama else ''
        f.write(str(gider.id) + '|' + gider.ad + '|' + aciklama + '\\n')

# Kasa
print('Exporting Kasa records:', Kasa.objects.count())
with open('/tmp/kasalar.txt', 'w', encoding='utf-8') as f:
    for kasa in Kasa.objects.all():
        bakiye = getattr(kasa, 'bakiye', kasa.baslangic_bakiye)
        f.write(str(kasa.id) + '|' + kasa.ad + '|' + kasa.tip + '|' + str(bakiye) + '\\n')

print('\\nExport completed successfully!')
