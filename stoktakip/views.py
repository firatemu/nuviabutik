from django.shortcuts import render
from django.http import HttpResponse
from django.db.models import Sum, Count, Q, F
from datetime import date, datetime
from satis.models import Satis, SatisDetay, Odeme
from urun.models import UrunVaryanti
from musteri.models import Musteri
from gider.models import Gider
from kasa.models import Kasa, KasaHareket

def dashboard_view(request):
    bugun = date.today()
    
    # Günlük satışlar
    gunluk_satislar = Satis.objects.filter(
        satis_tarihi__date=bugun,
        durum='tamamlandi'
    )
    
    # Satış istatistikleri
    satis_stats = gunluk_satislar.aggregate(
        toplam_tutar=Sum('toplam_tutar'),
        satis_adedi=Count('id')
    )
    
    bugunki_satis = satis_stats['toplam_tutar'] or 0
    satis_sayisi = satis_stats['satis_adedi'] or 0
    
    # Ürün ve müşteri sayıları
    toplam_urun = UrunVaryanti.objects.filter(aktif=True, urun__aktif=True).count()
    toplam_musteri = Musteri.objects.filter(aktif=True).count()
    
    # Günlük gider
    gunluk_gider = Gider.objects.filter(tarih=bugun).aggregate(
        toplam=Sum('tutar')
    )['toplam'] or 0
    
    # Stok uyarıları (kritik stok seviyesinin altında)
    kritik_stoklar = UrunVaryanti.objects.filter(
        aktif=True,
        urun__aktif=True,
        stok_miktari__lte=F('urun__kritik_stok_seviyesi')
    ).select_related('urun', 'renk', 'beden').count()
    
    # En çok satan ürünler (bugün)
    cok_satan_urunler = SatisDetay.objects.filter(
        satis__satis_tarihi__date=bugun,
        satis__durum='tamamlandi'
    ).values(
        'urun__ad'
    ).annotate(
        toplam_miktar=Sum('miktar'),
        toplam_ciro=Sum('toplam_fiyat')
    ).order_by('-toplam_miktar')[:5]
    
    # Son satışlar
    son_satislar = Satis.objects.filter(
        satis_tarihi__date=bugun,
        durum='tamamlandi'
    ).select_related('musteri', 'satici').order_by('-satis_tarihi')[:5]
    
    # Net kar hesaplama
    net_kar = bugunki_satis - gunluk_gider
    
    # Aylık satış trendi (son 7 gün)
    from datetime import timedelta
    haftalik_satis = []
    for i in range(7):
        tarih = bugun - timedelta(days=i)
        gunluk_tutar = Satis.objects.filter(
            satis_tarihi__date=tarih,
            durum='tamamlandi'
        ).aggregate(toplam=Sum('toplam_tutar'))['toplam'] or 0
        
        haftalik_satis.append({
            'tarih': tarih,
            'tutar': gunluk_tutar
        })
    
    haftalik_satis.reverse()  # Tarih sırasına göre
    
    context = {
        'bugun': bugun,
        'toplam_urun': toplam_urun,
        'toplam_musteri': toplam_musteri,
        'bugunki_satis': bugunki_satis,
        'satis_sayisi': satis_sayisi,
        'bugunki_gider_toplam': gunluk_gider,
        'net_kar': net_kar,
        'kritik_stoklar': kritik_stoklar,
        'cok_satan_urunler': cok_satan_urunler,
        'son_satislar': son_satislar,
        'haftalik_satis': haftalik_satis,
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
        toplam_tutar=Sum('toplam_tutar'),
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
