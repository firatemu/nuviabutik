"""
TSC Design - Etiket tasarımı
"""
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from urun.models import Urun, UrunVaryanti

def generate_label(data=None):
    """Print agent ile uyumlu ZPL generator"""
    
    # Print agent formatında veriler
    brand = data.get('brand', 'NUVIA') if data else 'NUVIA'
    product_code = data.get('product_code', '00001') if data else '00001'
    product_name = data.get('product_name', 'PREMIUM WEAR') if data else 'PREMIUM WEAR'
    size = data.get('size', 'XXL') if data else 'XXL'
    price = data.get('price', '1200') if data else '1200'
    color = data.get('color', 'Kırmızı') if data else 'Kırmızı'
    barcode = data.get('barcode', '123456789012') if data else '123456789012'
    
    # Fiyat formatını düzenle (TL kısmını kaldır)
    price_clean = str(price).replace(" TL", "").replace("TL", "").strip()
    
    return f"""CT~~CD,~CC^~CT~
^XA~TA000~JSN^LT0^MNW^MTT^PON^PMN^LH0,0^JMA^PR2,2~SD4^JUS^LRN^CI0^XZ
^XA
^MMT
^PW432
^LL0320
^LS0
^FT128,75^A0N,66,64^FH\^FDNUVIA^FS
^FT16,100^A0N,28,28^FH\^FDPREMIUM WEAR MAN & WOMAN^FS
^FT204,255^A0N,25,24^FH\^FDBeden:^FS
^FT281,255^A0N,25,24^FH\^FD{size}^FS
^FT204,286^A0N,25,24^FH\^FDFiyat:^FS
^FT275,288^A0N,25,24^FH\^FD{price_clean}^FS
^FT360,289^A0N,25,24^FH\^FDTL^FS
^FT204,154^A0N,25,24^FH\^FD{product_code}^FS
^FT204,189^A0N,25,24^FH\^FD{brand}^FS
^FT204,224^A0N,25,24^FH\^FDRenk:^FS
^FT272,224^A0N,25,24^FH\^FD{color}^FS
^FT24,296^BQN,2,8
^FH\^FDLA,{barcode}^FS
^PQ1,0,1,Y^XZ"""

@csrf_exempt
def tsc_design_as_zpl(request):
    """Etiket tasarımını ZPL formatında döndür"""
    
    # Test verileri
    test_data = {
        'brand': 'ADIDAS',
        'product_code': '00001',
        'product_name': 'PREMIUM WEAR',
        'price': '1299.99',
        'barcode': '1234567891023',
        'size': 'XXL',
        'color': 'Kırmızı'
    }
    
    zpl_content = generate_label(test_data)
    return HttpResponse(zpl_content, content_type='text/plain')

@csrf_exempt  
def tsc_design_dynamic_zpl(request):
    """Dinamik verilerle etiket tasarımını ZPL formatında döndür"""
    
    # Dinamik test verileri
    test_data = {
        'brand': 'NUVIA',
        'product_code': '00002',
        'product_name': 'PREMIUM WEAR',
        'price': '1299.99',
        'barcode': '1234567891023',
        'size': 'XXL',
        'color': 'Mavi'
    }
    
    zpl_content = generate_label(test_data)
    return HttpResponse(zpl_content, content_type='text/plain')

@csrf_exempt
def urun_etiket_zpl(request, urun_id):
    """Ürün için tüm varyantların etiketlerini ZPL döndür"""
    try:
        urun = get_object_or_404(Urun, id=urun_id)
        
        all_zpl_content = []
        
        # Varyasyonlu ürün kontrolü
        if urun.varyasyonlu:
            varyantlar = urun.varyantlar.filter(aktif=True)
            
            # Aktif varyant yoksa, tüm varyantlara bak
            if not varyantlar.exists():
                varyantlar = urun.varyantlar.all()
            
            # Hiç varyant yoksa varyasyonsuz olarak işle
            if not varyantlar.exists():
                print(f"Warning: Product {urun_id} is marked as variant but has no variants, treating as non-variant")
                # Varyasyonsuz ürün olarak işle
                data = {
                    'brand': urun.marka.ad if urun.marka else 'NUVIA',
                    'product_code': urun.urun_kodu or '00001',
                    'product_name': urun.ad,
                    'price': str(urun.satis_fiyati),
                    'size': 'Genel',
                    'color': 'Kırmızı',
                    'barcode': urun.barkod if hasattr(urun, 'barkod') else str(urun.id).zfill(12),
                    'variant_name': ''
                }
                zpl_content = generate_label(data)
                all_zpl_content.append(zpl_content)
            else:
                # Tüm varyantlar için etiket oluştur
                for varyant in varyantlar:
                    data = {
                        'brand': urun.marka.ad if urun.marka else 'NUVIA',
                        'product_code': urun.urun_kodu or '00001',
                        'product_name': urun.ad,
                        'price': str(urun.satis_fiyati),
                        'size': varyant.beden.ad if varyant.beden else 'Genel',
                        'color': varyant.renk.ad if varyant.renk else 'Kırmızı',
                        'barcode': varyant.barkod or f"{urun.id}{varyant.id}".zfill(12),
                        'variant_name': f"{varyant.beden.ad if varyant.beden else ''} {varyant.renk.ad if varyant.renk else ''}".strip()
                    }
                    zpl_content = generate_label(data)
                    all_zpl_content.append(zpl_content)
        else:
            # Varyasyonsuz ürün
            data = {
                'brand': urun.marka.ad if urun.marka else 'NUVIA',
                'product_code': urun.urun_kodu or '00001',
                'product_name': urun.ad,
                'price': str(urun.satis_fiyati),
                'size': 'Genel',
                'color': 'Kırmızı',
                'barcode': urun.barkod if hasattr(urun, 'barkod') else str(urun.id).zfill(12),
                'variant_name': ''
            }
            zpl_content = generate_label(data)
            all_zpl_content.append(zpl_content)
        
        # Tüm ZPL kodlarını birleştir
        combined_zpl = '\n'.join(all_zpl_content)
        return HttpResponse(combined_zpl, content_type='text/plain')
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
def varyant_etiket_zpl(request, varyant_id):
    """Ürün varyantı için etiket ZPL döndür"""
    try:
        varyant = get_object_or_404(UrunVaryanti, id=varyant_id)
        
        data = {
            'brand': varyant.urun.marka.ad if varyant.urun.marka else 'NUVIA',  # Marka bilgisi
            'product_code': varyant.urun.urun_kodu or '00001',  # Ürün kodu
            'product_name': varyant.urun.ad,  # Ürün adı
            'price': str(varyant.urun.satis_fiyati),
            'size': varyant.beden.ad if varyant.beden else 'Genel',
            'color': varyant.renk.ad if varyant.renk else 'Kırmızı',
            'barcode': varyant.barkod or f"{varyant.urun.id}{varyant.id}".zfill(12),
            'variant_name': f"{varyant.beden.ad if varyant.beden else ''} {varyant.renk.ad if varyant.renk else ''}".strip()
        }
        
        zpl_content = generate_label(data)
        return HttpResponse(zpl_content, content_type='text/plain')
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
