"""
Test etiket uçları — canonical Nuvia ZPL.
"""
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from .tsc_to_zpl_converter import generate_label


@csrf_exempt
def test_label_simple(request):
    """Örnek etiket (varsayılan demo veriler)."""
    return HttpResponse(generate_label(None), content_type='text/plain')


@csrf_exempt
def advanced_test_label(request):
    """Canonical şablon testi."""
    return HttpResponse(generate_label(None), content_type='text/plain')


@csrf_exempt
def premium_test_label(request):
    """Özel demo verilerle test."""
    test_data = {
        'product_code': 'PREM001',
        'pesin_fiyat': '1599.99',
        'taksitli_fiyat': '1899',
        'size': 'L',
        'barcode': '1234567890123',
    }
    return HttpResponse(generate_label(test_data), content_type='text/plain')
