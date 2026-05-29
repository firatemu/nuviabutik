from django.shortcuts import render
from django.http import HttpResponse
from decimal import Decimal

from django.db.models import Sum, Count, Q, F, Value, ExpressionWrapper, DecimalField
from django.db.models.functions import Coalesce
from datetime import date, datetime, timedelta
from satis.models import Satis, SatisDetay, Odeme
from urun.models import UrunVaryanti
from gider.models import Gider
from kasa.models import Kasa, KasaHareket


def _dashboard_tarih_araligi(request):
    """GET baslangic, bitis; varsayılan: bugün–bugün."""
    bugun = date.today()
    b = request.GET.get('baslangic')
    t = request.GET.get('bitis')
    try:
        if b and t:
            bas = datetime.strptime(b, '%Y-%m-%d').date()
            bit = datetime.strptime(t, '%Y-%m-%d').date()
        else:
            bas = bit = bugun
    except (ValueError, TypeError):
        bas = bit = bugun
    if bas > bit:
        bas, bit = bit, bas
    return bas, bit


def dashboard_view(request):
    baslangic, bitis = _dashboard_tarih_araligi(request)
    bugun = date.today()
    tek_gun = baslangic == bitis

    satis_donem = Satis.objects.filter(
        satis_tarihi__date__range=[baslangic, bitis],
        durum='tamamlandi',
    )

    satis_stats = satis_donem.aggregate(
        toplam_tutar=Sum('genel_toplam'),
        satis_adedi=Count('id'),
    )
    donem_satis = satis_stats['toplam_tutar'] or Decimal('0')
    if not isinstance(donem_satis, Decimal):
        donem_satis = Decimal(str(donem_satis))
    donem_satis_sayisi = satis_stats['satis_adedi'] or 0

    detay_donem = SatisDetay.objects.filter(
        satis__satis_tarihi__date__range=[baslangic, bitis],
        satis__durum='tamamlandi',
    )
    money = DecimalField(max_digits=14, decimal_places=2)
    donem_maliyet_satis = detay_donem.aggregate(
        s=Sum(
            ExpressionWrapper(
                F('urun__alis_fiyati') * F('miktar'),
                output_field=money,
            )
        )
    )['s'] or Decimal('0')
    if not isinstance(donem_maliyet_satis, Decimal):
        donem_maliyet_satis = Decimal(str(donem_maliyet_satis))
    satis_kari = donem_satis - donem_maliyet_satis
    satis_kar_yuzde = (
        (satis_kari / donem_maliyet_satis * Decimal('100'))
        if donem_maliyet_satis > 0
        else Decimal('0')
    )
    net_satis_kadin = detay_donem.filter(urun__cinsiyet='kadin').aggregate(
        s=Sum('toplam_fiyat')
    )['s'] or 0
    net_satis_erkek = detay_donem.filter(urun__cinsiyet='erkek').aggregate(
        s=Sum('toplam_fiyat')
    )['s'] or 0

    toplam_urun = UrunVaryanti.objects.filter(aktif=True, urun__aktif=True).count()

    donem_gider = Gider.objects.filter(tarih__range=[baslangic, bitis]).aggregate(
        toplam=Sum('tutar')
    )['toplam'] or Decimal('0')
    if not isinstance(donem_gider, Decimal):
        donem_gider = Decimal(str(donem_gider))

    kritik_stoklar = UrunVaryanti.objects.filter(
        aktif=True,
        urun__aktif=True,
        stok_miktari__lte=F('urun__kritik_stok_seviyesi'),
    ).count()

    cok_satan_urunler = SatisDetay.objects.filter(
        satis__satis_tarihi__date__range=[baslangic, bitis],
        satis__durum='tamamlandi',
    ).values('urun__ad').annotate(
        toplam_miktar=Sum('miktar'),
        toplam_ciro=Sum('toplam_fiyat'),
    ).order_by('-toplam_miktar')[:5]

    son_satislar = Satis.objects.filter(
        satis_tarihi__date__range=[baslangic, bitis],
        durum='tamamlandi',
    ).select_related('musteri', 'satici').order_by('-satis_tarihi')[:5]

    net_kar = donem_satis - donem_gider
    if not isinstance(net_kar, Decimal):
        net_kar = Decimal(str(net_kar))

    haftalik_satis = []
    for i in range(7):
        gun = bitis - timedelta(days=(6 - i))
        gunluk_tutar = Satis.objects.filter(
            satis_tarihi__date=gun,
            durum='tamamlandi',
        ).aggregate(toplam=Sum('genel_toplam'))['toplam'] or 0
        haftalik_satis.append({'tarih': gun, 'tutar': gunluk_tutar})

    odeme_donem = Odeme.objects.filter(
        odeme_tarihi__date__range=[baslangic, bitis]
    )
    donem_odeme_toplam = odeme_donem.aggregate(toplam=Sum('tutar'))['toplam'] or 0
    donem_odeme_adet = odeme_donem.count()
    odeme_tipi_donem = []
    tip_labels = dict(Odeme.ODEME_TIPLERI)
    for row in odeme_donem.values('odeme_tipi').annotate(
        toplam=Sum('tutar'), adet=Count('id')
    ).order_by('-toplam'):
        kod = row['odeme_tipi']
        odeme_tipi_donem.append({
            'kod': kod,
            'ad': tip_labels.get(kod, kod),
            'toplam': row['toplam'] or 0,
            'adet': row['adet'],
        })

    # Aynı dönemde kredi kartı — taksit sayısına göre dağılım (ödeme tipi kartı ile birlikte)
    odeme_kart_taksit_ozet = []
    for row in (
        odeme_donem.filter(odeme_tipi='kart')
        .annotate(_ts=Coalesce('taksit_sayisi', Value(1)))
        .values('_ts')
        .annotate(toplam=Sum('tutar'), adet=Count('id'))
        .order_by('_ts')
    ):
        ts = int(row['_ts'] or 1)
        if ts <= 1:
            etiket = 'Peşin (tek çekim)'
        else:
            etiket = f'{ts} taksit'
        odeme_kart_taksit_ozet.append({
            'taksit_sayisi': ts,
            'etiket': etiket,
            'toplam': row['toplam'] or 0,
            'adet': row['adet'],
        })

    son_odemeler = odeme_donem.select_related(
        'satis', 'satis__musteri'
    ).order_by('-odeme_tarihi')[:5]

    # Banka dağılımı: satış POS (kredi kartı) — Odeme.banka
    banka_labels = dict(Odeme.BANKA_SECENEKLERI)
    kart_odemeler_donem = odeme_donem.filter(odeme_tipi='kart')
    odeme_kart_banka_ozet = []
    for row in (
        kart_odemeler_donem.exclude(banka__in=[None, ''])
        .values('banka')
        .annotate(toplam=Sum('tutar'), adet=Count('id'))
        .order_by('-toplam')
    ):
        kod = row['banka']
        odeme_kart_banka_ozet.append({
            'kod': kod,
            'ad': banka_labels.get(kod, kod or '—'),
            'toplam': row['toplam'] or 0,
            'adet': row['adet'],
        })
    kartsiz_ozet = kart_odemeler_donem.filter(
        Q(banka__isnull=True) | Q(banka='')
    ).aggregate(toplam=Sum('tutar'), adet=Count('id'))
    odeme_kart_banksiz_toplam = kartsiz_ozet['toplam'] or 0
    odeme_kart_banksiz_adet = kartsiz_ozet['adet'] or 0

    context = {
        'bugun': bugun,
        'baslangic': baslangic,
        'bitis': bitis,
        'baslangic_str': baslangic.strftime('%Y-%m-%d'),
        'bitis_str': bitis.strftime('%Y-%m-%d'),
        'tek_gun': tek_gun,
        'toplam_urun': toplam_urun,
        'donem_maliyet_satis': donem_maliyet_satis,
        'satis_kari': satis_kari,
        'satis_kar_yuzde': satis_kar_yuzde,
        'donem_satis': donem_satis,
        'donem_satis_sayisi': donem_satis_sayisi,
        'bugunki_satis': donem_satis,
        'satis_sayisi': donem_satis_sayisi,
        'net_satis_kadin': net_satis_kadin,
        'net_satis_erkek': net_satis_erkek,
        'bugunki_gider_toplam': donem_gider,
        'net_kar': net_kar,
        'kritik_stoklar': kritik_stoklar,
        'cok_satan_urunler': cok_satan_urunler,
        'son_satislar': son_satislar,
        'haftalik_satis': haftalik_satis,
        'bugunki_odeme_toplam': donem_odeme_toplam,
        'bugunki_odeme_adet': donem_odeme_adet,
        'odeme_tipi_bugun': odeme_tipi_donem,
        'odeme_kart_taksit_ozet': odeme_kart_taksit_ozet,
        'son_odemeler': son_odemeler,
        'odeme_kart_banka_ozet': odeme_kart_banka_ozet,
        'odeme_kart_banksiz_toplam': odeme_kart_banksiz_toplam,
        'odeme_kart_banksiz_adet': odeme_kart_banksiz_adet,
    }

    return render(request, 'dashboard.html', context)

def gunluk_rapor_view(request):
    # Tarih parametresi
    tarih = request.GET.get('tarih', date.today().strftime('%Y-%m-%d'))
    
    try:
        secili_tarih = datetime.strptime(tarih, '%Y-%m-%d').date()
    except ValueError:
        secili_tarih = date.today()
    
    # Günlük satışlar
    gunluk_satislar = Satis.objects.filter(
        satis_tarihi__date=secili_tarih,
        durum='tamamlandi'
    )
    
    # Satış istatistikleri
    toplam_satis = gunluk_satislar.aggregate(
        toplam_tutar=Sum('genel_toplam'),
        satis_adedi=Count('id')
    )
    
    # Ödeme yöntemi bazında satışlar
    nakit_satislar = Odeme.objects.filter(
        satis__satis_tarihi__date=secili_tarih,
        satis__durum='tamamlandi',
        odeme_tipi='nakit'
    ).aggregate(
        toplam=Sum('tutar'), 
        adet=Count('id')
    )
    
    kart_satislar = Odeme.objects.filter(
        satis__satis_tarihi__date=secili_tarih,
        satis__durum='tamamlandi',
        odeme_tipi='kart'
    ).aggregate(
        toplam=Sum('tutar'), 
        adet=Count('id')
    )
    
    hediye_ceki_satislar = Odeme.objects.filter(
        satis__satis_tarihi__date=secili_tarih,
        satis__durum='tamamlandi',
        odeme_tipi='hediye_ceki'
    ).aggregate(
        toplam=Sum('tutar'), 
        adet=Count('id')
    )
    
    # En çok satan ürünler
    cok_satan_urunler = SatisDetay.objects.filter(
        satis__satis_tarihi__date=secili_tarih,
        satis__durum='tamamlandi'
    ).values(
        'urun__ad'
    ).annotate(
        toplam_miktar=Sum('miktar'),
        toplam_ciro=Sum('toplam_fiyat')
    ).order_by('-toplam_miktar')[:10]
    
    # Template için uygun format
    cok_satan_urunler = [{
        'urun': {'ad': item['urun__ad']},
        'toplam_miktar': item['toplam_miktar'],
        'toplam_ciro': item['toplam_ciro']
    } for item in cok_satan_urunler]
    
    # Son satışlar
    son_satislar = Satis.objects.filter(
        satis_tarihi__date=secili_tarih,
        durum='tamamlandi'
    ).select_related('musteri').order_by('-satis_tarihi')[:10]
    
    # Günlük giderler
    gunluk_giderler = Gider.objects.filter(tarih=secili_tarih)
    toplam_gider = gunluk_giderler.aggregate(toplam=Sum('tutar'))
    
    # Kar hesaplama
    toplam_satis_tutari = toplam_satis['toplam_tutar'] or 0
    toplam_gider_tutari = toplam_gider['toplam'] or 0
    net_kar = toplam_satis_tutari - toplam_gider_tutari
    
    # Kasa bilgileri
    kasalar = Kasa.objects.filter(aktif=True)
    kasa_durumu = []
    
    for kasa in kasalar:
        # Günlük kasa hareketleri
        gunluk_hareketler = KasaHareket.objects.filter(
            kasa=kasa,
            tarih__date=secili_tarih
        )
        
        gunluk_giris = gunluk_hareketler.filter(
            tip='giris'
        ).aggregate(toplam=Sum('tutar'))['toplam'] or 0
        
        gunluk_cikis = gunluk_hareketler.filter(
            tip='cikis'
        ).aggregate(toplam=Sum('tutar'))['toplam'] or 0
        
        gunluk_net = gunluk_giris - gunluk_cikis
        
        kasa_durumu.append({
            'kasa': kasa,
            'gunluk_giris': gunluk_giris,
            'gunluk_cikis': gunluk_cikis,
            'gunluk_net': gunluk_net,
            'mevcut_bakiye': kasa.bakiye()
        })
    
    # Template için uyumlu değişken adları
    satis_ozeti = {
        'toplam_satis_tutari': toplam_satis_tutari,
        'toplam_satis_sayisi': toplam_satis['satis_adedi'] or 0
    }
    
    gider_ozeti = {
        'toplam_gider_tutari': toplam_gider_tutari,
        'toplam_gider_sayisi': gunluk_giderler.count()
    }
    
    toplam_tahsilat = toplam_satis_tutari
    brut_kar = net_kar
    
    context = {
        'secili_tarih': secili_tarih,
        'toplam_satis': toplam_satis,
        'nakit_satislar': nakit_satislar,
        'kart_satislar': kart_satislar,
        'hediye_ceki_satislar': hediye_ceki_satislar,
        'cok_satan_urunler': cok_satan_urunler,
        'son_satislar': son_satislar,
        'gunluk_giderler': gunluk_giderler,
        'toplam_gider': toplam_gider,
        'net_kar': net_kar,
        'gunluk_satislar': gunluk_satislar,
        'kasa_durumu': kasa_durumu,
        # Template uyumlu değişkenler
        'satis_ozeti': satis_ozeti,
        'gider_ozeti': gider_ozeti,
        'toplam_tahsilat': toplam_tahsilat,
        'brut_kar': brut_kar,
    }
    
    return render(request, 'gunluk_rapor.html', context)

def gunluk_rapor_pdf_view(request):
    return HttpResponse('PDF not available')
