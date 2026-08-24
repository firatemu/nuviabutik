"""
Etiket Şablon Tasarımcısı Views
Sürükle-bırak etiket tasarım sistemi
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_http_methods
from django.db.models import Q
import json
from datetime import datetime

from .models import EtiketSablonu, EtiketSablonEleman, YaziciAyarlari, Urun, UrunVaryanti


@login_required
def etiket_tasarimci(request):
    """Ana etiket tasarımcı sayfası"""
    sablonlar = EtiketSablonu.objects.filter(
        Q(olusturan=request.user) | Q(varsayilan=True)
    ).order_by('-guncelleme_tarihi')
    
    kategoriler = Urun.objects.values_list('kategori__id', 'kategori__ad').distinct()
    
    # Aktif şablon bilgisi
    aktif_sablon = None
    sablon_id = request.GET.get('sablon')
    if sablon_id:
        try:
            aktif_sablon = EtiketSablonu.objects.get(id=sablon_id)
        except EtiketSablonu.DoesNotExist:
            pass
    
    context = {
        'sablonlar': sablonlar,
        'kategoriler': kategoriler,
        'sayfa_baslik': 'Etiket Şablon Tasarımcısı',
        'aktif_sablon': aktif_sablon,
    }
    return render(request, 'urun/etiket_tasarimci.html', context)


@login_required
def etiket_sablon_liste(request):
    """Şablon listesi sayfası"""
    sablonlar = EtiketSablonu.objects.filter(
        Q(olusturan=request.user) | Q(varsayilan=True)
    ).select_related('kategori', 'olusturan').order_by('-guncelleme_tarihi')
    
    context = {
        'sablonlar': sablonlar,
        'sayfa_baslik': 'Etiket Şablonları',
    }
    return render(request, 'urun/etiket_sablon_liste.html', context)


@login_required
@require_http_methods(["POST"])
def etiket_sablon_kaydet(request):
    """Yeni şablon kaydet veya güncelle"""
    try:
        data = json.loads(request.body)
        
        sablon_id = data.get('id')
        ad = data.get('ad', 'Yeni Şablon')
        genislik_mm = float(data.get('genislik_mm', 54))
        yukseklik_mm = float(data.get('yukseklik_mm', 40))
        kategori_id = data.get('kategori')
        varsayilan = data.get('varsayilan', False)
        tasarim_json = data.get('tasarim_json', {})
        
        if sablon_id:
            # Mevcut şablonu güncelle
            sablon = get_object_or_404(EtiketSablonu, id=sablon_id)
            if sablon.olusturan != request.user and not request.user.is_superuser:
                return JsonResponse({'success': False, 'error': 'Bu şablonu düzenleme yetkiniz yok'}, status=403)
        else:
            # Yeni şablon oluştur
            sablon = EtiketSablonu(olusturan=request.user)
        
        sablon.ad = ad
        sablon.genislik_mm = genislik_mm
        sablon.yukseklik_mm = yukseklik_mm
        sablon.tasarim_json = tasarim_json
        sablon.varsayilan = varsayilan
        
        if kategori_id:
            from .models import UrunKategoriUst
            sablon.kategori_id = kategori_id
        
        sablon.save()
        
        # Varsayılan işaretlenmişse diğerlerini kaldır
        if varsayilan:
            EtiketSablonu.objects.filter(
                kategori=sablon.kategori
            ).exclude(id=sablon.id).update(varsayilan=False)
        
        return JsonResponse({
            'success': True,
            'id': sablon.id,
            'ad': sablon.ad,
            'message': 'Şablon başarıyla kaydedildi'
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
@require_http_methods(["GET"])
def etiket_sablon_getir(request, sablon_id):
    """Şablon detayını getir"""
    try:
        sablon = get_object_or_404(EtiketSablonu, id=sablon_id)
        
        # Yetki kontrolü
        if sablon.olusturan != request.user and not sablon.varsayilan and not request.user.is_superuser:
            return JsonResponse({'error': 'Bu şablonu görüntüleme yetkiniz yok'}, status=403)
        
        # Elemanları getir
        elemanlar = sablon.elemanlar.all().order_by('siralama')
        
        return JsonResponse({
            'id': sablon.id,
            'ad': sablon.ad,
            'genislik_mm': float(sablon.genislik_mm),
            'yukseklik_mm': float(sablon.yukseklik_mm),
            'kategori': sablon.kategori_id,
            'varsayilan': sablon.varsayilan,
            'tasarim_json': sablon.tasarim_json,
            'elemanlar': [
                {
                    'id': e.id,
                    'eleman_tipi': e.eleman_tipi,
                    'pozisyon_x': e.pozisyon_x,
                    'pozisyon_y': e.pozisyon_y,
                    'genislik': e.genislik,
                    'yukseklik': e.yukseklik,
                    'donderece': e.donderece,
                    'icerik': e.icerik,
                    'veri_alan': e.veri_alan,
                    'font_aile': e.font_aile,
                    'font_boyut': e.font_boyut,
                    'font_kalin': e.font_kalin,
                    'font_renk': e.font_renk,
                    'arka_plan_renk': e.arka_plan_renk,
                    'barkod_tipi': e.barkod_tipi,
                    'barkod_yukseklik': e.barkod_yukseklik,
                    'insan_okunabilir': e.insan_okunabilir,
                    'kenarlik_kalinligi': e.kenarlik_kalinligi,
                    'kenarlik_rengi': e.kenarlik_rengi,
                    'dolgu_rengi': e.dolgu_rengi,
                    'kose_yuvarlakligi': e.kose_yuvarlakligi,
                    'gorunum_url': e.gorunum_url,
                    'siralama': e.siralama,
                }
                for e in elemanlar
            ]
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@require_http_methods(["DELETE"])
def etiket_sablon_sil(request, sablon_id):
    """Şablonu sil"""
    try:
        sablon = get_object_or_404(EtiketSablonu, id=sablon_id)
        
        # Yetki kontrolü
        if sablon.olusturan != request.user and not request.user.is_superuser:
            return JsonResponse({'error': 'Bu şablonu silme yetkiniz yok'}, status=403)
        
        # Varsayılan şablon silinemez
        if sablon.varsayilan:
            return JsonResponse({'error': 'Varsayılan şablon silinemez'}, status=400)
        
        sablon.delete()
        
        return JsonResponse({'success': True, 'message': 'Şablon silindi'})
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@require_http_methods(["POST"])
def etiket_eleman_kaydet(request, sablon_id):
    """Şablona eleman ekle veya güncelle"""
    try:
        sablon = get_object_or_404(EtiketSablonu, id=sablon_id)
        data = json.loads(request.body)
        
        eleman_id = data.get('id')
        
        if eleman_id:
            # Mevcut elemanı güncelle
            eleman = get_object_or_404(EtiketSablonEleman, id=eleman_id, sablon=sablon)
        else:
            # Yeni eleman oluştur
            eleman = EtiketSablonEleman(sablon=sablon)
        
        # Eleman özelliklerini güncelle
        eleman.eleman_tipi = data.get('eleman_tipi', 'text')
        eleman.pozisyon_x = data.get('pozisyon_x', 0)
        eleman.pozisyon_y = data.get('pozisyon_y', 0)
        eleman.genislik = data.get('genislik', 50)
        eleman.yukseklik = data.get('yukseklik', 20)
        eleman.donderece = data.get('donderece', 0)
        eleman.icerik = data.get('icerik', '')
        eleman.veri_alan = data.get('veri_alan', '')
        eleman.font_aile = data.get('font_aile', 'Arial')
        eleman.font_boyut = data.get('font_boyut', 12)
        eleman.font_kalin = data.get('font_kalin', False)
        eleman.font_renk = data.get('font_renk', '#000000')
        eleman.arka_plan_renk = data.get('arka_plan_renk', '#FFFFFF')
        eleman.barkod_tipi = data.get('barkod_tipi', 'CODE128')
        eleman.barkod_yukseklik = data.get('barkod_yukseklik', 20)
        eleman.insan_okunabilir = data.get('insan_okunabilir', True)
        eleman.kenarlik_kalinligi = data.get('kenarlik_kalinligi', 1)
        eleman.kenarlik_rengi = data.get('kenarlik_rengi', '#000000')
        eleman.dolgu_rengi = data.get('dolgu_rengi', '#FFFFFF')
        eleman.kose_yuvarlakligi = data.get('kose_yuvarlakligi', 0)
        eleman.gorunum_url = data.get('gorunum_url', '')
        eleman.siralama = data.get('siralama', 0)
        
        eleman.save()
        
        return JsonResponse({
            'success': True,
            'id': eleman.id,
            'message': 'Eleman kaydedildi'
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@require_http_methods(["DELETE"])
def etiket_eleman_sil(request, sablon_id, eleman_id):
    """Şablondan eleman sil"""
    try:
        eleman = get_object_or_404(EtiketSablonEleman, id=eleman_id, sablon_id=sablon_id)
        eleman.delete()
        
        return JsonResponse({'success': True, 'message': 'Eleman silindi'})
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def etiket_onizleme(request, sablon_id):
    """Şablonu önizle"""
    try:
        sablon = get_object_or_404(EtiketSablonu, id=sablon_id)
        urun_id = request.GET.get('urun_id')
        varyant_id = request.GET.get('varyant_id')
        
        # Veri context hazırla
        veri_context = {
            'urun_ad': 'Örnek Ürün Adı',
            'marka': 'Nuvia Original',
            'urun_kodu': '00001',
            'barkod': 'NUV0300SL00001001',
            'beden': 'L',
            'renk': 'Siyah',
            'fiyat': '2.499,00 TL',
            'pesin_fiyat': '2499',
            'taksitli_fiyat': '2624',
            'stok': '10',
            'tarih': datetime.now().strftime('%d.%m.%Y'),
            'sira_no': '001',
            'serbest': '',
        }
        
        # Gerçek ürün/varyant verisi
        if varyant_id:
            try:
                varyant = UrunVaryanti.objects.select_related('urun', 'renk', 'beden').get(id=varyant_id)
                u = varyant.urun

                def _plain_fiyat(val):
                    if not val:
                        return '0'
                    try:
                        f = float(val)
                        return str(int(f)) if f == int(f) else str(f)
                    except (TypeError, ValueError):
                        return str(val)

                pesin_plain = _plain_fiyat(u.pesin_fiyat)
                taks_plain = _plain_fiyat(u.taksitli_fiyat)
                veri_context = {
                    'urun_ad': u.ad,
                    'marka': u.marka.ad if u.marka else '',
                    'urun_kodu': u.urun_kodu or '',
                    'barkod': varyant.barkod,
                    'beden': varyant.beden.ad if varyant.beden else '',
                    'renk': varyant.renk.ad if varyant.renk else '',
                    'fiyat': f"{u.pesin_fiyat:,.2f} TL" if u.pesin_fiyat else '',
                    'pesin_fiyat': pesin_plain,
                    'taksitli_fiyat': taks_plain,
                    'stok': str(varyant.stok_miktari),
                    'tarih': datetime.now().strftime('%d.%m.%Y'),
                    'sira_no': str(varyant.id).zfill(3),
                    'serbest': '',
                }
            except UrunVaryanti.DoesNotExist:
                pass
        elif urun_id:
            try:
                urun = Urun.objects.get(id=urun_id)
                veri_context['urun_ad'] = urun.ad
                veri_context['marka'] = urun.marka.ad if urun.marka else ''
                veri_context['urun_kodu'] = urun.urun_kodu or ''
                veri_context['fiyat'] = f"{urun.pesin_fiyat:,.2f} TL" if urun.pesin_fiyat else ''
                veri_context['pesin_fiyat'] = str(urun.pesin_fiyat) if urun.pesin_fiyat else '0'
                veri_context['taksitli_fiyat'] = str(urun.taksitli_fiyat) if urun.taksitli_fiyat else '0'
            except Urun.DoesNotExist:
                pass
        
        context = {
            'sablon': sablon,
            'veri_context': veri_context,
        }
        return render(request, 'urun/etiket_onizleme.html', context)
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def yazici_ayarlari(request):
    """Yazıcı ayarları sayfası"""
    try:
        ayarlar, created = YaziciAyarlari.objects.get_or_create(
            user=request.user,
            defaults={
                'yazici_ad': 'Xprinter XP-470B',
                'yazici_tipi': 'Xprinter XP-470B',
                'etiket_genislik_mm': 54,
                'etiket_yukseklik_mm': 40,
                'kopya_sayisi': 1,
            }
        )
        
        if request.method == 'POST':
            ayarlar.yazici_ad = request.POST.get('yazici_ad', 'Xprinter XP-470B')
            ayarlar.yazici_tipi = request.POST.get('yazici_tipi', 'Xprinter XP-470B')
            ayarlar.etiket_genislik_mm = float(request.POST.get('etiket_genislik_mm', 54))
            ayarlar.etiket_yukseklik_mm = float(request.POST.get('etiket_yukseklik_mm', 40))
            ayarlar.kopya_sayisi = int(request.POST.get('kopya_sayisi', 1))
            ayarlar.print_agent_token = request.POST.get('print_agent_token', '')
            ayarlar.save()
            messages.success(request, 'Yazıcı ayarları kaydedildi')
            return redirect('urun:yazici_ayarlari')
        
        context = {
            'ayarlar': ayarlar,
            'sayfa_baslik': 'Yazıcı Ayarları',
        }
        return render(request, 'urun/yazici_ayarlari.html', context)
        
    except Exception as e:
        messages.error(request, f'Hata: {str(e)}')
        return redirect('dashboard')


@login_required
@require_http_methods(["GET"])
def urun_verileri_getir(request, urun_id):
    """Ürün verilerini JSON olarak getir"""
    try:
        urun = get_object_or_404(Urun, id=urun_id)
        
        veriler = {
            'urun_id': urun.id,
            'urun_ad': urun.ad,
            'marka': urun.marka.ad if urun.marka else '',
            'urun_kodu': urun.urun_kodu or '',
            'aciklama': urun.aciklama or '',
            'kategori': urun.kategori.ad if urun.kategori else '',
            'cinsiyet': urun.get_cinsiyet_display(),
            'pesin_fiyat': str(urun.pesin_fiyat) if urun.pesin_fiyat else '0',
            'taksitli_fiyat': str(urun.taksitli_fiyat) if urun.taksitli_fiyat else '0',
            'varyantlar': [
                {
                    'varyant_id': v.id,
                    'barkod': v.barkod,
                    'renk': v.renk.ad if v.renk else '',
                    'renk_kod': v.renk.kod if v.renk else '',
                    'beden': v.beden.ad if v.beden else '',
                    'fiyat': f"{v.urun.pesin_fiyat:,.2f} TL" if v.urun.pesin_fiyat else '',
                    'fiyat_sayisal': float(v.urun.pesin_fiyat) if v.urun.pesin_fiyat else 0,
                    'stok': v.stok_miktari,
                }
                for v in urun.varyantlar.filter(aktif=True).select_related('renk', 'beden', 'urun')
            ]
        }
        
        return JsonResponse(veriler)
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@require_http_methods(["GET"])
def varyant_verileri_getir(request, varyant_id):
    """Varyant verilerini JSON olarak getir"""
    try:
        varyant = get_object_or_404(
            UrunVaryanti.objects.select_related('urun', 'renk', 'beden'),
            id=varyant_id
        )
        urun = varyant.urun
        
        veriler = {
            'varyant_id': varyant.id,
            'urun_id': urun.id,
            'urun_ad': urun.ad,
            'marka': urun.marka.ad if urun.marka else '',
            'urun_kodu': urun.urun_kodu or '',
            'barkod': varyant.barkod,
            'renk': varyant.renk.ad if varyant.renk else '',
            'renk_kod': varyant.renk.kod if varyant.renk else '',
            'beden': varyant.beden.ad if varyant.beden else '',
            'fiyat': f"{urun.pesin_fiyat:,.2f} TL" if urun.pesin_fiyat else '',
            'fiyat_sayisal': float(urun.pesin_fiyat) if urun.pesin_fiyat else 0,
            'pesin_fiyat': str(urun.pesin_fiyat) if urun.pesin_fiyat else '0',
            'taksitli_fiyat': str(urun.taksitli_fiyat) if urun.taksitli_fiyat else '0',
            'stok': varyant.stok_miktari,
            'tarih': datetime.now().strftime('%d.%m.%Y'),
            'sira_no': str(varyant.id).zfill(3),
        }
        
        return JsonResponse(veriler)
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
