"""
Fiyat Değişiklik Raporu
Belirli tarih aralığında fiyat değişikliklerini raporlar
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from urun.fiyat_models import FiyatGecmisi
from decimal import Decimal


class Command(BaseCommand):
    help = 'Fiyat değişiklik raporu oluşturur'

    def add_arguments(self, parser):
        parser.add_argument(
            '--gun',
            type=int,
            default=7,
            help='Kaç gün geriye git (varsayılan: 7)',
        )
        parser.add_argument(
            '--neden',
            type=str,
            help='Belirli bir nedeni filtrele (zam, indirim, kampanya, vb.)',
        )
        parser.add_argument(
            '--export',
            type=str,
            help='CSV dosyasına export et (dosya yolu)',
        )

    def handle(self, *args, **options):
        gun = options['gun']
        neden = options['neden']
        export_path = options['export']

        # Tarih aralığı
        baslangic = timezone.now() - timedelta(days=gun)

        self.stdout.write(
            self.style.WARNING(f'\n{"="*70}\n')
        )
        self.stdout.write(
            self.style.WARNING(f'FİYAT DEĞİŞİKLİK RAPORU - Son {gun} Gün\n')
        )
        self.stdout.write(
            self.style.WARNING(f'{"="*70}\n')
        )

        # Query
        gecmisler = FiyatGecmisi.objects.filter(
            degisiklik_tarihi__gte=baslangic
        ).select_related('urun', 'degistiren')

        if neden:
            gecmisler = gecmisler.filter(neden=neden)

        toplam = gecmisler.count()

        if toplam == 0:
            self.stdout.write(
                self.style.WARNING(
                    'Belirtilen kriterlerde değişiklik bulunamadı.')
            )
            return

        # İstatistikler
        artislar = gecmisler.filter(
            yeni_satis_fiyati__gt=models.F('eski_satis_fiyati'))
        dususler = gecmisler.filter(
            yeni_satis_fiyati__lt=models.F('eski_satis_fiyati'))

        self.stdout.write(f'📊 GENEL İSTATİSTİKLER:')
        self.stdout.write(f'  • Toplam Değişiklik: {toplam}')
        self.stdout.write(f'  • Fiyat Artışı: {artislar.count()}')
        self.stdout.write(f'  • Fiyat Düşüşü: {dususler.count()}')
        self.stdout.write('')

        # Nedene göre grupla
        from django.db.models import Count
        neden_dagilim = gecmisler.values('neden').annotate(
            sayi=Count('neden')
        ).order_by('-sayi')

        self.stdout.write(f'📈 NEDENE GÖRE DAĞILIM:')
        for item in neden_dagilim:
            self.stdout.write(f'  • {item["neden"]}: {item["sayi"]} adet')
        self.stdout.write('')

        # En çok değişen ürünler
        from django.db.models import Count
        en_cok_degisen = FiyatGecmisi.objects.filter(
            degisiklik_tarihi__gte=baslangic
        ).values('urun__ad', 'urun__urun_kodu').annotate(
            degisiklik_sayisi=Count('id')
        ).order_by('-degisiklik_sayisi')[:10]

        self.stdout.write(f'🔄 EN ÇOK DEĞİŞEN ÜRÜNLER (Top 10):')
        for i, item in enumerate(en_cok_degisen, 1):
            self.stdout.write(
                f'  {i}. {item["urun__ad"]} ({item["urun__urun_kodu"]}): '
                f'{item["degisiklik_sayisi"]} değişiklik'
            )
        self.stdout.write('')

        # En büyük artış/düşüş
        if artislar.exists():
            en_buyuk_artis = artislar.order_by('-degisiklik_yuzdesi').first()
            self.stdout.write(
                f'⬆️  EN BÜYÜK ARTIŞ:\n'
                f'  • Ürün: {en_buyuk_artis.urun.ad}\n'
                f'  • {en_buyuk_artis.eski_satis_fiyati}₺ → {en_buyuk_artis.yeni_satis_fiyati}₺\n'
                f'  • %{en_buyuk_artis.degisiklik_yuzdesi}\n'
            )

        if dususler.exists():
            en_buyuk_dusus = dususler.order_by('degisiklik_yuzdesi').first()
            self.stdout.write(
                f'⬇️  EN BÜYÜK DÜŞÜŞ:\n'
                f'  • Ürün: {en_buyuk_dusus.urun.ad}\n'
                f'  • {en_buyuk_dusus.eski_satis_fiyati}₺ → {en_buyuk_dusus.yeni_satis_fiyati}₺\n'
                f'  • %{abs(en_buyuk_dusus.degisiklik_yuzdesi)}\n'
            )

        # Export
        if export_path:
            self._export_csv(gecmisler, export_path)

        self.stdout.write(self.style.WARNING(f'\n{"="*70}\n'))

    def _export_csv(self, queryset, file_path):
        """CSV'ye export et"""
        import csv

        with open(file_path, 'w', newline='', encoding='utf-8-sig') as csvfile:
            writer = csv.writer(csvfile)

            # Header
            writer.writerow([
                'Ürün Kodu',
                'Ürün Adı',
                'Eski Fiyat',
                'Yeni Fiyat',
                'Değişim (%)',
                'Değişim (TL)',
                'Neden',
                'Açıklama',
                'Değiştiren',
                'Tarih',
            ])

            # Data
            for gecmis in queryset:
                writer.writerow([
                    gecmis.urun.urun_kodu,
                    gecmis.urun.ad,
                    f'{gecmis.eski_satis_fiyati:.2f}',
                    f'{gecmis.yeni_satis_fiyati:.2f}',
                    f'{gecmis.degisiklik_yuzdesi:.2f}',
                    f'{gecmis.degisiklik_miktari:.2f}',
                    gecmis.get_neden_display(),
                    gecmis.aciklama or '',
                    gecmis.degistiren.username if gecmis.degistiren else '',
                    gecmis.degisiklik_tarihi.strftime('%d.%m.%Y %H:%M'),
                ])

        self.stdout.write(
            self.style.SUCCESS(f'\n✓ Rapor export edildi: {file_path}')
        )

