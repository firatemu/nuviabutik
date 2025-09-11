import os
import django

# SQLite için Django setup
os.environ.pop('DATABASE_URL', None)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'stoktakip.settings')
django.setup()

from gider.models import GiderKategori
from kasa.models import Kasa

print('=== Model Fields Check ===')

# GiderKategori fields
print('GiderKategori fields:')
for field in GiderKategori._meta.fields:
    print('  ', field.name)

if GiderKategori.objects.exists():
    gider = GiderKategori.objects.first()
    print('Sample GiderKategori:', gider, '- dir:', [attr for attr in dir(gider) if not attr.startswith('_')])

# Kasa fields
print('\\nKasa fields:')
for field in Kasa._meta.fields:
    print('  ', field.name)

if Kasa.objects.exists():
    kasa = Kasa.objects.first()
    print('Sample Kasa:', kasa, '- dir:', [attr for attr in dir(kasa) if not attr.startswith('_')])
