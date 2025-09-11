import os
import django
import json
from datetime import datetime

# PostgreSQL için Django setup
os.environ['DATABASE_URL'] = 'postgresql://nuviabutik_user:nuviabutik123@localhost/nuviabutik'
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'stoktakip.settings')
django.setup()

from kullanici.models import CustomUser
from django.utils import timezone

print('=== Importing Users to PostgreSQL ===')

# JSON dosyasını oku
with open('/tmp/sqlite_users.json', 'r', encoding='utf-8') as f:
    users_data = json.load(f)

for user_data in users_data:
    try:
        username = user_data['username']
        
        # Kullanıcı var mı kontrol et
        existing_user = CustomUser.objects.filter(username=username).first()
        
        if existing_user:
            print('User', username, 'already exists, updating...')
            user = existing_user
        else:
            print('Creating new user:', username)
            user = CustomUser()
        
        # Verileri set et
        user.username = user_data['username']
        user.email = user_data['email']
        user.first_name = user_data['first_name']
        user.last_name = user_data['last_name']
        user.password = user_data['password']  # Already hashed
        user.is_active = user_data['is_active']
        user.is_staff = user_data['is_staff']
        user.is_superuser = user_data['is_superuser']
        user.role = user_data.get('role', 'calisan')
        
        # Date fields
        if user_data['date_joined']:
            user.date_joined = datetime.fromisoformat(user_data['date_joined'].replace('Z', '+00:00'))
        if user_data['last_login']:
            user.last_login = datetime.fromisoformat(user_data['last_login'].replace('Z', '+00:00'))
        
        user.save()
        print(' Successfully imported:', username)
        
    except Exception as e:
        print(' Error importing:', username, ':', str(e))

print('\n=== Import Complete ===')
print('Total users in PostgreSQL:', CustomUser.objects.count())

# Test authentication
from django.contrib.auth import authenticate
test_users = ['admin', 'nuviaadmin', 'serdar']
for username in test_users:
    user = authenticate(username=username, password='nuviaadmin')
    if user:
        print('', username, 'authentication: SUCCESS')
    else:
        print('', username, 'authentication: FAILED')
