import os
import django

# PostgreSQL environment'ı ayarla
os.environ['DATABASE_URL'] = 'postgresql://nuviabutik_user:nuviabutik123@localhost/nuviabutik'
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'stoktakip.settings')
django.setup()

from django.core.management import call_command
from django.db import transaction

print('=== Importing data to PostgreSQL ===')

try:
    # Önce mevcut kullanıcıları korumak için fixture'dan kullanıcıları çıkar
    print('Processing fixture data...')
    
    import json
    with open('sqlite_data_export.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # CustomUser kayıtlarını filtrele (çünkü zaten var)
    filtered_data = [obj for obj in data if obj['model'] != 'kullanici.customuser']
    
    print(f'Original objects: {len(data)}')
    print(f'Filtered objects (without users): {len(filtered_data)}')
    
    # Filtrelenmiş veriyi yeni dosyaya yaz
    with open('filtered_data.json', 'w', encoding='utf-8') as f:
        json.dump(filtered_data, f, indent=2, ensure_ascii=False)
    
    # PostgreSQL'e import et
    print('Importing to PostgreSQL...')
    with transaction.atomic():
        call_command('loaddata', 'filtered_data.json', verbosity=2)
    
    print(' Data import completed successfully!')
    
except Exception as e:
    print(f' Import error: {e}')
    import traceback
    traceback.print_exc()
