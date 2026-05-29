"""
Barkod Sistemi V2'ye Geçiş Scripti
Eski fiyatlı barkodları yeni fiyatsız barkodlara dönüştürür
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from urun.models import UrunVaryanti
import time


class Command(BaseCommand):
    help = 'Barkod sistemini V2\'ye (fiyatsız) günceller'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Değişiklikleri yapmadan önizleme yapar',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Onay beklemeden direkt uygular',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        force = options['force']

        self.stdout.write(self.style.WARNING('=' * 70))
        self.stdout.write(self.style.WARNING('BARKOD SİSTEMİ V2 GEÇİŞ ARACI'))
        self.stdout.write(self.style.WARNING('=' * 70))
        self.stdout.write('')

        # Tüm varyantları al
        varyantlar = UrunVaryanti.objects.all().select_related('urun', 'renk', 'beden')
        toplam = varyantlar.count()

        self.stdout.write(f'📊 Toplam {toplam} varyant bulundu\n')

        if toplam == 0:
            self.stdout.write(self.style.WARNING(
                '⚠️  Güncellenecek varyant yok!'))
            return

        # Eski ve yeni format sayıları
        eski_format = 0
        yeni_format = 0

        degisiklikler = []

        for varyant in varyantlar:
            eski_barkod = varyant.barkod

            # Yeni barkod oluştur
            yeni_barkod = varyant.olustur_barkod()

            # Format kontrolü
            if eski_barkod and eski_barkod.startswith('NUV'):
                veri = eski_barkod[3:]
                if len(veri) == 13:
                    # Eski format (fiyatlı)
                    eski_format += 1
                    if eski_barkod != yeni_barkod:
                        degisiklikler.append({
                            'varyant': varyant,
                            'eski_barkod': eski_barkod,
                            'yeni_barkod': yeni_barkod
                        })
                elif len(veri) == 12:
                    # Zaten yeni format
                    yeni_format += 1
            else:
                # Legacy veya boş
                eski_format += 1
                degisiklikler.append({
                    'varyant': varyant,
                    'eski_barkod': eski_barkod or 'BOŞ',
                    'yeni_barkod': yeni_barkod
                })

        self.stdout.write('📈 İSTATİSTİKLER:')
        self.stdout.write(f'  • Eski Format (Fiyatlı): {eski_format}')
        self.stdout.write(f'  • Yeni Format (Fiyatsız): {yeni_format}')
        self.stdout.write(f'  • Güncellenecek: {len(degisiklikler)}')
        self.stdout.write('')

        if len(degisiklikler) == 0:
            self.stdout.write(self.style.SUCCESS(
                '✅ Tüm barkodlar zaten yeni formatta!'))
            return

        # Örnek değişiklikler göster
        self.stdout.write('📋 ÖRNEK DEĞİŞİKLİKLER (ilk 5):')
        for i, deg in enumerate(degisiklikler[:5], 1):
            varyant = deg['varyant']
            self.stdout.write(
                f'\n  {i}. {varyant.urun.ad} ({varyant.varyasyon_adi})')
            self.stdout.write(f'     Eski: {deg["eski_barkod"]}')
            self.stdout.write(f'     Yeni: {deg["yeni_barkod"]}')

        if len(degisiklikler) > 5:
            self.stdout.write(f'\n  ... ve {len(degisiklikler) - 5} tane daha')

        self.stdout.write('')

        # Dry run kontrolü
        if dry_run:
            self.stdout.write(self.style.WARNING(
                '🔍 DRY-RUN MODU: Değişiklikler uygulanmadı!'))
            self.stdout.write(self.style.WARNING(
                'Gerçek güncelleme için --dry-run olmadan çalıştırın.'))
            return

        # Onay al
        if not force:
            self.stdout.write(self.style.WARNING(
                '⚠️  UYARI: Bu işlem geri alınamaz!'))
            onay = input('\n❓ Devam etmek istiyor musunuz? (yes/no): ')

            if onay.lower() not in ['yes', 'y', 'evet', 'e']:
                self.stdout.write(self.style.ERROR('❌ İşlem iptal edildi.'))
                return

        # Güncelleme yap
        self.stdout.write('')
        self.stdout.write(self.style.WARNING('🚀 Güncelleme başlatılıyor...'))
        self.stdout.write('')

        basarili = 0
        hatali = 0

        with transaction.atomic():
            for i, deg in enumerate(degisiklikler, 1):
                varyant = deg['varyant']
                yeni_barkod = deg['yeni_barkod']

                try:
                    # Barkodu güncelle
                    varyant.barkod = yeni_barkod
                    varyant.save()

                    basarili += 1

                    # Progress bar
                    if i % 10 == 0 or i == len(degisiklikler):
                        yuzde = (i / len(degisiklikler)) * 100
                        self.stdout.write(
                            f'\r  İlerleme: [{i}/{len(degisiklikler)}] %{yuzde:.1f}',
                            ending=''
                        )
                        self.stdout.flush()

                except Exception as e:
                    hatali += 1
                    self.stdout.write('')
                    self.stdout.write(
                        self.style.ERROR(f'❌ Hata ({varyant.id}): {str(e)}')
                    )

        # Sonuç
        self.stdout.write('\n')
        self.stdout.write(self.style.SUCCESS('=' * 70))
        self.stdout.write(self.style.SUCCESS('✅ GÜNCELLEME TAMAMLANDI!'))
        self.stdout.write(self.style.SUCCESS('=' * 70))
        self.stdout.write('')
        self.stdout.write(f'✅ Başarılı: {basarili}')
        if hatali > 0:
            self.stdout.write(self.style.ERROR(f'❌ Hatalı: {hatali}'))
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('🎉 Yeni barkod sistemi aktif!'))
        self.stdout.write('')

        # Format özeti
        self.stdout.write('📝 YENİ BARKOD FORMAT:')
        self.stdout.write(
            '  NUV + Özellik(2) + Varyant(2) + Ürün(5) + Sıra(3)')
        self.stdout.write('  Toplam: 15 karakter (Eski: 16 karakter)')
        self.stdout.write('  Fiyat bilgisi: KALDIRILDI ✓')
        self.stdout.write('')

