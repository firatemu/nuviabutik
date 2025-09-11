import os
import django

os.environ['DATABASE_URL'] = 'postgresql://nuviabutik_user:nuviabutik123@localhost/nuviabutik'
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'stoktakip.settings')
django.setup()

from kullanici.models import CustomUser
from urun.models import Renk, Beden
from gider.models import GiderKategori
from kasa.models import Kasa
from satis.models import SiparisNumarasi

print('=== PostgreSQL Data Summary ===')
print('Users:', CustomUser.objects.count())
print('Colors (Renk):', Renk.objects.count())
print('Sizes (Beden):', Beden.objects.count()) 
print('Expense Categories:', GiderKategori.objects.count())
print('Cash Registers (Kasa):', Kasa.objects.count())
print('Order Numbers:', SiparisNumarasi.objects.count())

print('\\n=== Sample Data ===')
print('Colors:', [r.ad for r in Renk.objects.all()[:10]])
print('Sizes:', [b.ad for b in Beden.objects.all()[:10]])
print('Cash Registers:', [k.ad for k in Kasa.objects.all()])
