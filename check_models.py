import os
import django

# PostgreSQL environment
os.environ['DATABASE_URL'] = 'postgresql://nuviabutik_user:nuviabutik123@localhost/nuviabutik'
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'stoktakip.settings')
django.setup()

from kullanici.models import CustomUser

try:
    from urun.models import Urun
    urun_count = Urun.objects.count()
    print('Urun (Products):', urun_count)
except:
    print('Urun model not accessible')

try:
    from satis.models import Satis
    satis_count = Satis.objects.count()
    print('Satis (Sales):', satis_count)
except:
    print('Satis model not accessible')

try:
    from musteri.models import Musteri
    musteri_count = Musteri.objects.count()
    print('Musteri (Customers):', musteri_count)
except:
    print('Musteri model not accessible')

try:
    from gider.models import Gider
    gider_count = Gider.objects.count()
    print('Gider (Expenses):', gider_count)
except:
    print('Gider model not accessible')

print('Users:', CustomUser.objects.count())
