import os
import django

# SQLite için Django setup
os.environ.pop('DATABASE_URL', None)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'stoktakip.settings')
django.setup()

from kullanici.models import CustomUser, UserSession, UserActivityLog
from urun.models import Renk, Beden
from satis.models import SiparisNumarasi  
from gider.models import GiderKategori
from kasa.models import Kasa

print('=== Quick Data Export ===')

# Kullanıcılar zaten transfer edildi

# Renkler
print('Renk records:', Renk.objects.count())
renk_file = open('/tmp/renkler.txt', 'w', encoding='utf-8')
for renk in Renk.objects.all():
    renk_file.write(f'{renk.id}|{renk.ad}\\n')
renk_file.close()

# Bedenler  
print('Beden records:', Beden.objects.count())
beden_file = open('/tmp/bedenler.txt', 'w', encoding='utf-8')
for beden in Beden.objects.all():
    beden_file.write(f'{beden.id}|{beden.ad}\\n')
beden_file.close()

# Gider Kategorileri
print('GiderKategori records:', GiderKategori.objects.count())
gider_file = open('/tmp/gider_kategoriler.txt', 'w', encoding='utf-8')
for gider in GiderKategori.objects.all():
    gider_file.write(f'{gider.id}|{gider.kategori_adi}\\n')
gider_file.close()

# Kasa
print('Kasa records:', Kasa.objects.count())
kasa_file = open('/tmp/kasalar.txt', 'w', encoding='utf-8')
for kasa in Kasa.objects.all():
    kasa_file.write(f'{kasa.id}|{kasa.ad}|{kasa.bakiye}\\n')
kasa_file.close()

print('Files created in /tmp/')
