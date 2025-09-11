#!/usr/bin/env python
import os
import django
import sys

# Django ayarlarını yükle
sys.path.append('/var/www/nuviabutik')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'stoktakip.settings')
django.setup()

from django.contrib.auth import get_user_model
User = get_user_model()

try:
    # Mevcut admin kullanıcılarını listele
    print("=== Mevcut Admin Kullanıcıları ===")
    admin_users = User.objects.filter(is_superuser=True)
    
    if admin_users.exists():
        for user in admin_users:
            print(f"Username: {user.username}")
            print(f"Email: {user.email}")
            print(f"Aktif: {user.is_active}")
            print(f"Son giriş: {user.last_login}")
            print("-" * 30)
    else:
        print("Hiç admin kullanıcısı bulunamadı!")
    
    # Yeni admin kullanıcısı oluştur veya mevcut olanın şifresini güncelle
    username = 'admin'
    email = 'admin@nuviabutik.com'
    password = 'admin123456'
    
    try:
        user = User.objects.get(username=username)
        user.set_password(password)
        user.is_active = True
        user.is_staff = True
        user.is_superuser = True
        user.email = email
        user.save()
        print(f"Mevcut admin kullanıcısının şifresi güncellendi!")
    except User.DoesNotExist:
        user = User.objects.create_superuser(username, email, password)
        print(f"Yeni admin kullanıcısı oluşturuldu!")
    
    print(f"\n=== GİRİŞ BİLGİLERİ ===")
    print(f"Kullanıcı adı: {username}")
    print(f"Şifre: {password}")
    print(f"Email: {email}")
    print(f"Admin paneli: https://31.57.33.34/admin/")
    
except Exception as e:
    print(f"Hata: {e}")
