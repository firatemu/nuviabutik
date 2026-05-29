"""
Template Tags - Fiyat Gösterimi
Peşin ve Taksitli fiyat gösterimi için özel template tag'ler
"""

from django import template
from decimal import Decimal

register = template.Library()


@register.simple_tag
def fiyat_kutusu(urun):
    """
    Ürün için peşin/taksitli fiyat kutusu oluşturur

    Kullanım:
        {% load fiyat_tags %}
        {% fiyat_kutusu urun %}
    """
    html = f'''
    <div class="fiyat-kutusu" style="border: 1px solid #ddd; border-radius: 8px; padding: 15px; margin: 10px 0; background: #f9f9f9;">
        <div class="pesin" style="margin-bottom: 10px;">
            <span style="color: #666; font-size: 12px;">💵 PEŞİN FİYAT</span>
            <div style="font-size: 24px; font-weight: bold; color: #4CAF50;">
                {urun.pesin_fiyat:.2f}₺
            </div>
        </div>
        
        <div class="taksitli" style="margin-bottom: 10px;">
            <span style="color: #666; font-size: 12px;">💳 TAKSİTLİ FİYAT</span>
            <div style="font-size: 20px; font-weight: bold; color: #FF9800;">
                {urun.taksitli_fiyat:.2f}₺
            </div>
            <span style="color: #999; font-size: 11px;">
                (9 taksit x {(urun.taksitli_fiyat / 9):.2f}₺)
            </span>
        </div>
        
        <div class="tasarruf" style="background: #e3f2fd; padding: 8px; border-radius: 5px; text-align: center;">
            <span style="color: #2196F3; font-size: 13px; font-weight: 500;">
                ⚡ Peşin öde <strong>{urun.fiyat_farki:.2f}₺</strong> kazan!
            </span>
        </div>
    </div>
    '''
    return html


@register.simple_tag
def fiyat_badge(urun, tip='pesin'):
    """
    Basit fiyat badge oluşturur

    Kullanım:
        {% fiyat_badge urun 'pesin' %}
        {% fiyat_badge urun 'taksitli' %}
    """
    if tip == 'pesin':
        return f'<span style="background: #4CAF50; color: white; padding: 5px 10px; border-radius: 5px; font-weight: bold;">{urun.pesin_fiyat:.2f}₺</span>'
    else:
        return f'<span style="background: #FF9800; color: white; padding: 5px 10px; border-radius: 5px; font-weight: bold;">{urun.taksitli_fiyat:.2f}₺</span>'


@register.filter
def pesin_fiyat(urun):
    """
    Ürünün peşin fiyatını döndürür

    Kullanım:
        {{ urun|pesin_fiyat }}
    """
    return f"{urun.pesin_fiyat:.2f}₺"


@register.filter
def taksitli_fiyat(urun):
    """
    Ürünün taksitli fiyatını döndürür

    Kullanım:
        {{ urun|taksitli_fiyat }}
    """
    return f"{urun.taksitli_fiyat:.2f}₺"


@register.filter
def fiyat_farki(urun):
    """
    Fiyat farkını döndürür

    Kullanım:
        {{ urun|fiyat_farki }}
    """
    return f"{urun.fiyat_farki:.2f}₺"


@register.filter
def taksit_hesapla(fiyat, taksit_sayisi=9):
    """
    Taksit başına düşen tutarı hesaplar

    Kullanım:
        {{ urun.taksitli_fiyat|taksit_hesapla:9 }}
    """
    if isinstance(fiyat, (int, float, Decimal)) and fiyat > 0:
        return f"{(fiyat / taksit_sayisi):.2f}₺"
    return "0.00₺"


@register.inclusion_tag('urun/fiyat_karsilastirma.html')
def fiyat_karsilastirma(urun):
    """
    Fiyat karşılaştırma tablosu

    Kullanım:
        {% fiyat_karsilastirma urun %}
    """
    return {
        'urun': urun,
        'pesin': urun.pesin_fiyat,
        'taksitli': urun.taksitli_fiyat,
        'fark': urun.fiyat_farki,
        'fark_yuzde': urun.fiyat_farki_yuzdesi,
    }


@register.simple_tag
def fiyat_secici(urun, form_name='odeme_formu'):
    """
    Ödeme tipi seçici (radio button) oluşturur

    Kullanım:
        {% fiyat_secici urun %}
    """
    html = f'''
    <div class="fiyat-secici" style="border: 1px solid #ddd; border-radius: 8px; overflow: hidden;">
        <!-- Peşin Seçenek -->
        <label class="odeme-secenegi" style="display: block; padding: 15px; cursor: pointer; border-bottom: 1px solid #eee;">
            <input type="radio" name="odeme_tipi" value="pesin" checked 
                   onchange="document.getElementById('secili_fiyat').value='{urun.pesin_fiyat}'"
                   style="margin-right: 10px;">
            <div style="display: inline-block; vertical-align: middle;">
                <div style="font-weight: bold; font-size: 16px; color: #4CAF50;">
                    💵 Peşin: {urun.pesin_fiyat:.2f}₺
                </div>
                <div style="font-size: 12px; color: #666;">
                    Nakit/Havale ile ödeyin
                </div>
            </div>
            <span style="float: right; background: #4CAF50; color: white; padding: 3px 8px; border-radius: 3px; font-size: 11px;">
                %{urun.taksit_orani:.0f} İNDİRİM
            </span>
        </label>
        
        <!-- Taksitli Seçenek -->
        <label class="odeme-secenegi" style="display: block; padding: 15px; cursor: pointer;">
            <input type="radio" name="odeme_tipi" value="taksitli"
                   onchange="document.getElementById('secili_fiyat').value='{urun.taksitli_fiyat}'"
                   style="margin-right: 10px;">
            <div style="display: inline-block; vertical-align: middle;">
                <div style="font-weight: bold; font-size: 16px; color: #FF9800;">
                    💳 Taksitli: {urun.taksitli_fiyat:.2f}₺
                </div>
                <div style="font-size: 12px; color: #666;">
                    9 taksit x {(urun.taksitli_fiyat / 9):.2f}₺
                </div>
            </div>
        </label>
    </div>
    <input type="hidden" id="secili_fiyat" name="secili_fiyat" value="{urun.pesin_fiyat}">
    '''
    return html

