import os
import django

# Force PostgreSQL
os.environ['DATABASE_URL'] = 'postgresql://nuviabutik_user:nuviabutik123@localhost/nuviabutik'
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'stoktakip.settings')
django.setup()

from django.core.management import execute_from_command_line
import sys

sys.argv = ['manage.py', 'migrate']
execute_from_command_line(sys.argv)
