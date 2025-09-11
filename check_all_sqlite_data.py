import os
import django

# SQLite için Django setup
os.environ.pop('DATABASE_URL', None)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'stoktakip.settings')
django.setup()

from django.apps import apps

print('=== All SQLite Data Check ===')

# Tüm modelleri kontrol et
total_records = 0
models_with_data = []

for app_config in apps.get_app_configs():
    if app_config.name in ['django.contrib.admin', 'django.contrib.auth', 'django.contrib.contenttypes', 'django.contrib.sessions']:
        continue
        
    for model in app_config.get_models():
        try:
            count = model.objects.count()
            if count > 0:
                print(f'{model._meta.app_label}.{model.__name__}: {count} records')
                models_with_data.append({
                    'app': model._meta.app_label,
                    'model': model.__name__,
                    'count': count,
                    'model_class': model
                })
                total_records += count
        except Exception as e:
            print(f'Error checking {model._meta.app_label}.{model.__name__}: {str(e)}')

print(f'\nTotal models with data: {len(models_with_data)}')
print(f'Total records: {total_records}')

# İlk birkaç record'u göster
for model_info in models_with_data:
    if model_info['count'] > 0:
        try:
            print(f'\n--- {model_info[ app]}.{model_info[model]} Sample Records ---')
            model_class = model_info['model_class']
            for obj in model_class.objects.all()[:3]:
                print(f'  ID: {obj.pk} - {str(obj)[:100]}')
        except Exception as e:
            print(f'  Error showing samples: {str(e)}')
