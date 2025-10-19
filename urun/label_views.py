"""
Django Views for Label API
ZPL Etiket API Endpoints
"""

from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import json

from .models import Urun, UrunVaryanti
# ZPL Generator - Çalışan format kullan
from stoktakip.tsc_to_zpl_converter import generate_label

@csrf_exempt
@require_http_methods(["GET"])
def get_label_api(request, urun_id):
    """
    Ürün ID'sine göre ZPL etiketi döndür
    URL: /urun/api/getlabel/<id>/
    """
    try:
        # Ürünü bul
        urun = get_object_or_404(Urun, id=urun_id)
        
        # İlk varyantı al (varsa)
        varyant = urun.urunvaryanti_set.first()
        
        # Etiket verisini hazırla (çalışan format için)
        label_data = {
            'brand': 'NUVIA',  # Sabit
            'subtitle': 'PREMIUM WEAR MAN & WOMAN',  # Sabit
            'price': str(urun.satis_fiyati) if urun.satis_fiyati else '0.00',
            'size': varyant.beden.ad if varyant and varyant.beden else 'Genel',
            'barcode': varyant.barkod if varyant and varyant.barkod else str(urun.id).zfill(13),
            'product_code': urun.urun_kodu or str(urun.id)
        }
        
        # ZPL generator - çalışan format
        zpl_content = generate_label(label_data)
        
        # Content-Type: text/plain (RAW format)
        response = HttpResponse(zpl_content, content_type='text/plain; charset=utf-8')
        response['Content-Disposition'] = f'attachment; filename="label_{urun_id}.prn"'
        
        return response
        
    except Exception as e:
        return JsonResponse({
            'error': f'Label generation failed: {str(e)}',
            'success': False
        }, status=500)

@csrf_exempt  
@require_http_methods(["GET"])
def get_variant_label_api(request, variant_id):
    """
    Varyant ID'sine göre ZPL etiketi döndür
    URL: /urun/api/getlabel/variant/<id>/
    """
    try:
        # Varyantı bul
        varyant = get_object_or_404(UrunVaryanti, id=variant_id)
        urun = varyant.urun
        
        # Etiket verisini hazırla (çalışan format için)
        label_data = {
            'brand': 'NUVIA',  # Sabit
            'subtitle': 'PREMIUM WEAR MAN & WOMAN',  # Sabit
            'price': str(urun.satis_fiyati) if urun.satis_fiyati else '0.00',
            'size': varyant.beden.ad if varyant.beden else 'Genel',
            'barcode': varyant.barkod or f"{urun.id}{varyant.id}",
            'product_code': urun.urun_kodu or str(urun.id)
        }
        
        # ZPL generator - çalışan format
        zpl_content = generate_label(label_data)
        
        # Content-Type: text/plain (RAW format)
        response = HttpResponse(zpl_content, content_type='text/plain; charset=utf-8')
        response['Content-Disposition'] = f'attachment; filename="variant_label_{variant_id}.prn"'
        
        return response
        
    except Exception as e:
        return JsonResponse({
            'error': f'Variant label generation failed: {str(e)}',
            'success': False
        }, status=500)

@csrf_exempt
@require_http_methods(["GET"])  
def test_label_api(request):
    """
    Test etiketi döndür
    URL: /urun/api/getlabel/test/
    """
    try:
        # Test verileri
        test_data = {
            'brand': 'NUVIA',
            'subtitle': 'PREMIUM WEAR MAN & WOMAN',
            'price': '999.99',
            'size': 'L',
            'barcode': '1234567890123',
            'product_code': 'TEST001'
        }
        zpl_content = generate_label(test_data)
        
        response = HttpResponse(zpl_content, content_type='text/plain; charset=utf-8')
        response['Content-Disposition'] = 'attachment; filename="test_label.prn"'
        
        return response
        
    except Exception as e:
        return JsonResponse({
            'error': f'Test label generation failed: {str(e)}',
            'success': False
        }, status=500)