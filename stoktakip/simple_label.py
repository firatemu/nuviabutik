"""
Simple Label API for immediate testing
"""
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from .advanced_zpl import AdvancedZPLGenerator

@csrf_exempt
def test_label_simple(request):
    """Improved ZPL test label with better design"""
    zpl_content = """^XA
~TA000
~JSN
^LT0
^MNW
^MTD
^PON
^PMN
^LH0,0
^JMA
^PR4,4
~SD15
^JUS
^LRN
^CI27
^PA0,1,1,0

^FO30,30^CF0,28^FDNUVIA BUTIK^FS
^FO30,65^GB380,2,2^FS

^FO30,85^CF0,18^FDPremium Wear Collection^FS

^FO30,125^CF0,22^FDTest Urun Adi^FS

^FO30,165^CF0,20^FDFiyat: 1200.00 TL^FS
^FO250,165^CF0,20^FDBeden: XL^FS

^FO30,200^BY2,2,50
^BCN,50,Y,N,N
^FD1234567890123^FS

^FO30,270^CF0,14^FDKod: TEST001^FS
^FO250,270^CF0,12^FD24.09.2025^FS

^FO30,295^GB380,1,1^FS

^XZ"""
    
    return HttpResponse(zpl_content, content_type='text/plain')

@csrf_exempt  
def advanced_test_label(request):
    """Advanced ZPL generator test"""
    generator = AdvancedZPLGenerator()
    zpl_content = generator.test_label()
    return HttpResponse(zpl_content, content_type='text/plain')

@csrf_exempt
def premium_test_label(request):
    """Premium design test"""
    generator = AdvancedZPLGenerator()
    test_data = {
        'brand': 'NUVIA',
        'product_name': 'Premium Koleksiyon',
        'price': '1599.99',
        'size': 'L', 
        'barcode': '1234567890123',
        'product_code': 'PREM001',
        'subtitle': 'Luxury Collection'
    }
    zpl_content = generator.generate_premium_label(test_data)
    return HttpResponse(zpl_content, content_type='text/plain')