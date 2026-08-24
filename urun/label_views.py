"""
Django Views for Label API
ZPL Etiket API Endpoints
"""

from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_http_methods

from kullanici.decorators import login_required_json

from .models import Urun, UrunVaryanti
from stoktakip.tsc_to_zpl_converter import generate_label, varyant_barkod_etiket_icin


@login_required_json
@require_http_methods(["GET", "POST"])
def get_label_api(request, urun_id):
    """
    Ürün ID'sine göre ZPL etiketi döndür
    URL: /urun/api/getlabel/<id>/
    """
    try:
        urun = get_object_or_404(Urun, id=urun_id)
        varyant = urun.varyantlar.first()

        pesin = str(urun.pesin_fiyat) if urun.pesin_fiyat is not None else str(urun.satis_fiyati or 0)
        taksit = str(urun.taksitli_fiyat) if urun.taksitli_fiyat is not None else pesin
        bc = (
            varyant_barkod_etiket_icin(varyant)
            if varyant
            else str(urun.id).zfill(12)
        )
        label_data = {
            'pesin_fiyat': pesin,
            'taksitli_fiyat': taksit,
            'size': varyant.beden.ad if varyant and varyant.beden else 'Genel',
            'barcode': bc,
            'product_code': urun.urun_kodu or str(urun.id),
        }

        zpl_content = generate_label(label_data)

        if request.method == 'POST':
            return JsonResponse({'success': True, 'zpl': zpl_content})

        response = HttpResponse(zpl_content, content_type='text/plain; charset=utf-8')
        response['Content-Disposition'] = f'attachment; filename="label_{urun_id}.prn"'
        return response

    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Label generation failed: {str(e)}',
        }, status=500)


@login_required_json
@require_http_methods(["GET", "POST"])
def get_variant_label_api(request, variant_id):
    """Varyant ID'sine göre ZPL etiketi döndür"""
    try:
        varyant = get_object_or_404(UrunVaryanti, id=variant_id)
        urun = varyant.urun

        pesin = str(urun.pesin_fiyat) if urun.pesin_fiyat is not None else str(urun.satis_fiyati or 0)
        taksit = str(urun.taksitli_fiyat) if urun.taksitli_fiyat is not None else pesin
        label_data = {
            'pesin_fiyat': pesin,
            'taksitli_fiyat': taksit,
            'size': varyant.beden.ad if varyant.beden else 'Genel',
            'barcode': varyant_barkod_etiket_icin(varyant),
            'product_code': urun.urun_kodu or str(urun.id),
        }

        zpl_content = generate_label(label_data)

        if request.method == 'POST':
            return JsonResponse({'success': True, 'zpl': zpl_content})

        response = HttpResponse(zpl_content, content_type='text/plain; charset=utf-8')
        response['Content-Disposition'] = f'attachment; filename="variant_label_{variant_id}.prn"'
        return response

    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Variant label generation failed: {str(e)}',
        }, status=500)


@login_required_json
@require_http_methods(["GET", "POST"])
def test_label_api(request):
    """Test etiketi döndür"""
    try:
        test_data = {
            'product_code': 'TEST001',
            'pesin_fiyat': '999',
            'taksitli_fiyat': '1199',
            'size': 'L',
            'barcode': '1234567890123',
        }
        zpl_content = generate_label(test_data)

        if request.method == 'POST':
            return JsonResponse({'success': True, 'zpl': zpl_content})

        response = HttpResponse(zpl_content, content_type='text/plain; charset=utf-8')
        response['Content-Disposition'] = 'attachment; filename="test_label.prn"'
        return response

    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Test label generation failed: {str(e)}',
        }, status=500)


@login_required_json
def qztray_varyant_etiket(request, varyant_id):
    """QZ Tray için varyant etiketi JSON API'si."""
    try:
        varyant = get_object_or_404(UrunVaryanti, id=varyant_id)
        urun = varyant.urun

        data = {
            'product_code': urun.urun_kodu or str(urun.id),
            'pesin_fiyat': str(urun.pesin_fiyat) if urun.pesin_fiyat is not None else str(urun.satis_fiyati or 0),
            'taksitli_fiyat': str(urun.taksitli_fiyat) if urun.taksitli_fiyat is not None else str(urun.satis_fiyati or 0),
            'size': varyant.beden.ad if varyant.beden else 'Genel',
            'barcode': varyant_barkod_etiket_icin(varyant),
        }

        zpl_data = generate_label(data)

        return JsonResponse({
            'success': True,
            'zpl_data': zpl_data,
            'message': f'{varyant.varyasyon_adi} etiketi hazırlandı.',
        })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Etiket oluşturulamadı: {str(e)}',
        }, status=500)


@login_required_json
def qztray_urun_toplu_etiket(request, urun_id):
    """QZ Tray için tüm varyantların toplu etiket JSON API'si."""
    try:
        urun = get_object_or_404(Urun, id=urun_id)
        varyantlar = urun.varyantlar.filter(aktif=True).select_related('beden', 'renk')

        if not varyantlar.exists():
            varyantlar = urun.varyantlar.all().select_related('beden', 'renk')

        etiket_listesi = []

        if varyantlar.exists():
            for varyant in varyantlar:
                data = {
                    'product_code': urun.urun_kodu or str(urun.id),
                    'pesin_fiyat': str(urun.pesin_fiyat) if urun.pesin_fiyat is not None else str(urun.satis_fiyati or 0),
                    'taksitli_fiyat': str(urun.taksitli_fiyat) if urun.taksitli_fiyat is not None else str(urun.satis_fiyati or 0),
                    'size': varyant.beden.ad if varyant.beden else 'Genel',
                    'barcode': varyant_barkod_etiket_icin(varyant),
                }
                zpl_data = generate_label(data)
                etiket_listesi.append({
                    'varyant_id': varyant.id,
                    'varyant_adi': varyant.varyasyon_adi,
                    'zpl_data': zpl_data,
                })
        else:
            data = {
                'product_code': urun.urun_kodu or str(urun.id),
                'pesin_fiyat': str(urun.pesin_fiyat) if urun.pesin_fiyat is not None else str(urun.satis_fiyati or 0),
                'taksitli_fiyat': str(urun.taksitli_fiyat) if urun.taksitli_fiyat is not None else str(urun.satis_fiyati or 0),
                'size': 'Genel',
                'barcode': str(urun.id).zfill(12),
            }
            zpl_data = generate_label(data)
            etiket_listesi.append({
                'varyant_id': None,
                'varyant_adi': urun.ad,
                'zpl_data': zpl_data,
            })

        return JsonResponse({
            'success': True,
            'etiket_listesi': etiket_listesi,
            'toplam_etiket': len(etiket_listesi),
            'message': f'{len(etiket_listesi)} etiket hazırlandı.',
        })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Toplu etiket oluşturulamadı: {str(e)}',
        }, status=500)
