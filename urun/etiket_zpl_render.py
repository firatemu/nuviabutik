"""
Etiket tasarımcısı (tasarim_json.elements) -> ZPL.
"""
import re
from stoktakip.tsc_to_zpl_converter import _zpl_ascii, _price_plain, _barcode_qr_payload


def _strip_zpl_cmd_chars(s):
    return re.sub(r'[\^~\\\r\n\x00-\x1F]', ' ', str(s or '')).strip()[:120]


def _resolve_barcode_value(el, data):
    df = el.get('dataField') or '{barkod}'
    if df == '{urun_kodu}':
        raw = data.get('product_code') or data.get('urun_kodu') or ''
    elif df == '{barkod}':
        raw = data.get('barcode') or data.get('barkod') or ''
    else:
        raw = el.get('content') or data.get('barcode') or ''
    raw = re.sub(r'[^\w]', '', str(raw or ''))
    return raw or '0'


def _resolve_text(el, data):
    df = (el.get('dataField') or '').strip()
    pesin = data.get('pesin_fiyat')
    taksit = data.get('taksitli_fiyat')
    fb = data.get('price')
    if pesin is None and fb is not None:
        pesin = fb
    if taksit is None and fb is not None:
        taksit = fb

    if df == '{urun_kodu}':
        return _zpl_ascii(data.get('product_code') or data.get('urun_kodu'), 20)
    if df == '{beden}':
        return _zpl_ascii(data.get('size') or data.get('beden'), 12)
    if df == '{pesin_fiyat}':
        return _price_plain(pesin, '0')
    if df == '{taksitli_fiyat}':
        return _price_plain(taksit, _price_plain(pesin, '0'))
    if df == '{barkod}':
        return _zpl_ascii(data.get('barcode'), 24)
    if df == '{fiyat}':
        p = _price_plain(pesin, '0')
        return _strip_zpl_cmd_chars(f'{p} TL')
    if df == '{urun_ad}':
        return _zpl_ascii(data.get('product_name') or data.get('urun_ad'), 40)
    if df == '{marka}':
        return _zpl_ascii(data.get('marka'), 20)

    return _zpl_ascii(el.get('content'), 80) or ''


def render_zpl_from_elements(elements, data, canvas_w_mm=54, canvas_h_mm=40):
    """elements: etiket tasarımcısı JSON listesi (type, x,y,width,height mm, ...)."""
    if not elements:
        return None
    data = data or {}
    pw = int(round(float(canvas_w_mm) * 8))
    ll = int(round(float(canvas_h_mm) * 8))

    parts = [
        '^XA~TA000~JSN^LT0^MNW^MTT^PON^PMN^LH0,0^JMA^PR4,4~SD15^JUS^LRN^CI0^XZ',
        '^XA',
        '^MMT',
        f'^PW{pw}',
        f'^LL{ll}',
        '^LS0',
    ]

    for el in elements:
        typ = el.get('type') or el.get('eleman_tipi')
        if not typ:
            continue
        x = max(0, int(round(float(el.get('x', 0)) * 8)))
        y = max(0, int(round(float(el.get('y', 0)) * 8)))

        if typ == 'text':
            txt = _resolve_text(el, data)
            if not txt and not el.get('dataField'):
                continue
            fh = max(18, int(round((float(el.get('fontSize', 12))) * 2)))
            fw = max(16, int(round((float(el.get('fontSize', 12))) * 1.8)))
            safe = _strip_zpl_cmd_chars(txt) or ' '
            parts.append(f'^FT{x},{y}^A0N,{fh},{fw}^FH\\^FD{safe}^FS')

        elif typ == 'barcode_1d':
            raw = _resolve_barcode_value(el, data)
            h = max(40, int(round(float(el.get('barcodeHeight', 20)) * 2)))
            btype = (el.get('barcodeType') or 'CODE128').upper()
            cmd = {'CODE128': 'BC', 'CODE39': 'BA', 'EAN13': 'BE', 'EAN8': 'B8', 'UPCA': 'BU'}.get(btype, 'BC')
            parts.append(f'^FO{x},{y}^{cmd}N,{h},Y,N,N^FD{raw}^FS')

        elif typ == 'barcode_2d':
            raw = _resolve_barcode_value(el, data)
            mod = int(el.get('qrModule') or 5)
            mod = min(10, max(2, mod))
            payload = _barcode_qr_payload(raw if raw != '0' else data.get('barcode'))
            parts.append(f'^FT{x},{y}^BQN,2,{mod}^FH\\^FD{payload}^FS')

        elif typ == 'rectangle':
            w = max(1, int(round(float(el.get('width', 1)) * 8)))
            h = max(1, int(round(float(el.get('height', 1)) * 8)))
            t = max(1, int(round(float(el.get('borderMm', 3)))))
            parts.append(f'^FO{x},{y}^GB{w},{h},{t}^FS')

        elif typ == 'line':
            w = max(1, int(round(float(el.get('width', 1)) * 8)))
            parts.append(f'^FO{x},{y}^GB{w},2,2^FS')

    parts.append('^PQ1,0,1,Y^XZ')
    return '\n'.join(parts) + '\n'
