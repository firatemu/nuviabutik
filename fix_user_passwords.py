import os
import django

# PostgreSQL için Django setup
os.environ['DATABASE_URL'] = 'postgresql://nuviabutik_user:nuviabutik123@localhost/nuviabutik'
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'stoktakip.settings')
django.setup()

from kullanici.models import CustomUser
from django.contrib.auth import authenticate

print('=== Fixing User Passwords ===')

# Tüm kullanıcıları al ve şifrelerini ayarla
users_passwords = {
    'admin': 'nuviaadmin',
    'nuviaadmin': 'nuviaadmin',
    'serdar': 'nuviaadmin'
}

for username, password in users_passwords.items():
    try:
        user = CustomUser.objects.get(username=username)
        user.set_password(password)
        user.save()
        print(' Password set for:', username)
        
        # Test authentication
        auth_user = authenticate(username=username, password=password)
        if auth_user:
            print(' Authentication test passed for:', username)
        else:
            print(' Authentication test failed for:', username)
            
    except CustomUser.DoesNotExist:
        print(' User not found:', username)
    except Exception as e:
        print(' Error for', username, ':', str(e))

print('\n=== Password Fix Complete ===')
print('All users should now be able to login with password: nuviaadmin')
