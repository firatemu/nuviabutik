import os
import django

# SQLite için Django setup
os.environ.pop('DATABASE_URL', None)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'stoktakip.settings')
django.setup()

from kasa.models import Kasa

print('=== Fixed Kasa Export ===')

with open('/tmp/kasalar_fixed.txt', 'w', encoding='utf-8') as f:
    for kasa in Kasa.objects.all():
        # bakiye() method çağırılmalı
        try:
            bakiye_value = kasa.bakiye()
        except:
            bakiye_value = kasa.baslangic_bakiye
        
        f.write(str(kasa.id) + '|' + kasa.ad + '|' + kasa.tip + '|' + str(bakiye_value) + '\\n')
        print('Exported Kasa:', kasa.ad, 'Bakiye:', bakiye_value)

print('Fixed kasa file created: /tmp/kasalar_fixed.txt')
