import os
import django
import json

# SQLite için Django setup
os.environ.pop('DATABASE_URL', None)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'stoktakip.settings')
django.setup()

from kullanici.models import CustomUser

print('=== Exporting SQLite Users ===')
users_data = []

for user in CustomUser.objects.all():
    user_data = {
        'id': user.id,
        'username': user.username,
        'email': user.email,
        'first_name': user.first_name,
        'last_name': user.last_name,
        'password': user.password,  # hashed password
        'is_active': user.is_active,
        'is_staff': user.is_staff,
        'is_superuser': user.is_superuser,
        'date_joined': user.date_joined.isoformat() if user.date_joined else None,
        'last_login': user.last_login.isoformat() if user.last_login else None,
        'role': getattr(user, 'role', 'calisan'),
    }
    users_data.append(user_data)
    print('Exported user:', user.username)

# JSON dosyasına kaydet
with open('/tmp/sqlite_users.json', 'w', encoding='utf-8') as f:
    json.dump(users_data, f, indent=2, ensure_ascii=False)

print('Users exported to /tmp/sqlite_users.json')
print('Total users:', len(users_data))
