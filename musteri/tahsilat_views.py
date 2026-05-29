from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.db import transaction
from django.db.models import Q, Sum
from django.utils.dateparse import parse_date, parse_datetime
from django.utils import timezone
from django.core.paginator import Paginator
from .models import Musteri, Tahsilat, TahsilatDetay, BorcAlacakHareket
from satis.models import Satis, Odeme
import json
import re
from decimal import Decimal, InvalidOperation


def _parse_post_tutar(raw):
    """POST tutar alanı: 15000.50 veya 15.000,50 gibi değerleri Decimal yapar."""
    if raw is None:
        return Decimal('0')
    s = str(raw).strip().replace('₺', '').replace(' ', '')
    if not s:
        return Decimal('0')
    if ',' in s:
        s = s.replace('.', '').replace(',', '.')
    else:
        s = re.sub(r'[^\d.\-]', '', s)
    try:
        return Decimal(s)
    except (InvalidOperation, ValueError):
        raise ValueError('Geçersiz tutar formatı')


def _musteri_duzenleme_icin_get(musteri_id, tahsilat):
    """Düzenlemede mevcut müşteri veya aktif müşteri seçilebilir."""
    try:
        musteri = Musteri.objects.get(pk=musteri_id)
    except Musteri.DoesNotExist:
        return None
    if musteri.pk == tahsilat.musteri_id or musteri.aktif:
        return musteri
    return None


@login_required
def borc_alacak_listesi(request):
    """Müşteri borç-alacak listesi"""
    # Filtreleme
    search = request.GET.get('search', '')
    durum = request.GET.get('durum', 'all')  # all, borclu, alacakli
    
    # Borcu olan müşteriler (acik_hesap_bakiye > 0)
    musteriler = Musteri.objects.filter(aktif=True)
    
    if search:
        musteriler = musteriler.filter(
            Q(ad__icontains=search) |
            Q(soyad__icontains=search) |
            Q(telefon__icontains=search) |
            Q(firma_adi__icontains=search)
        )
    
    if durum == 'borclu':
        musteriler = musteriler.filter(acik_hesap_bakiye__gt=0)
    elif durum == 'alacakli':
        musteriler = musteriler.filter(acik_hesap_bakiye__lt=0)
    
    # Müşteri bazında istatistikler ekle
    for musteri in musteriler:
        # Son 30 günlük satışlar
        musteri.son_30gun_satis = Satis.objects.filter(
            musteri=musteri,
            durum='tamamlandi',
            satis_tarihi__gte=timezone.now() - timezone.timedelta(days=30)
        ).aggregate(toplam=Sum('toplam_tutar'))['toplam'] or 0
        
        # Son 30 günlük tahsilatlar
        musteri.son_30gun_tahsilat = Tahsilat.objects.filter(
            musteri=musteri,
            durum='tahsil_edildi',
            tahsilat_tarihi__gte=timezone.now() - timezone.timedelta(days=30)
        ).aggregate(toplam=Sum('tutar'))['toplam'] or 0
    
    # Sayfalama
    paginator = Paginator(musteriler.order_by('-acik_hesap_bakiye'), 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Özet istatistikler
    toplam_borc = musteriler.filter(acik_hesap_bakiye__gt=0).aggregate(
        toplam=Sum('acik_hesap_bakiye'))['toplam'] or 0
    toplam_alacak = abs(musteriler.filter(acik_hesap_bakiye__lt=0).aggregate(
        toplam=Sum('acik_hesap_bakiye'))['toplam'] or 0)
    borclu_musteri_sayisi = musteriler.filter(acik_hesap_bakiye__gt=0).count()
    
    context = {
        'page_obj': page_obj,
        'search': search,
        'durum': durum,
        'toplam_borc': toplam_borc,
        'toplam_alacak': toplam_alacak,
        'borclu_musteri_sayisi': borclu_musteri_sayisi,
        'toplam_musteri_sayisi': musteriler.count(),
    }
    
    return render(request, 'musteri/borc_alacak_listesi.html', context)


@login_required
def musteri_borc_detay(request, musteri_id):
    """Müşteri borç detayı"""
    musteri = get_object_or_404(Musteri, id=musteri_id)
    
    # Veresiye satışlar (açık hesap ödemeli)
    # Açık hesap ödemesi olan satışları bul
    acik_hesap_satis_ids = Odeme.objects.filter(
        odeme_tipi='acik_hesap'
    ).values_list('satis_id', flat=True)
    
    odenmemis_satislar = Satis.objects.filter(
        id__in=acik_hesap_satis_ids,
        musteri=musteri,
        durum='tamamlandi'
    ).order_by('-satis_tarihi')
    
    # Son hareketler
    hareketler = BorcAlacakHareket.objects.filter(
        musteri=musteri
    ).order_by('-hareket_tarihi')[:20]
    
    # Son tahsilatlar
    tahsilatlar = Tahsilat.objects.filter(
        musteri=musteri
    ).order_by('-tahsilat_tarihi')[:10]
    
    context = {
        'musteri': musteri,
        'odenmemis_satislar': odenmemis_satislar,
        'hareketler': hareketler,
        'tahsilatlar': tahsilatlar,
    }
    
    return render(request, 'musteri/musteri_borc_detay.html', context)



@login_required
def tahsilat_listesi(request):
    """Tahsilat listesi - modern dashboard view"""
    search = request.GET.get('search', '')
    durum = request.GET.get('durum', 'all')
    tahsilat_tipi = request.GET.get('tahsilat_tipi', 'all')
    baslangic_tarihi = request.GET.get('baslangic_tarihi', '')
    bitis_tarihi = request.GET.get('bitis_tarihi', '')
    musteri_id = request.GET.get('musteri', '')
    filtre_musteri = None

    tahsilatlar = Tahsilat.objects.select_related('musteri').all()

    if musteri_id:
        try:
            filtre_musteri = Musteri.objects.get(pk=musteri_id)
            tahsilatlar = tahsilatlar.filter(musteri_id=musteri_id)
        except (Musteri.DoesNotExist, ValueError):
            musteri_id = ''
    
    if search:
        tahsilatlar = tahsilatlar.filter(
            Q(tahsilat_no__icontains=search) |
            Q(musteri__ad__icontains=search) |
            Q(musteri__soyad__icontains=search) |
            Q(musteri__telefon__icontains=search)
        )
    
    if durum != 'all':
        tahsilatlar = tahsilatlar.filter(durum=durum)

    if tahsilat_tipi != 'all':
        tahsilatlar = tahsilatlar.filter(tahsilat_tipi=tahsilat_tipi)
    
    if baslangic_tarihi:
        tahsilatlar = tahsilatlar.filter(tahsilat_tarihi__date__gte=baslangic_tarihi)
    
    if bitis_tarihi:
        tahsilatlar = tahsilatlar.filter(tahsilat_tarihi__date__lte=bitis_tarihi)
    
    # Sayfalama
    paginator = Paginator(tahsilatlar.order_by('-tahsilat_tarihi'), 50)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Özet istatistikler
    toplam_tahsilat = tahsilatlar.filter(durum='tahsil_edildi').aggregate(toplam=Sum('tutar'))['toplam'] or 0

    # Bugünkü tahsilat
    bugun = timezone.now().date()
    bugunku_tahsilat = Tahsilat.objects.filter(
        durum='tahsil_edildi',
        tahsilat_tarihi__date=bugun
    ).aggregate(toplam=Sum('tutar'))['toplam'] or 0

    # İptal sayısı
    iptal_sayisi = tahsilatlar.filter(durum='iptal').count()

    # Toplam borç (müşteri borçları)
    toplam_borc = Musteri.objects.filter(aktif=True, acik_hesap_bakiye__gt=0).aggregate(
        toplam=Sum('acik_hesap_bakiye'))['toplam'] or 0
    
    context = {
        'page_obj': page_obj,
        'search': search,
        'durum': durum,
        'tahsilat_tipi': tahsilat_tipi,
        'baslangic_tarihi': baslangic_tarihi,
        'bitis_tarihi': bitis_tarihi,
        'toplam_tahsilat': toplam_tahsilat,
        'bugunku_tahsilat': bugunku_tahsilat,
        'toplam_borc': toplam_borc,
        'iptal_sayisi': iptal_sayisi,
        'filtre_musteri': filtre_musteri,
        'musteri_id': musteri_id,
    }
    
    return render(request, 'musteri/tahsilat_listesi.html', context)


@login_required
def tahsilat_detay(request, tahsilat_id):
    """Tahsilat detayı ve fiş"""
    tahsilat = get_object_or_404(Tahsilat, id=tahsilat_id)

    if request.GET.get('format') == 'json':
        return JsonResponse({
            'tahsilat_no': tahsilat.tahsilat_no,
            'tahsilat_tarihi': tahsilat.tahsilat_tarihi.strftime('%d.%m.%Y %H:%M'),
            'musteri': tahsilat.musteri.tam_ad if tahsilat.musteri else '-',
            'tahsilat_tipi': tahsilat.get_tahsilat_tipi_display(),
            'tutar': float(tahsilat.tutar),
            'aciklama': tahsilat.aciklama or '',
        })
    
    context = {
        'tahsilat': tahsilat,
    }
    
    return render(request, 'musteri/tahsilat_detay.html', context)


@login_required
def tahsilat_ekle(request):
    """Modern tahsilat ekleme formu"""
    if request.method == 'GET':
        return render(request, 'musteri/tahsilat_ekle.html')
    
    elif request.method == 'POST':
        try:
            # Form verilerini al
            musteri_id = request.POST.get('musteri_id')
            tutar = Decimal(request.POST.get('tutar', '0'))
            tahsilat_tipi = request.POST.get('tahsilat_tipi')
            aciklama = request.POST.get('aciklama', '')
            
            # Validation
            if not musteri_id:
                return JsonResponse({
                    'success': False,
                    'message': 'Müşteri seçimi zorunludur.'
                })
            
            if tutar <= 0:
                return JsonResponse({
                    'success': False,
                    'message': 'Tahsilat tutarı 0\'dan büyük olmalıdır.'
                })
            
            if not tahsilat_tipi:
                return JsonResponse({
                    'success': False,
                    'message': 'Ödeme yöntemi seçimi zorunludur.'
                })
            
            # Müşteri kontrolü
            try:
                musteri = Musteri.objects.get(id=musteri_id, aktif=True)
            except Musteri.DoesNotExist:
                return JsonResponse({
                    'success': False,
                    'message': 'Geçersiz müşteri seçimi.'
                })
            
            # Ek bilgiler (ödeme tipine göre)
            taksit_sayisi = 1  # Varsayılan
            durum = 'tahsil_edildi'  # Varsayılan durum
            
            # Kredi kartı için taksit bilgisi
            if tahsilat_tipi == 'kart':
                taksit_sayisi = int(request.POST.get('taksit_sayisi', 1))
            
            # Tahsilat kaydı oluştur
            tahsilat = Tahsilat.objects.create(
                musteri=musteri,
                tutar=tutar,
                tahsilat_tipi=tahsilat_tipi,
                taksit_sayisi=taksit_sayisi,
                aciklama=aciklama,
                tahsilat_eden=request.user,
                durum=durum
            )
            
            # Müşteri bakiyesini güncelle ve hareket ekle
            if durum == 'tahsil_edildi':  # Sadece tahsil edilmiş ödemeler için
                musteri.alacak_hareket_ekle(
                    tutar=tutar,
                    aciklama=f'Tahsilat - {tahsilat.tahsilat_no}',
                    tahsilat=tahsilat,
                    user=request.user
                )
            
            return JsonResponse({
                'success': True,
                'message': f'Tahsilat başarıyla kaydedildi. Tahsilat No: {tahsilat.tahsilat_no}',
                'tahsilat_no': tahsilat.tahsilat_no,
                'tahsilat_id': tahsilat.id
            })
            
        except ValueError as e:
            return JsonResponse({
                'success': False,
                'message': 'Geçersiz tutar formatı.'
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'Tahsilat kaydedilirken hata oluştu: {str(e)}'
            })
    
    return JsonResponse({
        'success': False,
        'message': 'Geçersiz istek metodu.'
    })


def _tahsilat_ledger_kayitlarini_temizle(tahsilat, musteri_ids=None):
    """Tahsilata bağlı cari hareketleri sil (bakiye sonra yeniden hesaplanır)."""
    tahsilat_no = tahsilat.tahsilat_no
    base = BorcAlacakHareket.objects.filter(tahsilat=tahsilat)
    if musteri_ids:
        base = base.filter(musteri_id__in=musteri_ids)
    base.delete()

    extra = BorcAlacakHareket.objects.filter(
        aciklama__icontains=tahsilat_no,
    ).filter(
        Q(aciklama__icontains='Tahsilat Düzeltme')
        | Q(aciklama__startswith=f'Tahsilat - {tahsilat_no}')
    )
    if musteri_ids:
        extra = extra.filter(musteri_id__in=musteri_ids)
    extra.delete()


@login_required
def tahsilat_duzenle(request, tahsilat_id):
    """Tahsilat düzenleme"""
    tahsilat = get_object_or_404(Tahsilat, id=tahsilat_id)
    
    if request.method == 'GET':
        musteriler = Musteri.objects.filter(
            Q(aktif=True) | Q(pk=tahsilat.musteri_id)
        ).distinct().order_by('ad', 'soyad')
        context = {
            'tahsilat': tahsilat,
            'musteriler': musteriler,
        }
        return render(request, 'musteri/tahsilat_duzenle.html', context)
    
    elif request.method == 'POST':
        try:
            with transaction.atomic():
                tahsilat = get_object_or_404(
                    Tahsilat.objects.select_for_update(),
                    id=tahsilat_id,
                )
                eski_musteri_id = tahsilat.musteri_id
                eski_durum = tahsilat.durum

                musteri_id = request.POST.get('musteri_id')
                tutar = _parse_post_tutar(request.POST.get('tutar'))
                tahsilat_tipi = request.POST.get('tahsilat_tipi')
                aciklama = request.POST.get('aciklama', '')

                vade_str = (request.POST.get('vade_tarihi') or '').strip()
                vade_tarihi = parse_date(vade_str) if vade_str else None
                cek_senet_no = request.POST.get('cek_senet_no', '')
                banka = request.POST.get('banka', '')
                referans_no = request.POST.get('referans_no', '')

                if not musteri_id:
                    return JsonResponse({
                        'success': False,
                        'message': 'Müşteri seçimi zorunludur.',
                    })

                if tutar <= 0:
                    return JsonResponse({
                        'success': False,
                        'message': 'Tahsilat tutarı 0\'dan büyük olmalıdır.',
                    })

                if not tahsilat_tipi:
                    return JsonResponse({
                        'success': False,
                        'message': 'Tahsilat tipi seçimi zorunludur.',
                    })

                yeni_musteri = _musteri_duzenleme_icin_get(musteri_id, tahsilat)
                if not yeni_musteri:
                    return JsonResponse({
                        'success': False,
                        'message': 'Geçersiz müşteri seçimi.',
                    })

                tahsilat.musteri = yeni_musteri
                tahsilat.tutar = tutar
                tahsilat.tahsilat_tipi = tahsilat_tipi
                tahsilat.aciklama = aciklama
                tahsilat.vade_tarihi = vade_tarihi
                tahsilat.cek_senet_no = cek_senet_no or None
                tahsilat.banka = banka or None
                tahsilat.referans_no = referans_no or None

                if tahsilat_tipi == 'kart':
                    tahsilat.taksit_sayisi = int(request.POST.get('taksit_sayisi', 1) or 1)
                else:
                    tahsilat.taksit_sayisi = None

                tarih_str = (request.POST.get('tahsilat_tarihi') or '').strip()
                if tarih_str:
                    parsed = parse_datetime(tarih_str)
                    if parsed:
                        if timezone.is_naive(parsed):
                            parsed = timezone.make_aware(parsed)
                        tahsilat.tahsilat_tarihi = parsed

                tahsilat.save()

                if eski_durum == 'tahsil_edildi' or tahsilat.durum == 'tahsil_edildi':
                    etkilenen_musteriler = {
                        x for x in (eski_musteri_id, yeni_musteri.id) if x
                    }
                    _tahsilat_ledger_kayitlarini_temizle(
                        tahsilat, musteri_ids=etkilenen_musteriler,
                    )
                    for mid in etkilenen_musteriler:
                        Musteri.objects.get(pk=mid).bakiye_yeniden_hesapla()

                    if tahsilat.durum == 'tahsil_edildi':
                        yeni_musteri.alacak_hareket_ekle(
                            tutar=tutar,
                            aciklama=f'Tahsilat - {tahsilat.tahsilat_no}',
                            tahsilat=tahsilat,
                            user=request.user,
                            tarih=tahsilat.tahsilat_tarihi,
                        )

            tahsilat.refresh_from_db()
            return JsonResponse({
                'success': True,
                'message': f'Tahsilat başarıyla güncellendi. Tahsilat No: {tahsilat.tahsilat_no}',
                'tahsilat_no': tahsilat.tahsilat_no,
                'tahsilat_id': tahsilat.id,
            })

        except ValueError as e:
            msg = str(e) if str(e) else 'Geçersiz tutar formatı.'
            return JsonResponse({
                'success': False,
                'message': msg,
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'Tahsilat güncellenirken hata oluştu: {str(e)}',
            })
    
    return JsonResponse({
        'success': False,
        'message': 'Geçersiz istek metodu.',
    })


@login_required
def tahsilat_iptal(request, tahsilat_id):
    """Tahsilat iptal etme"""
    tahsilat = get_object_or_404(Tahsilat, id=tahsilat_id)
    
    if request.method == 'POST':
        if tahsilat.durum == 'iptal':
            messages.warning(request, 'Bu tahsilat zaten iptal edilmiş!')
            return redirect('musteri:tahsilat_detay', tahsilat_id=tahsilat.id)
        
        try:
            # Tahsilat durumunu iptal et
            tahsilat.durum = 'iptal'
            tahsilat.save()
            
            # İptal hareketi ekle (müşteri bakiyesi burada güncellenir)
            tahsilat.musteri.borc_hareket_ekle(
                tutar=tahsilat.tutar,
                aciklama=f'Tahsilat İptal - {tahsilat.tahsilat_no}',
                user=request.user
            )
            
            messages.success(request, 'Tahsilat başarıyla iptal edildi!')
            return redirect('musteri:tahsilat_detay', tahsilat_id=tahsilat.id)
            
        except Exception as e:
            messages.error(request, f'Tahsilat iptal edilirken hata oluştu: {str(e)}')
    
    context = {
        'tahsilat': tahsilat,
    }
    
    return render(request, 'musteri/tahsilat_iptal.html', context)
    
@login_required
def ajax_son_hareketler(request):
    """AJAX endpoint for recent customer transactions"""
    musteri_id = request.GET.get('musteri_id')

    if not musteri_id:
        return JsonResponse({'success': False, 'message': 'Müşteri ID gerekli.'})

    try:
        hareketler = BorcAlacakHareket.objects.filter(
            musteri_id=musteri_id
        ).order_by('-hareket_tarihi')[:5]

        hareket_data = []
        for h in hareketler:
            hareket_data.append({
                'id': h.id,
                'hareket_tipi': h.hareket_tipi,
                'tutar': float(h.tutar),
                'onceki_bakiye': float(h.onceki_bakiye),
                'yeni_bakiye': float(h.yeni_bakiye),
                'aciklama': h.aciklama,
                'hareket_tarihi': h.hareket_tarihi.strftime('%d.%m.%Y %H:%M'),
            })

        return JsonResponse({'success': True, 'hareketler': hareket_data})

    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})


@login_required
def borc_alacak_dekont_ekle(request):
    """Borç/Alacak dekontu ekleme"""
    if request.method == 'POST':
        try:
            import json
            
            # JSON veya Form data kontrolü
            if request.content_type == 'application/json':
                data = json.loads(request.body)
            else:
                data = request.POST
                
            musteri_id = data.get('musteri_id')
            islem_tipi = data.get('islem_tipi')  # 'borc' veya 'alacak'
            tutar = Decimal(str(data.get('tutar', '0')))
            aciklama = data.get('aciklama', '')
            islem_tarihi_str = data.get('islem_tarihi')
            
            islem_tarihi = None
            if islem_tarihi_str:
                from django.utils import timezone
                from datetime import datetime
                try:
                    # 'YYYY-MM-DD' formatını 'YYYY-MM-DD HH:MM:SS' formatına çevir (güncel saat ile)
                    bugun = timezone.now()
                    secilen_tarih = datetime.strptime(islem_tarihi_str, '%Y-%m-%d')
                    islem_tarihi = bugun.replace(
                        year=secilen_tarih.year, 
                        month=secilen_tarih.month, 
                        day=secilen_tarih.day
                    )
                except ValueError:
                    pass

            # Validation
            if not musteri_id:
                return JsonResponse({'success': False, 'message': 'Müşteri seçimi zorunludur.'})
            
            if not islem_tipi or islem_tipi not in ['borc', 'alacak']:
                return JsonResponse({'success': False, 'message': 'Geçersiz işlem tipi.'})
            
            if tutar <= 0:
                return JsonResponse({'success': False, 'message': 'Tutar 0\'dan büyük olmalıdır.'})
            
            # Müşteri kontrolü
            try:
                musteri = Musteri.objects.get(id=musteri_id, aktif=True)
            except Musteri.DoesNotExist:
                return JsonResponse({'success': False, 'message': 'Geçersiz müşteri.'})
            
            # İşlemi gerçekleştir
            if islem_tipi == 'borc':
                # Borç Dekontu - Müşteriyi borçlandır (Bakiyeyi artır)
                musteri.borc_hareket_ekle(
                    tutar=tutar,
                    aciklama=f'Borç Dekontu: {aciklama}',
                    user=request.user,
                    tarih=islem_tarihi
                )
                mesaj = 'Borç dekontu başarıyla eklendi.'
                
            else:
                # Alacak Dekontu - Müşteriyi alacaklandır (Bakiyeyi azalt)
                musteri.alacak_hareket_ekle(
                    tutar=tutar,
                    aciklama=f'Alacak Dekontu: {aciklama}',
                    user=request.user,
                    tarih=islem_tarihi
                )
                mesaj = 'Alacak dekontu başarıyla eklendi.'
            
            return JsonResponse({
                'success': True, 
                'message': mesaj,
                'yeni_bakiye': str(musteri.acik_hesap_bakiye)
            })
            
        except Exception as e:
            return JsonResponse({'success': False, 'message': f'Hata oluştu: {str(e)}'})
            
    return JsonResponse({'success': False, 'message': 'Geçersiz istek metodu.'})
