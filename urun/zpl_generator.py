"""
ZPL Label Generator for Xprinter XP-470B
NuviaButik Etiket Sistemi
"""

from datetime import datetime
import re

class ZPLLabelGenerator:
    def __init__(self):
        self.label_width = 448  # 56mm = ~448 dots
        self.label_height = 320  # 40mm = ~320 dots
        
    def clean_text(self, text):
        """ZPL için text temizle"""
        if not text:
            return ""
        # Türkçe karakterleri değiştir
        replacements = {
            'ç': 'c', 'Ç': 'C', 'ğ': 'g', 'Ğ': 'G',
            'ı': 'i', 'İ': 'I', 'ö': 'o', 'Ö': 'O', 
            'ş': 's', 'Ş': 'S', 'ü': 'u', 'Ü': 'U'
        }
        for tr, en in replacements.items():
            text = text.replace(tr, en)
        # Özel karakterleri temizle
        text = re.sub(r'[^\w\s\.-]', '', str(text))
        return text.strip()
        
    def format_price(self, price):
        """Fiyat formatla"""
        try:
            if isinstance(price, str):
                # String'den sayı çıkar
                price_clean = re.sub(r'[^\d.,]', '', price)
                price_clean = price_clean.replace(',', '.')
                price_float = float(price_clean)
            else:
                price_float = float(price)
            return f"{price_float:.2f} TL"
        except:
            return str(price) + " TL"
            
    def generate_product_label(self, product_data):
        """Ürün için ZPL etiketi oluştur"""
        
        # Veri temizleme
        brand = self.clean_text(product_data.get('brand', 'NUVIA'))[:15]
        product_name = self.clean_text(product_data.get('product_name', ''))[:20]
        price = self.format_price(product_data.get('price', '0.00'))
        size = self.clean_text(product_data.get('size', ''))[:5]
        barcode = str(product_data.get('barcode', '1234567890123'))[:13]
        product_code = self.clean_text(product_data.get('product_code', ''))[:15]
        subtitle = self.clean_text(product_data.get('subtitle', 'Premium Wear'))[:25]
        
        # ZPL Template
        zpl_content = f"""^XA
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

^FO50,30^CF0,25^FD{brand}^FS
^FO50,65^CF0,16^FD{subtitle}^FS

^FO50,100^CF0,20^FD{product_name}^FS

^FO50,140^CF0,18^FDFiyat: {price}^FS
^FO250,140^CF0,18^FDBeden: {size}^FS

^FO50,175^BQN,2,4^FDMA,{barcode}^FS

^FO50,260^CF0,14^FDKod: {product_code}^FS
^FO250,260^CF0,12^FD{datetime.now().strftime("%d.%m.%Y %H:%M")}^FS

^FO50,290^GB348,1,1^FS

^XZ"""
        
        return zpl_content.strip()
        
    def generate_variant_label(self, variant_data):
        """Varyant için özel ZPL etiketi"""
        return self.generate_product_label(variant_data)
        
    def test_label(self):
        """Test etiketi oluştur"""
        test_data = {
            'brand': 'NUVIA',
            'product_name': 'Test Urun',
            'price': '1200.00',
            'size': 'XL',
            'barcode': '1234567891023',
            'product_code': 'TEST001',
            'subtitle': 'Premium Test Collection'
        }
        return self.generate_product_label(test_data)