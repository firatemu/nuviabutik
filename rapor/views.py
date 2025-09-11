from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.db.models import Sum, Count, F
from datetime import date, datetime, timedelta
from openpyxl import Workbook
from reportlab.pdfgen import canvas
from satis.models import Satis, SatisDetay
from urun.models import Urun
from musteri.models import Musteri


@login_required
def gunluk_satis(request):
    """Günlük satış raporu view'ı"""
    bugun = date.today()
    tarih = request.GET.get('tarih', bugun.strftime('%Y-%m-%d'))
    
    try:
        secili_tarih = datetime.strptime(tarih, '%Y-%m-%d').date()
    except ValueError:
        secili_tarih = bugun
    
    # Günlük satışlar - detaylı bilgi ile
    satislar = Satis.objects.filter(
        satis_tarihi__date=secili_tarih,
        durum='tamamlandi'
    ).select_related('musteri', 'satici').prefetch_related('satisdetay_set__varyant__urun__kategori', 'satisdetay_set__varyant__urun__marka')
    
    # Günlük satış detayları - ürün bazında
    satis_detaylari = SatisDetay.objects.filter(
        satis__satis_tarihi__date=secili_tarih,
        satis__durum='tamamlandi'
    ).select_related(
        'satis', 'satis__musteri', 'satis__satici',
        'varyant', 'varyant__urun', 
        'varyant__urun__kategori', 'varyant__urun__marka',
        'varyant__renk', 'varyant__beden'
    ).order_by('-satis__satis_tarihi')
    
    # İstatistikler
    toplam_satis = satislar.aggregate(
        toplam=Sum('toplam_tutar'),
        adet=Count('id')
    )
    
    toplam_urun_sayisi = satis_detaylari.aggregate(
        toplam_adet=Sum('miktar')
    )['toplam_adet'] or 0
    
    context = {
        'satislar': satislar,
        'satis_detaylari': satis_detaylari,
        'tarih': secili_tarih.strftime('%Y-%m-%d'),
        'toplam_satis': toplam_satis['toplam'] or 0,
        'satis_sayisi': toplam_satis['adet'] or 0,
        'toplam_urun_sayisi': toplam_urun_sayisi,
    }
    return render(request, 'rapor/gunluk_satis.html', context)


@login_required
def stok_raporu(request):
    """Stok raporu view'ı"""
    from urun.models import UrunVaryanti, UrunKategoriUst, Marka
    from django.db.models import Sum, Q
    
    # Tüm varyantları al ve ürün bazında grupla
    varyantlar = UrunVaryanti.objects.filter(
        aktif=True, 
        urun__aktif=True
    ).select_related('urun', 'urun__kategori', 'urun__marka', 'renk', 'beden').order_by('urun__kategori__ad', 'urun__ad')
    
    # Arama filtreleri
    arama = request.GET.get('arama', '').strip()
    kategori_id = request.GET.get('kategori')
    marka_id = request.GET.get('marka')
    durum = request.GET.get('durum')
    
    # Sıralama parametreleri
    sort_field = request.GET.get('sort', 'urun__ad')
    sort_order = request.GET.get('order', 'asc')
    
    # Geçerli sıralama alanları
    valid_sort_fields = [
        'urun__ad', 'renk__ad', 'barkod', 'urun__kategori__ad', 
        'urun__marka__ad', 'urun__alis_fiyati', 'urun__satis_fiyati', 'stok_miktari'
    ]
    
    if sort_field not in valid_sort_fields:
        sort_field = 'urun__ad'
    
    # Sıralama yönü
    if sort_order == 'desc':
        sort_field = '-' + sort_field
    
    # Arama filtresi
    if arama:
        varyantlar = varyantlar.filter(
            Q(urun__ad__icontains=arama) |
            Q(barkod__icontains=arama) |
            Q(urun__urun_kodu__icontains=arama) |
            Q(renk__ad__icontains=arama) |
            Q(beden__ad__icontains=arama)
        )
    
    # Kategori filtresi
    if kategori_id:
        varyantlar = varyantlar.filter(urun__kategori_id=kategori_id)
    
    # Marka filtresi
    if marka_id:
        varyantlar = varyantlar.filter(urun__marka_id=marka_id)
    
    # Stok durumu filtresi
    if durum == 'tukendi':
        varyantlar = varyantlar.filter(stok_miktari=0)
    elif durum == 'kritik':
        varyantlar = varyantlar.filter(stok_miktari__gt=0, stok_miktari__lte=5)
    elif durum == 'normal':
        varyantlar = varyantlar.filter(stok_miktari__gt=5)
    
    # Sıralama uygula
    varyantlar = varyantlar.order_by(sort_field, 'urun__ad', 'renk__ad', 'beden__ad')
    
    # Dropdown için veriler
    kategoriler = UrunKategoriUst.objects.all().order_by('ad')
    markalar = Marka.objects.all().order_by('ad')
    
    context = {
        'varyantlar': varyantlar,
        'kategoriler': kategoriler,
        'markalar': markalar,
        'arama': arama,
        'kategori_id': kategori_id,
        'marka_id': marka_id,
        'durum': durum,
        'sort_field': request.GET.get('sort', 'urun__ad'),
        'sort_order': request.GET.get('order', 'asc'),
    }
    return render(request, 'rapor/stok_raporu.html', context)


@login_required
def cok_satan_urunler(request):
    """En çok satan ürünler raporu view'ı"""
    # Tarih aralığı
    baslangic = request.GET.get('baslangic')
    bitis = request.GET.get('bitis')
    
    if not baslangic:
        # Varsayılan: Bu ay
        baslangic = date.today().replace(day=1)
    else:
        baslangic = datetime.strptime(baslangic, '%Y-%m-%d').date()
    
    if not bitis:
        bitis = date.today()
    else:
        bitis = datetime.strptime(bitis, '%Y-%m-%d').date()
    
    # En çok satan ürünler
    cok_satanlar = SatisDetay.objects.filter(
        satis__satis_tarihi__date__range=[baslangic, bitis],
        satis__durum='tamamlandi'
    ).values('urun').annotate(
        toplam_miktar=Sum('miktar'),
        toplam_ciro=Sum('toplam_fiyat')
    ).order_by('-toplam_miktar')[:20]
    
    # Ürün bilgilerini ekle
    for item in cok_satanlar:
        item['urun_obj'] = Urun.objects.get(pk=item['urun'])
    
    context = {
        'cok_satanlar': cok_satanlar,
        'baslangic': baslangic,
        'bitis': bitis,
    }
    return render(request, 'rapor/cok_satan_urunler.html', context)


@login_required
def kar_zarar(request):
    """Kâr/Zarar analizi view'ı"""
    # Tarih aralığı
    baslangic = request.GET.get('baslangic')
    bitis = request.GET.get('bitis')
    
    if not baslangic:
        baslangic = date.today().replace(day=1)
    else:
        baslangic = datetime.strptime(baslangic, '%Y-%m-%d').date()
    
    if not bitis:
        bitis = date.today()
    else:
        bitis = datetime.strptime(bitis, '%Y-%m-%d').date()
    
    # Satış detayları
    satis_detaylari = SatisDetay.objects.filter(
        satis__satis_tarihi__date__range=[baslangic, bitis],
        satis__durum='tamamlandi'
    )
    
    # Kâr/Zarar hesaplama
    toplam_ciro = 0
    toplam_maliyet = 0
    
    for detay in satis_detaylari:
        toplam_ciro += detay.toplam_fiyat
        toplam_maliyet += (detay.urun.alis_fiyati * detay.miktar)
    
    toplam_kar = toplam_ciro - toplam_maliyet
    kar_marji = (toplam_kar / toplam_ciro * 100) if toplam_ciro > 0 else 0
    
    context = {
        'toplam_ciro': toplam_ciro,
        'toplam_maliyet': toplam_maliyet,
        'toplam_kar': toplam_kar,
        'kar_marji': kar_marji,
        'baslangic': baslangic,
        'bitis': bitis,
    }
    return render(request, 'rapor/kar_zarar.html', context)


@login_required
def musteri_raporu(request):
    """Müşteri raporu view'ı"""
    musteriler = Musteri.objects.filter(aktif=True)
    
    # Müşteri satış istatistikleri
    musteri_stats = []
    for musteri in musteriler:
        satislar = Satis.objects.filter(musteri=musteri, durum='tamamlandi')
        toplam_satis = satislar.aggregate(toplam=Sum('toplam_tutar'))['toplam'] or 0
        satis_adedi = satislar.count()
        
        if satis_adedi > 0:
            musteri_stats.append({
                'musteri': musteri,
                'toplam_satis': toplam_satis,
                'satis_adedi': satis_adedi,
                'ortalama_satis': toplam_satis / satis_adedi
            })
    
    # En çok alışveriş yapan müşteriler
    musteri_stats.sort(key=lambda x: x['toplam_satis'], reverse=True)
    
    context = {
        'musteri_stats': musteri_stats[:20],
    }
    return render(request, 'rapor/musteri_raporu.html', context)


# Excel Export Views
@login_required
def gunluk_satis_excel(request):
    """Günlük satış Excel export"""
    tarih = request.GET.get('tarih', date.today().strftime('%Y-%m-%d'))
    secili_tarih = datetime.strptime(tarih, '%Y-%m-%d').date()
    
    satislar = Satis.objects.filter(
        satis_tarihi__date=secili_tarih,
        durum='tamamlandi'
    )
    
    # Excel dosyası oluştur
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = f"Günlük Satış - {secili_tarih}"
    
    # Başlıklar
    headers = ['Satış No', 'Müşteri', 'Toplam Tutar', 'Ödeme Tipi', 'Tarih']
    for col, header in enumerate(headers, 1):
        worksheet.cell(row=1, column=col, value=header)
    
    # Veriler
    for row, satis in enumerate(satislar, 2):
        worksheet.cell(row=row, column=1, value=satis.satis_no)
        worksheet.cell(row=row, column=2, value=satis.musteri.tam_ad if satis.musteri else 'Bilinmeyen')
        worksheet.cell(row=row, column=3, value=float(satis.toplam_tutar))
        worksheet.cell(row=row, column=4, value=satis.get_odeme_tipi_display())
        worksheet.cell(row=row, column=5, value=satis.satis_tarihi.strftime('%d.%m.%Y %H:%M'))
    
    # Response
    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename="gunluk_satis_{secili_tarih}.xlsx"'
    workbook.save(response)
    return response


@login_required
def gunluk_satis_pdf(request):
    """Günlük satış PDF export"""
    # PDF oluşturma kodu buraya gelecek
    pass


@login_required
def stok_excel(request):
    """Stok raporu Excel export"""
    from urun.models import UrunVaryanti
    
    varyantlar = UrunVaryanti.objects.filter(
        aktif=True, 
        urun__aktif=True
    ).select_related('urun', 'urun__kategori', 'urun__marka', 'renk', 'beden').order_by('urun__kategori__ad', 'urun__ad')
    
    # Filtreler
    durum = request.GET.get('durum')
    if durum == 'tukendi':
        varyantlar = varyantlar.filter(stok_miktari=0)
    elif durum == 'kritik':
        varyantlar = varyantlar.filter(stok_miktari__gt=0, stok_miktari__lte=5)
    
    # Excel dosyası oluştur
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = "Stok Raporu"
    
    # Başlıklar
    headers = ['Ürün Adı', 'Varyant', 'Barkod', 'Kategori', 'Marka', 'Alış Fiyatı', 'Satış Fiyatı', 'Kar Oranı %', 'Stok Miktarı', 'Durum']
    for col, header in enumerate(headers, 1):
        worksheet.cell(row=1, column=col, value=header)
    
    # Veriler
    for row, varyant in enumerate(varyantlar, 2):
        varyant_adi = ""
        if varyant.renk:
            varyant_adi += varyant.renk.ad
        if varyant.renk and varyant.beden:
            varyant_adi += " - "
        if varyant.beden:
            varyant_adi += varyant.beden.ad
        if not varyant_adi:
            varyant_adi = "Standart"
            
        durum_text = "Normal"
        if varyant.stok_miktari == 0:
            durum_text = "Tükendi"
        elif varyant.stok_miktari <= 5:
            durum_text = "Kritik"
        
        worksheet.cell(row=row, column=1, value=varyant.urun.ad)
        worksheet.cell(row=row, column=2, value=varyant_adi)
        worksheet.cell(row=row, column=3, value=varyant.barkod)
        worksheet.cell(row=row, column=4, value=str(varyant.urun.kategori))
        worksheet.cell(row=row, column=5, value=str(varyant.urun.marka) if varyant.urun.marka else "-")
        worksheet.cell(row=row, column=6, value=float(varyant.urun.alis_fiyati))
        worksheet.cell(row=row, column=7, value=float(varyant.urun.satis_fiyati))
        worksheet.cell(row=row, column=8, value=float(varyant.urun.kar_orani))
        worksheet.cell(row=row, column=9, value=varyant.stok_miktari)
        worksheet.cell(row=row, column=10, value=durum_text)
    
    # Response
    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = 'attachment; filename="stok_raporu.xlsx"'
    workbook.save(response)
    return response


@login_required
def stok_pdf(request):
    """Stok raporu PDF export"""
    # PDF oluşturma kodu buraya gelecek
    pass


@login_required
def kar_zarar_excel(request):
    """Kâr/Zarar Excel export"""
    # Excel oluşturma kodu buraya gelecek
    pass


@login_required
def kar_zarar_pdf(request):
    """Kâr/Zarar PDF export"""
    # PDF oluşturma kodu buraya gelecek
    pass


@login_required
def stok_hareketleri(request, varyant_id):
    """Ürün varyantının stok hareketleri"""
    from urun.models import UrunVaryanti, StokHareket
    from satis.models import SatisDetay
    from django.shortcuts import get_object_or_404
    
    varyant = get_object_or_404(UrunVaryanti, id=varyant_id)
    
    # Satış hareketleri (çıkışlar)
    satis_hareketleri = SatisDetay.objects.filter(
        varyant=varyant
    ).select_related('satis', 'satis__musteri', 'satis__satici').order_by('-satis__satis_tarihi')
    
    # Stok hareketleri (giriş, çıkış, düzeltme vb.)
    stok_hareketleri = StokHareket.objects.filter(
        varyant=varyant
    ).select_related('kullanici').order_by('-olusturma_tarihi')
    
    context = {
        'varyant': varyant,
        'satis_hareketleri': satis_hareketleri,
        'stok_hareketleri': stok_hareketleri,
        'title': f'{varyant.urun.ad} - Stok Hareketleri'
    }
    return render(request, 'rapor/stok_hareketleri.html', context)
