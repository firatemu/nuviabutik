import os
from django.core.management.base import BaseCommand
from urun.models import Beden
from django.db import IntegrityError


class Command(BaseCommand):
    help = 'Create size data (XS-XXXL and 28-46)'

    def handle(self, *args, **options):
        # Harf bedenleri: XS, S, M, L, XL, XXL, XXXL
        harf_bedenleri = ['XS', 'S', 'M', 'L', 'XL', 'XXL', 'XXXL']
        
        # Rakam bedenleri: 28-46 (çift sayılar)
        rakam_bedenleri = list(range(28, 47, 2))  # 28, 30, 32, ..., 46
        
        created_count = 0
        existing_count = 0
        
        # Harf bedenlerini ekle
        for i, beden_adi in enumerate(harf_bedenleri):
            try:
                beden, created = Beden.objects.get_or_create(
                    ad=beden_adi,
                    defaults={
                        'kod': beden_adi[0] if len(beden_adi) == 1 else str(i+1),
                        'tip': 'harf',
                        'sira': i+1
                    }
                )
                if created:
                    created_count += 1
                    self.stdout.write(f'✓ Harf beden "{beden_adi}" oluşturuldu.')
                else:
                    existing_count += 1
                    self.stdout.write(f'- Harf beden "{beden_adi}" zaten mevcut.')
            except IntegrityError as e:
                self.stdout.write(
                    self.style.ERROR(f'Harf beden "{beden_adi}" eklenirken hata: {e}')
                )
        
        # Rakam bedenlerini ekle
        for i, beden_no in enumerate(rakam_bedenleri):
            beden_adi = str(beden_no)
            try:
                beden, created = Beden.objects.get_or_create(
                    ad=beden_adi,
                    defaults={
                        'kod': str(beden_no)[-1],  # Son rakam
                        'tip': 'rakam',
                        'sira': i+1
                    }
                )
                if created:
                    created_count += 1
                    self.stdout.write(f'✓ Rakam beden "{beden_adi}" oluşturuldu.')
                else:
                    existing_count += 1
                    self.stdout.write(f'- Rakam beden "{beden_adi}" zaten mevcut.')
            except IntegrityError as e:
                self.stdout.write(
                    self.style.ERROR(f'Rakam beden "{beden_adi}" eklenirken hata: {e}')
                )
        
        # Özet
        self.stdout.write(
            self.style.SUCCESS(
                f'\n📊 Beden Ekleme Özeti:\n'
                f'✓ Yeni oluşturulan: {created_count}\n'
                f'- Zaten mevcut: {existing_count}\n'
                f'📏 Toplam beden sayısı: {Beden.objects.count()}'
            )
        )
        
        # Tüm bedenleri listele
        self.stdout.write(f'\n📋 Mevcut Bedenler:')
        bedenler = Beden.objects.all().order_by('id')
        for beden in bedenler:
            self.stdout.write(f'  • {beden.beden_adi} - {beden.aciklama}')
