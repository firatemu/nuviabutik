from django.core.management.base import BaseCommand
from django.core.cache import cache
from urun.models import UrunKategoriUst, Marka, Urun
from django.db.models import Sum, Count, Q


class Command(BaseCommand):
    help = 'Warm up cache with frequently accessed data'

    def handle(self, *args, **options):
        self.stdout.write('Starting cache warming...')
        
        # Warm up kategoriler cache
        kategoriler = list(UrunKategoriUst.objects.filter(aktif=True).order_by('ad').values('id', 'ad'))
        cache.set('aktif_kategoriler', kategoriler, 3600)
        self.stdout.write(f'✓ Cached {len(kategoriler)} categories')
        
        # Warm up markalar cache
        markalar = list(Marka.objects.filter(aktif=True).order_by('ad').values('id', 'ad'))
        cache.set('aktif_markalar', markalar, 3600)
        self.stdout.write(f'✓ Cached {len(markalar)} brands')
        
        # Warm up statistics cache
        stats_query = Urun.objects.aggregate(
            toplam_urun=Count('id'),
            aktif_urun=Count('id', filter=Q(aktif=True)),
        )
        
        # Calculate stock statistics
        urunler_stok = Urun.objects.annotate(
            stok_toplam=Sum('varyantlar__stok_miktari')
        ).values('stok_toplam', 'kritik_stok_seviyesi')
        
        kritik_stok = 0
        tukenen_stok = 0
        for urun_data in urunler_stok:
            stok = urun_data['stok_toplam'] or 0
            kritik = urun_data['kritik_stok_seviyesi']
            if stok == 0:
                tukenen_stok += 1
            elif 0 < stok <= kritik:
                kritik_stok += 1
        
        stats = {
            'toplam_urun': stats_query['toplam_urun'],
            'aktif_urun': stats_query['aktif_urun'],
            'kritik_stok': kritik_stok,
            'tukenen_stok': tukenen_stok,
        }
        
        cache.set('urun_istatistikleri', stats, 300)
        self.stdout.write(f'✓ Cached product statistics')
        
        # Warm up stock report cache
        from django.db.models import Case, When, IntegerField
        urunler = Urun.objects.select_related('kategori', 'marka').annotate(
            toplam_stok_miktari=Sum('varyantlar__stok_miktari'),
            stok_durumu=Case(
                When(toplam_stok_miktari=0, then=0),
                When(toplam_stok_miktari__lte=10, then=1),
                default=2,
                output_field=IntegerField()
            )
        ).order_by('ad')
        
        cache.set('stok_durumu_raporu', urunler, 600)
        self.stdout.write(f'✓ Cached stock report for {urunler.count()} products')
        
        self.stdout.write(self.style.SUCCESS('Cache warming completed successfully!'))