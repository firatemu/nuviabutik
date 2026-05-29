"""
Fiyat Sistemini Güncelleme - Peşin/Taksitli Sisteme Geçiş
Eski satis_fiyati değerlerini pesin_fiyat'a aktar
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from urun.models import Urun
from decimal import Decimal


class Command(BaseCommand):
    help = 'Eski fiyat sistemini yeni peşin/taksitli sisteme günceller'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Değişiklikleri yapmadan önizleme yapar',
        )
        parser.add_argument(
            '--taksit-orani',
            type=float,
            default=5.0,
            help='Taksit fark oranı (varsayılan: 5)',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        taksit_orani = Decimal(str(options['taksit_orani']))

        self.stdout.write(self.style.WARNING('=' * 70))
        self.stdout.write(self.style.WARNING('FİYAT SİSTEMİ GÜNCELLEMESİ'))
        self.stdout.write(self.style.WARNING('Peşin/Taksitli Sisteme Geçiş'))
        self.stdout.write(self.style.WARNING('=' * 70))
        self.stdout.write('')

        # Tüm ürünleri al
        urunler = Urun.objects.all()
        toplam = urunler.count()

        self.stdout.write(f'📊 Toplam {toplam} ürün bulundu\n')

        if toplam == 0:
            self.stdout.write(self.style.WARNING(
                '⚠️  Güncellenecek ürün yok!'))
            return

        # Analiz
        sifir_fiyatli = urunler.filter(satis_fiyati=0).count()
        pesin_bos = urunler.filter(pesin_fiyat=0).count()

        self.stdout.write('📈 DURUM ANALİZİ:')
        self.stdout.write(f'  • Sıfır fiyatlı ürün: {sifir_fiyatli}')
        self.stdout.write(f'  • Peşin fiyat boş: {pesin_bos}')
        self.stdout.write(f'  • Güncellenecek: {pesin_bos}')
        self.stdout.write('')

        # Örnek hesaplama göster
        ornek_urun = urunler.filter(satis_fiyati__gt=0).first()
        if ornek_urun:
            eski_fiyat = ornek_urun.satis_fiyati
            yeni_pesin = eski_fiyat
            yeni_taksitli = eski_fiyat * (1 + (taksit_orani / 100))

            self.stdout.write('📋 ÖRNEK DÖNÜŞÜM:')
            self.stdout.write(f'  Ürün: {ornek_urun.ad}')
            self.stdout.write(f'  Eski Sistem:')
            self.stdout.write(f'    • Satış Fiyatı: {eski_fiyat}₺')
            self.stdout.write(f'  Yeni Sistem:')
            self.stdout.write(f'    • Peşin Fiyat: {yeni_pesin}₺')
            self.stdout.write(
                f'    • Taksitli Fiyat: {yeni_taksitli:.2f}₺ (+%{taksit_orani})')
            self.stdout.write(f'    • Fark: {yeni_taksitli - yeni_pesin:.2f}₺')
            self.stdout.write('')

        # Dry run kontrolü
        if dry_run:
            self.stdout.write(self.style.WARNING(
                '🔍 DRY-RUN MODU: Değişiklikler uygulanmadı!'))
            self.stdout.write(self.style.WARNING(
                'Gerçek güncelleme için --dry-run olmadan çalıştırın.'))
            return

        # Onay al
        self.stdout.write(self.style.WARNING(
            '⚠️  ÖNEMLİ: Bu işlem tüm ürünleri güncelleyecek!'))
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
        atlanan = 0

        with transaction.atomic():
            for i, urun in enumerate(urunler, 1):
                try:
                    # Eğer pesin_fiyat zaten doluysa atla
                    if urun.pesin_fiyat > 0:
                        atlanan += 1
                        continue

                    # Eski satış fiyatını peşin fiyata aktar
                    urun.pesin_fiyat = urun.satis_fiyati
                    urun.taksit_orani = taksit_orani

                    # Taksitli fiyat otomatik hesaplanacak (save metodunda)
                    urun.save()

                    basarili += 1

                    # Progress bar
                    if i % 10 == 0 or i == toplam:
                        yuzde = (i / toplam) * 100
                        self.stdout.write(
                            f'\r  İlerleme: [{i}/{toplam}] %{yuzde:.1f}',
                            ending=''
                        )
                        self.stdout.flush()

                except Exception as e:
                    hatali += 1
                    self.stdout.write('')
                    self.stdout.write(
                        self.style.ERROR(f'❌ Hata ({urun.id}): {str(e)}')
                    )

        # Sonuç
        self.stdout.write('\n')
        self.stdout.write(self.style.SUCCESS('=' * 70))
        self.stdout.write(self.style.SUCCESS('✅ GÜNCELLEME TAMAMLANDI!'))
        self.stdout.write(self.style.SUCCESS('=' * 70))
        self.stdout.write('')
        self.stdout.write(f'✅ Başarılı: {basarili}')
        self.stdout.write(f'⏭️  Atlanan: {atlanan} (zaten güncel)')
        if hatali > 0:
            self.stdout.write(self.style.ERROR(f'❌ Hatalı: {hatali}'))
        self.stdout.write('')

        # Özet
        self.stdout.write('📝 YENİ FİYAT SİSTEMİ:')
        self.stdout.write(f'  • Peşin Fiyat: Eski satış fiyatı')
        self.stdout.write(f'  • Taksitli Fiyat: Peşin + %{taksit_orani}')
        self.stdout.write(f'  • Otomatik Hesaplama: Aktif ✓')
        self.stdout.write('')

        # Kontrol önerisi
        self.stdout.write(self.style.SUCCESS('🎉 Sistem hazır!'))
        self.stdout.write('')
        self.stdout.write('💡 KONTROL:')
        self.stdout.write('  python manage.py shell')
        self.stdout.write('  >>> from urun.models import Urun')
        self.stdout.write('  >>> u = Urun.objects.first()')
        self.stdout.write(
            '  >>> print(f"Peşin: {u.pesin_fiyat}₺, Taksitli: {u.taksitli_fiyat}₺")')
        self.stdout.write('')

