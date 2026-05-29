from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.db.models import Q, Sum
from django.views.decorators.http import require_http_methods
from .models import Musteri, MusteriGruplar


@login_required
def musteri_listesi(request):
    """Müşteri listesi view'ı"""
    from django.utils import timezone
    from datetime import timedelta
    from django.db.models import Sum, Count
    from satis.models import Satis
    from .models import Tahsilat, BorcAlacakHareket

    # Base queryset - show all customers (active and inactive)
    musteriler = Musteri.objects.all().order_by('ad', 'soyad')

    # Get filter parameters
    query = request.GET.get('q', '')
    tip_filter = request.GET.get('tip', 'all')
    durum_filter = request.GET.get('durum', 'all')
    aktif_filter = request.GET.get('aktif', 'all')

    # Apply search filter
    if query:
        musteriler = musteriler.filter(
            Q(ad__icontains=query) |
            Q(soyad__icontains=query) |
            Q(telefon__icontains=query) |
            Q(email__icontains=query) |
            Q(firma_adi__icontains=query)
        )

    # Apply customer type filter
    if tip_filter != 'all':
        musteriler = musteriler.filter(tip=tip_filter)

    # Apply active status filter
    if aktif_filter == 'True':
        musteriler = musteriler.filter(aktif=True)
    elif aktif_filter == 'False':
        musteriler = musteriler.filter(aktif=False)

    # Apply balance status filter
    if durum_filter == 'borclu':
        musteriler = musteriler.filter(acik_hesap_bakiye__gt=0)
    elif durum_filter == 'alacakli':
        musteriler = musteriler.filter(acik_hesap_bakiye__lt=0)
    elif durum_filter == 'sifir':
        musteriler = musteriler.filter(acik_hesap_bakiye=0)

    # Calculate 30 days ago
    thirty_days_ago = timezone.now() - timedelta(days=30)

    # Annotate with 30-day stats
    musteriler = musteriler.annotate(
        son_30gun_satis=Sum(
            'satis__toplam_tutar',
            filter=Q(satis__satis_tarihi__gte=thirty_days_ago) & Q(satis__durum='tamamlandi')
        )
    ).annotate(
        son_30gun_tahsilat=Sum(
            'tahsilat__tutar',
            filter=Q(tahsilat__tahsilat_tarihi__gte=thirty_days_ago) & Q(tahsilat__durum='tahsil_edildi')
        )
    )

    # Replace None with 0 for the annotated fields
    for musteri in musteriler:
        if musteri.son_30gun_satis is None:
            musteri.son_30gun_satis = 0
        if musteri.son_30gun_tahsilat is None:
            musteri.son_30gun_tahsilat = 0

    # Calculate statistics
    toplam_musteri = Musteri.objects.count()
    aktif_count = Musteri.objects.filter(aktif=True).count()
    borclu_count = Musteri.objects.filter(acik_hesap_bakiye__gt=0).count()
    alacakli_count = Musteri.objects.filter(acik_hesap_bakiye__lt=0).count()

    # Paginate
    paginator = Paginator(musteriler, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'query': query,
        'tip_filter': tip_filter,
        'durum_filter': durum_filter,
        'aktif_filter': aktif_filter,
        'toplam_musteri': toplam_musteri,
        'borclu_count': borclu_count,
        'alacakli_count': alacakli_count,
        'aktif_count': aktif_count,
    }
    return render(request, 'musteri/musteri_listesi.html', context)


@login_required
def musteri_ekle(request):
    """Müşteri ekleme view'ı"""
    if request.method == 'POST':
        ad = request.POST.get('ad')
        soyad = request.POST.get('soyad')
        telefon = request.POST.get('telefon')
        email = request.POST.get('email', '')
        adres = request.POST.get('adres', '')
        il = request.POST.get('il', '')
        ilce = request.POST.get('ilce', '')
        tip = request.POST.get('tip', 'bireysel')
        notlar = request.POST.get('notlar', '')
        acik_hesap_limit = request.POST.get('acik_hesap_limit', '0.00')
        
        # Tip özelinde alanlar
        tc_no = request.POST.get('tc_no', '')
        vergi_no = request.POST.get('vergi_no', '')
        vergi_dairesi = request.POST.get('vergi_dairesi', '')
        firma_adi = request.POST.get('firma_adi', '')
        
        # Temel validasyon
        if not (ad and soyad and telefon):
            messages.error(request, 'Ad, soyad ve telefon alanları gerekli.')
            return render(request, 'musteri/musteri_form.html', {
                'title': 'Müşteri Ekle',
                'form_data': request.POST
            })
        
        # Tip özelinde validasyon
        if tip == 'kurumsal':
            if not (firma_adi and vergi_no and vergi_dairesi):
                messages.error(request, 'Kurumsal müşteriler için firma adı, vergi numarası ve vergi dairesi gerekli.')
                return render(request, 'musteri/musteri_form.html', {
                    'title': 'Müşteri Ekle',
                    'form_data': request.POST
                })
        else:  # bireysel
            if tc_no and len(tc_no) != 11:
                messages.error(request, 'TC kimlik numarası 11 haneli olmalıdır.')
                return render(request, 'musteri/musteri_form.html', {
                    'title': 'Müşteri Ekle',
                    'form_data': request.POST
                })
        
        # Telefon kontrolü
        if Musteri.objects.filter(telefon=telefon).exists():
            messages.error(request, 'Bu telefon numarası zaten kayıtlı!')
            return render(request, 'musteri/musteri_form.html', {
                'title': 'Müşteri Ekle',
                'form_data': request.POST
            })
        
        # Vergi numarası kontrolü (eğer girilmişse)
        if vergi_no and Musteri.objects.filter(vergi_no=vergi_no).exists():
            messages.error(request, 'Bu vergi numarası zaten kayıtlı!')
            return render(request, 'musteri/musteri_form.html', {
                'title': 'Müşteri Ekle',
                'form_data': request.POST
            })
        
        # TC numarası kontrolü (eğer girilmişse)
        if tc_no and Musteri.objects.filter(tc_no=tc_no).exists():
            messages.error(request, 'Bu TC kimlik numarası zaten kayıtlı!')
            return render(request, 'musteri/musteri_form.html', {
                'title': 'Müşteri Ekle',
                'form_data': request.POST
            })
        
        try:
            # Açık hesap limit'i decimal'e çevir
            from decimal import Decimal
            try:
                acik_hesap_limit = Decimal(acik_hesap_limit or '0.00')
            except:
                acik_hesap_limit = Decimal('0.00')
            
            musteri = Musteri.objects.create(
                ad=ad,
                soyad=soyad,
                telefon=telefon,
                email=email,
                adres=adres,
                il=il,
                ilce=ilce,
                tip=tip,
                notlar=notlar,
                tc_no=tc_no if tc_no else None,
                vergi_no=vergi_no if vergi_no else None,
                vergi_dairesi=vergi_dairesi if vergi_dairesi else None,
                firma_adi=firma_adi if firma_adi else None,
                acik_hesap_limit=acik_hesap_limit,
                kaydeden=request.user
            )
            
            musteri_adi = firma_adi if tip == 'kurumsal' else f'{ad} {soyad}'
            messages.success(request, f'{musteri_adi} başarıyla eklendi.')
            return redirect('musteri:liste')
            
        except Exception as e:
            messages.error(request, f'Müşteri eklenirken hata oluştu: {str(e)}')
    
    context = {
        'title': 'Müşteri Ekle',
        'form_data': request.POST if request.method == 'POST' else {}
    }
    return render(request, 'musteri/musteri_form.html', context)


@login_required
def musteri_duzenle(request, pk):
    """Müşteri düzenleme view'ı"""
    musteri = get_object_or_404(Musteri, pk=pk)
    
    if request.method == 'POST':
        musteri.ad = request.POST.get('ad', musteri.ad)
        musteri.soyad = request.POST.get('soyad', musteri.soyad)
        telefon = request.POST.get('telefon', musteri.telefon)
        
        # Telefon kontrolü (kendisi hariç)
        if telefon != musteri.telefon and Musteri.objects.filter(telefon=telefon).exists():
            messages.error(request, 'Bu telefon numarası zaten kayıtlı!')
            return render(request, 'musteri/musteri_form.html', {
                'musteri': musteri,
                'title': 'Müşteri Düzenle'
            })
        
        musteri.telefon = telefon
        musteri.email = request.POST.get('email', musteri.email)
        musteri.adres = request.POST.get('adres', musteri.adres)
        musteri.il = request.POST.get('il', musteri.il)
        musteri.ilce = request.POST.get('ilce', musteri.ilce)
        musteri.tip = request.POST.get('tip', musteri.tip)
        musteri.notlar = request.POST.get('notlar', musteri.notlar)
        
        # Açık hesap limit'i güncelle
        acik_hesap_limit = request.POST.get('acik_hesap_limit', '0.00')
        try:
            from decimal import Decimal
            musteri.acik_hesap_limit = Decimal(acik_hesap_limit or '0.00')
        except:
            musteri.acik_hesap_limit = Decimal('0.00')
        
        musteri.save()
        messages.success(request, f'{musteri.tam_ad} başarıyla güncellendi.')
        return redirect('musteri_detay', pk=musteri.pk)
    
    context = {
        'musteri': musteri,
        'title': 'Müşteri Düzenle'
    }
    return render(request, 'musteri/musteri_form.html', context)


@login_required
def musteri_detay(request, pk):
    """Müşteri detay view'ı"""
    musteri = get_object_or_404(Musteri, pk=pk)

    from satis.models import Satis
    from .models import Tahsilat

    tum_satislar = Satis.objects.filter(musteri=musteri).order_by('-satis_tarihi')
    tum_tahsilatlar = Tahsilat.objects.filter(musteri=musteri).order_by('-tahsilat_tarihi')

    toplam_satis = Satis.objects.filter(
        musteri=musteri,
        durum='tamamlandi'
    ).aggregate(toplam=Sum('genel_toplam'))['toplam'] or 0

    toplam_tahsilat = Tahsilat.objects.filter(
        musteri=musteri,
        durum='tahsil_edildi'
    ).aggregate(toplam=Sum('tutar'))['toplam'] or 0

    context = {
        'musteri': musteri,
        'son_satislar': tum_satislar,
        'son_tahsilatlar': tum_tahsilatlar,
        'satis_sayisi': tum_satislar.count(),
        'tahsilat_sayisi': tum_tahsilatlar.count(),
        'toplam_satis': toplam_satis,
        'toplam_tahsilat': toplam_tahsilat,
    }
    return render(request, 'musteri/musteri_detay.html', context)


@login_required
def musteri_sil(request, pk):
    """Müşteri silme view'ı"""
    musteri = get_object_or_404(Musteri, pk=pk)
    
    if request.method == 'POST':
        musteri.aktif = False
        musteri.save()
        messages.success(request, f'{musteri.tam_ad} başarıyla silindi.')
        return redirect('musteri:liste')
    
    return render(request, 'musteri/musteri_sil.html', {'musteri': musteri})


@login_required
def musteri_grup_listesi(request):
    """Müşteri grup listesi view'ı"""
    gruplar = MusteriGruplar.objects.filter(aktif=True)
    context = {'gruplar': gruplar}
    return render(request, 'musteri/grup_listesi.html', context)


@login_required
def musteri_grup_ekle(request):
    """Müşteri grup ekleme view'ı"""
    if request.method == 'POST':
        ad = request.POST.get('ad')
        aciklama = request.POST.get('aciklama', '')
        indirim_orani = request.POST.get('indirim_orani', 0)
        
        if ad:
            MusteriGruplar.objects.create(
                ad=ad,
                aciklama=aciklama,
                indirim_orani=indirim_orani
            )
            messages.success(request, 'Müşteri grubu başarıyla eklendi.')
            return redirect('musteri:musteri_grup_listesi')
        else:
            messages.error(request, 'Grup adı gerekli.')
    
    context = {'title': 'Müşteri Grup Ekle'}
    return render(request, 'musteri/grup_form.html', context)


@login_required
def musteri_grup_duzenle(request, pk):
    """Müşteri grup düzenleme view'ı"""
    grup = get_object_or_404(MusteriGruplar, pk=pk)
    
    if request.method == 'POST':
        grup.ad = request.POST.get('ad', grup.ad)
        grup.aciklama = request.POST.get('aciklama', grup.aciklama)
        grup.indirim_orani = request.POST.get('indirim_orani', grup.indirim_orani)
        grup.save()
        
        messages.success(request, f'{grup.ad} başarıyla güncellendi.')
        return redirect('musteri:musteri_grup_listesi')
    
    context = {
        'grup': grup,
        'title': 'Müşteri Grup Düzenle'
    }
    return render(request, 'musteri/grup_form.html', context)


# AJAX Views
@login_required
def telefon_kontrol(request):
    """Telefon kontrol AJAX view'ı"""
    telefon = request.GET.get('telefon')
    musteri_id = request.GET.get('musteri_id')  # Düzenleme için
    
    query = Musteri.objects.filter(telefon=telefon)
    if musteri_id:
        query = query.exclude(pk=musteri_id)
    
    exists = query.exists()
    return JsonResponse({'exists': exists})


@login_required
def musteri_ara(request):
    """Müşteri arama AJAX view'ı"""
    query = request.GET.get('q', '')
    
    if len(query) >= 2:
        musteriler = Musteri.objects.filter(
            Q(ad__icontains=query) | 
            Q(soyad__icontains=query) | 
            Q(telefon__icontains=query) |
            Q(firma_adi__icontains=query),
            aktif=True
        )[:10]
        
        data = []
        for musteri in musteriler:
            data.append({
                'id': musteri.id,
                'ad': musteri.ad,
                'soyad': musteri.soyad,
                'telefon': musteri.telefon,
                'tip': musteri.tip,
                'firma_adi': musteri.firma_adi,
                'acik_hesap_bakiye': float(musteri.acik_hesap_bakiye or 0),
                'acik_hesap_limit': float(musteri.acik_hesap_limit or 0),
            })
        
        return JsonResponse({'success': True, 'musteriler': data})
    
    return JsonResponse({'success': True, 'musteriler': []})

@require_http_methods(["GET"])
def musteri_ajax_detay(request, musteri_id):
    """AJAX ile müşteri detayını getir"""
    try:
        musteri = get_object_or_404(Musteri, id=musteri_id, aktif=True)

        musteri_data = {
            'id': musteri.id,
            'ad': musteri.ad,
            'soyad': musteri.soyad,
            'telefon': musteri.telefon,
            'email': musteri.email,
            'tip': musteri.tip,
            'firma_adi': musteri.firma_adi,
            'tc_no': musteri.tc_no,
            'vergi_no': musteri.vergi_no,
            'acik_hesap_bakiye': float(musteri.acik_hesap_bakiye or 0),
            'acik_hesap_limit': float(musteri.acik_hesap_limit or 0),
        }

        return JsonResponse({
            'success': True,
            'musteri': musteri_data
        })

    except Musteri.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Müşteri bulunamadı'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })


@login_required
@require_http_methods(["POST"])
def musteri_toggle_aktif(request):
    """AJAX ile müşteri aktif/pasif durumunu değiştir"""
    musteri_id = request.POST.get('musteri_id')

    if not musteri_id:
        return JsonResponse({'success': False, 'error': 'Müşteri ID gerekli'})

    try:
        musteri = get_object_or_404(Musteri, id=musteri_id)

        # Pasif yapilmak isteniyorsa bakiye kontrolü yap
        if not musteri.aktif:
            # Aktif yapiliyor - izin ver
            musteri.aktif = True
            musteri.save()
            return JsonResponse({
                'success': True,
                'message': f'{musteri.tam_ad} başarıyla aktif edildi.',
                'yeni_durum': 'aktif'
            })
        else:
            # Pasif yapilmak isteniyor - bakiye kontrolü
            bakiye = float(musteri.acik_hesap_bakiye or 0)
            if bakiye != 0:
                bakiye_tipi = 'borçlu' if bakiye > 0 else 'alacaklı'
                return JsonResponse({
                    'success': False,
                    'error': f'{musteri.tam_ad} pasif yapılamaz. Müşterinin {bakiye_tipi} bakiyesi ({abs(bakiye):.2f} ₺) bulunmaktadır. Önce bakiyeyi sıfıra indirin.'
                })

            musteri.aktif = False
            musteri.save()
            return JsonResponse({
                'success': True,
                'message': f'{musteri.tam_ad} başarıyla pasif edildi.',
                'yeni_durum': 'pasif'
            })

    except Musteri.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Müşteri bulunamadı'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})
