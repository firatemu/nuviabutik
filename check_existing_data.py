import os
import django

# PostgreSQL için Django setup
os.environ['DATABASE_URL'] = 'postgresql://nuviabutik_user:nuviabutik123@localhost/nuviabutik'
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'stoktakip.settings')
django.setup()

from urun.models import Renk, Beden
from gider.models import GiderKategori
from kasa.models import Kasa

print('=== Existing Data in PostgreSQL ===')

print('Renkler:', Renk.objects.count())
for renk in Renk.objects.all()[:5]:
    print('  ', renk.id, '-', renk.ad, '- kod:', getattr(renk, 'kod', 'None'))

print('Bedenler:', Beden.objects.count())
for beden in Beden.objects.all()[:5]:
    print('  ', beden.id, '-', beden.ad)

print('Gider Kategorileri:', GiderKategori.objects.count())
for gider in GiderKategori.objects.all()[:5]:
    print('  ', gider.id, '-', gider.ad)

print('Kasalar:', Kasa.objects.count())
for kasa in Kasa.objects.all():
    print('  ', kasa.id, '-', kasa.ad, '-', kasa.tip)
