import os
import django

# SQLite için environment ayarını geçici olarak kaldır
if 'DATABASE_URL' in os.environ:
    del os.environ['DATABASE_URL']

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'stoktakip.settings')
django.setup()

from django.core.management import call_command
from django.core import serializers
from django.apps import apps
import json

print('=== Exporting data from SQLite ===')

# Tüm modelleri al (auth ve admin hariç)
all_models = apps.get_models()
app_models = []

for model in all_models:
    app_label = model._meta.app_label
    if app_label not in ['auth', 'admin', 'contenttypes', 'sessions']:
        app_models.append(f'{app_label}.{model.__name__}')

print('Models to export:', app_models)

# Her model için veri sayısını kontrol et
for model_name in app_models:
    try:
        app_label, model_class = model_name.split('.')
        model = apps.get_model(app_label, model_class)
        count = model.objects.count()
        print(f'{model_name}: {count} records')
    except Exception as e:
        print(f'{model_name}: error - {e}')

# Verileri export et
try:
    print('\\nExporting data to fixture...')
    with open('sqlite_data_export.json', 'w', encoding='utf-8') as f:
        call_command('dumpdata', *app_models, stdout=f, indent=2, use_natural_foreign_keys=True)
    print(' Data exported to sqlite_data_export.json')
except Exception as e:
    print(f' Export error: {e}')
