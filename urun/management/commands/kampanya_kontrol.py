"""
Kampanya Kontrol ve Otomatik Geri Alma
Cron job olarak çalıştırılabilir
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from urun.fiyat_models import FiyatKampanya


class Command(BaseCommand):
    help = 'Kampanyaları kontrol eder ve süresi bitenleri otomatik geri alır'

    def handle(self, *args, **options):
        self.stdout.write('Kampanya kontrolü başlatılıyor...')

        # Süresi bitmiş, geri alınacak kampanyalar
        kampanyalar = FiyatKampanya.objects.filter(
            durum='aktif',
            otomatik_geri_al=True,
            geri_alindi=False,
            bitis_tarihi__lte=timezone.now()
        )

        toplam = kampanyalar.count()
        self.stdout.write(f'Geri alınacak {toplam} kampanya bulundu')

        basarili = 0
        hatali = 0

        for kampanya in kampanyalar:
            self.stdout.write(f'\n🔄 İşleniyor: {kampanya.ad}')

            try:
                success, message = kampanya.geri_al()

                if success:
                    self.stdout.write(
                        self.style.SUCCESS(f'  ✓ {message}')
                    )
                    basarili += 1
                else:
                    self.stdout.write(
                        self.style.WARNING(f'  ⚠ {message}')
                    )

            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'  ✗ Hata: {str(e)}')
                )
                hatali += 1

        # Özet
        self.stdout.write('\n' + '='*50)
        self.stdout.write(self.style.SUCCESS(f'✓ Başarılı: {basarili}'))
        if hatali > 0:
            self.stdout.write(self.style.ERROR(f'✗ Hatalı: {hatali}'))
        self.stdout.write('='*50)

