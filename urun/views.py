from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q, Sum, Avg
from decimal import Decimal
from .models import Urun, UrunKategoriUst, Renk, Beden, Marka, UrunVaryanti, StokHareket
from .forms import StokGirisForm, StokCikisForm, StokDuzeltmeForm, StokSayimForm


@login_required
def urun_listesi(request):
    """Ürün listesi - Client-side filtreleme ile"""

    # Tüm ürünleri getir (filtreleme JavaScript'te yapılacak)
    urunler = Urun.objects.select_related(
        'kategori', 'marka').prefetch_related('varyantlar').all().order_by('-id')

    # Her ürün için silme kontrolü ekle
    def silme_kontrolu_hizli(urun):
        """Hızlı silme kontrolü - sadece boolean döner"""
        from satis.models import SatisDetay

        # Satış kontrolü
        if SatisDetay.objects.filter(urun=urun).exists():
            return False

        # Stok kontrolü
        if urun.toplam_stok > 0:
            return False

        # Varyant stok kontrolü
        for varyant in urun.varyantlar.all():
            if varyant.stok_miktari > 0:
                return False

        return True

    # Sayfalama
    paginator = Paginator(urunler, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Her ürüne silme izni bilgisi ekle
    for urun in page_obj:
        urun.silme_izni = silme_kontrolu_hizli(urun)

    # İstatistikler
    tum_urunler = Urun.objects.all()
    toplam_urun = tum_urunler.count()
    aktif_urun = tum_urunler.filter(aktif=True).count()
    kritik_stok = len([u for u in tum_urunler if 0 <
                      u.toplam_stok <= u.kritik_stok_seviyesi])
    tukenen_stok = len([u for u in tum_urunler if u.toplam_stok == 0])

    context = {
        'page_obj': page_obj,
        'urunler': page_obj,
        'title': 'Ürün Listesi',
        'toplam_urun': toplam_urun,
        'aktif_urun': aktif_urun,
        'kritik_stok': kritik_stok,
        'tukenen_stok': tukenen_stok,
    }
    return render(request, 'urun/liste.html', context)


@login_required
def urun_ekle(request):
    """Ürün ekleme"""
    if request.method == 'POST':
        try:
            # Temel bilgileri al
            ad = request.POST.get('ad', '').strip()
            aciklama = request.POST.get('aciklama', '').strip()
            kategori_id = request.POST.get('kategori')
            marka_id = request.POST.get(
                'marka') if request.POST.get('marka') else None
            cinsiyet = request.POST.get('cinsiyet', 'kadin')
            birim = request.POST.get('birim', 'adet')
            varyasyonlu = request.POST.get('varyasyonlu') == 'on'

            # Resim dosyası al
            resim = request.FILES.get('resim')

            # Fiyat bilgileri - boş değerler için 0 kullan
            alis_fiyati_str = request.POST.get('alis_fiyati', '0').strip()
            kar_orani_str = request.POST.get('kar_orani', '50').strip()
            satis_fiyati_str = request.POST.get('satis_fiyati', '0').strip()

            alis_fiyati = Decimal(
                alis_fiyati_str) if alis_fiyati_str else Decimal('0')
            kar_orani = Decimal(
                kar_orani_str) if kar_orani_str else Decimal('50')
            satis_fiyati = Decimal(
                satis_fiyati_str) if satis_fiyati_str else Decimal('0')

            # Kategori ve marka objeleri
            kategori = get_object_or_404(UrunKategoriUst, id=kategori_id)
            marka = Marka.objects.get(id=marka_id) if marka_id else None

            # Ürün oluştur
            urun = Urun.objects.create(
                ad=ad,
                aciklama=aciklama,
                kategori=kategori,
                marka=marka,
                cinsiyet=cinsiyet,
                birim=birim,
                varyasyonlu=varyasyonlu,
                alis_fiyati=alis_fiyati,
                kar_orani=kar_orani,
                satis_fiyati=satis_fiyati,
                resim=resim,  # Resim dosyasını ekle
                olusturan=request.user
            )

            # Varyantları oluştur
            if varyasyonlu:
                # Seçilen renk ve bedenler
                secilen_renkler = request.POST.getlist('renkler')
                secilen_bedenler = request.POST.getlist('bedenler')

                if secilen_renkler and secilen_bedenler:
                    # Kombinasyonları oluştur
                    for renk_id in secilen_renkler:
                        for beden_id in secilen_bedenler:
                            renk = Renk.objects.get(id=renk_id)
                            beden = Beden.objects.get(id=beden_id)

                            UrunVaryanti.objects.create(
                                urun=urun,
                                renk=renk,
                                beden=beden,
                                stok_miktari=1,  # Varsayılan stok
                                stok_kaydedildi=False,  # Henüz kaydedilmemiş
                                aktif=True
                            )

                    messages.success(
                        request, f'✅ {urun.ad} ve {len(secilen_renkler) * len(secilen_bedenler)} varyantı eklendi!')
                else:
                    messages.warning(
                        request, 'Varyasyonlu ürün için renk ve beden seçmelisiniz!')
            else:
                # Varyasyonsuz ürün için tek varyant oluştur
                UrunVaryanti.objects.create(
                    urun=urun,
                    renk=None,
                    beden=None,
                    stok_miktari=int(request.POST.get('stok_miktari', 0)),
                    stok_kaydedildi=True,  # Varyasyonsuz ürünler direkt kaydedilmiş sayılır
                    aktif=True
                )
                messages.success(request, f'✅ {urun.ad} ürünü eklendi!')

            return redirect('urun:liste')

        except Exception as e:
            messages.error(request, f'❌ Ürün eklenirken hata oluştu: {str(e)}')

    context = {
        'kategoriler': UrunKategoriUst.objects.filter(aktif=True).order_by('ad'),
        'markalar': Marka.objects.filter(aktif=True).order_by('ad'),
        'renkler': Renk.objects.filter(aktif=True).order_by('sira'),
        'bedenler': Beden.objects.filter(aktif=True).order_by('tip', 'sira'),
        'title': 'Yeni Ürün Ekle'
    }
    return render(request, 'urun/ekle.html', context)


def barkod_sorgula(request):
    """Barkod sorgulama"""
    barkod = request.GET.get('barkod', '').strip()
    urun = None
    varyant = None

    if barkod:
        try:
            # Önce direkt barkod ile varyant ara
            varyant = UrunVaryanti.objects.select_related(
                'urun').get(barkod=barkod, aktif=True)
            urun = varyant.urun
        except UrunVaryanti.DoesNotExist:
            # Direkt bulunamazsa barkod çözümleyerek ara
            sonuc = UrunVaryanti.barkod_cozumle(barkod)

            if sonuc:
                try:
                    # Çözümlenen bilgiler ile ürün ve varyant bul
                    from .models import Urun, UrunRenk, UrunBeden

                    # Ürün numarası ile ürün bul
                    urun_obj = Urun.objects.get(
                        urun_numarasi=sonuc['urun_numarasi'], aktif=True)

                    # Renk ve beden bilgileri varsa varyant bul
                    filters = {'urun': urun_obj, 'aktif': True}

                    if sonuc.get('renk_kodu'):
                        renk = UrunRenk.objects.get(kod=sonuc['renk_kodu'])
                        filters['renk'] = renk

                    if sonuc.get('beden_kodu'):
                        beden = UrunBeden.objects.get(kod=sonuc['beden_kodu'])
                        filters['beden'] = beden

                    varyant = UrunVaryanti.objects.get(**filters)
                    urun = urun_obj

                except (Urun.DoesNotExist, UrunVaryanti.DoesNotExist, UrunRenk.DoesNotExist, UrunBeden.DoesNotExist):
                    messages.error(
                        request, f'Barkod çözümlendi ancak ürün bulunamadı! (Ürün No: {sonuc.get("urun_numarasi", "?")})')
            else:
                messages.error(request, 'Geçersiz barkod formatı!')

    # Ürün bulunduysa tüm varyantlarını da getir
    varyantlar = []
    if urun:
        varyantlar = UrunVaryanti.objects.filter(
            urun=urun,
            aktif=True
        ).select_related('renk', 'beden').order_by('renk__ad', 'beden__ad')

    context = {
        'title': 'Barkod Sorgula',
        'barkod': barkod,
        'urun': urun,
        'varyant': varyant,
        'varyantlar': varyantlar,
        'aranan_varyant': varyant  # Aranan spesifik varyantı ayırt etmek için
    }
    return render(request, 'urun/barkod_sorgula.html', context)


@login_required
def kategori_yonetimi(request):
    """Kategori yönetimi"""
    from django.db.models import Count

    kategoriler = UrunKategoriUst.objects.all().order_by('ad')

    # Toplam ürün sayısını hesapla
    toplam_urun_sayisi = Urun.objects.count()

    context = {
        'kategoriler': kategoriler,
        'ust_kategoriler': kategoriler,  # Template beklenen değişken
        'toplam_urun_sayisi': toplam_urun_sayisi,
        'title': 'Kategori Yönetimi'
    }
    return render(request, 'urun/kategori_yonetimi.html', context)


@login_required
def ust_kategori_ekle(request):
    """Üst kategori ekleme/düzenleme"""
    if request.method == 'POST':
        kategori_id = request.GET.get('edit')
        ad = request.POST.get('ad')
        aciklama = request.POST.get('aciklama', '')

        if not ad:
            messages.error(request, 'Kategori adı gereklidir!')
            return redirect('urun:kategori')

        try:
            if kategori_id:  # Düzenleme
                kategori = get_object_or_404(UrunKategoriUst, id=kategori_id)
                kategori.ad = ad
                kategori.aciklama = aciklama
                kategori.save()
                messages.success(
                    request, f'{ad} kategorisi başarıyla güncellendi!')
            else:  # Yeni ekleme
                UrunKategoriUst.objects.create(
                    ad=ad,
                    aciklama=aciklama,
                    aktif=True
                )
                messages.success(
                    request, f'{ad} kategorisi başarıyla eklendi!')
        except Exception as e:
            messages.error(request, f'Hata oluştu: {str(e)}')

    return redirect('urun:kategori')


@login_required
def ust_kategori_sil(request, kategori_id):
    """Üst kategori silme"""
    if request.method == 'POST':
        try:
            kategori = get_object_or_404(UrunKategoriUst, id=kategori_id)
            kategori_ad = kategori.ad

            # Kategoriye bağlı ürün var mı kontrol et
            if kategori.urun_set.exists():
                messages.error(
                    request, f'{kategori_ad} kategorisine bağlı ürünler bulunuyor. Önce ürünleri başka kategoriye taşıyın.')
            else:
                kategori.delete()
                messages.success(
                    request, f'{kategori_ad} kategorisi başarıyla silindi!')
        except Exception as e:
            messages.error(request, f'Hata oluştu: {str(e)}')

    return redirect('urun:kategori')


@login_required
def marka_listesi(request):
    """Marka listesi"""
    if request.method == 'POST':
        try:
            ad = request.POST.get('ad', '').strip()
            aciklama = request.POST.get('aciklama', '').strip()

            if ad:
                Marka.objects.create(
                    ad=ad,
                    aciklama=aciklama
                )
                messages.success(request, f'{ad} markası başarıyla eklendi!')
            else:
                messages.error(request, 'Marka adı boş olamaz!')
        except Exception as e:
            messages.error(request, f'Hata oluştu: {str(e)}')

        return redirect('urun:marka_listesi')

    markalar = Marka.objects.all().order_by('ad')

    # Her marka için ürün sayısını hesapla
    for marka in markalar:
        marka.urun_sayisi = marka.urun_set.count()

    context = {
        'markalar': markalar,
        'title': 'Marka Yönetimi'
    }
    return render(request, 'urun/marka_listesi.html', context)


@login_required
def marka_ekle(request):
    """Marka ekleme"""
    if request.method == 'POST':
        try:
            ad = request.POST.get('ad', '').strip()
            aciklama = request.POST.get('aciklama', '').strip()
            logo = request.FILES.get('logo')

            if ad:
                Marka.objects.create(
                    ad=ad,
                    aciklama=aciklama,
                    logo=logo
                )
                messages.success(request, f'{ad} markası başarıyla eklendi!')
                return redirect('urun:marka_listesi')
            else:
                messages.error(request, 'Marka adı boş olamaz!')
        except Exception as e:
            messages.error(request, f'Hata oluştu: {str(e)}')

    context = {
        'title': 'Yeni Marka Ekle'
    }
    return render(request, 'urun/marka_ekle.html', context)


@login_required
def marka_duzenle(request, pk):
    """Marka düzenleme"""
    marka = get_object_or_404(Marka, pk=pk)

    if request.method == 'POST':
        try:
            ad = request.POST.get('ad', '').strip()
            aciklama = request.POST.get('aciklama', '').strip()
            logo = request.FILES.get('logo')

            if ad:
                marka.ad = ad
                marka.aciklama = aciklama
                if logo:
                    marka.logo = logo
                marka.save()
                messages.success(
                    request, f'{ad} markası başarıyla güncellendi!')
                return redirect('urun:marka_listesi')
            else:
                messages.error(request, 'Marka adı boş olamaz!')
        except Exception as e:
            messages.error(request, f'Hata oluştu: {str(e)}')

    # İstatistikler hesapla
    toplam_urun = marka.urun_set.count()
    # Aktif ürün sayısı
    stokta_urun_sayisi = marka.urun_set.filter(aktif=True).count()

    context = {
        'marka': marka,
        'toplam_urun': toplam_urun,
        'stokta_urun_sayisi': stokta_urun_sayisi,
        'title': 'Marka Düzenle'
    }
    return render(request, 'urun/marka_duzenle.html', context)


@login_required
def marka_sil(request, pk):
    """Marka silme"""
    marka = get_object_or_404(Marka, pk=pk)

    # Silme kontrolü
    urun_sayisi = marka.urun_set.count()
    if urun_sayisi > 0:
        messages.error(
            request, f'{marka.ad} markasına ait {urun_sayisi} ürün bulunduğu için silinemez!')
        return redirect('urun:marka_listesi')

    if request.method == 'POST':
        ad = marka.ad
        marka.delete()
        messages.success(request, f'{ad} markası başarıyla silindi!')
        return redirect('urun:marka_listesi')

    context = {
        'marka': marka,
        'title': 'Marka Sil'
    }
    return render(request, 'urun/marka_sil.html', context)


@login_required
def stok_durumu(request):
    """Stok durumu raporu"""
    urunler = Urun.objects.select_related(
        'kategori', 'marka').all().order_by('ad')

    # Stok durumu filtresi
    stok_filtre = request.GET.get('stok_filtre', 'tumu')
    if stok_filtre == 'tukenmek_uzere':
        urunler = urunler.filter(stok_miktari__lte=10)
    elif stok_filtre == 'tukenmis':
        urunler = urunler.filter(stok_miktari=0)
    elif stok_filtre == 'stokta_var':
        urunler = urunler.filter(stok_miktari__gt=0)

    context = {
        'urunler': urunler,
        'stok_filtre': stok_filtre,
        'title': 'Stok Durumu'
    }
    return render(request, 'urun/stok_raporu.html', context)


@login_required
def en_cok_satanlar(request):
    """En çok satan ürünler raporu"""
    from django.db.models import Sum
    from satis.models import SatisDetay

    # En çok satan ürünler (son 30 gün)
    import datetime
    son_30_gun = datetime.date.today() - datetime.timedelta(days=30)

    en_cok_satanlar = SatisDetay.objects.filter(
        satis__satis_tarihi__date__gte=son_30_gun
    ).values(
        'urun__ad', 'urun__urun_kodu', 'urun__satis_fiyati',
        'urun__kategori__ad', 'urun__marka__ad'
    ).annotate(
        toplam_miktar=Sum('miktar'),
        toplam_tutar=Sum('toplam_fiyat')
    ).order_by('-toplam_miktar')[:20]

    context = {
        'en_cok_satanlar': en_cok_satanlar,
        'title': 'En Çok Satanlar'
    }
    return render(request, 'urun/en_cok_satanlar.html', context)


@login_required
def kar_zarar_raporu(request):
    """Kar zarar raporu"""
    from django.db.models import Sum, F
    from satis.models import SatisDetay
    import datetime

    # Tarih filtreleri
    bugun = datetime.date.today()
    son_30_gun = bugun - datetime.timedelta(days=30)

    # Kar zarar hesaplaması
    satislar = SatisDetay.objects.filter(
        satis__siparis_tarihi__gte=son_30_gun
    ).aggregate(
        toplam_satis=Sum('toplam_fiyat'),
        toplam_miktar=Sum('miktar')
    )

    # Ürün bazında kar zarar
    urun_kar_zarar = SatisDetay.objects.filter(
        satis__siparis_tarihi__gte=son_30_gun
    ).values(
        'urun__ad', 'urun__alis_fiyati', 'urun__satis_fiyati'
    ).annotate(
        toplam_miktar=Sum('miktar'),
        toplam_satis=Sum('toplam_fiyat'),
        toplam_maliyet=Sum(F('miktar') * F('urun__alis_fiyati')),
        kar=Sum(F('toplam_fiyat') - (F('miktar') * F('urun__alis_fiyati')))
    ).order_by('-kar')

    context = {
        'satislar': satislar,
        'urun_kar_zarar': urun_kar_zarar,
        'title': 'Kar Zarar Raporu'
    }
    return render(request, 'urun/kar_zarar.html', context)


@login_required
def urun_detay(request, urun_id):
    """Ürün detay sayfası"""
    urun = get_object_or_404(Urun, id=urun_id)
    varyantlar = urun.varyantlar.filter(
        aktif=True).order_by('renk__ad', 'beden__ad')

    # Silme kontrolü
    def silme_kontrolu_detay(urun):
        """Detaylı silme kontrolü"""
        from satis.models import SatisDetay

        # Satış kontrolü
        if SatisDetay.objects.filter(urun=urun).exists():
            return False, "Bu ürün daha önce satılmıştır."

        # Stok kontrolü
        if urun.toplam_stok > 0:
            return False, f"Bu ürünün stoğu bulunmaktadır ({urun.toplam_stok} adet)."

        # Varyant stok kontrolü
        for varyant in urun.varyantlar.all():
            if varyant.stok_miktari > 0:
                return False, f"'{varyant.varyasyon_adi}' varyantının stoğu bulunmaktadır."

        return True, ""

    silme_izni, silme_mesaji = silme_kontrolu_detay(urun)

    context = {
        'urun': urun,
        'varyantlar': varyantlar,
        'title': f'{urun.ad} - Detay',
        'silme_izni': silme_izni,
        'silme_mesaji': silme_mesaji
    }
    return render(request, 'urun/detay.html', context)


@login_required
def urun_duzenle(request, urun_id):
    """Ürün düzenleme sayfası"""
    urun = get_object_or_404(Urun, id=urun_id)

    if request.method == 'POST':
        try:
            # Temel bilgileri güncelle
            urun.ad = request.POST.get('ad', '').strip()
            urun.aciklama = request.POST.get('aciklama', '').strip()

            # Kategori ve marka güncelle
            kategori_id = request.POST.get('kategori')
            marka_id = request.POST.get(
                'marka') if request.POST.get('marka') else None

            urun.kategori = get_object_or_404(UrunKategoriUst, id=kategori_id)
            urun.marka = Marka.objects.get(id=marka_id) if marka_id else None

            # Diğer alanları güncelle
            urun.cinsiyet = request.POST.get('cinsiyet', 'unisex')
            urun.birim = request.POST.get('birim', 'adet')

            # Fiyat bilgileri - boş değerler için 0 kullan
            alis_fiyati_str = request.POST.get('alis_fiyati', '0').strip()
            kar_orani_str = request.POST.get('kar_orani', '50').strip()
            satis_fiyati_str = request.POST.get('satis_fiyati', '0').strip()

            # Eski satış fiyatını kaydet
            eski_satis_fiyati = urun.satis_fiyati

            urun.alis_fiyati = Decimal(
                alis_fiyati_str) if alis_fiyati_str else Decimal('0')
            urun.kar_orani = Decimal(
                kar_orani_str) if kar_orani_str else Decimal('50')
            urun.satis_fiyati = Decimal(
                satis_fiyati_str) if satis_fiyati_str else Decimal('0')

            # Satış fiyatı değişti mi kontrol et
            fiyat_degisti = eski_satis_fiyati != urun.satis_fiyati

            # Resim güncelleme
            if request.POST.get('remove_image') == 'true':
                # Mevcut resmi sil
                if urun.resim:
                    urun.resim.delete(save=False)
                    urun.resim = None
            elif 'resim' in request.FILES:
                # Yeni resim yükle
                urun.resim = request.FILES['resim']

            urun.save()

            # Fiyat değiştiyse barkodları güncelle
            if fiyat_degisti:
                barkod_guncellendi = 0
                varyantlar = UrunVaryanti.objects.filter(urun=urun)
                for varyant in varyantlar:
                    # Yeni barkod oluştur
                    yeni_barkod = varyant.olustur_barkod()
                    if yeni_barkod != varyant.barkod:
                        varyant.barkod = yeni_barkod
                        varyant.save()
                        barkod_guncellendi += 1

                if barkod_guncellendi > 0:
                    messages.success(
                        request, f'✅ {urun.ad} ürünü güncellendi ve {barkod_guncellendi} varyantın barkodu otomatik olarak yenilendi!')
                else:
                    messages.success(
                        request, f'✅ {urun.ad} ürünü başarıyla güncellendi!')
            else:
                messages.success(
                    request, f'✅ {urun.ad} ürünü başarıyla güncellendi!')

            return redirect('urun:detay', urun_id=urun.id)

        except Exception as e:
            messages.error(request, f'❌ Hata: {str(e)}')

    # Form için gerekli veriler
    kategoriler = UrunKategoriUst.objects.filter(aktif=True).order_by('ad')
    markalar = Marka.objects.filter(aktif=True).order_by('ad')

    context = {
        'urun': urun,
        'kategoriler': kategoriler,
        'markalar': markalar,
        'title': f'{urun.ad} - Düzenle'
    }
    return render(request, 'urun/duzenle.html', context)


@login_required
def urun_sil(request, urun_id):
    """Ürün silme"""
    urun = get_object_or_404(Urun, id=urun_id)

    # Silme kontrolü - hareket görmüş veya stoğu olan ürünler silinemez
    def silme_kontrolu(urun):
        """Ürünün silinip silinemeyeceğini kontrol eder"""
        from satis.models import SatisDetay

        # 1. Satış kontrolü - Bu ürün herhangi bir satışta var mı?
        satis_var = SatisDetay.objects.filter(urun=urun).exists()
        if satis_var:
            return False, "Bu ürün daha önce satılmıştır. Hareket görmüş ürünler silinemez."

        # 2. Stok kontrolü - Ürünün toplam stoğu var mı?
        toplam_stok = urun.toplam_stok
        if toplam_stok > 0:
            return False, f"Bu ürünün stoğu bulunmaktadır ({toplam_stok} adet). Stoğu olan ürünler silinemez."

        # 3. Varyant kontrolü - Herhangi bir varyantın stoğu var mı?
        for varyant in urun.varyantlar.all():
            if varyant.stok_miktari > 0:
                return False, f"'{varyant.varyasyon_adi}' varyantının stoğu bulunmaktadır ({varyant.stok_miktari} adet). Stoğu olan ürünler silinemez."

        return True, ""

    if request.method == 'POST':
        urun_adi = urun.ad

        # Silme kontrolü yap
        silme_izni, hata_mesaji = silme_kontrolu(urun)

        if not silme_izni:
            messages.error(request, f'❌ {hata_mesaji}')
            return redirect('urun:liste')

        try:
            # Varyantları da sil
            urun.varyantlar.all().delete()
            # Ürünü sil
            urun.delete()
            messages.success(request, f'✅ {urun_adi} ürünü başarıyla silindi!')
        except Exception as e:
            messages.error(request, f'❌ Silme işlemi sırasında hata: {str(e)}')

        return redirect('urun:liste')

    # GET isteği - onay sayfası
    # Silme kontrolü yap ve bilgileri template'e gönder
    silme_izni, hata_mesaji = silme_kontrolu(urun)

    context = {
        'urun': urun,
        'title': f'{urun.ad} - Sil',
        'silme_izni': silme_izni,
        'hata_mesaji': hata_mesaji
    }
    return render(request, 'urun/sil_onay.html', context)


@login_required
def varyasyon_yonet(request, urun_id):
    """Ürün varyasyonlarını yönetme sayfası"""
    urun = get_object_or_404(Urun, id=urun_id)

    # Sadece varyasyonlu ürünler için
    if not urun.varyasyonlu:
        messages.error(request, 'Bu ürün varyasyonlu değil!')
        return redirect('urun:detay', urun_id)

    # Mevcut varyantları getir
    mevcut_varyantlar = UrunVaryanti.objects.filter(
        urun=urun).select_related('renk', 'beden')

    # Düzenlenebilir varyant var mı kontrol et (stok_kaydedildi=False olanlar)
    has_editable_variants = mevcut_varyantlar.filter(
        stok_kaydedildi=False).exists()

    # Tüm renk ve bedenler
    renkler = Renk.objects.filter(aktif=True).order_by('sira', 'ad')
    bedenler = Beden.objects.filter(aktif=True).order_by('tip', 'sira', 'ad')

    context = {
        'urun': urun,
        'mevcut_varyantlar': mevcut_varyantlar,
        'has_editable_variants': has_editable_variants,
        'renkler': renkler,
        'bedenler': bedenler,
        'title': f'{urun.ad} - Varyasyon Yönetimi'
    }

    return render(request, 'urun/varyasyon_yonet.html', context)


@login_required
def varyasyon_olustur(request, urun_id):
    """Seçilen renk ve bedenlerle otomatik varyasyon oluşturma"""
    urun = get_object_or_404(Urun, id=urun_id)

    if not urun.varyasyonlu:
        return JsonResponse({'success': False, 'error': 'Bu ürün varyasyonlu değil!'})

    if request.method == 'POST':
        try:
            # Seçilen renk ve beden ID'lerini al
            renk_ids = request.POST.getlist('renkler')
            beden_ids = request.POST.getlist('bedenler')

            if not renk_ids and not beden_ids:
                return JsonResponse({'success': False, 'error': 'En az bir renk veya beden seçmelisiniz!'})

            # Eğer hiç renk seçilmemişse None olarak işle
            if not renk_ids:
                renk_ids = [None]
            # Eğer hiç beden seçilmemişse None olarak işle
            if not beden_ids:
                beden_ids = [None]

            created_count = 0
            skipped_count = 0

            with transaction.atomic():
                # Tüm kombinasyonları oluştur
                for renk_id in renk_ids:
                    for beden_id in beden_ids:
                        # Renk ve beden objelerini al
                        renk = Renk.objects.get(
                            id=renk_id) if renk_id else None
                        beden = Beden.objects.get(
                            id=beden_id) if beden_id else None

                        # Bu kombinasyon zaten var mı kontrol et
                        varyant_exists = UrunVaryanti.objects.filter(
                            urun=urun,
                            renk=renk,
                            beden=beden
                        ).exists()

                        if not varyant_exists:
                            # Yeni varyant oluştur
                            UrunVaryanti.objects.create(
                                urun=urun,
                                renk=renk,
                                beden=beden,
                                stok_miktari=1,  # Başlangıç stoku 1
                                stok_kaydedildi=False,  # Henüz kaydedilmemiş
                                aktif=True
                            )
                            created_count += 1
                        else:
                            skipped_count += 1

            return JsonResponse({
                'success': True,
                'created': created_count,
                'skipped': skipped_count,
                'message': f'{created_count} varyant oluşturuldu, {skipped_count} zaten mevcuttu.'
            })

        except Exception as e:
            return JsonResponse({'success': False, 'error': f'Hata oluştu: {str(e)}'})

    return JsonResponse({'success': False, 'error': 'Geçersiz istek!'})


@login_required
def varyant_duzenle(request, varyant_id):
    """Varyant düzenleme"""
    from .models import StokHareket
    varyant = get_object_or_404(UrunVaryanti, id=varyant_id)

    if request.method == 'POST':
        try:
            yeni_stok_miktari = int(request.POST.get('stok_miktari', 0))
            aktif = request.POST.get('aktif') == 'on'

            # Eski stok miktarını al
            eski_stok = varyant.stok_miktari

            # Eğer stok miktarı değiştiyse stok hareketi oluştur
            if eski_stok != yeni_stok_miktari:
                fark = yeni_stok_miktari - eski_stok
                if fark > 0:
                    hareket_tipi = 'giris'
                    miktar = fark
                    aciklama = f'Manuel stok girişi (+{fark})'
                else:
                    hareket_tipi = 'cikis'
                    miktar = abs(fark)
                    aciklama = f'Manuel stok çıkışı (-{abs(fark)})'

                # Stok hareketini oluştur
                StokHareket.stok_hareketi_olustur(
                    varyant=varyant,
                    hareket_tipi=hareket_tipi,
                    miktar=miktar,
                    kullanici=request.user,
                    aciklama=aciklama,
                    referans_id=f'manuel_{varyant.id}'
                )
            else:
                # Sadece aktiflik durumu değişti
                varyant.aktif = aktif
                try:
                    varyant.save()
                except ValueError:
                    # Stok koruması varsa güvenli save yap
                    varyant.save(stok_hareket_guncelleme=True)

            return JsonResponse({
                'success': True,
                'message': f'{varyant.varyasyon_adi} başarıyla güncellendi!'
            })

        except Exception as e:
            return JsonResponse({'success': False, 'error': f'Hata oluştu: {str(e)}'})

    return JsonResponse({'success': False, 'error': 'Geçersiz istek!'})


@login_required
def varyant_sil(request, varyant_id):
    """Varyant silme"""
    varyant = get_object_or_404(UrunVaryanti, id=varyant_id)

    if request.method == 'POST':
        try:
            varyasyon_adi = varyant.varyasyon_adi
            varyant.delete()

            return JsonResponse({
                'success': True,
                'message': f'{varyasyon_adi} varyantı silindi!'
            })

        except Exception as e:
            return JsonResponse({'success': False, 'error': f'Hata oluştu: {str(e)}'})

    return JsonResponse({'success': False, 'error': 'Geçersiz istek!'})


@login_required
def varyant_toplu_stok_guncelle(request, urun_id):
    """Tüm varyantlar için toplu stok güncelleme - sadece henüz kaydedilmemiş varyantlar"""
    from .models import StokHareket
    urun = get_object_or_404(Urun, id=urun_id)

    if request.method == 'POST':
        try:
            updated_count = 0
            skipped_count = 0

            with transaction.atomic():
                for key, value in request.POST.items():
                    if key.startswith('stok_'):
                        varyant_id = key.replace('stok_', '')
                        try:
                            varyant = UrunVaryanti.objects.get(
                                id=varyant_id, urun=urun)

                            # Sadece henüz kaydedilmemiş varyantları güncelle
                            if not varyant.stok_kaydedildi:
                                yeni_stok_miktari = int(value) if value else 0
                                eski_stok = varyant.stok_miktari

                                # İlk stok girişi ise stok hareketi oluştur
                                if yeni_stok_miktari > 0:
                                    # İlk stok girişi için varyantın stok miktarını sıfırla
                                    varyant.stok_miktari = 0

                                    StokHareket.stok_hareketi_olustur(
                                        varyant=varyant,
                                        hareket_tipi='giris',
                                        miktar=yeni_stok_miktari,
                                        kullanici=request.user,
                                        aciklama=f'İlk stok girişi - {varyant.varyasyon_adi}',
                                        referans_id=f'ilk_stok_{varyant.id}'
                                    )
                                else:
                                    # Stok miktarı 0 ise sadece kaydedildi işaretle
                                    varyant.stok_miktari = 0
                                    varyant.save(stok_hareket_guncelleme=True)

                                varyant.stok_kaydedildi = True  # Artık kaydedildi olarak işaretle
                                varyant.save(stok_hareket_guncelleme=True)
                                updated_count += 1
                            else:
                                skipped_count += 1

                        except (UrunVaryanti.DoesNotExist, ValueError):
                            continue

            message = f'{updated_count} varyant stoku güncellendi!'
            if skipped_count > 0:
                message += f' ({skipped_count} varyant zaten kaydedilmiş olduğu için atlandı)'

            return JsonResponse({
                'success': True,
                'message': message
            })

        except Exception as e:
            return JsonResponse({'success': False, 'error': f'Hata oluştu: {str(e)}'})

    return JsonResponse({'success': False, 'error': 'Geçersiz istek!'})


# === STOK HAREKETLERİ YÖNETİMİ ===

@login_required
def stok_yonetimi_ana(request):
    """Stok yönetimi ana sayfası"""
    # Genel stok istatistikleri
    from django.db.models import Sum, Count, F

    # Toplam stok sayıları
    toplam_urun = Urun.objects.filter(aktif=True).count()
    toplam_varyant = UrunVaryanti.objects.filter(aktif=True).count()
    toplam_stok = UrunVaryanti.objects.filter(aktif=True).aggregate(
        toplam=Sum('stok_miktari')
    )['toplam'] or 0

    # Son stok hareketleri (son 10 adet)
    son_hareketler = StokHareket.objects.select_related(
        'varyant__urun', 'kullanici'
    ).order_by('-olusturma_tarihi')[:10]

    # Kritik stok seviyesindeki ürünler
    kritik_stoklar = UrunVaryanti.objects.select_related('urun').filter(
        aktif=True,
        stok_miktari__lte=F('urun__kritik_stok_seviyesi')
    ).order_by('stok_miktari')[:10]

    # Hareket tiplerinin sayıları (bu ay)
    from datetime import datetime, timedelta
    bu_ay_baslangic = datetime.now().replace(
        day=1, hour=0, minute=0, second=0, microsecond=0)

    hareket_istatistikleri = {}
    for hareket_tipi, hareket_adi in StokHareket.HAREKET_TIPLERI:
        hareket_istatistikleri[hareket_tipi] = StokHareket.objects.filter(
            hareket_tipi=hareket_tipi,
            olusturma_tarihi__gte=bu_ay_baslangic
        ).count()

    context = {
        'toplam_urun': toplam_urun,
        'toplam_varyant': toplam_varyant,
        'toplam_stok': toplam_stok,
        'son_hareketler': son_hareketler,
        'kritik_stoklar': kritik_stoklar,
        'hareket_istatistikleri': hareket_istatistikleri,
    }

    return render(request, 'urun/stok_yonetimi_ana.html', context)


@login_required
def stok_giris_view(request):
    """Stok giriş işlemi"""
    if request.method == 'POST':
        form = StokGirisForm(request.POST)
        if form.is_valid():
            try:
                with transaction.atomic():
                    varyant = form.cleaned_data['varyant']
                    miktar = form.cleaned_data['miktar']
                    aciklama = form.cleaned_data['aciklama']

                    # Stok hareketi oluştur
                    StokHareket.stok_hareketi_olustur(
                        varyant=varyant,
                        hareket_tipi='giris',
                        miktar=miktar,
                        aciklama=aciklama,
                        kullanici=request.user
                    )

                    messages.success(
                        request, f'✅ {varyant.varyasyon_adi} için {miktar} adet stok giriş işlemi başarıyla tamamlandı!')
                    return redirect('urun:stok_giris')

            except Exception as e:
                messages.error(
                    request, f'❌ Stok giriş işlemi sırasında hata: {str(e)}')
    else:
        form = StokGirisForm()

    return render(request, 'urun/stok_giris.html', {'form': form})


@login_required
def stok_cikis_view(request):
    """Stok çıkış işlemi"""
    if request.method == 'POST':
        form = StokCikisForm(request.POST)
        if form.is_valid():
            try:
                with transaction.atomic():
                    varyant = form.cleaned_data['varyant']
                    miktar = form.cleaned_data['miktar']
                    aciklama = form.cleaned_data['aciklama']

                    # Stok yeterlilik kontrolü
                    if varyant.stok_miktari < miktar:
                        messages.error(
                            request, f'❌ Yetersiz stok! {varyant.varyasyon_adi} için mevcut stok: {varyant.stok_miktari} adet')
                        return render(request, 'urun/stok_cikis.html', {'form': form})

                    # Stok hareketi oluştur
                    StokHareket.stok_hareketi_olustur(
                        varyant=varyant,
                        hareket_tipi='cikis',
                        miktar=miktar,
                        aciklama=aciklama,
                        kullanici=request.user
                    )

                    messages.success(
                        request, f'✅ {varyant.varyasyon_adi} için {miktar} adet stok çıkış işlemi başarıyla tamamlandı!')
                    return redirect('urun:stok_cikis')

            except Exception as e:
                messages.error(
                    request, f'❌ Stok çıkış işlemi sırasında hata: {str(e)}')
    else:
        form = StokCikisForm()

    return render(request, 'urun/stok_cikis.html', {'form': form})


@login_required
def stok_duzeltme_view(request):
    """Stok düzeltme işlemi"""
    if request.method == 'POST':
        form = StokDuzeltmeForm(request.POST)
        if form.is_valid():
            try:
                with transaction.atomic():
                    varyant = form.cleaned_data['varyant']
                    yeni_miktar = form.cleaned_data['yeni_miktar']
                    aciklama = form.cleaned_data['aciklama']

                    eski_miktar = varyant.stok_miktari
                    fark = yeni_miktar - eski_miktar

                    if fark == 0:
                        messages.warning(
                            request, f'⚠️ {varyant.varyasyon_adi} için stok miktarı değişmedi.')
                        return render(request, 'urun/stok_duzeltme.html', {'form': form})

                    # Stok hareketi oluştur
                    hareket_tipi = 'duzeltme_artis' if fark > 0 else 'duzeltme_azalis'
                    aciklama_detay = f"{aciklama} (Eski: {eski_miktar}, Yeni: {yeni_miktar}, Fark: {fark:+d})"

                    StokHareket.stok_hareketi_olustur(
                        varyant=varyant,
                        hareket_tipi=hareket_tipi,
                        miktar=abs(fark),
                        aciklama=aciklama_detay,
                        kullanici=request.user
                    )

                    messages.success(
                        request, f'✅ {varyant.varyasyon_adi} için stok düzeltme işlemi başarıyla tamamlandı! (Eski: {eski_miktar}, Yeni: {yeni_miktar})')
                    return redirect('urun:stok_duzeltme')

            except Exception as e:
                messages.error(
                    request, f'❌ Stok düzeltme işlemi sırasında hata: {str(e)}')
    else:
        form = StokDuzeltmeForm()

    return render(request, 'urun/stok_duzeltme.html', {'form': form})


@login_required
def sayim_eksigi_view(request):
    """Sayım eksiği - Stok azaltma işlemi"""
    varyant = None
    arama_yapildi = False

    if request.method == 'POST':
        if 'arama' in request.POST:
            # Arama işlemi
            arama_terimi = request.POST.get('arama_terimi', '').strip()
            arama_yapildi = True

            if arama_terimi:
                try:
                    # Önce barkod ile ara
                    varyant = UrunVaryanti.objects.select_related(
                        'urun').get(barkod=arama_terimi)
                except UrunVaryanti.DoesNotExist:
                    # Sonra ürün adı ile ara
                    varyantlar = UrunVaryanti.objects.select_related('urun', 'renk', 'beden').filter(
                        urun__ad__icontains=arama_terimi
                    )
                    if varyantlar.exists():
                        varyant = varyantlar.first()
                    else:
                        messages.error(
                            request, f'❌ "{arama_terimi}" için ürün bulunamadı!')

        elif 'islem' in request.POST and request.POST.get('varyant_id'):
            # Stok azaltma işlemi
            try:
                with transaction.atomic():
                    varyant = UrunVaryanti.objects.get(
                        id=request.POST.get('varyant_id'))
                    azaltilacak_miktar = int(request.POST.get('miktar', 0))
                    aciklama = request.POST.get('aciklama', '').strip()

                    if azaltilacak_miktar <= 0:
                        messages.error(
                            request, '❌ Azaltılacak miktar 0\'dan büyük olmalıdır!')
                        return redirect('urun:sayim_eksigi')

                    if azaltilacak_miktar > varyant.stok_miktari:
                        messages.error(
                            request, f'❌ Mevcut stoktan ({varyant.stok_miktari} adet) fazla azaltılamaz!')
                        return redirect('urun:sayim_eksigi')

                    if not aciklama:
                        messages.error(request, '❌ Açıklama zorunludur!')
                        return redirect('urun:sayim_eksigi')

                    # Stok hareketi oluştur
                    StokHareket.stok_hareketi_olustur(
                        varyant=varyant,
                        hareket_tipi='sayim_eksik',
                        miktar=azaltilacak_miktar,
                        aciklama=f"Sayım Eksiği: {aciklama}",
                        kullanici=request.user
                    )

                    messages.success(
                        request, f'✅ {varyant.varyasyon_adi} için {azaltilacak_miktar} adet stok azaltıldı!')
                    return redirect('urun:sayim_eksigi')

            except Exception as e:
                messages.error(request, f'❌ İşlem sırasında hata: {str(e)}')

    context = {
        'varyant': varyant,
        'arama_yapildi': arama_yapildi,
        'sayfa_baslik': 'Sayım Eksiği',
        'sayfa_aciklama': 'Barkod veya ürün adı ile arayıp stok azaltın',
        'islem_tipi': 'eksik'
    }
    return render(request, 'urun/sayim_islem.html', context)


@login_required
def sayim_fazlasi_view(request):
    """Sayım fazlası - Stok artırma işlemi"""
    varyant = None
    arama_yapildi = False

    if request.method == 'POST':
        if 'arama' in request.POST:
            # Arama işlemi
            arama_terimi = request.POST.get('arama_terimi', '').strip()
            arama_yapildi = True

            if arama_terimi:
                try:
                    # Önce barkod ile ara
                    varyant = UrunVaryanti.objects.select_related(
                        'urun').get(barkod=arama_terimi)
                except UrunVaryanti.DoesNotExist:
                    # Sonra ürün adı ile ara
                    varyantlar = UrunVaryanti.objects.select_related('urun', 'renk', 'beden').filter(
                        urun__ad__icontains=arama_terimi
                    )
                    if varyantlar.exists():
                        varyant = varyantlar.first()
                    else:
                        messages.error(
                            request, f'❌ "{arama_terimi}" için ürün bulunamadı!')

        elif 'islem' in request.POST and request.POST.get('varyant_id'):
            # Stok artırma işlemi
            try:
                with transaction.atomic():
                    varyant = UrunVaryanti.objects.get(
                        id=request.POST.get('varyant_id'))
                    arttirilacak_miktar = int(request.POST.get('miktar', 0))
                    aciklama = request.POST.get('aciklama', '').strip()

                    if arttirilacak_miktar <= 0:
                        messages.error(
                            request, '❌ Arttırılacak miktar 0\'dan büyük olmalıdır!')
                        return redirect('urun:sayim_fazlasi')

                    if not aciklama:
                        messages.error(request, '❌ Açıklama zorunludur!')
                        return redirect('urun:sayim_fazlasi')

                    # Stok hareketi oluştur
                    StokHareket.stok_hareketi_olustur(
                        varyant=varyant,
                        hareket_tipi='sayim_fazla',
                        miktar=arttirilacak_miktar,
                        aciklama=f"Sayım Fazlası: {aciklama}",
                        kullanici=request.user
                    )

                    messages.success(
                        request, f'✅ {varyant.varyasyon_adi} için {arttirilacak_miktar} adet stok eklendi!')
                    return redirect('urun:sayim_fazlasi')

            except Exception as e:
                messages.error(request, f'❌ İşlem sırasında hata: {str(e)}')

    context = {
        'varyant': varyant,
        'arama_yapildi': arama_yapildi,
        'sayfa_baslik': 'Sayım Fazlası',
        'sayfa_aciklama': 'Barkod veya ürün adı ile arayıp stok ekleyin',
        'islem_tipi': 'fazla'
    }
    return render(request, 'urun/sayim_islem.html', context)


@login_required
def stok_hareket_listesi(request):
    """Stok hareketleri listesi"""
    hareketler = StokHareket.objects.select_related(
        'varyant__urun', 'kullanici'
    ).order_by('-olusturma_tarihi')

    # Filtreleme
    hareket_tipi = request.GET.get('hareket_tipi')
    if hareket_tipi:
        hareketler = hareketler.filter(hareket_tipi=hareket_tipi)

    # Barkod ile filtreleme
    barkod = request.GET.get('barkod', '').strip()
    if barkod:
        hareketler = hareketler.filter(varyant__barkod__icontains=barkod)

    # Ürün adı ile filtreleme (opsiyonel)
    urun_adi = request.GET.get('urun_adi', '').strip()
    if urun_adi:
        hareketler = hareketler.filter(varyant__urun__ad__icontains=urun_adi)

    # Sayfalama
    paginator = Paginator(hareketler, 50)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'hareket_tipi': hareket_tipi,
        'barkod': barkod,
        'urun_adi': urun_adi,
        'hareket_tipleri': StokHareket.HAREKET_TIPLERI,
    }

    return render(request, 'urun/stok_hareket_listesi.html', context)


@login_required
def fiyat_guncelleme(request):
    """Toplu fiyat güncelleme"""
    if request.method == 'POST':
        try:
            guncelleme_tipi = request.POST.get('guncelleme_tipi')
            kategori_id = request.POST.get('kategori')
            marka_id = request.POST.get('marka')

            # Base queryset
            urunler = Urun.objects.filter(aktif=True)

            # Filtreler
            if kategori_id:
                urunler = urunler.filter(kategori_id=kategori_id)

            if marka_id:
                urunler = urunler.filter(marka_id=marka_id)

            updated_count = 0
            barkod_guncellendi = 0

            with transaction.atomic():
                if guncelleme_tipi == 'oran':
                    # Yüzde ile güncelleme
                    oran = Decimal(str(request.POST.get('oran', 0)))
                    if oran != 0:
                        for urun in urunler:
                            eski_fiyat = urun.satis_fiyati
                            if oran > 0:  # Artış
                                urun.satis_fiyati = urun.satis_fiyati * \
                                    (Decimal('1') + oran / Decimal('100'))
                            else:  # Azalış
                                urun.satis_fiyati = urun.satis_fiyati * \
                                    (Decimal('1') + oran / Decimal('100'))
                            urun.save()
                            updated_count += 1

                            # Barkod güncelle
                            # Barkod güncelle
                            for varyant in urun.varyantlari.all():
                                varyant.olustur_barkod()
                                barkod_guncellendi += 1

                elif guncelleme_tipi == 'sabit':
                    # Sabit miktar ile güncelleme
                    miktar = Decimal(str(request.POST.get('miktar', 0)))
                    if miktar != 0:
                        for urun in urunler:
                            yeni_fiyat = urun.satis_fiyati + miktar
                            urun.satis_fiyati = max(Decimal('0'), yeni_fiyat)
                            urun.save()
                            updated_count += 1

                            # Barkod güncelle
                            for varyant in urun.varyantlari.all():
                                varyant.olustur_barkod()
                                barkod_guncellendi += 1

                elif guncelleme_tipi == 'kar_orani':
                    # Kar oranına göre güncelleme
                    yeni_kar_orani = Decimal(
                        str(request.POST.get('kar_orani', 50)))
                    for urun in urunler:
                        if urun.alis_fiyati > 0:
                            urun.kar_orani = yeni_kar_orani
                            urun.satis_fiyati = urun.alis_fiyati * \
                                (Decimal('1') + yeni_kar_orani / Decimal('100'))
                            urun.save()
                            updated_count += 1

                            # Barkod güncelle
                            for varyant in urun.varyantlari.all():
                                varyant.olustur_barkod()
                                barkod_guncellendi += 1

            if barkod_guncellendi > 0:
                messages.success(
                    request, f'✅ {updated_count} ürünün fiyatı güncellendi ve {barkod_guncellendi} varyant barkodu yenilendi!')
            else:
                messages.success(
                    request, f'✅ {updated_count} ürünün fiyatı başarıyla güncellendi!')

        except Exception as e:
            messages.error(
                request, f'❌ Fiyat güncelleme sırasında hata: {str(e)}')

    # Context verileri
    kategoriler = UrunKategoriUst.objects.filter(aktif=True).order_by('ad')
    markalar = Marka.objects.filter(aktif=True).order_by('ad')

    # İstatistikler
    toplam_urun = Urun.objects.filter(aktif=True).count()
    ortalama_fiyat = Urun.objects.filter(aktif=True).aggregate(
        ortalama=Avg('satis_fiyati')
    )['ortalama'] or 0

    context = {
        'kategoriler': kategoriler,
        'markalar': markalar,
        'toplam_urun': toplam_urun,
        'ortalama_fiyat': ortalama_fiyat,
        'title': 'Toplu Fiyat Güncelleme'
    }

    return render(request, 'urun/fiyat_guncelleme.html', context)
