import os
import django

# SQLite için Django setup
os.environ.pop('DATABASE_URL', None)  # PostgreSQL config'ini kaldır
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'stoktakip.settings')
django.setup()

from kullanici.models import CustomUser
from django.contrib.auth.models import User

print('=== SQLite Database Check ===')
try:
    users = CustomUser.objects.all()
    print('CustomUser count:', users.count())
    for user in users:
        print('  User:', user.username, '(ID:', user.id, ')')
except Exception as e:
    print('CustomUser error:', str(e))

try:
    # Diğer modelleri import et
    from urun.models import Urun
    products = Urun.objects.all()
    print('Products count:', products.count())
except Exception as e:
    print('Products error:', str(e))

try:
    from musteri.models import Musteri
    customers = Musteri.objects.all()
    print('Customers count:', customers.count())
except Exception as e:
    print('Customers error:', str(e))

try:
    from satis.models import Satis
    sales = Satis.objects.all()
    print('Sales count:', sales.count())
except Exception as e:
    print('Sales error:', str(e))
