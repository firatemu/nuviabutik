from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q, Sum
from django.db import IntegrityError
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.cache import never_cache
from kullanici.decorators import login_required_json, menu_permission_required
from satis.services.checkout import complete_checkout, parse_request_payload
from satis.services.exceptions import CheckoutError
import logging

logger = logging.getLogger('satis.checkout')
from .models import Satis, SatisDetay, Odeme, SiparisNumarasi
from urun.models import Urun, UrunVaryanti
from musteri.models import Musteri
from kasa.models import Kasa, KasaHareket


@never_cache
@ensure_csrf_cookie
@login_required
@menu_permission_required('satis:ekrani')
def satis_ekrani(request):
    """Satış ekranı view'ı"""
    from django.db.models import Sum, Count
    from datetime import datetime, timedelta
    from .models import SatisSiparisi

    # URL'den müşteri ID'sini al veya varsayılan müşteriyi seç
    musteri_id = request.GET.get('musteri')
    secili_musteri = None

    if musteri_id:
        try:
            secili_musteri = Musteri.objects.get(id=musteri_id, aktif=True)
        except Musteri.DoesNotExist:
            messages.warning(request, 'Seçilen müşteri bulunamadı.')

    # URL'den sipariş ID'sini al (sipariş yükleme için)
    siparis_id = request.GET.get('siparis_id')
    yuklenecek_siparis = None

    if siparis_id:
        try:
            yuklenecek_siparis = SatisSiparisi.objects.get(
                id=siparis_id,
                durum__in=['taslak', 'hazir']
            )
            # Siparişteki müşteriyi otomatik seç
            if yuklenecek_siparis.musteri:
                secili_musteri = yuklenecek_siparis.musteri
        except SatisSiparisi.DoesNotExist:
            messages.warning(
                request, 'Seçilen sipariş bulunamadı veya yüklenemez durumda.')

    # Eğer müşteri seçili değilse, veritabanındaki ilk aktif müşteriyi seç
    if not secili_musteri:
        try:
            secili_musteri = Musteri.objects.filter(
                aktif=True).order_by('id').first()
        except:
            pass  # Eğer hiç müşteri yoksa None kalacak

    # Bugünün tarih aralığı
    bugun = datetime.now().date()
    bugun_baslangic = datetime.combine(bugun, datetime.min.time())
    bugun_bitis = datetime.combine(bugun, datetime.max.time())

    # Bugünkü ödemeleri ödeme türüne göre topla
    bugunun_odeme_toplami = Odeme.objects.filter(
        odeme_tarihi__range=[bugun_baslangic, bugun_bitis]
    ).values('odeme_tipi').annotate(
        toplam_tutar=Sum('tutar'),
        toplam_adet=Count('id')
    ).order_by('odeme_tipi')

    # Sonraki sipariş numarasını preview olarak göster (sayacı artırmaz)
    siparis_no_preview = SiparisNumarasi.sonraki_numara_preview()

    # Satış elemanı açılır listesi: yalnızca bu kullanıcı adları (büyük/küçük harf duyarsız)
    from kullanici.models import CustomUser
    satis_elemanlari = CustomUser.objects.filter(is_active=True).filter(
        Q(username__iexact='cagla') | Q(username__iexact='sevgi')
    ).order_by('first_name', 'last_name', 'username')

    eleman_list = list(satis_elemanlari)
    secili_satici_pk = None
    user = getattr(request, 'user', None)
    if user and user.is_authenticated:
        for u in eleman_list:
            if u.pk == user.pk:
                secili_satici_pk = u.pk
                break
    if secili_satici_pk is None and eleman_list:
        secili_satici_pk = eleman_list[0].pk

    context = {
        'title': 'Satış Ekranı',
        'secili_musteri': secili_musteri,
        'siparis_no': siparis_no_preview,
        'bugunun_odeme_toplami': bugunun_odeme_toplami,
        'satis_elemanlari': eleman_list,
        'secili_satici_pk': secili_satici_pk,
        'yuklenecek_siparis': yuklenecek_siparis,
    }
    return render(request, 'satis/satis_ekrani.html', context)


@login_required
def satis_ping(request):
    """Satış ekranı açıkken oturumu canlı tutmak için hafif endpoint."""
    if hasattr(request, 'session') and request.session.session_key:
        request.session.modified = True
    return JsonResponse({'success': True})


@login_required
def satis_listesi(request):
    """Satış listesi view'ı"""
    from django.db.models import Sum, Count, Avg, F
    from datetime import datetime

    satislar = Satis.objects.all().order_by('-siparis_tarihi')

    # Müşteri filtresi (müşteri detaydan "Tümünü Gör")
    musteri_id = request.GET.get('musteri')
    filtre_musteri = None
    if musteri_id:
        try:
            filtre_musteri = Musteri.objects.get(pk=musteri_id)
            satislar = satislar.filter(musteri_id=musteri_id)
        except (Musteri.DoesNotExist, ValueError):
            musteri_id = None

    # Arama
    query = request.GET.get('q')
    if query:
        satislar = satislar.filter(
            Q(siparis_no__icontains=query) |
            Q(satis_no__icontains=query) |
            Q(musteri__ad__icontains=query) |
            Q(musteri__soyad__icontains=query)
        )

    # Tarih filtreleri
    tarih_baslangic = request.GET.get('tarih_baslangic')
    tarih_bitis = request.GET.get('tarih_bitis')

    if tarih_baslangic:
        try:
            baslangic = datetime.strptime(tarih_baslangic, '%Y-%m-%d').date()
            satislar = satislar.filter(siparis_tarihi__date__gte=baslangic)
        except ValueError:
            pass

    if tarih_bitis:
        try:
            bitis = datetime.strptime(tarih_bitis, '%Y-%m-%d').date()
            satislar = satislar.filter(siparis_tarihi__date__lte=bitis)
        except ValueError:
            pass

    # Durum filtresi
    durum = request.GET.get('durum')
    if durum:
        satislar = satislar.filter(durum=durum)

    # İstatistikler hesaplama (Net Tutar, Adet, Sayı)
    istatistikler = satislar.aggregate(
        toplam_net=Sum('genel_toplam'),  # Net tutar
        toplam_adet=Sum('satisdetay__miktar'),
        satış_sayısı=Count('id')
    )

    toplam_tutar_val = istatistikler['toplam_net'] or 0
    
    # Toplam indirim tutarını stored value'dan al
    toplam_indirim_val = satislar.aggregate(
        toplam_indirim=Sum('indirim_tutari')
    )['toplam_indirim'] or 0
    
    # Toplam brüt tutar = Net + İndirim
    toplam_brut_tutar = toplam_tutar_val + toplam_indirim_val

    # Ortalama satışı manuel hesapla
    ortalama_satis = 0
    if istatistikler['satış_sayısı'] and istatistikler['satış_sayısı'] > 0:
        ortalama_satis = toplam_tutar_val / istatistikler['satış_sayısı']

    # Görünüm modu (card/table)
    view_mode = request.GET.get('view', 'card')  # varsayılan card görünümü

    # Sayfalama (görünüm moduna göre sayfa başına öğe sayısı)
    items_per_page = 12 if view_mode == 'card' else 20
    paginator = Paginator(satislar, items_per_page)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Sayfa toplamını hesapla
    sayfa_toplam_tutar = sum([satis.genel_toplam for satis in page_obj])
    sayfa_toplam_indirim = sum([satis.toplam_indirim_tutari for satis in page_obj])
    sayfa_toplam_adet = sum([satis.toplam_urun_adedi for satis in page_obj])
    sayfa_toplam_brut = sum([satis.brut_ara_toplam for satis in page_obj])

    context = {
        'page_obj': page_obj,
        'query': query,
        'view_mode': view_mode,
        'toplam_tutar': toplam_tutar_val,
        'toplam_brut_tutar': toplam_brut_tutar,
        'toplam_indirim': toplam_indirim_val,
        'toplam_adet': istatistikler['toplam_adet'] or 0,
        'sayfa_toplam_tutar': sayfa_toplam_tutar,
        'sayfa_toplam_brut': sayfa_toplam_brut,
        'sayfa_toplam_indirim': sayfa_toplam_indirim,
        'sayfa_toplam_adet': sayfa_toplam_adet,
        'ortalama_satis': ortalama_satis,
        'tarih_baslangic': tarih_baslangic,
        'tarih_bitis': tarih_bitis,
        'durum': durum,
        'filtre_musteri': filtre_musteri,
        'musteri_id': musteri_id,
    }
    return render(request, 'satis/satis_listesi.html', context)


@login_required
def satis_detay(request, pk):
    """Satış detay view'ı"""
    satis = get_object_or_404(Satis, pk=pk)
    satis_detaylari = satis.satisdetay_set.all().select_related('urun', 'varyant', 'varyant__renk', 'varyant__beden')

    # İndirim hesaplamaları
    toplam_urun_indirimi = sum(
        detay.indirim_tutari for detay in satis_detaylari)
    genel_indirim = satis.indirim_tutari - \
        toplam_urun_indirimi if satis.indirim_tutari > toplam_urun_indirimi else 0

    context = {
        'satis': satis,
        'satis_detaylari': satis_detaylari,
        'odemeler': satis.odeme_set.all(),
        'toplam_urun_adedi': satis_detaylari.count(),
        'toplam_urun_indirimi': toplam_urun_indirimi,
        'genel_indirim': genel_indirim,
    }
    return render(request, 'satis/satis_detay.html', context)


@login_required_json
@menu_permission_required('satis:satis_tamamla')
@require_POST
def satis_tamamla(request):
    """Satış tamamlama — iş mantığı checkout service katmanında."""
    import json
    try:
        sepet_data, musteri_id, odeme_detaylari, data = parse_request_payload(request)
        result = complete_checkout(
            request.user,
            sepet_data,
            musteri_id,
            odeme_detaylari,
            data=data,
            session=request.session,
        )
        return JsonResponse(result)
    except CheckoutError as exc:
        logger.warning('checkout_rejected user=%s msg=%s', request.user.username, exc.message)
        payload = {'success': False, 'message': exc.message}
        if exc.errors:
            payload['errors'] = exc.errors
        return JsonResponse(payload, status=400)
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'message': 'Geçersiz JSON verisi.'}, status=400)
    except Exception as exc:
        logger.exception('checkout_error user=%s', request.user.username)
        return JsonResponse({'success': False, 'message': f'Hata: {exc}'}, status=500)


@login_required
def satici_rapor_redirect(request):
    """Legacy satış modülü satıcı raporu → rapor uygulaması."""
    return redirect('rapor:satici_raporu')


@login_required
def satici_rapor(request):
    """Satış elemanı ana rapor sayfası"""
    from django.db.models import Sum, Count
    from datetime import datetime, timedelta
    from kullanici.models import CustomUser

    # Bugünkü tarih
    bugun = datetime.now().date()

    # Satış elemanları
    satis_elemanlari = CustomUser.objects.filter(
        is_active=True,
        role__in=['admin', 'manager', 'cashier', 'satici']
    ).order_by('first_name', 'last_name', 'username')

    # Her satış elemanı için özet bilgiler
    satici_ozet = []
    for elemanl in satis_elemanlari:
        # Bu ayki satışlar
        bugun_baslangic = datetime.combine(bugun, datetime.min.time())
        ay_baslangic = bugun_baslangic.replace(day=1)

        satislar = Satis.objects.filter(
            satici=elemanl,
            siparis_tarihi__gte=ay_baslangic,
            durum='tamamlandi'
        )

        # İadeler (hediye çeki oluşturan işlemler)
        from hediye.models import HediyeCeki
        iadeler = HediyeCeki.objects.filter(
            olusturan=elemanl,
            olusturma_tarihi__gte=ay_baslangic,
            aciklama__icontains='İade'
        )

        toplam_satis = satislar.aggregate(
            tutar=Sum('toplam_tutar'),
            adet=Count('id')
        )

        toplam_iade = iadeler.aggregate(
            tutar=Sum('tutar'),
            adet=Count('id')
        )

        net_satis = (toplam_satis['tutar'] or 0) - (toplam_iade['tutar'] or 0)

        satici_ozet.append({
            'elemanl': elemanl,
            'satis_tutari': toplam_satis['tutar'] or 0,
            'satis_adedi': toplam_satis['adet'] or 0,
            'iade_tutari': toplam_iade['tutar'] or 0,
            'iade_adedi': toplam_iade['adet'] or 0,
            'net_satis': net_satis,
        })

    context = {
        'title': 'Satış Elemanı Raporları',
        'satici_ozet': satici_ozet,
        'bugun': bugun,
    }

    return render(request, 'satis/satici_rapor.html', context)


@login_required
def satici_gunluk(request):
    """Satış elemanı günlük detay raporu"""
    from django.db.models import Sum, Count
    from datetime import datetime, timedelta
    from kullanici.models import CustomUser

    # Tarih parametreleri
    tarih_str = request.GET.get('tarih')
    satici_id = request.GET.get('satici')

    if tarih_str:
        try:
            secili_tarih = datetime.strptime(tarih_str, '%Y-%m-%d').date()
        except ValueError:
            secili_tarih = datetime.now().date()
    else:
        secili_tarih = datetime.now().date()

    # Satış elemanı seçimi
    secili_satici = None
    if satici_id:
        try:
            secili_satici = CustomUser.objects.get(pk=satici_id)
        except CustomUser.DoesNotExist:
            pass

    # Satış elemanları listesi
    satis_elemanlari = CustomUser.objects.filter(
        is_active=True,
        role__in=['admin', 'manager', 'cashier', 'satici']
    ).order_by('first_name', 'last_name', 'username')

    # Günlük veriler
    gun_baslangic = datetime.combine(secili_tarih, datetime.min.time())
    gun_bitis = datetime.combine(secili_tarih, datetime.max.time())

    if secili_satici:
        # Belirli satış elemanının günlük detayları
        satislar = Satis.objects.filter(
            satici=secili_satici,
            siparis_tarihi__range=[gun_baslangic, gun_bitis],
            durum='tamamlandi'
        ).order_by('-siparis_tarihi')

        # İadeler
        from hediye.models import HediyeCeki
        iadeler = HediyeCeki.objects.filter(
            olusturan=secili_satici,
            olusturma_tarihi__range=[gun_baslangic, gun_bitis],
            aciklama__icontains='İade'
        ).order_by('-olusturma_tarihi')

        # Toplamlar
        toplam_satis = satislar.aggregate(
            tutar=Sum('toplam_tutar'),
            adet=Count('id')
        )

        toplam_iade = iadeler.aggregate(
            tutar=Sum('tutar'),
            adet=Count('id')
        )

        net_satis = (toplam_satis['tutar'] or 0) - (toplam_iade['tutar'] or 0)

        gunluk_ozet = {
            'satis_tutari': toplam_satis['tutar'] or 0,
            'satis_adedi': toplam_satis['adet'] or 0,
            'iade_tutari': toplam_iade['tutar'] or 0,
            'iade_adedi': toplam_iade['adet'] or 0,
            'net_satis': net_satis,
        }
    else:
        satislar = []
        iadeler = []
        gunluk_ozet = {}

    context = {
        'title': 'Günlük Satış Raporu',
        'satis_elemanlari': satis_elemanlari,
        'secili_satici': secili_satici,
        'secili_tarih': secili_tarih,
        'satislar': satislar,
        'iadeler': iadeler,
        'gunluk_ozet': gunluk_ozet,
    }

    return render(request, 'satis/satici_gunluk.html', context)


@login_required
def satici_aylik(request):
    """Satış elemanı aylık analiz raporu"""
    from django.db.models import Sum, Count
    from datetime import datetime, timedelta
    from kullanici.models import CustomUser
    import calendar

    # Ay ve yıl parametreleri
    yil = int(request.GET.get('yil', datetime.now().year))
    ay = int(request.GET.get('ay', datetime.now().month))
    satici_id = request.GET.get('satici')

    # Satış elemanı seçimi
    secili_satici = None
    if satici_id:
        try:
            secili_satici = CustomUser.objects.get(pk=satici_id)
        except CustomUser.DoesNotExist:
            pass

    # Satış elemanları listesi
    satis_elemanlari = CustomUser.objects.filter(
        is_active=True,
        role__in=['admin', 'manager', 'cashier', 'satici']
    ).order_by('first_name', 'last_name', 'username')

    # Ay aralığı
    ay_baslangic = datetime(yil, ay, 1)
    if ay == 12:
        ay_bitis = datetime(yil + 1, 1, 1) - timedelta(days=1)
    else:
        ay_bitis = datetime(yil, ay + 1, 1) - timedelta(days=1)

    ay_bitis = datetime.combine(ay_bitis.date(), datetime.max.time())

    if secili_satici:
        # Aylık satışlar
        satislar = Satis.objects.filter(
            satici=secili_satici,
            siparis_tarihi__range=[ay_baslangic, ay_bitis],
            durum='tamamlandi'
        )

        # Aylık iadeler
        from hediye.models import HediyeCeki
        iadeler = HediyeCeki.objects.filter(
            olusturan=secili_satici,
            olusturma_tarihi__range=[ay_baslangic, ay_bitis],
            aciklama__icontains='İade'
        )

        # Günlük dağılım
        gunluk_satislar = {}
        for gun in range(1, calendar.monthrange(yil, ay)[1] + 1):
            gun_baslangic = datetime(yil, ay, gun)
            gun_bitis = datetime.combine(
                gun_baslangic.date(), datetime.max.time())

            gun_satislar = satislar.filter(
                siparis_tarihi__range=[gun_baslangic, gun_bitis]
            ).aggregate(
                tutar=Sum('toplam_tutar'),
                adet=Count('id')
            )

            gun_iadeler = iadeler.filter(
                olusturma_tarihi__range=[gun_baslangic, gun_bitis]
            ).aggregate(
                tutar=Sum('tutar'),
                adet=Count('id')
            )

            gunluk_satislar[gun] = {
                'satis_tutari': gun_satislar['tutar'] or 0,
                'satis_adedi': gun_satislar['adet'] or 0,
                'iade_tutari': gun_iadeler['tutar'] or 0,
                'iade_adedi': gun_iadeler['adet'] or 0,
                'net_satis': (gun_satislar['tutar'] or 0) - (gun_iadeler['tutar'] or 0),
            }

        # Toplam özet
        toplam_satis = satislar.aggregate(
            tutar=Sum('toplam_tutar'),
            adet=Count('id')
        )

        toplam_iade = iadeler.aggregate(
            tutar=Sum('tutar'),
            adet=Count('id')
        )

        aylik_ozet = {
            'satis_tutari': toplam_satis['tutar'] or 0,
            'satis_adedi': toplam_satis['adet'] or 0,
            'iade_tutari': toplam_iade['tutar'] or 0,
            'iade_adedi': toplam_iade['adet'] or 0,
            'net_satis': (toplam_satis['tutar'] or 0) - (toplam_iade['tutar'] or 0),
            'ortalama_gunluk': ((toplam_satis['tutar'] or 0) - (toplam_iade['tutar'] or 0)) / calendar.monthrange(yil, ay)[1],
        }
    else:
        gunluk_satislar = {}
        aylik_ozet = {}

    context = {
        'title': 'Aylık Satış Analizi',
        'satis_elemanlari': satis_elemanlari,
        'secili_satici': secili_satici,
        'yil': yil,
        'ay': ay,
        'ay_adi': calendar.month_name[ay],
        'gunluk_satislar': gunluk_satislar,
        'aylik_ozet': aylik_ozet,
    }

    return render(request, 'satis/satici_aylik.html', context)


@login_required
def satis_iptal(request, pk):
    """Satış iptal view'ı"""
    satis = get_object_or_404(Satis, pk=pk)

    if request.method == 'POST':
        satis.durum = 'iptal'
        satis.save()
        messages.success(request, f'Satış #{satis.satis_no} iptal edildi.')
        return redirect('satis:liste')

    return render(request, 'satis/satis_iptal.html', {'satis': satis})


@login_required
@menu_permission_required('satis:iade_ana_sayfa')
def iade_ana_sayfa(request):
    """Genel iade ana sayfası - satış seçme ekranı"""
    from django.db.models import Q

    # Arama parametresi
    search = request.GET.get('search', '')

    # Tamamlanmış tüm satışlar (tarih sınırı yok; arama tüm geçmişe uygulanır)
    satislar = (
        Satis.objects.filter(durum='tamamlandi')
        .select_related('musteri')
        .order_by('-satis_tarihi')
    )

    # Arama filtresi
    if search:
        satislar = satislar.filter(
            Q(satis_no__icontains=search) |
            Q(siparis_no__icontains=search) |
            Q(musteri__ad__icontains=search) |
            Q(musteri__soyad__icontains=search) |
            Q(musteri__telefon__icontains=search)
        )

    # Sayfalama — varsayılan 100; GET ile 50–300 arası seçilebilir
    try:
        per_page = int(request.GET.get('per_page', '100'))
    except (TypeError, ValueError):
        per_page = 100
    per_page = max(50, min(per_page, 300))

    from django.core.paginator import Paginator
    paginator = Paginator(satislar, per_page)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'search_query': search,
        'per_page': per_page,
    }

    return render(request, 'satis/iade_ana_sayfa.html', context)


@login_required
@menu_permission_required('satis:satis_iade')
def satis_iade(request, pk):
    """Satış iade view'ı - Basit ve stabil versiyon"""
    from hediye.models import HediyeCeki
    from django.utils import timezone
    from datetime import timedelta
    import string
    import random
    from decimal import Decimal

    def _enrich_kalem_for_iade(kalem):
        """Satır brüt/net/indirim — hediye çeki satır neti (toplam_fiyat) üzerinden hesaplanır."""
        miktar = Decimal(kalem.miktar or 0)
        if miktar <= 0:
            miktar = Decimal('1')
        net_satir = Decimal(kalem.toplam_fiyat or 0)
        net_birim = (net_satir / miktar).quantize(Decimal('0.01'))
        brut_birim = Decimal(kalem.birim_fiyat or 0)
        brut_satir = (brut_birim * miktar).quantize(Decimal('0.01'))
        indirim = (brut_satir - net_satir).quantize(Decimal('0.01'))
        if indirim < 0:
            indirim = Decimal('0')
        kalem.net_birim_fiyat = net_birim
        kalem.brut_birim_fiyat = brut_birim
        kalem.satir_indirim = indirim
        kalem.satir_brut_toplam = brut_satir
        kalem.satir_net_toplam = net_satir
        return kalem

    def _iade_satir_net_tutari(kalem, iade_miktar):
        return (kalem.net_birim_fiyat * Decimal(iade_miktar)).quantize(
            Decimal('0.01')
        )

    def _kalemleri_iade_icin_hazirla(qs):
        return [_enrich_kalem_for_iade(k) for k in qs]

    def _satis_iade_ozet(satis_obj):
        kalemler_qs = satis_obj.satisdetay_set.all()
        net_kalemler = sum(
            (Decimal(k.toplam_fiyat or 0) for k in kalemler_qs),
            Decimal('0'),
        )
        brut_kalemler = sum(
            (
                Decimal(k.birim_fiyat or 0) * Decimal(k.miktar or 0)
                for k in kalemler_qs
            ),
            Decimal('0'),
        )
        return {
            'net_odenen': satis_obj.genel_toplam,
            'brut_toplam': satis_obj.brut_ara_toplam,
            'indirim_toplam': satis_obj.indirim_tutari or Decimal('0'),
            'net_kalemler_toplam': net_kalemler,
            'brut_kalemler_toplam': brut_kalemler,
        }

    satis = get_object_or_404(Satis, pk=pk)

    # Sadece tamamlanmış satışlar iade edilebilir
    if satis.durum != 'tamamlandi':
        messages.error(request, 'Sadece tamamlanmış satışlar iade edilebilir!')
        return redirect('satis:liste')

    # Satış kalemlerini al
    kalemler = _kalemleri_iade_icin_hazirla(
        satis.satisdetay_set.all().order_by('id')
    )
    satis_ozet = _satis_iade_ozet(satis)

    if request.method == 'POST':
        try:
            detay_map = {d.pk: d for d in satis.satisdetay_set.all()}

            def _parse_iade_miktari(post, kalem_obj):
                """İade adedi: POST'tan güvenli okuma + işaretli satırda alan gelmezse tam satır."""
                kid = kalem_obj.pk
                key = f'iade_miktar_{kid}'
                secili_key = f'urun_secili_{kid}'
                secili = secili_key in post

                ham = post.get(key)
                # Aynı isimle birden fazla değer gelirse son geçerli varsayılır

                if ham is None:
                    raw = ''
                elif isinstance(ham, list):
                    raw = str(ham[-1]).strip() if ham else ''
                else:
                    raw = str(ham).strip()

                sayi = 0
                if raw:
                    try:
                        sayi = int(raw)
                    except ValueError:
                        try:
                            q = Decimal(raw.replace(',', '.'))
                            if q == q.to_integral_value():
                                sayi = int(q)
                        except Exception:
                            sayi = 0
                if sayi < 0:
                    sayi = 0

                # İşaretlenmiş ama miktar <= 0: tam satır iade (eksik veya 0 girilmiş de olsa)
                if secili and sayi <= 0:
                    sayi = int(kalem_obj.miktar)
                return sayi

            post_kalem_ids = set()
            for key in request.POST:
                if key.startswith('urun_secili_'):
                    try:
                        post_kalem_ids.add(int(key[len('urun_secili_'):]))
                    except ValueError:
                        pass
                elif key.startswith('iade_miktar_'):
                    try:
                        post_kalem_ids.add(int(key[len('iade_miktar_'):]))
                    except ValueError:
                        pass

            ids_to_process = post_kalem_ids or set(detay_map.keys())

            iade_edilecek_urunler = []
            toplam_iade_tutari = Decimal('0')

            for kid in sorted(ids_to_process):
                if kid not in detay_map:
                    continue
                detay = detay_map[kid]
                kalem = _enrich_kalem_for_iade(detay)
                iade_miktar = _parse_iade_miktari(request.POST, detay)

                if iade_miktar > 0:
                    # Miktar kontrolü
                    if iade_miktar > kalem.miktar:
                        messages.error(
                            request, f'{kalem.urun.ad} için iade miktarı satılan adetten fazla olamaz!')
                        kalemler_err = _kalemleri_iade_icin_hazirla(
                            satis.satisdetay_set.all().order_by('id')
                        )
                        return render(request, 'satis/satis_iade.html', {
                            'satis': satis,
                            'kalemler': kalemler_err,
                            'satis_ozet': _satis_iade_ozet(satis),
                        })

                    # İade tutarı: satır neti (toplam_fiyat) üzerinden oransal — etiket/list birim fiyatı değil
                    iade_tutar = _iade_satir_net_tutari(kalem, iade_miktar)
                    toplam_iade_tutari += iade_tutar

                    iade_edilecek_urunler.append({
                        'kalem': kalem,
                        'miktar': iade_miktar,
                        'tutar': iade_tutar
                    })

            # Hiç ürün seçilmediyse hata ver
            if not iade_edilecek_urunler:
                logger.warning(
                    'iade bos POST | satis_id=%s | keys=%s',
                    pk,
                    [k for k in request.POST if 'iade' in k or 'urun_secili' in k],
                )
                messages.error(
                    request, 'İade edilecek en az bir ürün seçmelisiniz!')
                kalemler_err = _kalemleri_iade_icin_hazirla(
                    satis.satisdetay_set.all().order_by('id')
                )
                return render(request, 'satis/satis_iade.html', {
                    'satis': satis,
                    'kalemler': kalemler_err,
                    'satis_ozet': _satis_iade_ozet(satis),
                })

            if toplam_iade_tutari <= 0:
                messages.error(
                    request,
                    'Hesaplanan iade tutarı sıfır; hediye çeki oluşturulamaz.')
                kalemler_err = _kalemleri_iade_icin_hazirla(
                    satis.satisdetay_set.all().order_by('id')
                )
                return render(request, 'satis/satis_iade.html', {
                    'satis': satis,
                    'kalemler': kalemler_err,
                    'satis_ozet': _satis_iade_ozet(satis),
                })

            from urun.models import StokHareket

            def _yeni_hediye_kodu():
                return ''.join(random.choices(
                    string.ascii_uppercase + string.digits, k=12))

            _satis_tarih = satis.satis_tarihi or satis.siparis_tarihi
            _tarih_str = (
                _satis_tarih.strftime('%d.%m.%Y %H:%M')
                if _satis_tarih else '-'
            )
            _satis_etiket = satis.satis_no or satis.siparis_no or str(satis.pk)

            orig_genel_toplam = Decimal(satis.genel_toplam or 0)

            with transaction.atomic():
                hediye_ceki = None
                for _attempt in range(25):
                    try:
                        hediye_ceki = HediyeCeki.objects.create(
                            kod=_yeni_hediye_kodu(),
                            tutar=toplam_iade_tutari,
                            kalan_tutar=toplam_iade_tutari,
                            gecerlilik_tarihi=timezone.now().date() + timedelta(days=365),
                            olusturan=request.user,
                            musteri=satis.musteri,
                            durum='aktif',
                            aktif=True,
                            aciklama=(
                                f'İade - Satış #{_satis_etiket} ({_tarih_str})'
                            ),
                        )
                        logger.info('HediyeCeki oluşturuldu | kod=%s | tutar=%s | satis_id=%s | musteri=%s',
                                    hediye_ceki.kod, toplam_iade_tutari, pk,
                                    getattr(satis.musteri, 'id', None))
                        break
                    except IntegrityError:
                        if _attempt == 24:
                            raise
                        continue
                if hediye_ceki is None:
                    raise RuntimeError('Hediye çeki oluşturulamadı.')

                for item in iade_edilecek_urunler:
                    kalem = item['kalem']
                    urun = kalem.urun
                    varyant = kalem.varyant
                    if varyant is None:
                        varyant = urun.varyantlar.filter(aktif=True).first()

                    if varyant is None:
                        logger.warning(
                            'İade varyant bulunamadı, stok hareketi oluşturulamaz | '
                            'kalem_id=%s | urun_id=%s | satis_id=%s',
                            kalem.pk, urun.pk, pk)
                        raise RuntimeError(
                            f'İade tamamlanamadı: "{urun.ad}" ürünü için geçerli bir varyant bulunamadı. '
                            f'Stok hareketi oluşturulamıyor. Lütfen ürün kartını kontrol edin.'
                        )
                    StokHareket.stok_hareketi_olustur(
                        varyant=varyant,
                        hareket_tipi='giris',
                        miktar=item['miktar'],
                        kullanici=request.user,
                        aciklama=(
                            f'İade: {_satis_etiket} -> '
                            f'Hediye Çeki: {hediye_ceki.kod}'
                        ),
                        referans_id=str(hediye_ceki.id),
                    )
                    logger.info(
                        'StokHareket (giris) oluşturuldu | varyant_id=%s | miktar=%s | '
                        'onceki_stok=%s | yeni_stok=%s | hediye_ceki_id=%s',
                        varyant.pk, item['miktar'], varyant.stok_miktari - item['miktar'],
                        varyant.stok_miktari, hediye_ceki.id)

                    if item['miktar'] == kalem.miktar:
                        SatisDetay.objects.filter(pk=kalem.pk).delete()
                    else:
                        eski_m = kalem.miktar
                        yeni_m = eski_m - item['miktar']
                        yeni_toplam = (
                            (kalem.toplam_fiyat or Decimal('0')) - item['tutar']
                        )
                        oran = (
                            (Decimal(yeni_m) / Decimal(eski_m))
                            if eski_m else Decimal('0')
                        )
                        yeni_indirim = (
                            (kalem.indirim_tutari or Decimal('0')) * oran
                        ).quantize(Decimal('0.01'))
                        SatisDetay.objects.filter(pk=kalem.pk).update(
                            miktar=yeni_m,
                            toplam_fiyat=yeni_toplam.quantize(Decimal('0.01')),
                            indirim_tutari=yeni_indirim,
                        )

                satis_kilit = Satis.objects.select_for_update().get(pk=satis.pk)
                kalan_detay_var = satis_kilit.satisdetay_set.exists()
                if not kalan_detay_var:
                    satis_kilit.ara_toplam = Decimal('0')
                    satis_kilit.indirim_tutari = Decimal('0')
                    satis_kilit.durum = 'iade'
                else:
                    kalan_net = satis_kilit.satisdetay_set.aggregate(
                        s=Sum('toplam_fiyat')
                    )['s'] or Decimal('0')
                    yeni_genel = (
                        orig_genel_toplam - toplam_iade_tutari
                    ).quantize(Decimal('0.01'))
                    if yeni_genel < 0:
                        yeni_genel = Decimal('0')
                    satis_kilit.ara_toplam = kalan_net
                    k_orani = Decimal(
                        str(
                            satis_kilit.kdv_orani
                            if satis_kilit.kdv_orani is not None
                            else 0
                        )
                    )
                    kdv = (kalan_net * (k_orani / Decimal('100'))).quantize(
                        Decimal('0.01')
                    )
                    toplam_tutar = (kalan_net + kdv).quantize(Decimal('0.01'))
                    indirim = (toplam_tutar - yeni_genel).quantize(
                        Decimal('0.01')
                    )
                    if indirim < 0:
                        indirim = Decimal('0')
                    satis_kilit.indirim_tutari = indirim
                satis_kilit.save()

                # Açık hesap: iade oranında müşteri borcunu düş (nakit/kart kasa ters kaydı yapılmaz)
                if satis.musteri and orig_genel_toplam > 0:
                    acik_hesap_toplam = (
                        Odeme.objects.filter(
                            satis_id=satis.pk,
                            odeme_tipi='acik_hesap',
                        ).aggregate(s=Sum('tutar'))['s'] or Decimal('0')
                    )
                    if acik_hesap_toplam > 0:
                        iade_oran = toplam_iade_tutari / orig_genel_toplam
                        borc_dusumu = (acik_hesap_toplam * iade_oran).quantize(
                            Decimal('0.01')
                        )
                        if borc_dusumu > 0:
                            satis.musteri.alacak_hareket_ekle(
                                tutar=borc_dusumu,
                                aciklama=(
                                    f'İade - Satış #{_satis_etiket} - '
                                    f'Hediye Çeki: {hediye_ceki.kod}'
                                ),
                                user=request.user,
                            )
                            logger.info(
                                'İade açık hesap borç düşümü | musteri_id=%s | tutar=%s | satis_id=%s',
                                satis.musteri.pk, borc_dusumu, pk,
                            )

            messages.success(
                request,
                f'İade başarılı! Hediye çeki: {hediye_ceki.kod} '
                f'({toplam_iade_tutari} ₺)',
            )
            return redirect('satis:iade_fisi', hediye_ceki_id=hediye_ceki.pk)

        except Exception as e:
            logger.exception(
                'İade işlemi başarısız | satis_id=%s | toplam_iade_tutari=%s | '
                'iade_edilecek_urunler=%s | error=%s',
                pk, toplam_iade_tutari,
                [{'kalem': item['kalem'].pk, 'miktar': item['miktar'], 'tutar': str(item['tutar'])}
                 for item in iade_edilecek_urunler] if 'iade_edilecek_urunler' in dir() else '[]',
                str(e),
            )
            messages.error(request, f'İade işlemi başarısız: {str(e)}')
            kalemler_err = _kalemleri_iade_icin_hazirla(
                satis.satisdetay_set.all().order_by('id')
            )
            return render(request, 'satis/satis_iade.html', {
                'satis': satis,
                'kalemler': kalemler_err,
                'satis_ozet': _satis_iade_ozet(satis),
            })

    # GET request - formu göster
    return render(request, 'satis/satis_iade.html', {
        'satis': satis,
        'kalemler': kalemler,
        'satis_ozet': satis_ozet,
    })


@login_required
def iade_fisi(request, hediye_ceki_id):
    """İade fişi görüntüleme"""
    from hediye.models import HediyeCeki

    hediye_ceki = get_object_or_404(HediyeCeki, pk=hediye_ceki_id)

    # Sadece oluşturan kullanıcı veya admin görebilir
    if (
        hediye_ceki.olusturan_id != getattr(request.user, 'pk', None)
        and not request.user.is_staff
    ):
        messages.error(request, 'Bu fişi görüntüleme yetkiniz yok!')
        return redirect('satis:liste')

    context = {
        'hediye_ceki': hediye_ceki,
        'print_mode': request.GET.get('print', False)
    }

    return render(request, 'satis/iade_fisi.html', context)


@login_required
def iade_fisi_pdf(request, hediye_ceki_id):
    """İade fişi PDF çıktısı"""
    from hediye.models import HediyeCeki
    from django.http import HttpResponse
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import A4, A5
    from reportlab.lib.colors import black, blue, green
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
    from reportlab.lib.units import inch, mm
    from reportlab.lib import colors
    import io
    import os
    from django.conf import settings

    hediye_ceki = get_object_or_404(HediyeCeki, pk=hediye_ceki_id)

    # Sadece oluşturan kullanıcı veya admin indirebilir
    if (
        hediye_ceki.olusturan_id != getattr(request.user, 'pk', None)
        and not request.user.is_staff
    ):
        messages.error(request, 'Bu fişi indirme yetkiniz yok!')
        return redirect('satis:liste')

    # Font sistemi (daha önce kullandığımız sistem)
    def detect_font():
        """Windows TTF fontlarını algıla"""
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        import os

        fonts_to_try = [
            (r"C:\Windows\Fonts\arialuni.ttf", "Arial Unicode MS"),
            (r"C:\Windows\Fonts\calibri.ttf", "Calibri"),
            (r"C:\Windows\Fonts\times.ttf", "Times New Roman")
        ]

        for font_path, font_name in fonts_to_try:
            if os.path.exists(font_path):
                try:
                    pdfmetrics.registerFont(TTFont(font_name, font_path))
                    return font_name
                except:
                    continue

        # Fallback font
        return "Helvetica"

    font_name = detect_font()

    # PDF response
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="iade_fisi_{hediye_ceki.kod}.pdf"'

    # PDF oluştur
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A5, rightMargin=30,
                            leftMargin=30, topMargin=30, bottomMargin=30)

    # Stiller
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=16,
        spaceAfter=20,
        alignment=1,  # Center
        textColor=colors.darkblue,
        fontName=font_name
    )

    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=12,
        spaceAfter=10,
        spaceBefore=15,
        textColor=colors.darkgreen,
        fontName=font_name
    )

    normal_style = ParagraphStyle(
        'CustomNormal',
        parent=styles['Normal'],
        fontSize=10,
        fontName=font_name,
        leftIndent=10
    )

    # İçerik
    story = []

    # Başlık
    story.append(Paragraph("İADE FİŞİ", title_style))
    story.append(Spacer(1, 20))

    # Hediye çeki bilgileri
    story.append(Paragraph("HEDİYE ÇEKİ BİLGİLERİ", heading_style))

    hediye_data = [
        ['Hediye Çeki Kodu:', hediye_ceki.kod],
        ['Tutar:', f"{hediye_ceki.tutar:.2f} ₺"],
        ['Geçerlilik Tarihi:',
            hediye_ceki.gecerlilik_tarihi.strftime('%d.%m.%Y')],
        ['Oluşturma Tarihi:', hediye_ceki.olusturma_tarihi.strftime(
            '%d.%m.%Y %H:%M')],
    ]

    if hediye_ceki.musteri:
        hediye_data.append(
            ['Müşteri:', f"{hediye_ceki.musteri.ad} {hediye_ceki.musteri.soyad}"])

    hediye_table = Table(hediye_data, colWidths=[1.5*inch, 2*inch])
    hediye_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, -1), font_name),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))

    story.append(hediye_table)
    story.append(Spacer(1, 20))

    # İade açıklaması
    if hediye_ceki.aciklama:
        story.append(Paragraph("İADE SEBEBİ", heading_style))
        story.append(Paragraph(hediye_ceki.aciklama, normal_style))
        story.append(Spacer(1, 20))

    # Kullanım bilgileri
    story.append(Paragraph("KULLANIM BİLGİLERİ", heading_style))
    story.append(
        Paragraph("• Bu hediye çeki tek seferlik kullanılabilir.", normal_style))
    story.append(Paragraph("• Mağazamızda geçerlidir.", normal_style))
    story.append(Paragraph("• Para üstü verilmez.", normal_style))
    story.append(Paragraph(
        f"• Geçerlilik tarihi: {hediye_ceki.gecerlilik_tarihi.strftime('%d.%m.%Y')}", normal_style))

    # PDF'i oluştur
    doc.build(story)
    pdf = buffer.getvalue()
    buffer.close()
    response.write(pdf)

    return response


@login_required
def satis_yazdir(request, pk):
    """Satış yazdırma view'ı"""
    satis = get_object_or_404(Satis, pk=pk)

    # Sadece tamamlanmış satışları yazdırabilir
    if satis.durum != 'tamamlandi':
        messages.error(request, 'Sadece tamamlanmış satışlar yazdırılabilir.')
        return redirect('satis:detay', pk=pk)

    # Satış detayları
    satis_detaylari = satis.satisdetay_set.all().select_related('urun')

    # İndirim hesaplamaları
    toplam_urun_indirimi = sum(
        detay.indirim_tutari for detay in satis_detaylari)
    genel_indirim = satis.indirim_tutari - \
        toplam_urun_indirimi if satis.indirim_tutari > toplam_urun_indirimi else 0

    context = {
        'satis': satis,
        'satis_detaylari': satis_detaylari,
        'odemeler': satis.odeme_set.all(),
        'toplam_urun_indirimi': toplam_urun_indirimi,
        'genel_indirim': genel_indirim,
    }
    return render(request, 'satis/satis_yazdir.html', context)


@login_required
def satis_degisim_fisi(request, pk):
    """Değişim fişi — satış fişi ile aynı termal format, fiyat bilgisi olmadan."""
    satis = get_object_or_404(Satis, pk=pk)

    if satis.durum != 'tamamlandi':
        messages.error(request, 'Sadece tamamlanmış satışlar için değişim fişi oluşturulabilir.')
        return redirect('satis:detay', pk=pk)

    satis_detaylari = satis.satisdetay_set.select_related(
        'urun',
        'urun__kategori',
        'varyant',
        'varyant__renk',
        'varyant__beden',
    ).all()

    toplam_adet = sum(d.miktar for d in satis_detaylari)

    return render(request, 'satis/satis_degisim_fisi.html', {
        'satis': satis,
        'satis_detaylari': satis_detaylari,
        'toplam_adet': toplam_adet,
    })


@login_required_json
def barkod_sorgula(request):
    """Barkod sorgulama AJAX view'ı"""
    from urun.models import UrunVaryanti

    barkod = request.GET.get('barkod')

    if barkod:
        try:
            # Barkod UrunVaryanti modelinde bulunuyor
            varyant = UrunVaryanti.objects.select_related(
                'urun', 'urun__kategori', 'renk', 'beden'
            ).get(barkod=barkod, aktif=True)
            urun = varyant.urun

            if varyant.stok_miktari > 0 and urun.aktif:
                data = {
                    'success': True,
                    'urun': {
                        'id': urun.id,
                        'varyant_id': varyant.id,
                        'ad': urun.ad,
                        'varyasyon': varyant.varyasyon_adi,
                        'beden': varyant.beden.ad if varyant.beden else 'Tek Beden',
                        'renk': varyant.renk.ad if varyant.renk else 'Standart',
                        'barkod': varyant.barkod,
                        # JavaScript'te 'fiyat' ve 'pesin_fiyat' olarak kullanılıyor - Peşin fiyat dönüyoruz
                        'fiyat': float(urun.pesin_fiyat),
                        'pesin_fiyat': float(urun.pesin_fiyat),
                        # Geriye dönük uyumluluk için
                        'satis_fiyati': float(urun.pesin_fiyat),
                        'stok_miktari': varyant.stok_miktari,
                        'kategori': str(urun.kategori),
                        'kod': urun.urun_kodu
                    }
                }
            else:
                data = {'success': False, 'message': 'Ürün stokta yok!'}
        except UrunVaryanti.DoesNotExist:
            data = {'success': False, 'message': 'Barkod bulunamadı!'}
    else:
        data = {'success': False, 'message': 'Barkod girilmedi!'}

    return JsonResponse(data)


# AJAX Views
@login_required_json
def urun_ara(request):
    """Ürün arama AJAX view'ı"""
    from urun.models import UrunVaryanti
    from django.db.models import Value, F
    from django.db.models.functions import Lower, Replace

    query = request.GET.get('q', '')
    kriter = (request.GET.get('kriter') or 'hepsi').strip().lower()

    if len(query) >= 1:
        def norm_expr(field_name: str):
            """
            Türkçe karakterler ve büyük/küçük harf için normalize edilmiş arama alanı üretir.
            Not: Postgres'te lower('İ') -> 'i̇' birleşik karakter üretebildiği için
            büyük harf dönüşümünü Lower öncesi Replace ile ele alıyoruz.
            """
            expr = F(field_name)
            # Büyük harf Türkçe karakterleri düzelt
            expr = Replace(expr, Value('İ'), Value('i'))
            expr = Replace(expr, Value('I'), Value('i'))
            expr = Replace(expr, Value('Ş'), Value('s'))
            expr = Replace(expr, Value('Ç'), Value('c'))
            expr = Replace(expr, Value('Ğ'), Value('g'))
            expr = Replace(expr, Value('Ü'), Value('u'))
            expr = Replace(expr, Value('Ö'), Value('o'))
            # Lower
            expr = Lower(expr)
            # Küçük harf Türkçe karakterleri ASCII'ye indir
            expr = Replace(expr, Value('ı'), Value('i'))
            expr = Replace(expr, Value('ş'), Value('s'))
            expr = Replace(expr, Value('ç'), Value('c'))
            expr = Replace(expr, Value('ğ'), Value('g'))
            expr = Replace(expr, Value('ü'), Value('u'))
            expr = Replace(expr, Value('ö'), Value('o'))
            return expr

        def norm_text(s: str) -> str:
            s = (s or '').strip()
            s = s.replace('İ', 'i').replace('I', 'i')
            s = s.replace('Ş', 's').replace('Ç', 'c').replace('Ğ', 'g').replace('Ü', 'u').replace('Ö', 'o')
            s = s.lower()
            s = s.replace('ı', 'i').replace('ş', 's').replace('ç', 'c').replace('ğ', 'g').replace('ü', 'u').replace('ö', 'o')
            return s

        qn = norm_text(query)

        base = UrunVaryanti.objects.filter(
            aktif=True,
            urun__aktif=True,
            stok_miktari__gt=0
        ).select_related('urun', 'urun__kategori', 'urun__marka', 'renk', 'beden')

        # Normalize edilmiş alanlar üzerinden filtrele (TR uyumlu, case-insensitive)
        base = base.annotate(
            ad_n=norm_expr('urun__ad'),
            barkod_n=norm_expr('barkod'),
            kod_n=norm_expr('urun__urun_kodu'),
        )

        if kriter == 'ad':
            filt = Q(ad_n__contains=qn)
        elif kriter == 'barkod':
            filt = Q(barkod_n__contains=qn)
        elif kriter in ('kod', 'urun_kodu', 'urun-kodu'):
            filt = Q(kod_n__contains=qn)
        else:
            filt = Q(ad_n__contains=qn) | Q(barkod_n__contains=qn) | Q(kod_n__contains=qn)

        # Tüm uygun sonuçlar: pratik bir üst limit koyuyoruz (ekran için)
        # Not: varyasyon_adi bir @property, order_by kullanılamaz
        varyantlar = base.filter(filt).order_by('urun__ad', 'renk__ad', 'beden__ad', 'barkod')[:200]

        data = []
        for varyant in varyantlar:
            data.append({
                'id': varyant.urun.id,
                'varyant_id': varyant.id,
                'ad': varyant.urun.ad,
                'varyasyon': varyant.varyasyon_adi,
                'beden': varyant.beden.ad if varyant.beden else 'Tek Beden',
                'renk': varyant.renk.ad if varyant.renk else 'Standart',
                'barkod': varyant.barkod,
                'urun_kodu': varyant.urun.urun_kodu,
                # JavaScript'te 'fiyat' ve 'pesin_fiyat' olarak kullanılıyor - Peşin fiyat dönüyoruz
                'fiyat': float(varyant.urun.pesin_fiyat),
                'pesin_fiyat': float(varyant.urun.pesin_fiyat),
                # Geriye dönük uyumluluk için
                'satis_fiyati': float(varyant.urun.pesin_fiyat),
                'stok_miktari': varyant.stok_miktari,
                'kategori': str(varyant.urun.kategori) if varyant.urun.kategori else 'Kategori Yok',
                'marka': str(varyant.urun.marka) if varyant.urun.marka else 'Marka Yok',
                'kod': varyant.urun.urun_kodu
            })

        return JsonResponse({'success': True, 'urunler': data})

    return JsonResponse({'success': False, 'urunler': []})


@login_required
def sepete_ekle(request):
    """Sepete ekleme AJAX view'ı"""
    from urun.models import UrunVaryanti

    if request.method == 'POST':
        varyant_id = request.POST.get('varyant_id')
        urun_id = request.POST.get('urun_id')  # Eski sistemle uyumluluk için
        miktar = int(request.POST.get('miktar', 1))

        try:
            # Önce varyant_id ile dene, yoksa urun_id ile ilk varyantı al
            if varyant_id:
                varyant = UrunVaryanti.objects.get(
                    pk=varyant_id, aktif=True, urun__aktif=True)
            elif urun_id:
                varyant = UrunVaryanti.objects.filter(
                    urun_id=urun_id, aktif=True, urun__aktif=True).first()
                if not varyant:
                    return JsonResponse({'success': False, 'message': 'Ürün varyantı bulunamadı!'})
            else:
                return JsonResponse({'success': False, 'message': 'Ürün ID eksik!'})

            if varyant.stok_miktari < miktar:
                return JsonResponse({'success': False, 'message': 'Yeterli stok yok!'})

            # Session'dan sepeti al
            sepet = request.session.get('sepet', {})

            sepet_key = f"v_{varyant.id}"  # Varyant bazlı key

            if sepet_key in sepet:
                sepet[sepet_key]['miktar'] += miktar
            else:
                sepet[sepet_key] = {
                    'varyant_id': varyant.id,
                    'urun_id': varyant.urun.id,
                    'ad': varyant.urun.ad,
                    'varyasyon': varyant.varyasyon_adi,
                    'barkod': varyant.barkod,
                    'fiyat': str(varyant.urun.pesin_fiyat),
                    'miktar': miktar,
                }

            # Toplam hesapla
            sepet[sepet_key]['toplam'] = str(
                float(sepet[sepet_key]['fiyat']) * sepet[sepet_key]['miktar']
            )

            # Session'a kaydet
            request.session['sepet'] = sepet

            return JsonResponse({'success': True, 'message': 'Ürün sepete eklendi'})

        except UrunVaryanti.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Ürün varyantı bulunamadı!'})

    return JsonResponse({'success': False, 'message': 'Geçersiz istek!'})


@login_required
def sepetten_cikar(request):
    """Sepetten çıkarma AJAX view'ı"""
    if request.method == 'POST':
        urun_id = request.POST.get('urun_id')

        sepet = request.session.get('sepet', {})

        if str(urun_id) in sepet:
            del sepet[str(urun_id)]
            request.session['sepet'] = sepet
            return JsonResponse({'success': True, 'message': 'Ürün sepetten çıkarıldı'})

        return JsonResponse({'success': False, 'message': 'Ürün sepette bulunamadı!'})

    return JsonResponse({'success': False, 'message': 'Geçersiz istek!'})


@login_required
def sepet_temizle(request):
    """Sepet temizleme AJAX view'ı"""
    if request.method == 'POST':
        request.session['sepet'] = {}
        return JsonResponse({'success': True, 'message': 'Sepet temizlendi'})

    return JsonResponse({'success': False, 'message': 'Geçersiz istek!'})


@login_required_json
def taksitli_fiyatlar(request):
    """Taksitli fiyatları getiren AJAX view'ı"""
    import json
    
    if request.method == 'POST':
        try:
            # Gelen ürün ID'lerini al
            urun_ids_json = request.POST.get('urun_ids')
            if not urun_ids_json:
                return JsonResponse({'success': False, 'message': 'Ürün ID listesi boş!'})
            
            urun_ids = json.loads(urun_ids_json)
            
            # Ürünlerin taksitli fiyatlarını al
            fiyatlar = {}
            for urun_id in urun_ids:
                try:
                    urun = Urun.objects.get(id=urun_id)
                    fiyatlar[urun_id] = float(urun.taksitli_fiyat)
                except Urun.DoesNotExist:
                    # Ürün bulunamadıysa atla
                    continue
            
            return JsonResponse({
                'success': True,
                'fiyatlar': fiyatlar
            })
            
        except json.JSONDecodeError:
            return JsonResponse({'success': False, 'message': 'Geçersiz JSON formatı!'})
        except Exception as e:
            return JsonResponse({'success': False, 'message': f'Hata: {str(e)}'})
    
    return JsonResponse({'success': False, 'message': 'Geçersiz istek!'})


@login_required_json
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
                'telefon': musteri.telefon or 'Telefon yok',
                'tip': musteri.tip,
                'firma_adi': musteri.firma_adi or '',
                'acik_hesap_bakiye': float(musteri.acik_hesap_bakiye or 0),
                'acik_hesap_limit': float(musteri.acik_hesap_limit or 0),
                'tam_ad': musteri.firma_adi if musteri.tip == 'kurumsal' and musteri.firma_adi else f"{musteri.ad} {musteri.soyad}"
            })

        return JsonResponse({'success': True, 'musteriler': data})

    return JsonResponse({'success': False, 'musteriler': []})


@login_required_json
def hediye_ceki_sorgula(request):
    """Hediye çeki sorgulama AJAX view'ı"""
    from hediye.models import HediyeCeki
    from django.utils import timezone

    kod = request.GET.get('kod', '').strip()

    if not kod:
        return JsonResponse({'success': False, 'message': 'Hediye çeki kodu gerekli!'})

    try:
        hediye_ceki = HediyeCeki.objects.get(kod=kod, aktif=True)

        # Hediye çeki kullanılabilir mi kontrol et
        if not hediye_ceki.kullanilabilir_mi:
            reasons = []
            if hediye_ceki.durum != 'aktif':
                reasons.append(f"Durum: {hediye_ceki.get_durum_display()}")
            if hediye_ceki.kalan_tutar <= 0:
                reasons.append("Bakiye kalmamış")
            if hediye_ceki.gecerlilik_tarihi < timezone.now().date():
                reasons.append("Süresi dolmuş")

            return JsonResponse({
                'success': False,
                'message': f"Hediye çeki kullanılamaz: {', '.join(reasons)}"
            })

        # Hediye çeki bilgilerini döndür
        data = {
            'kod': hediye_ceki.kod,
            'tutar': float(hediye_ceki.tutar),
            'kalan_tutar': float(hediye_ceki.kalan_tutar),
            'gecerlilik_tarihi': hediye_ceki.gecerlilik_tarihi.strftime('%d.%m.%Y'),
            'durum': hediye_ceki.get_durum_display()
        }

        return JsonResponse({'success': True, 'hediye_ceki': data})

    except HediyeCeki.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Hediye çeki bulunamadı!'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Hata: {str(e)}'})


@login_required
def yeni_siparis_no(request):
    """Yeni sipariş numarası preview getir"""
    siparis_no_preview = SiparisNumarasi.sonraki_numara_preview()

    return JsonResponse({
        'success': True,
        'siparis_no': siparis_no_preview
    })


@login_required
def tahsilat_listesi(request):
    """Tahsilat listesi view'ı"""
    from django.db.models import Sum, Count, Q
    from datetime import datetime, date, timedelta

    # Tüm ödemeleri getir
    odemeler = Odeme.objects.select_related(
        'satis', 'satis__musteri', 'satis__satici').order_by('-odeme_tarihi')

    # Arama
    query = request.GET.get('q')
    if query:
        odemeler = odemeler.filter(
            Q(satis__siparis_no__icontains=query) |
            Q(satis__satis_no__icontains=query) |
            Q(satis__musteri__ad__icontains=query) |
            Q(satis__musteri__soyad__icontains=query) |
            Q(hediye_ceki_kodu__icontains=query)
        )

    # Tarih filtreleri
    tarih_baslangic = request.GET.get('tarih_baslangic')
    tarih_bitis = request.GET.get('tarih_bitis')

    if tarih_baslangic:
        try:
            baslangic = datetime.strptime(tarih_baslangic, '%Y-%m-%d').date()
            odemeler = odemeler.filter(odeme_tarihi__date__gte=baslangic)
        except ValueError:
            pass

    if tarih_bitis:
        try:
            bitis = datetime.strptime(tarih_bitis, '%Y-%m-%d').date()
            odemeler = odemeler.filter(odeme_tarihi__date__lte=bitis)
        except ValueError:
            pass

    # Ödeme tipi filtresi
    odeme_tipi = request.GET.get('odeme_tipi')
    if odeme_tipi:
        odemeler = odemeler.filter(odeme_tipi=odeme_tipi)

    # Görünüm modu (card/table)
    view_mode = request.GET.get('view', 'table')  # varsayılan table görünümü

    # İstatistikler hesaplama
    istatistikler = odemeler.aggregate(
        toplam_tutar=Sum('tutar'),
        odeme_sayisi=Count('id')
    )

    # Bugünkü tahsilatlar
    bugun = date.today()
    bugun_odemeler = odemeler.filter(odeme_tarihi__date=bugun)
    bugun_toplam = bugun_odemeler.aggregate(toplam=Sum('tutar'))['toplam'] or 0
    bugun_sayisi = bugun_odemeler.count()

    # Sayfalama
    from django.core.paginator import Paginator
    items_per_page = 12 if view_mode == 'card' else 25
    paginator = Paginator(odemeler, items_per_page)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Sayfa toplamını hesapla
    sayfa_toplam_tutar = sum([odeme.tutar for odeme in page_obj])

    context = {
        'page_obj': page_obj,
        'query': query,
        'view_mode': view_mode,
        'toplam_tutar': istatistikler['toplam_tutar'] or 0,
        'odeme_sayisi': istatistikler['odeme_sayisi'] or 0,
        'sayfa_toplam_tutar': sayfa_toplam_tutar,
        'bugun_toplam': bugun_toplam,
        'bugun_sayisi': bugun_sayisi,
        'tarih_baslangic': tarih_baslangic,
        'tarih_bitis': tarih_bitis,
        'odeme_tipi': odeme_tipi,
        'odeme_tipleri': Odeme.ODEME_TIPLERI,
        'title': 'Tahsilat Listesi',
    }

    return render(request, 'satis/tahsilat_listesi.html', context)


@login_required
def tahsilat_rapor(request):
    """Tahsilat raporları view'ı"""
    from django.db.models import Sum, Count, Q
    from datetime import date, timedelta

    bugün = date.today()
    bu_ay_başı = bugün.replace(day=1)

    # Temel istatistikler
    bugün_tahsilat = Odeme.objects.filter(
        odeme_tarihi__date=bugün
    ).aggregate(toplam=Sum('tutar'))['toplam'] or 0

    bu_ay_tahsilat = Odeme.objects.filter(
        odeme_tarihi__date__gte=bu_ay_başı
    ).aggregate(toplam=Sum('tutar'))['toplam'] or 0

    # Ödeme tipi bazında istatistikler
    odeme_tipi_istatistikleri = []
    for kod, ad in Odeme.ODEME_TIPLERI:
        bu_ay_toplam = Odeme.objects.filter(
            odeme_tipi=kod,
            odeme_tarihi__date__gte=bu_ay_başı
        ).aggregate(toplam=Sum('tutar'))['toplam'] or 0

        odeme_adedi = Odeme.objects.filter(
            odeme_tipi=kod,
            odeme_tarihi__date__gte=bu_ay_başı
        ).count()

        if bu_ay_toplam > 0 or odeme_adedi > 0:
            odeme_tipi_istatistikleri.append({
                'kod': kod,
                'ad': ad,
                'bu_ay_toplam': bu_ay_toplam,
                'odeme_adedi': odeme_adedi,
                'renk': {
                    'nakit': '#28a745',
                    'kart': '#007bff',
                    'hediye_ceki': '#ffc107',
                    'acik_hesap': '#dc3545'
                }.get(kod, '#6c757d'),
                'ikon': {
                    'nakit': 'fas fa-money-bill-wave',
                    'kart': 'fas fa-credit-card',
                    'hediye_ceki': 'fas fa-gift',
                    'acik_hesap': 'fas fa-handshake'
                }.get(kod, 'fas fa-coins')
            })

    # Günlük trend (son 30 gün)
    otuz_gün_önce = bugün - timedelta(days=30)
    günlük_trend = Odeme.objects.filter(
        odeme_tarihi__date__gte=otuz_gün_önce
    ).extra(
        select={'tarih': 'DATE(odeme_tarihi)'}
    ).values('tarih').annotate(
        toplam=Sum('tutar'),
        adet=Count('id')
    ).order_by('tarih')

    # En büyük tahsilatlar (bu ay)
    en_buyuk_tahsilatlar = Odeme.objects.filter(
        odeme_tarihi__date__gte=bu_ay_başı
    ).select_related('satis', 'satis__musteri').order_by('-tutar')[:10]

    # Satıcı bazında tahsilat
    satici_tahsilat = Odeme.objects.filter(
        odeme_tarihi__date__gte=bu_ay_başı
    ).values(
        'satis__satici__first_name',
        'satis__satici__last_name',
        'satis__satici__username'
    ).annotate(
        toplam_tahsilat=Sum('tutar'),
        tahsilat_adedi=Count('id')
    ).order_by('-toplam_tahsilat')[:10]

    context = {
        'title': 'Tahsilat Raporları',
        'bugün_tahsilat': bugün_tahsilat,
        'bu_ay_tahsilat': bu_ay_tahsilat,
        'odeme_tipi_istatistikleri': odeme_tipi_istatistikleri,
        'günlük_trend': günlük_trend,
        'en_buyuk_tahsilatlar': en_buyuk_tahsilatlar,
        'satici_tahsilat': satici_tahsilat,
        'bugün': bugün,
        'bu_ay_başı': bu_ay_başı,
    }

    return render(request, 'satis/tahsilat_rapor.html', context)


# Satış Siparişi View'ları

@login_required
def siparis_olustur(request):
    """Yeni satış siparişi oluşturma ekranı"""
    from .models import SatisSiparisi
    from musteri.models import Musteri
    from kullanici.models import CustomUser
    from datetime import datetime

    # Sonraki sipariş numarasını preview olarak göster
    siparis_no_preview = SatisSiparisi.sonraki_siparis_no()

    # Müşteri listesi
    musteriler = Musteri.objects.filter(aktif=True).order_by('ad', 'soyad')

    # Satış elemanları
    satis_elemanlari = CustomUser.objects.filter(
        is_active=True,
        role__in=['satici', 'cashier']  # Hem satış elemanı hem kasiyer rollerini dahil et
    ).exclude(
        username__in=['admin', 'nuviaadmin']
    ).order_by('first_name', 'last_name', 'username')

    context = {
        'title': 'Yeni Satış Siparişi',
        'siparis_no': siparis_no_preview,
        'musteriler': musteriler,
        'satis_elemanlari': satis_elemanlari,
    }
    return render(request, 'satis/siparis_olustur.html', context)


@login_required_json
def siparis_kaydet(request):
    """Satış siparişi kaydetme"""
    from .models import SatisSiparisi, SatisSiparisiDetay
    from urun.models import Urun
    from musteri.models import Musteri
    from kullanici.models import CustomUser
    from decimal import Decimal
    from django.conf import settings
    import json

    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'POST metodu gereklidir'})

    try:
        data = json.loads(request.body)
        sepet = data.get('sepet', [])
        musteri_id = data.get('musteri_id')
        satici_id = data.get('satici_id')
        odeme_detaylari = data.get('odeme_detaylari', {})
        genel_indirim = Decimal(str(data.get('genel_indirim', 0)))
        aciklama = data.get('aciklama', '')
        durum = data.get('durum', 'taslak')  # taslak veya hazir

        if not sepet:
            return JsonResponse({'success': False, 'message': 'Sepet boş olamaz'})

        # Müşteri kontrolü
        musteri = None
        if musteri_id:
            try:
                musteri = Musteri.objects.get(id=musteri_id, aktif=True)
            except Musteri.DoesNotExist:
                return JsonResponse({'success': False, 'message': 'Müşteri bulunamadı'})

        # Satıcı kontrolü
        satici = None
        if satici_id:
            try:
                satici = CustomUser.objects.get(id=satici_id, is_active=True)
            except CustomUser.DoesNotExist:
                satici = request.user
        else:
            satici = request.user

        # Sipariş numarası oluştur
        siparis_no = SatisSiparisi.sonraki_siparis_no()

        # Toplam hesaplama - Frontend'deki gibi
        ara_toplam = Decimal('0')

        for item in sepet:
            miktar = int(item['miktar'])
            birim_fiyat = Decimal(str(item['fiyat']))
            urun_indirim = Decimal(str(item.get('indirim', 0)))

            satir_toplami = (birim_fiyat * miktar) - urun_indirim
            ara_toplam += satir_toplami

        # Genel indirim uygula
        indirim_sonrasi_toplam = ara_toplam - genel_indirim

        # KDV hesapla (KDV dahil olmayan toplam üzerinden)
        kdv_orani = Decimal('18.00')
        kdv_tutari = indirim_sonrasi_toplam * kdv_orani / Decimal('100')
        genel_toplam = indirim_sonrasi_toplam + kdv_tutari

        # Sipariş oluştur
        siparis = SatisSiparisi.objects.create(
            siparis_no=siparis_no,
            musteri=musteri,
            ara_toplam=indirim_sonrasi_toplam,  # İndirim sonrası ara toplam
            indirim_tutari=genel_indirim,
            kdv_orani=kdv_orani,
            kdv_tutari=kdv_tutari,
            genel_toplam=genel_toplam,
            durum=durum,
            satici=satici,
            odeme_yontemi=odeme_detaylari.get(
                'odeme_yontemi') if odeme_detaylari else None,
            odeme_detaylari=odeme_detaylari if odeme_detaylari else None,
            notlar=aciklama
        )

        # Sipariş detaylarını oluştur
        for item in sepet:
            try:
                urun = Urun.objects.get(id=item.get('id', item.get('urun_id')))
                miktar = int(item['miktar'])
                birim_fiyat = Decimal(str(item['fiyat']))
                urun_indirim = Decimal(str(item.get('indirim', 0)))

                SatisSiparisiDetay.objects.create(
                    siparis=siparis,
                    urun=urun,
                    miktar=miktar,
                    birim_fiyat=birim_fiyat,
                    indirim_tutari=urun_indirim,
                    toplam=(birim_fiyat * miktar) - urun_indirim
                )
            except Urun.DoesNotExist:
                continue

        return JsonResponse({
            'success': True,
            'message': 'Sipariş başarıyla kaydedildi!',
            'siparis_id': siparis.id,
            'siparis_no': siparis.siparis_no,
            'durum': siparis.get_durum_display()
        })

    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'message': 'Geçersiz JSON verisi'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Hata: {str(e)}'})


@login_required
def siparis_listesi(request):
    """Satış siparişleri listesi"""
    from .models import SatisSiparisi
    from django.db.models import Sum, Count
    from kullanici.models import CustomUser
    from django.conf import settings

    siparisler = SatisSiparisi.objects.all().order_by('-olusturma_tarihi')

    # Filtreleme
    durum_filter = request.GET.get('durum')
    if durum_filter:
        siparisler = siparisler.filter(durum=durum_filter)

    satici_filter = request.GET.get('satici')
    if satici_filter:
        siparisler = siparisler.filter(satici_id=satici_filter)

    # Arama
    q = request.GET.get('q')
    if q:
        siparisler = siparisler.filter(
            Q(siparis_no__icontains=q) |
            Q(musteri__ad__icontains=q) |
            Q(musteri__soyad__icontains=q) |
            Q(notlar__icontains=q)
        )

    # Sayfalama
    paginator = Paginator(siparisler, 20)
    page = request.GET.get('page')
    page_obj = paginator.get_page(page)

    # İstatistikler
    toplam_siparis = siparisler.count()
    toplam_tutar = siparisler.aggregate(
        toplam=Sum('genel_toplam'))['toplam'] or 0

    # Durum dağılımı
    durum_dagilimi = SatisSiparisi.objects.values('durum').annotate(
        adet=Count('id'),
        toplam_tutar=Sum('genel_toplam')
    ).order_by('durum')

    # Satıcılar (listeye göre aktif satıcılar)
    # Not: SatisSiparisi.satici alanında related_name tanımlı olmadığından
    # ters ilişki adı 'satissiparisi_set' değildir; güvenli yol olarak siparisler üzerinden id listesi alınır.
    satici_ids = siparisler.values_list('satici_id', flat=True).distinct()
    saticilar = CustomUser.objects.filter(
        is_active=True,
        id__in=list(satici_ids)
    ).order_by('first_name', 'last_name')

    context = {
        'title': 'Satış Siparişleri',
        'page_obj': page_obj,
        'toplam_siparis': toplam_siparis,
        'toplam_tutar': toplam_tutar,
        'durum_dagilimi': durum_dagilimi,
        'saticilar': saticilar,
        'durum_filter': durum_filter,
        'satici_filter': satici_filter,
        'q': q,
    }

    return render(request, 'satis/siparis_listesi.html', context)


@login_required
def siparis_detay(request, pk):
    """Satış siparişi detayı"""
    from .models import SatisSiparisi

    siparis = get_object_or_404(SatisSiparisi, pk=pk)
    # İlişki: SatisSiparisiDetay.siparis -> related_name='detaylar'
    detaylar = siparis.detaylar.all().select_related('urun')

    context = {
        'title': f'Sipariş Detayı - {siparis.siparis_no}',
        'siparis': siparis,
        'detaylar': detaylar,
    }

    return render(request, 'satis/siparis_detay.html', context)


@login_required_json
def siparis_satisa_donustur(request, pk):
    """Siparişi satışa dönüştür"""
    from .models import SatisSiparisi

    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'POST metodu gereklidir'})

    try:
        siparis = get_object_or_404(SatisSiparisi, pk=pk)

        if siparis.durum != 'hazir':
            return JsonResponse({
                'success': False,
                'message': 'Sadece "Satışa Hazır" durumundaki siparişler satışa dönüştürülebilir'
            })

        satis = siparis.satisa_donustur(user=request.user)

        return JsonResponse({
            'success': True,
            'message': 'Sipariş başarıyla satışa dönüştürüldü!',
            'satis_id': satis.id,
            'siparis_no': satis.siparis_no
        })

    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Hata: {str(e)}'})


@login_required
def siparis_satis_ekraninda_yukle(request):
    """Siparişteki ürünleri satış ekranına yükle (AJAX)"""
    from .models import SatisSiparisi
    import json

    try:
        siparis_id = request.GET.get('siparis_id')
        siparis = SatisSiparisi.objects.get(
            id=siparis_id,
            durum__in=['taslak', 'hazir']
        )

        # Sipariş detaylarını al
        detaylar = siparis.detaylar.all().select_related('urun')

        detay_listesi = []
        for detay in detaylar:
            detay_listesi.append({
                'urun': {
                    'id': detay.urun.id,
                    'kod': detay.urun.urun_kodu or '',
                    'ad': detay.urun.ad,
                    'barkod': '',  # Barkod varyant seviyesinde
                    'kategori': detay.urun.kategori.ad if detay.urun.kategori else '',
                    'kdv_orani': 18.0,  # Sabit KDV oranı
                    'resim': detay.urun.resim.url if detay.urun.resim else None
                },
                'miktar': int(detay.miktar),
                'birim_fiyat': float(detay.birim_fiyat),
                'indirim_tutari': float(detay.indirim_tutari),
                'toplam_tutar': float(detay.toplam)
            })

        # Ödeme detaylarını parse et
        odeme_detaylari = {}
        if siparis.odeme_detaylari:
            try:
                odeme_detaylari = json.loads(siparis.odeme_detaylari)
            except json.JSONDecodeError:
                pass

        return JsonResponse({
            'success': True,
            'siparis': {
                'id': siparis.id,
                'siparis_no': siparis.siparis_no,
                'musteri_id': siparis.musteri.id if siparis.musteri else None,
                'musteri_ad': f"{siparis.musteri.ad} {siparis.musteri.soyad}" if siparis.musteri else 'Perakende',
                'odeme_yontemi': siparis.odeme_yontemi,
                'banka': odeme_detaylari.get('banka', ''),
                'notlar': siparis.notlar or '',
                'detaylar': detay_listesi
            }
        })

    except SatisSiparisi.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Sipariş bulunamadı veya yüklenemez durumda'
        })


@login_required_json
def siparis_sil(request, pk):
    """Taslak durumundaki siparişi sil"""
    from .models import SatisSiparisi

    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'POST metodu gereklidir'})

    try:
        siparis = get_object_or_404(SatisSiparisi, pk=pk)

        # Sadece taslak durumundaki siparişler silinebilir
        if siparis.durum != 'taslak':
            return JsonResponse({
                'success': False,
                'message': 'Sadece taslak durumundaki siparişler silinebilir'
            })

        # Sipariş numarasını kaydet
        siparis_no = siparis.siparis_no

        # Siparişi sil (CASCADE ile detayları da silinir)
        siparis.delete()

        return JsonResponse({
            'success': True,
            'message': f'Sipariş {siparis_no} başarıyla silindi!'
        })

    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Hata: {str(e)}'})
