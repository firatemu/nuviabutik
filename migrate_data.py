import os
import django
import sqlite3
from datetime import datetime

# PostgreSQL environment'ı ayarla
os.environ['DATABASE_URL'] = 'postgresql://nuviabutik_user:nuviabutik123@localhost/nuviabutik'
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'stoktakip.settings')
django.setup()

from django.db import transaction
from kullanici.models import CustomUser

print('=== Data Migration Script ===')

# SQLite'dan verileri oku
sqlite_conn = sqlite3.connect('db.sqlite3')
sqlite_conn.row_factory = sqlite3.Row
cursor = sqlite_conn.cursor()

print('Reading SQLite data...')

# Kullanıcıları oku
cursor.execute('SELECT * FROM kullanici_customuser')
sqlite_users = cursor.fetchall()

print(f'Found {len(sqlite_users)} users in SQLite')

# PostgreSQL'e kullanıcıları aktar
with transaction.atomic():
    for user_row in sqlite_users:
        try:
            user, created = CustomUser.objects.get_or_create(
                username=user_row['username'],
                defaults={
                    'email': user_row['email'] or '',
                    'first_name': user_row['first_name'] or '',
                    'last_name': user_row['last_name'] or '',
                    'is_staff': bool(user_row['is_staff']),
                    'is_superuser': bool(user_row['is_superuser']),
                    'is_active': bool(user_row['is_active']),
                    'date_joined': user_row['date_joined'],
                    'password': user_row['password'],
                    'role': user_row.get('role', 'calisan')
                }
            )
            if created:
                print(f' Created user: {user.username}')
            else:
                print(f'  User already exists: {user.username}')
                
        except Exception as e:
            print(f' Error with user {user_row[ username]}: {e}')

sqlite_conn.close()

print('Data migration completed!')

# Test authentication
from django.contrib.auth import authenticate
test_users = ['admin', 'nuviaadmin', 'serdar']
for username in test_users:
    user = authenticate(username=username, password='nuviaadmin')
    if user:
        print(f' Auth test OK: {username}')
    else:
        print(f' Auth test FAILED: {username}')
