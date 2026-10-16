"""
WSL / local development settings.

Kullanım:
    export DJANGO_SETTINGS_MODULE=stoktakip.local
    python manage.py migrate
    python manage.py runserver

Prod settings (`stoktakip.settings`) dokunulmaz; sadece DEBUG/DB/cache
varsayılanları ezilir. Tüm production davranışı aynıdır.
"""

import os

# settings.py import edilmeden önce DEBUG=True ve SECRET_KEY ayarlanmalı,
# yoksa "SECRET_KEY required when DEBUG=False" hatası fırlatır.
os.environ.setdefault('DEBUG', 'True')
os.environ.setdefault('SECRET_KEY', 'django-insecure-local-dev-only')
os.environ.setdefault('DATABASE_URL', '')  # SQLite'a düşmesi için
os.environ.setdefault('USE_REDIS_CACHE', 'False')

from .settings import *  # noqa: F401,F403

DEBUG = True
SECRET_KEY = os.environ.get(
    'SECRET_KEY',
    'django-insecure-local-dev-only-do-not-use-in-prod',
)

# Localde SQLite (ek kurulum yok)
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',  # noqa: F405
    }
}

# Redis olmadan geliştir
USE_REDIS_CACHE = False
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'nuviabutik-local',
    }
}
SESSION_ENGINE = 'django.contrib.sessions.backends.db'

# Localde HTTPS zorunluluğunu kapat
SECURE_SSL_REDIRECT = False
SECURE_PROXY_SSL_HEADER = None
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False

# Localde tüm hostlar kabul
ALLOWED_HOSTS = ['*']  # noqa: F405

# E-posta: stdout'a yaz
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# Print agent endpoint'leri localde çalışmaz; sadece debug bayrağı
NUVIA_PRINT_AGENT_DEBUG = True
