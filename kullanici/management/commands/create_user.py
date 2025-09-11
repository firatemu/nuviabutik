import os
from django.core.management.base import BaseCommand
from kullanici.models import CustomUser
from django.db import IntegrityError


class Command(BaseCommand):
    help = 'Create a new user'

    def add_arguments(self, parser):
        parser.add_argument('--username', type=str, help='Username for the new user')
        parser.add_argument('--email', type=str, help='Email for the new user')
        parser.add_argument('--password', type=str, help='Password for the new user')
        parser.add_argument('--role', type=str, default='kasiyer', help='Role for the new user (admin, kasiyer, mudur)')
        parser.add_argument('--is-staff', action='store_true', help='Make user staff')
        parser.add_argument('--is-superuser', action='store_true', help='Make user superuser')

    def handle(self, *args, **options):
        username = options['username']
        email = options['email'] 
        password = options['password']
        role = options['role']
        is_staff = options['is_staff']
        is_superuser = options['is_superuser']
        
        if not username or not email or not password:
            self.stdout.write(
                self.style.ERROR('Username, email and password are required.')
            )
            return
            
        try:
            if CustomUser.objects.filter(username=username).exists():
                self.stdout.write(
                    self.style.ERROR(f'User "{username}" already exists.')
                )
                return
                
            if is_superuser:
                user = CustomUser.objects.create_superuser(
                    username=username,
                    email=email,
                    password=password,
                    role=role
                )
            else:
                user = CustomUser.objects.create_user(
                    username=username,
                    email=email,
                    password=password,
                    role=role,
                    is_staff=is_staff
                )
                
            self.stdout.write(
                self.style.SUCCESS(f'User "{username}" created successfully with role "{role}".')
            )
            
        except IntegrityError as e:
            self.stdout.write(
                self.style.ERROR(f'Error creating user: {e}')
            )
