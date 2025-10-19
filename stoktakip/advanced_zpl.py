"""
Gelişmiş ZPL Label Generator
Xprinter XP-470B için optimize edilmiş tasarım
"""

from datetime import datetime
import re

class AdvancedZPLGenerator:
    def __init__(self):
        # 56mm x 40mm etiket boyutu (448 x 320 dots @ 8dots/mm)
        self.width = 448
        self.height = 320
        self.margin = 30
        
    def clean_text(self, text, max_length=None):
        """Text temizleme ve uzunluk sınırı"""
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
        text = text.strip()
        
        # Uzunluk sınırı
        if max_length and len(text) > max_length:
            text = text[:max_length-3] + "..."
            
        return text
        
    def format_price(self, price):
        """Fiyat formatla"""
        try:
            if isinstance(price, str):
                price_clean = re.sub(r'[^\d.,]', '', price)
                price_clean = price_clean.replace(',', '.')
                price_float = float(price_clean)
            else:
                price_float = float(price)
                
            return f"{price_float:.2f} TL"
        except:
            return "0.00 TL"
            
    def generate_optimized_label(self, data):
        """Optimize edilmiş etiket tasarımı"""
        
        # Veri temizleme
        brand = self.clean_text(data.get('brand', 'NUVIA'), 20)
        product_name = self.clean_text(data.get('product_name', 'Urun'), 25)
        price = self.format_price(data.get('price', '0.00'))
        size = self.clean_text(data.get('size', ''), 8)
        barcode = str(data.get('barcode', '1234567890123'))[:13]
        product_code = self.clean_text(data.get('product_code', ''), 15)
        subtitle = self.clean_text(data.get('subtitle', 'Premium Wear'), 30)
        
        # Güncel tarih
        current_date = datetime.now().strftime("%d.%m.%Y")
        
        # ZPL Template - 56mm x 40mm optimize
        zpl = f"""^XA
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

^FO{self.margin},{self.margin}^CF0,28^FD{brand}^FS
^FO{self.margin},65^GB{self.width-60},2,2^FS

^FO{self.margin},85^CF0,16^FD{subtitle}^FS

^FO{self.margin},115^CF0,20^FD{product_name}^FS

^FO{self.margin},155^CF0,18^FDFiyat: {price}^FS
^FO{self.margin + 200},155^CF0,18^FDBeden: {size}^FS

^FO{self.margin + 50},185^BY2,2,40
^BCN,40,Y,N,N
^FD{barcode}^FS

^FO{self.margin},250^CF0,12^FDKod: {product_code}^FS
^FO{self.margin + 200},250^CF0,10^FD{current_date}^FS

^FO{self.margin},275^GB{self.width-60},1,1^FS

^XZ"""
        
        return zpl.strip()
        
    def generate_premium_label(self, data):
        """Premium tasarım - daha şık görünüm"""
        
        brand = self.clean_text(data.get('brand', 'NUVIA'), 15)
        product_name = self.clean_text(data.get('product_name', 'Urun'), 20)
        price = self.format_price(data.get('price', '0.00'))
        size = self.clean_text(data.get('size', ''), 5)
        barcode = str(data.get('barcode', '1234567890123'))[:13]
        product_code = self.clean_text(data.get('product_code', ''), 12)
        
        zpl = f"""^XA
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

^FO{self.margin + 140},25^CF0,30^FD{brand}^FS

^FO{self.margin},55^GB{self.width-60},3,3^FS

^FO{self.margin + 20},75^CF0,18^FD{product_name}^FS

^FO{self.margin + 20},105^CF0,16^FD{price}^FS
^FO{self.margin + 200},105^CF0,16^FD{size}^FS

^FO{self.margin + 30},130^BY2,3,45
^BCN,45,Y,N,N  
^FD{barcode}^FS

^FO{self.margin},200^CF0,11^FD{product_code}^FS
^FO{self.margin + 200},200^CF0,9^FD{datetime.now().strftime("%d/%m/%Y")}^FS

^FO{self.margin},220^GB{self.width-60},1,1^FS
^FO{self.margin},230^GB{self.width-60},1,1^FS

^XZ"""
        
        return zpl.strip()
        
    def test_label(self):
        """Test etiketi"""
        test_data = {
            'brand': 'NUVIA',
            'product_name': 'Premium Test Urun',
            'price': '1299.99',
            'size': 'XL',
            'barcode': '1234567890123',
            'product_code': 'TEST001',
            'subtitle': 'Premium Collection'
        }
        return self.generate_optimized_label(test_data)