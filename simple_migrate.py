import os
import django
import sqlite3

# PostgreSQL environment
os.environ['DATABASE_URL'] = 'postgresql://nuviabutik_user:nuviabutik123@localhost/nuviabutik'
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'stoktakip.settings')
django.setup()

from django.db import transaction
from kullanici.models import CustomUser
from django.contrib.auth import authenticate

print('=== Simple Data Migration ===')

# SQLite connection
sqlite_conn = sqlite3.connect('db.sqlite3')
sqlite_conn.row_factory = sqlite3.Row
cursor = sqlite_conn.cursor()

# Read users from SQLite
cursor.execute('SELECT username, email, first_name, last_name, is_staff, is_superuser, is_active, date_joined, password FROM kullanici_customuser')
sqlite_users = cursor.fetchall()

print('Found users in SQLite:')
for user_row in sqlite_users:
    print('- Username:', user_row[0], 'Email:', user_row[1])

print('\\nMigrating to PostgreSQL...')

# Migrate users to PostgreSQL
with transaction.atomic():
    for user_row in sqlite_users:
        try:
            user, created = CustomUser.objects.get_or_create(
                username=user_row[0],
                defaults={
                    'email': user_row[1] or '',
                    'first_name': user_row[2] or '',
                    'last_name': user_row[3] or '',
                    'is_staff': bool(user_row[4]),
                    'is_superuser': bool(user_row[5]),
                    'is_active': bool(user_row[6]),
                    'date_joined': user_row[7],
                    'password': user_row[8],
                    'role': 'yonetici' if user_row[5] else 'calisan'
                }
            )
            if created:
                print(' Created:', user.username)
            else:
                print('  Already exists:', user.username)
                
        except Exception as e:
            print(' Error with', user_row[0], ':', str(e))

sqlite_conn.close()
print('Migration completed!')
