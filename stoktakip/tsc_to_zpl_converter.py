"""
Nuvia Premium Wear — tek canonical ZPL etiket şablonu (Zebra uyumlu).
"""
import re
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404
from kullanici.decorators import login_required_json
from urun.models import Urun, UrunVaryanti


def varyant_barkod_etiket_icin(varyant):
    """Yazdırma: DB'deki barkod; boşsa olustur_barkod() ile güncel değer."""
    stored = (varyant.barkod or '').strip()
    if stored:
        return stored
    try:
        return varyant.olustur_barkod()
    except Exception:
        ur = varyant.urun
        return f"{ur.id}{varyant.id}".zfill(12)


def _label_barcode_value(data):
    """API/Türkçe anahtar uyumu: barcode veya barkod."""
    data = data or {}
    v = data.get('barcode')
    if v is None or (isinstance(v, str) and not v.strip()):
        v = data.get('barkod')
    return str(v or '').strip()


def _normalize_label_data(data):
    if not data:
        return {}
    out = dict(data)
    if (out.get('barcode') in (None, '') or
            (isinstance(out.get('barcode'), str) and not str(out['barcode']).strip())):
        bk = out.get('barkod')
        if bk is not None and str(bk).strip():
            out['barcode'] = str(bk).strip()
    if not (out.get('product_code') or '').strip() and (out.get('urun_kodu') or '').strip():
        out['product_code'] = str(out['urun_kodu']).strip()
    return out


def _zpl_ascii(text, max_len=None):
    """Türkçe karakterleri ASCII'ye çevir; ^FD alanları için güvenli metin."""
    if text is None:
        text = ''
    s = str(text)
    replacements = {
        'ç': 'c', 'Ç': 'C', 'ğ': 'g', 'Ğ': 'G',
        'ı': 'i', 'İ': 'I', 'ö': 'o', 'Ö': 'O',
        'ş': 's', 'Ş': 'S', 'ü': 'u', 'Ü': 'U',
    }
    for tr, en in replacements.items():
        s = s.replace(tr, en)
    s = re.sub(r'[^\w\s\.\-]', '', s)
    s = re.sub(r'\s+', ' ', s).strip()
    if max_len and len(s) > max_len:
        s = s[:max_len]
    return s if s else '-'


def _price_plain(val, default='0'):
    """Fiyatı etikette gösterilecek düz tam sayı stringine çevir (TL ayrı yazılıyor)."""
    if val is None:
        return default
    s = str(val).replace(' TL', '').replace('TL', '').replace(',', '.').strip()
    try:
        return str(int(float(s)))
    except (TypeError, ValueError):
        return _zpl_ascii(s, 12) or default


def _barcode_qr_payload(barcode):
    """QR ^FD alanı: LA,<barkod> — güvenli karakterler."""
    raw = re.sub(r'[^\w]', '', str(barcode or ''))
    if not raw:
        raw = '0'
    return f'LA,{raw[:48]}'


def _bc128_style_and_digits(data, product_code_display):
    """
    Ofis barkodu >:STIL>RAKAMLAR — etiket Kod satırı product_code ile ayrı olabilir (ör. 0001 + NUV03MB...).
    - barcode 'NUV03MB500558001' ise önek NUV03MB, rakam 500558001
    - yalnızca rakam ise önek product_code_display (veya X)
    - data['barcode_style_code'] / stil_kodu / model_kodu varsa önek zorunlu kabul edilir
    """
    data = data or {}
    raw = _label_barcode_value(data)
    explicit = (
        data.get('barcode_style_code')
        or data.get('stil_kodu')
        or data.get('model_kodu')
    )

    i = len(raw)
    while i > 0 and raw[i - 1].isdigit():
        i -= 1
    alpha_prefix = raw[:i].strip()
    digit_suffix = raw[i:]

    if explicit:
        pc = re.sub(r'[^\dA-Za-z]', '', str(explicit))[:20]
        if digit_suffix.isdigit() and digit_suffix:
            digits = digit_suffix[:20]
        else:
            digits = re.sub(r'[^\d]', '', raw)[:20]
            # stil + tam barkod aynı stringde değilse rakamları hamdan al
            if not digits:
                digits = re.sub(r'[^\d]', '', str(data.get('barcode_numeric') or ''))[:20]
    elif alpha_prefix and digit_suffix.isdigit():
        pc = re.sub(r'[^\dA-Za-z]', '', alpha_prefix)[:20]
        digits = digit_suffix[:20]
    else:
        pc = re.sub(r'[^\dA-Za-z]', '', str(product_code_display or ''))[:20]
        digits = re.sub(r'[^\d]', '', raw)[:20]

    if not pc:
        pc = 'X'
    if not digits:
        digits = '0'
    return pc, digits


def _bc128_fd_line(data, product_code_display):
    """
    Code 128 ^FD: varsayılan tek blok >:TAMBARKOD^FS (NUV03MB00558001 birebir, ara > yok).
    İki parça >:sol>sağ yalnızca barcode_style_code / stil_kodu / model_kodu verilirse.
    """
    data = data or {}
    explicit = (
        data.get('barcode_style_code')
        or data.get('stil_kodu')
        or data.get('model_kodu')
    )
    if explicit:
        pc, digits = _bc128_style_and_digits(data, product_code_display)
        return f'^FD>:{pc}>{digits}^FS'

    raw = _label_barcode_value(data)
    if not raw:
        raw = str(product_code_display or '0')
    safe = re.sub(r'[^\dA-Za-z]', '', str(raw))[:48]
    if not safe:
        safe = '0'
    return f'^FD>:{safe}^FS'


def _digits_last8_for_qr(digits_str):
    """Ofis QR kuralı: rakam bloğunun son 8 hanesi (ör. 500558001 → 00558001)."""
    d = re.sub(r'\D', '', str(digits_str or ''))
    if not d:
        d = '0'
    if len(d) >= 8:
        return d[-8:]
    return d.rjust(8, '0')


def _barcode_plain_for_qr(data, product_code_display):
    """
    QR ^FD içeriği (LA, ön eki _barcode_qr_payload ile eklenir).
    Stil+rakam barkotta: stil + rakamın son 8 hanesi (Code128 >:STIL>RAKAM ile uyumlu).
    Aksi halde tek blok alfanumerik barkod.
    """
    data = data or {}
    raw = _label_barcode_value(data) or ''

    i = len(raw)
    while i > 0 and raw[i - 1].isdigit():
        i -= 1
    alpha_prefix = raw[:i].strip()
    digit_suffix = raw[i:]

    explicit = (
        data.get('barcode_style_code')
        or data.get('stil_kodu')
        or data.get('model_kodu')
    )

    if alpha_prefix and digit_suffix.isdigit():
        pc_qr = re.sub(r'[^\dA-Za-z]', '', alpha_prefix)[:20] or 'X'
        return f'{pc_qr}{_digits_last8_for_qr(digit_suffix)}'[:48]

    if explicit:
        pc, digits = _bc128_style_and_digits(data, product_code_display)
        return f'{pc}{_digits_last8_for_qr(digits)}'[:48]

    if raw:
        return re.sub(r'[^\dA-Za-z]', '', str(raw))[:48]
    return re.sub(r'[^\dA-Za-z]', '', str(product_code_display or '0'))[:48]


def build_nuvia_exact_zpl(data):
    """
    Ofis / Zebra tasarımı ile birebir aynı ZPL (dinamik: beden, kod, fiyatlar, barkod).
    İlk satır: yazıcı köprü başlığı (\\x10 CT~~...).
    """
    data = _normalize_label_data(data or {})
    product_code = _zpl_ascii(data.get('product_code', '0001'), 20)
    size = _zpl_ascii(data.get('size', 'XXL'), 12)

    pesin = data.get('pesin_fiyat')
    taksit = data.get('taksitli_fiyat')
    fb = data.get('price')
    if pesin is None and fb is not None:
        pesin = fb
    if taksit is None and fb is not None:
        taksit = fb
    pesin_s = _price_plain(pesin, '0')
    taksit_s = _price_plain(taksit, pesin_s)
    bc_line = _bc128_fd_line(data, product_code)
    qr_fd = _barcode_qr_payload(_barcode_plain_for_qr(data, product_code))

    prefix = '\x10CT~~CD,~CC^~CT~\n'
    zpl = f"""^XA~TA000~JSN^LT0^MNW^MTT^PON^PMN^LH0,0^JMA^PR4,4~SD15^JUS^LRN^CI0^XZ
^XA
^MMT
^PW432
^LL0320
^LS0
^FT135,71^A0N,66,64^FH\\^FDNUVIA^FS
^FT19,98^A0N,28,28^FH\\^FDPREMIUM WEAR MAN & WOMAN^FS
^FT30,185^A0N,25,24^FH\\^FDBeden^FS
^FT102,185^A0N,25,24^FH\\^FD{size}^FS
^FT242,145^A0N,25,24^FH\\^FDPesin^FS
^FT324,145^A0N,25,24^FH\\^FD{pesin_s}^FS
^FT386,145^A0N,25,24^FH\\^FDTL^FS
^FT97,145^A0N,25,24^FH\\^FD{product_code}^FS
^FT30,145^A0N,25,24^FH\\^FDKod^FS
^FT242,185^A0N,25,24^FH\\^FDTaksitli^FS
^FT324,185^A0N,25,24^FH\\^FD{taksit_s}^FS
^FT386,185^A0N,25,24^FH\\^FDTL^FS
^FO21,104^GB394,98,3^FS
^BY1,3,76^FT23,289^BCN,,Y,N
{bc_line}
^FT326,293^BQN,2,4
^FH\\^FD{qr_fd}^FS
^PQ1,0,1,Y^XZ
"""
    return prefix + zpl


def generate_label(data=None):
    """
    - 'Nuvia Premium Wear' + tasarim_json.zpl_engine == 'exact': Ofis ZPL (birebir).
    - Aksi halde tasarim_json.elements ile ZPL (tasarımcı kaynaklı).
    - Şablon yoksa: build_nuvia_exact_zpl yedek.
    """
    data = _normalize_label_data(data or {})

    try:
        from urun.models import EtiketSablonu
        from urun.etiket_zpl_render import render_zpl_from_elements

        sablon = EtiketSablonu.objects.filter(ad='Nuvia Premium Wear').first()
        if not sablon:
            for s in EtiketSablonu.objects.filter(varsayilan=True).order_by('-id'):
                if s.tasarim_json and s.tasarim_json.get('elements'):
                    sablon = s
                    break
        if sablon:
            tj = sablon.tasarim_json or {}
            if sablon.ad == 'Nuvia Premium Wear' and tj.get('zpl_engine') == 'exact':
                return build_nuvia_exact_zpl(data)
            els = tj.get('elements')
            if els:
                z = render_zpl_from_elements(
                    els,
                    data,
                    float(sablon.genislik_mm),
                    float(sablon.yukseklik_mm),
                )
                if z:
                    return z
    except Exception:
        pass

    return build_nuvia_exact_zpl(data)


@login_required_json
def tsc_design_as_zpl(request):
    """Etiket tasarımını ZPL formatında döndür"""

    test_data = {
        'product_code': '0001',
        'pesin_fiyat': '1200',
        'taksitli_fiyat': '1400',
        'barcode': '123456789012',
        'size': 'XXL',
    }

    zpl_content = generate_label(test_data)
    return HttpResponse(zpl_content, content_type='text/plain')


@login_required_json
def tsc_design_dynamic_zpl(request):
    """Dinamik verilerle etiket tasarımını ZPL formatında döndür"""

    test_data = {
        'product_code': '0002',
        'pesin_fiyat': '1299.99',
        'taksitli_fiyat': '1499',
        'barcode': '1234567891023',
        'size': 'XL',
    }

    zpl_content = generate_label(test_data)
    return HttpResponse(zpl_content, content_type='text/plain')


@login_required_json
def urun_etiket_zpl(request, urun_id):
    """Ürün için tüm varyantların etiketlerini ZPL döndür"""
    try:
        urun = get_object_or_404(Urun, id=urun_id)

        all_zpl_content = []

        if urun.varyasyonlu:
            varyantlar = urun.varyantlar.filter(aktif=True)

            if not varyantlar.exists():
                varyantlar = urun.varyantlar.all()

            if not varyantlar.exists():
                data = {
                    'product_code': urun.urun_kodu or str(urun.id),
                    'pesin_fiyat': str(urun.pesin_fiyat),
                    'taksitli_fiyat': str(urun.taksitli_fiyat),
                    'size': 'Genel',
                    'barcode': getattr(urun, 'barkod', None) or str(urun.id).zfill(12),
                }
                all_zpl_content.append(generate_label(data))
            else:
                for varyant in varyantlar:
                    data = {
                        'product_code': urun.urun_kodu or str(urun.id),
                        'pesin_fiyat': str(urun.pesin_fiyat),
                        'taksitli_fiyat': str(urun.taksitli_fiyat),
                        'size': varyant.beden.ad if varyant.beden else 'Genel',
                        'barcode': varyant_barkod_etiket_icin(varyant),
                    }
                    all_zpl_content.append(generate_label(data))
        else:
            data = {
                'product_code': urun.urun_kodu or str(urun.id),
                'pesin_fiyat': str(urun.pesin_fiyat),
                'taksitli_fiyat': str(urun.taksitli_fiyat),
                'size': 'Genel',
                'barcode': getattr(urun, 'barkod', None) or str(urun.id).zfill(12),
            }
            all_zpl_content.append(generate_label(data))

        combined_zpl = '\n'.join(all_zpl_content)
        return HttpResponse(combined_zpl, content_type='text/plain')

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required_json
def varyant_etiket_zpl(request, varyant_id):
    """Ürün varyantı için etiket ZPL döndür"""
    try:
        varyant = get_object_or_404(UrunVaryanti, id=varyant_id)
        urun = varyant.urun

        data = {
            'product_code': urun.urun_kodu or str(urun.id),
            'pesin_fiyat': str(urun.pesin_fiyat),
            'taksitli_fiyat': str(urun.taksitli_fiyat),
            'size': varyant.beden.ad if varyant.beden else 'Genel',
            'barcode': varyant_barkod_etiket_icin(varyant),
        }

        zpl_content = generate_label(data)
        return HttpResponse(zpl_content, content_type='text/plain')

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
