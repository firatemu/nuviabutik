import os
import django
import json
from decimal import Decimal
from datetime import datetime, date

# SQLite için Django setup
os.environ.pop('DATABASE_URL', None)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'stoktakip.settings')
django.setup()

from django.apps import apps
from django.core import serializers

print('=== Exporting All SQLite Data ===')

def custom_serializer(obj):
    if isinstance(obj, Decimal):
        return float(obj)
    elif isinstance(obj, (datetime, date)):
        return obj.isoformat()
    raise TypeError(f Object of type -encodedCommand dAB5AHAAZQAoAG8AYgBqACkALgBfAF8AbgBhAG0AZQBfAF8A is not JSON serializable)

all_data = {}

# Önemli modeller
important_models = [
    'kullanici.CustomUser',
    'kullanici.UserSession', 
    'kullanici.UserActivityLog',
    'urun.Renk',
    'urun.Beden',
    'satis.SiparisNumarasi',
    'gider.GiderKategori',
    'kasa.Kasa'
]

for app_config in apps.get_app_configs():
    if app_config.name in ['django.contrib.admin', 'django.contrib.auth', 'django.contrib.contenttypes', 'django.contrib.sessions']:
        continue
        
    for model in app_config.get_models():
        model_key = f'{model._meta.app_label}.{model.__name__}'
        
        try:
            count = model.objects.count()
            if count > 0:
                print(f'Exporting {model_key}: {count} records')
                
                # Django serializer kullan
                serialized_data = serializers.serialize('json', model.objects.all())
                all_data[model_key] = json.loads(serialized_data)
                
        except Exception as e:
            print(f'Error exporting {model_key}: {str(e)}')

# JSON dosyasına kaydet
with open('/tmp/sqlite_all_data.json', 'w', encoding='utf-8') as f:
    json.dump(all_data, f, indent=2, ensure_ascii=False, default=custom_serializer)

print(f'\\nExport complete!')
print(f'Total models exported: {len(all_data)}')
print(f'Data saved to: /tmp/sqlite_all_data.json')

# Dosya boyutunu göster
import os
file_size = os.path.getsize('/tmp/sqlite_all_data.json')
print(f'File size: {file_size / 1024:.2f} KB')
EOF -inputFormat xml -outputFormat text
