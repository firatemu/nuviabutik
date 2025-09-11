import os
import django
import json

# PostgreSQL environment
os.environ['DATABASE_URL'] = 'postgresql://nuviabutik_user:nuviabutik123@localhost/nuviabutik'
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'stoktakip.settings')
django.setup()

from django.db import transaction
from django.apps import apps

print('=== Smart Data Import ===')

# JSON dosyasını oku
with open('sqlite_data_export.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# Model gruplarına göre ayır
model_groups = {}
for obj in data:
    model_name = obj['model']
    if model_name not in model_groups:
        model_groups[model_name] = []
    model_groups[model_name].append(obj)

print(f'Found {len(model_groups)} different models')

# Öncelik sırası (bağımlılıklar nedeniyle)
priority_order = [
    'urun.renk',
    'urun.beden', 
    'gider.giderkategori',
    'kasa.kasa',
    'satis.siparisnumarasi',
    'kullanici.usersession',
    'kullanici.useractivitylog'
]

import_stats = {}

with transaction.atomic():
    for model_name in priority_order:
        if model_name in model_groups:
            print(f'\\nImporting {model_name}...')
            objects = model_groups[model_name]
            
            try:
                # Model classını al
                app_label, model_class = model_name.split('.')
                Model = apps.get_model(app_label, model_class)
                
                created_count = 0
                existing_count = 0
                
                for obj_data in objects:
                    fields = obj_data['fields']
                    pk = obj_data['pk']
                    
                    # get_or_create kullan
                    try:
                        instance, created = Model.objects.get_or_create(
                            pk=pk,
                            defaults=fields
                        )
                        if created:
                            created_count += 1
                        else:
                            existing_count += 1
                    except Exception as e:
                        print(f'  Error with {model_name} pk={pk}: {e}')
                
                import_stats[model_name] = {
                    'created': created_count,
                    'existing': existing_count
                }
                
                print(f'   {model_name}: {created_count} created, {existing_count} already existed')
                
            except Exception as e:
                print(f'   Error importing {model_name}: {e}')

print('\\n=== Import Summary ===')
for model_name, stats in import_stats.items():
    print(f'{model_name}: {stats[ created]} new, {stats[existing]} existing')

print('\\nData migration completed!')
