import os
import django

# Environment variable'ı set et
os.environ['DATABASE_URL'] = 'postgresql://nuviabutik_user:nuviabutik123@localhost/nuviabutik'

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'stoktakip.settings')
django.setup()

from django.conf import settings
print('DATABASE_URL from env:', os.environ.get('DATABASE_URL'))
print('Django DB Engine:', settings.DATABASES['default']['ENGINE'])
print('Django DB Name:', settings.DATABASES['default']['NAME'])
