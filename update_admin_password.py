#!/usr/bin/env python
import os
import django
import sys

# Django ayarlarını yükle
sys.path.append('/var/www/nuviabutik')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'stoktakip.settings')
django.setup()

from django.contrib.auth import get_user_model

try:
    User = get_user_model()
    
    # Admin kullanıcısını bul ve şifresini güncelle
    username = 'admin'
    new_password = '8423Azem'
    
    user = User.objects.get(username=username)
    user.set_password(new_password)
    user.save()
    
    print(f"✅ Admin kullanıcısının şifresi başarıyla güncellendi!")
    print(f"Kullanıcı adı: {username}")
    print(f"Yeni şifre: {new_password}")
    print(f"Admin paneli: https://31.57.33.34/admin/")
    
except User.DoesNotExist:
    print(f"❌ '{username}' kullanıcısı bulunamadı!")
except Exception as e:
    print(f"❌ Hata: {e}")
