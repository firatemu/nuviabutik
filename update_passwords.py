import os
import django

# PostgreSQL environment
os.environ['DATABASE_URL'] = 'postgresql://nuviabutik_user:nuviabutik123@localhost/nuviabutik'
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'stoktakip.settings')
django.setup()

from kullanici.models import CustomUser
from django.contrib.auth.hashers import make_password

print('=== Updating All User Passwords ===')

# Yeni şifre
new_password = '8423Azem'

# Tüm kullanıcıları al
users = CustomUser.objects.all()

print(f'Found {users.count()} users')

for user in users:
    old_password_hash = user.password[:20] + '...'
    
    # Şifreyi güncelle
    user.set_password(new_password)
    user.save()
    
    # Test authentication
    from django.contrib.auth import authenticate
    test_user = authenticate(username=user.username, password=new_password)
    
    if test_user:
        print(f' {user.username}: Password updated and verified')
    else:
        print(f' {user.username}: Password update failed')

print(f'\\nAll user passwords have been set to: {new_password}')

print('\\n=== Testing Login for All Users ===')
usernames = ['admin', 'nuviaadmin', 'serdar']
for username in usernames:
    user = authenticate(username=username, password=new_password)
    if user:
        print(f' Login test OK: {username}')
    else:
        print(f' Login test FAILED: {username}')

print('Password update completed!')
