import os
import django
from django.conf import settings
from django.template.loader import get_template
from django.test import RequestFactory
import sys

# Add the project directory to sys.path
sys.path.append('/var/www/nuviabutik')

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'stoktakip.settings')
django.setup()

def test_template():
    try:
        print("Checking template: urun/liste.html")
        t = get_template('urun/liste.html')
        print("Template loaded successfully")
        
        from urun.models import Urun
        from kullanici.models import CustomUser
        
        user = CustomUser.objects.filter(is_superuser=True).first()
        if not user:
            print("No superuser found, trying any user")
            user = CustomUser.objects.first()
            
        rf = RequestFactory()
        request = rf.get('/urun/')
        request.user = user
        
        from urun.views import urun_listesi
        response = urun_listesi(request)
        print(f"Response status: {response.status_code}")
        
    except Exception as e:
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_template()
