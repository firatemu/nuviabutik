import os
import django

os.environ['DATABASE_URL'] = 'postgresql://nuviabutik_user:nuviabutik123@localhost/nuviabutik'
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'stoktakip.settings')
django.setup()

from kullanici.models import CustomUser

# Admin kullanıcısı oluştur
admin_user, created = CustomUser.objects.get_or_create(
    username='admin',
    defaults={
        'email': 'admin@nuviabutik.com',
        'first_name': 'Admin',
        'last_name': 'User',
        'is_staff': True,
        'is_superuser': True,
        'role': 'yonetici'
    }
)
admin_user.set_password('nuviaadmin')
admin_user.save()

print('Admin user created/updated successfully')

# Test authentication
from django.contrib.auth import authenticate
user = authenticate(username='admin', password='nuviaadmin')
if user:
    print(' Authentication test successful')
else:
    print(' Authentication test failed')

print('PostgreSQL setup complete!')
