import json
from decimal import Decimal
from datetime import datetime

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse, JsonResponse
from django.views.decorators.http import require_POST, require_GET
from django.views.decorators.csrf import ensure_csrf_cookie
from django.db import transaction
from django.db.models import Q, Value, F
from django.db.models.functions import Lower, Replace
from django.core.paginator import Paginator
from django.utils import timezone

from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
from openpyxl.utils import get_column_letter

from kullanici.decorators import login_required_json
from .models import Urun, UrunVaryanti, StokHareket, StokSayimi, StokSayimiDetay


# ==============================================================================
# 1. SAYIM EKRANI ANA VİEW
# ==============================================================================

@ensure_csrf_cookie
@login_required
def sayim_ekrani_view(request):
    """
    Satış Ekranı mimarisinde, barkod ve ürün arama destekli kurumsal Stok Sayım Ekranı.
    """
    sayim_id = request.GET.get('sayim_id')
    aktif_sayim = None
    initial_items = []

    if sayim_id:
        try:
            aktif_sayim = StokSayimi.objects.prefetch_related(
                'detaylar__varyant__urun__kategori',
                'detaylar__varyant__renk',
                'detaylar__varyant__beden'
            ).get(id=sayim_id, durum='taslak')
            for d in aktif_sayim.detaylar.all():
                v = d.varyant
                u = v.urun
                initial_items.append({
                    'id': u.id,
                    'varyant_id': v.id,
                    'ad': u.ad,
                    'varyasyon': v.varyasyon_adi,
                    'beden': v.beden.ad if v.beden else 'Tek Beden',
                    'renk': v.renk.ad if v.renk else 'Standart',
                    'barkod': v.barkod,
                    'kod': u.urun_kodu,
                    'kategori': str(u.kategori) if u.kategori else '',
                    'stok_miktari': v.stok_miktari,
                    'sayilan_miktar': d.sayilan_miktar,
                    'pesin_fiyat': float(u.pesin_fiyat) if hasattr(u, 'pesin_fiyat') and u.pesin_fiyat else 0.0,
                })
        except StokSayimi.DoesNotExist:
            messages.warning(request, 'Seçilen taslak sayım bulunamadı veya tamamlanmış.')

    # Yeni sayım numarası preview
    sayim_no_preview = aktif_sayim.sayim_no if aktif_sayim else StokSayimi.yeni_sayim_no()

    # Varsa son 5 tamamlanmış sayım özeti (bilgi amaçlı)
    son_sayimlar = StokSayimi.objects.all().order_by('-olusturma_tarihi')[:5]

    context = {
        'title': 'Hızlı Stok Sayımı',
        'sayim_no': sayim_no_preview,
        'aktif_sayim': aktif_sayim,
        'initial_items_json': json.dumps(initial_items, ensure_ascii=False),
        'son_sayimlar': son_sayimlar,
    }
    return render(request, 'urun/sayim_ekrani.html', context)


# ==============================================================================
# 2. AJAX ENDPOINT'LERİ (BARKOD SORGULA & ÜRÜN ARA)
# ==============================================================================

@login_required_json
def sayim_barkod_sorgula(request):
    """
    Barkod ile varyant sorgulama endpoint'i.
    Satış ekranından farklı olarak stoğu 0 olan ürünleri de getirir.
    """
    barkod = (request.GET.get('barkod') or '').strip()

    if not barkod:
        return JsonResponse({'success': False, 'message': 'Barkod girilmedi!'})

    try:
        varyant = UrunVaryanti.objects.select_related(
            'urun', 'urun__kategori', 'urun__marka', 'renk', 'beden'
        ).get(barkod=barkod, aktif=True, urun__aktif=True)
        urun = varyant.urun

        resim_url = None
        if hasattr(urun, 'ana_resim') and urun.ana_resim:
            try:
                resim_url = urun.ana_resim.url
            except Exception:
                resim_url = None

        return JsonResponse({
            'success': True,
            'urun': {
                'id': urun.id,
                'varyant_id': varyant.id,
                'ad': urun.ad,
                'varyasyon': varyant.varyasyon_adi,
                'beden': varyant.beden.ad if varyant.beden else 'Tek Beden',
                'renk': varyant.renk.ad if varyant.renk else 'Standart',
                'barkod': varyant.barkod,
                'kod': urun.urun_kodu,
                'kategori': str(urun.kategori) if urun.kategori else '',
                'stok_miktari': varyant.stok_miktari,
                'pesin_fiyat': float(urun.pesin_fiyat) if hasattr(urun, 'pesin_fiyat') and urun.pesin_fiyat else 0.0,
                'resim': resim_url,
            }
        })
    except UrunVaryanti.DoesNotExist:
        return JsonResponse({'success': False, 'message': f'"{barkod}" barkoduna ait ürün bulunamadı!'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Sorgu hatası: {str(e)}'}, status=500)


@login_required_json
def sayim_urun_ara(request):
    """
    İsim, kod ve barkod ile ürün arama endpoint'i.
    Türkçe karakter normalize edilmiş filtreleme yapar; stoğu 0 olanlar da dahildir.
    """
    query = (request.GET.get('q') or '').strip()
    kriter = (request.GET.get('kriter') or 'hepsi').strip().lower()

    if len(query) < 1:
        return JsonResponse({'success': True, 'urunler': []})

    def norm_expr(field_name: str):
        expr = F(field_name)
        expr = Replace(expr, Value('İ'), Value('i'))
        expr = Replace(expr, Value('I'), Value('i'))
        expr = Replace(expr, Value('Ş'), Value('s'))
        expr = Replace(expr, Value('Ç'), Value('c'))
        expr = Replace(expr, Value('Ğ'), Value('g'))
        expr = Replace(expr, Value('Ü'), Value('u'))
        expr = Replace(expr, Value('Ö'), Value('o'))
        expr = Lower(expr)
        expr = Replace(expr, Value('ı'), Value('i'))
        expr = Replace(expr, Value('ş'), Value('s'))
        expr = Replace(expr, Value('ç'), Value('c'))
        expr = Replace(expr, Value('ğ'), Value('g'))
        expr = Replace(expr, Value('ü'), Value('u'))
        expr = Replace(expr, Value('ö'), Value('o'))
        return expr

    def norm_text(s: str) -> str:
        s = (s or '').strip()
        s = s.replace('İ', 'i').replace('I', 'i')
        s = s.replace('Ş', 's').replace('Ç', 'c').replace('Ğ', 'g').replace('Ü', 'u').replace('Ö', 'o')
        s = s.lower()
        s = s.replace('ı', 'i').replace('ş', 's').replace('ç', 'c').replace('ğ', 'g').replace('ü', 'u').replace('ö', 'o')
        return s

    qn = norm_text(query)

    base = UrunVaryanti.objects.filter(
        aktif=True,
        urun__aktif=True
    ).select_related('urun', 'urun__kategori', 'urun__marka', 'renk', 'beden')

    base = base.annotate(
        ad_n=norm_expr('urun__ad'),
        barkod_n=norm_expr('barkod'),
        kod_n=norm_expr('urun__urun_kodu'),
    )

    if kriter == 'ad':
        filt = Q(ad_n__contains=qn)
    elif kriter == 'barkod':
        filt = Q(barkod_n__contains=qn)
    elif kriter in ('kod', 'urun_kodu', 'urun-kodu'):
        filt = Q(kod_n__contains=qn)
    else:
        filt = Q(ad_n__contains=qn) | Q(barkod_n__contains=qn) | Q(kod_n__contains=qn)

    varyantlar = base.filter(filt)[:50]

    sonuc = []
    for v in varyantlar:
        u = v.urun
        resim_url = None
        if hasattr(u, 'ana_resim') and u.ana_resim:
            try:
                resim_url = u.ana_resim.url
            except Exception:
                resim_url = None

        sonuc.append({
            'id': u.id,
            'varyant_id': v.id,
            'ad': u.ad,
            'varyasyon': v.varyasyon_adi,
            'beden': v.beden.ad if v.beden else 'Tek Beden',
            'renk': v.renk.ad if v.renk else 'Standart',
            'barkod': v.barkod,
            'kod': u.urun_kodu,
            'urun_kodu': u.urun_kodu,
            'kategori': str(u.kategori) if u.kategori else '',
            'stok_miktari': v.stok_miktari,
            'pesin_fiyat': float(u.pesin_fiyat) if hasattr(u, 'pesin_fiyat') and u.pesin_fiyat else 0.0,
            'resim': resim_url,
        })

    return JsonResponse({'success': True, 'urunler': sonuc})


# ==============================================================================
# 3. SAYIM KAYDET & STOK EŞİTLEME (TRANSACTIONAL)
# ==============================================================================

@require_POST
@login_required_json
def sayim_kaydet(request):
    """
    Sayım listesini onaylayıp kaydeder.
    Her varyant için:
      - Eğer sayılan < sistem ise: 'sayim_eksik' hareketi oluşturur ve stok düşer.
      - Eğer sayılan > sistem ise: 'sayim_fazla' hareketi oluşturur ve stok artar.
      - Sonuçta varyantın güncel stoğu sayılan miktara eşitlenir!
    """
    try:
        data = json.loads(request.body.decode('utf-8'))
    except Exception:
        return JsonResponse({'success': False, 'message': 'Geçersiz JSON verisi!'}, status=400)

    sayim_no = (data.get('sayim_no') or '').strip()
    baslik = (data.get('baslik') or '').strip()
    aciklama = (data.get('aciklama') or '').strip()
    items = data.get('items', [])
    sayim_id = data.get('sayim_id')

    if not items:
        return JsonResponse({'success': False, 'message': 'Sayım listesinde hiç ürün yok!'}, status=400)

    try:
        with transaction.atomic():
            if sayim_id:
                sayim = get_object_or_404(StokSayimi, id=sayim_id)
                if sayim.durum == 'tamamlandi':
                    return JsonResponse({'success': False, 'message': 'Bu sayım daha önce tamamlanmış!'}, status=400)
            else:
                if not sayim_no:
                    sayim_no = StokSayimi.yeni_sayim_no()
                sayim = StokSayimi.objects.create(
                    sayim_no=sayim_no,
                    baslik=baslik or f"Stok Sayımı {timezone.now().strftime('%d.%m.%Y %H:%M')}",
                    aciklama=aciklama,
                    kullanici=request.user,
                    durum='taslak'
                )

            sayim.baslik = baslik or sayim.baslik or f"Stok Sayımı {timezone.now().strftime('%d.%m.%Y %H:%M')}"
            sayim.aciklama = aciklama or sayim.aciklama
            sayim.tamamlayan = request.user
            sayim.tamamlanma_tarihi = timezone.now()

            # Kalemleri işle ve stok hareketlerini oluştur
            for item in items:
                vid = item.get('varyant_id')
                sayilan = int(item.get('sayilan_miktar', 0))
                if sayilan < 0:
                    sayilan = 0

                varyant = UrunVaryanti.objects.select_for_update().select_related('urun').get(id=vid)
                sistem_stok = varyant.stok_miktari
                fark = sayilan - sistem_stok
                hareket = None

                if fark < 0:
                    # Eksik tespit edildi -> stok azaltılacak
                    eksik_adet = abs(fark)
                    hareket = StokHareket.stok_hareketi_olustur(
                        varyant=varyant,
                        hareket_tipi='sayim_eksik',
                        miktar=eksik_adet,
                        kullanici=request.user,
                        aciklama=f"Sayım #{sayim.sayim_no} Eksiği: Sistem={sistem_stok}, Sayılan={sayilan}",
                        referans_id=sayim.sayim_no
                    )
                elif fark > 0:
                    # Fazla tespit edildi -> stok artırılacak
                    fazla_adet = fark
                    hareket = StokHareket.stok_hareketi_olustur(
                        varyant=varyant,
                        hareket_tipi='sayim_fazla',
                        miktar=fazla_adet,
                        kullanici=request.user,
                        aciklama=f"Sayım #{sayim.sayim_no} Fazlası: Sistem={sistem_stok}, Sayılan={sayilan}",
                        referans_id=sayim.sayim_no
                    )

                # Detay kaydını oluştur veya güncelle
                detay, _ = StokSayimiDetay.objects.update_or_create(
                    sayim=sayim,
                    varyant=varyant,
                    defaults={
                        'sistem_stok': sistem_stok,
                        'sayilan_miktar': sayilan,
                        'fark': fark,
                        'birim_fiyat': varyant.urun.pesin_fiyat if hasattr(varyant.urun, 'pesin_fiyat') and varyant.urun.pesin_fiyat else Decimal('0.00'),
                        'stok_hareket': hareket
                    }
                )

            # Sayımı tamamlandı olarak işaretle
            sayim.durum = 'tamamlandi'
            sayim.save()
            sayim.istatistikleri_guncelle()

            return JsonResponse({
                'success': True,
                'sayim_id': sayim.id,
                'sayim_no': sayim.sayim_no,
                'message': f"Sayım #{sayim.sayim_no} başarıyla tamamlandı! Stoklar eşitlendi."
            })

    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Kayıt sırasında hata oluştu: {str(e)}'}, status=500)


@require_POST
@login_required_json
def sayim_taslak_kaydet(request):
    """
    Sayım verilerini stokları değiştirmeden taslak olarak kaydeder.
    Daha sonra sayıma kalınan yerden devam edilebilir.
    """
    try:
        data = json.loads(request.body.decode('utf-8'))
    except Exception:
        return JsonResponse({'success': False, 'message': 'Geçersiz JSON verisi!'}, status=400)

    sayim_no = (data.get('sayim_no') or '').strip()
    baslik = (data.get('baslik') or '').strip()
    aciklama = (data.get('aciklama') or '').strip()
    items = data.get('items', [])
    sayim_id = data.get('sayim_id')

    if not items:
        return JsonResponse({'success': False, 'message': 'Kaydedilecek ürün bulunamadı!'}, status=400)

    try:
        with transaction.atomic():
            if sayim_id:
                sayim = get_object_or_404(StokSayimi, id=sayim_id)
                if sayim.durum == 'tamamlandi':
                    return JsonResponse({'success': False, 'message': 'Bu sayım zaten tamamlanmış!'}, status=400)
            else:
                if not sayim_no:
                    sayim_no = StokSayimi.yeni_sayim_no()
                sayim = StokSayimi.objects.create(
                    sayim_no=sayim_no,
                    baslik=baslik or f"Stok Sayımı (Taslak) {timezone.now().strftime('%d.%m.%Y %H:%M')}",
                    aciklama=aciklama,
                    kullanici=request.user,
                    durum='taslak'
                )

            sayim.baslik = baslik or sayim.baslik
            sayim.aciklama = aciklama or sayim.aciklama
            sayim.durum = 'taslak'
            sayim.save()

            for item in items:
                vid = item.get('varyant_id')
                sayilan = int(item.get('sayilan_miktar', 0))
                if sayilan < 0:
                    sayilan = 0

                varyant = UrunVaryanti.objects.select_related('urun').get(id=vid)
                sistem_stok = varyant.stok_miktari
                fark = sayilan - sistem_stok

                StokSayimiDetay.objects.update_or_create(
                    sayim=sayim,
                    varyant=varyant,
                    defaults={
                        'sistem_stok': sistem_stok,
                        'sayilan_miktar': sayilan,
                        'fark': fark,
                        'birim_fiyat': varyant.urun.pesin_fiyat if hasattr(varyant.urun, 'pesin_fiyat') and varyant.urun.pesin_fiyat else Decimal('0.00'),
                    }
                )

            sayim.istatistikleri_guncelle()

            return JsonResponse({
                'success': True,
                'sayim_id': sayim.id,
                'sayim_no': sayim.sayim_no,
                'message': f"Sayım taslağı (#{sayim.sayim_no}) başarıyla kaydedildi."
            })
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Taslak kaydedilirken hata: {str(e)}'}, status=500)


# ==============================================================================
# 4. EXCEL EXPORT (KAYDETMEDEN ÖNCE VEYA SONRA)
# ==============================================================================

def _generate_excel_workbook(sayim_no, baslik, kullanici_adi, tarih_str, items_data):
    """
    Stok sayım listesi için kurumsal tasarımlı Excel çalışma kitabı üretir.
    """
    wb = Workbook()
    ws = wb.active
    ws.title = "Stok Sayım Listesi"
    ws.views.sheetView[0].showGridLines = True

    # Stiller
    font_title = Font(name='Segoe UI', size=16, bold=True, color='0D3B66')
    font_meta = Font(name='Segoe UI', size=10, bold=False, color='555555')
    font_meta_bold = Font(name='Segoe UI', size=10, bold=True, color='333333')
    font_head = Font(name='Segoe UI', size=11, bold=True, color='FFFFFF')
    font_data = Font(name='Segoe UI', size=10, color='222222')
    font_data_bold = Font(name='Segoe UI', size=10, bold=True, color='222222')
    font_eksik = Font(name='Segoe UI', size=10, bold=True, color='C53030')
    font_fazla = Font(name='Segoe UI', size=10, bold=True, color='22543D')
    font_esit = Font(name='Segoe UI', size=10, color='4A5568')

    fill_head = PatternFill(start_color='0D3B66', end_color='0D3B66', fill_type='solid')
    fill_eksik = PatternFill(start_color='FED7D7', end_color='FED7D7', fill_type='solid')
    fill_fazla = PatternFill(start_color='C6F6D5', end_color='C6F6D5', fill_type='solid')
    fill_esit = PatternFill(start_color='EDF2F7', end_color='EDF2F7', fill_type='solid')
    fill_total = PatternFill(start_color='E2E8F0', end_color='E2E8F0', fill_type='solid')

    border_thin = Border(
        left=Side(style='thin', color='CBD5E0'),
        right=Side(style='thin', color='CBD5E0'),
        top=Side(style='thin', color='CBD5E0'),
        bottom=Side(style='thin', color='CBD5E0'),
    )
    border_total = Border(
        top=Side(style='medium', color='0D3B66'),
        bottom=Side(style='double', color='0D3B66'),
        left=Side(style='thin', color='CBD5E0'),
        right=Side(style='thin', color='CBD5E0'),
    )

    align_center = Alignment(horizontal='center', vertical='center')
    align_left = Alignment(horizontal='left', vertical='center')
    align_right = Alignment(horizontal='right', vertical='center')

    # Başlık Alanı
    ws.merge_cells('A1:L1')
    ws['A1'] = "NUVİABUTİK — STOK SAYIM LİSTESİ"
    ws['A1'].font = font_title
    ws['A1'].alignment = align_left
    ws.row_dimensions[1].height = 28

    ws['A2'] = "Sayım No:"
    ws['A2'].font = font_meta_bold
    ws['B2'] = sayim_no
    ws['B2'].font = font_meta

    ws['D2'] = "Tarih:"
    ws['D2'].font = font_meta_bold
    ws['E2'] = tarih_str
    ws['E2'].font = font_meta

    ws['G2'] = "Personel:"
    ws['G2'].font = font_meta_bold
    ws['H2'] = kullanici_adi
    ws['H2'].font = font_meta

    ws['J2'] = "Toplam Kalem:"
    ws['J2'].font = font_meta_bold
    ws['K2'] = len(items_data)
    ws['K2'].font = font_meta_bold
    ws.row_dimensions[2].height = 20

    # Tablo Başlıkları
    headers = [
        ('Sıra', 8, align_center),
        ('Barkod', 18, align_center),
        ('Ürün Kodu', 14, align_center),
        ('Ürün Adı', 32, align_left),
        ('Kategori', 18, align_left),
        ('Renk', 12, align_center),
        ('Beden', 12, align_center),
        ('Sistem Stoğu', 14, align_right),
        ('Sayılan Miktar', 14, align_right),
        ('Fark', 12, align_right),
        ('Durum', 14, align_center),
        ('Birim Fiyat (₺)', 16, align_right),
    ]

    header_row = 4
    ws.row_dimensions[header_row].height = 26
    for col_idx, (col_name, col_width, col_align) in enumerate(headers, 1):
        cell = ws.cell(row=header_row, column=col_idx, value=col_name)
        cell.font = font_head
        cell.fill = fill_head
        cell.alignment = col_align
        cell.border = border_thin
        col_letter = get_column_letter(col_idx)
        ws.column_dimensions[col_letter].width = col_width

    # Satır Verileri
    curr_row = 5
    toplam_sistem = 0
    toplam_sayilan = 0
    toplam_fark = 0

    for idx, item in enumerate(items_data, 1):
        sistem = int(item.get('sistem_stok', 0))
        sayilan = int(item.get('sayilan_miktar', 0))
        fark = sayilan - sistem
        fiyat = float(item.get('pesin_fiyat', 0) or 0)

        toplam_sistem += sistem
        toplam_sayilan += sayilan
        toplam_fark += fark

        if fark < 0:
            durum_str = f"Eksik ({abs(fark)})"
            durum_fill = fill_eksik
            durum_font = font_eksik
        elif fark > 0:
            durum_str = f"Fazla (+{fark})"
            durum_fill = fill_fazla
            durum_font = font_fazla
        else:
            durum_str = "Eşit (0)"
            durum_fill = fill_esit
            durum_font = font_esit

        row_values = [
            (idx, align_center, font_data, None),
            (item.get('barkod', ''), align_center, font_data, None),
            (item.get('kod', '') or item.get('urun_kodu', ''), align_center, font_data, None),
            (item.get('ad', ''), align_left, font_data_bold, None),
            (item.get('kategori', ''), align_left, font_data, None),
            (item.get('renk', ''), align_center, font_data, None),
            (item.get('beden', ''), align_center, font_data, None),
            (sistem, align_right, font_data, None),
            (sayilan, align_right, font_data_bold, None),
            (f"{'+' if fark > 0 else ''}{fark}", align_right, durum_font, durum_fill),
            (durum_str, align_center, durum_font, durum_fill),
            (fiyat, align_right, font_data, None),
        ]

        ws.row_dimensions[curr_row].height = 20
        for col_idx, (val, aln, fnt, fll) in enumerate(row_values, 1):
            cell = ws.cell(row=curr_row, column=col_idx, value=val)
            cell.alignment = aln
            cell.font = fnt
            if fll:
                cell.fill = fll
            cell.border = border_thin
            if col_idx == 12:
                cell.number_format = '#,##0.00'

        curr_row += 1

    # Toplam Satırı
    ws.row_dimensions[curr_row].height = 24
    ws.merge_cells(start_row=curr_row, start_column=1, end_row=curr_row, end_column=7)
    tot_cell = ws.cell(row=curr_row, column=1, value="GENEL TOPLAM")
    tot_cell.font = font_head
    tot_cell.fill = fill_head
    tot_cell.alignment = align_right

    for c in range(1, 8):
        ws.cell(row=curr_row, column=c).border = border_total
        ws.cell(row=curr_row, column=c).fill = fill_head

    # Sistem Toplam
    c8 = ws.cell(row=curr_row, column=8, value=toplam_sistem)
    c8.font = font_data_bold
    c8.alignment = align_right
    c8.border = border_total
    c8.fill = fill_total

    # Sayılan Toplam
    c9 = ws.cell(row=curr_row, column=9, value=toplam_sayilan)
    c9.font = font_data_bold
    c9.alignment = align_right
    c9.border = border_total
    c9.fill = fill_total

    # Fark Toplam
    c10 = ws.cell(row=curr_row, column=10, value=f"{'+' if toplam_fark > 0 else ''}{toplam_fark}")
    c10.font = font_fazla if toplam_fark > 0 else (font_eksik if toplam_fark < 0 else font_esit)
    c10.alignment = align_right
    c10.border = border_total
    c10.fill = fill_total

    # Durum & Fiyat boşlukları
    for c in (11, 12):
        cell = ws.cell(row=curr_row, column=c, value="")
        cell.border = border_total
        cell.fill = fill_total

    return wb


@login_required
def sayim_excel_export(request):
    """
    Ekrandaki güncel sayım listesini (kaydetmeden ÖNCE de çalışır)
    veya daha önce kaydedilmiş bir sayımı Excel (.xlsx) olarak indirir.
    """
    if request.method == 'POST':
        # Canlı ekrandan gelen veriyi export et
        try:
            data = json.loads(request.body.decode('utf-8'))
        except Exception:
            return HttpResponse('Geçersiz JSON verisi', status=400)

        sayim_no = (data.get('sayim_no') or 'YENI_SAYIM').strip()
        baslik = (data.get('baslik') or 'Stok Sayım Listesi').strip()
        items = data.get('items', [])
        kullanici_adi = request.user.get_full_name() or request.user.username
        tarih_str = timezone.now().strftime('%d.%m.%Y %H:%M')

        # Gelen item'ların bilgilerini zenginleştir
        enriched_items = []
        variant_ids = [it.get('varyant_id') for it in items if it.get('varyant_id')]
        v_map = {
            v.id: v for v in UrunVaryanti.objects.filter(id__in=variant_ids).select_related(
                'urun', 'urun__kategori', 'renk', 'beden'
            )
        }

        for it in items:
            vid = it.get('varyant_id')
            v = v_map.get(vid)
            if v:
                u = v.urun
                enriched_items.append({
                    'barkod': v.barkod,
                    'kod': u.urun_kodu,
                    'ad': u.ad,
                    'kategori': str(u.kategori) if u.kategori else '',
                    'renk': v.renk.ad if v.renk else 'Standart',
                    'beden': v.beden.ad if v.beden else 'Tek Beden',
                    'sistem_stok': v.stok_miktari,
                    'sayilan_miktar': it.get('sayilan_miktar', 0),
                    'pesin_fiyat': float(u.pesin_fiyat) if hasattr(u, 'pesin_fiyat') and u.pesin_fiyat else 0.0,
                })
            else:
                enriched_items.append({
                    'barkod': it.get('barkod', ''),
                    'kod': it.get('kod', ''),
                    'ad': it.get('ad', ''),
                    'kategori': it.get('kategori', ''),
                    'renk': it.get('renk', ''),
                    'beden': it.get('beden', ''),
                    'sistem_stok': it.get('stok_miktari', 0),
                    'sayilan_miktar': it.get('sayilan_miktar', 0),
                    'pesin_fiyat': it.get('pesin_fiyat', 0.0),
                })

        wb = _generate_excel_workbook(sayim_no, baslik, kullanici_adi, tarih_str, enriched_items)

    else:
        # GET ile kayıtlı sayım ID üzerinden export
        sayim_id = request.GET.get('sayim_id')
        if not sayim_id:
            return HttpResponse('Sayım ID belirtilmedi', status=400)

        sayim = get_object_or_404(
            StokSayimi.objects.prefetch_related(
                'detaylar__varyant__urun__kategori',
                'detaylar__varyant__renk',
                'detaylar__varyant__beden'
            ),
            id=sayim_id
        )

        sayim_no = sayim.sayim_no
        baslik = sayim.baslik or 'Stok Sayımı'
        kullanici_adi = sayim.kullanici.get_full_name() if sayim.kullanici else 'Bilinmiyor'
        tarih_str = sayim.olusturma_tarihi.strftime('%d.%m.%Y %H:%M')

        enriched_items = []
        for d in sayim.detaylar.all():
            v = d.varyant
            u = v.urun
            enriched_items.append({
                'barkod': v.barkod,
                'kod': u.urun_kodu,
                'ad': u.ad,
                'kategori': str(u.kategori) if u.kategori else '',
                'renk': v.renk.ad if v.renk else 'Standart',
                'beden': v.beden.ad if v.beden else 'Tek Beden',
                'sistem_stok': d.sistem_stok,
                'sayilan_miktar': d.sayilan_miktar,
                'pesin_fiyat': float(d.birim_fiyat),
            })

        wb = _generate_excel_workbook(sayim_no, baslik, kullanici_adi, tarih_str, enriched_items)

    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    safe_filename = f"stok_sayim_{sayim_no}_{timezone.now().strftime('%Y%m%d_%H%M')}.xlsx"
    response['Content-Disposition'] = f'attachment; filename="{safe_filename}"'
    wb.save(response)
    return response


# ==============================================================================
# 5. GEÇMİŞ SAYIMLAR LİSTESİ VE DETAY VIEW
# ==============================================================================

@login_required
def sayim_listesi_view(request):
    """
    Geçmiş stok sayımlarının listelendiği yönetim ekranı.
    """
    sayimlar = StokSayimi.objects.select_related('kullanici', 'tamamlayan').all().order_by('-olusturma_tarihi')

    # Filtreler
    durum = request.GET.get('durum')
    if durum in ('taslak', 'tamamlandi', 'iptal'):
        sayimlar = sayimlar.filter(durum=durum)

    q = request.GET.get('q', '').strip()
    if q:
        sayimlar = sayimlar.filter(
            Q(sayim_no__icontains=q) |
            Q(baslik__icontains=q) |
            Q(aciklama__icontains=q)
        )

    tarih_bas = request.GET.get('tarih_bas')
    tarih_bit = request.GET.get('tarih_bit')
    if tarih_bas:
        try:
            d_bas = datetime.strptime(tarih_bas, '%Y-%m-%d').date()
            sayimlar = sayimlar.filter(olusturma_tarihi__date__gte=d_bas)
        except ValueError:
            pass
    if tarih_bit:
        try:
            d_bit = datetime.strptime(tarih_bit, '%Y-%m-%d').date()
            sayimlar = sayimlar.filter(olusturma_tarihi__date__lte=d_bit)
        except ValueError:
            pass

    paginator = Paginator(sayimlar, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Özet metrikler
    toplam_sayim_sayisi = StokSayimi.objects.count()
    tamamlanan_sayisi = StokSayimi.objects.filter(durum='tamamlandi').count()
    taslak_sayisi = StokSayimi.objects.filter(durum='taslak').count()

    context = {
        'title': 'Stok Sayım Geçmişi',
        'sayimlar': page_obj,
        'toplam_sayim_sayisi': toplam_sayim_sayisi,
        'tamamlanan_sayisi': tamamlanan_sayisi,
        'taslak_sayisi': taslak_sayisi,
        'secili_durum': durum,
        'q': q,
        'tarih_bas': tarih_bas,
        'tarih_bit': tarih_bit,
    }
    return render(request, 'urun/sayim_listesi.html', context)


@login_required
def sayim_detay_view(request, sayim_id):
    """
    Belirli bir sayımın kalem bazlı detay raporu.
    """
    sayim = get_object_or_404(
        StokSayimi.objects.select_related('kullanici', 'tamamlayan'),
        id=sayim_id
    )

    detaylar = sayim.detaylar.select_related(
        'varyant__urun__kategori',
        'varyant__renk',
        'varyant__beden',
        'stok_hareket'
    ).order_by('-son_okuma_tarihi')

    # Filtre: fark türü (eksik, fazla, esit)
    fark_tipi = request.GET.get('fark')
    if fark_tipi == 'eksik':
        detaylar = detaylar.filter(fark__lt=0)
    elif fark_tipi == 'fazla':
        detaylar = detaylar.filter(fark__gt=0)
    elif fark_tipi == 'esit':
        detaylar = detaylar.filter(fark=0)

    # Kalem içi arama
    q = request.GET.get('q', '').strip()
    if q:
        detaylar = detaylar.filter(
            Q(varyant__barkod__icontains=q) |
            Q(varyant__urun__ad__icontains=q) |
            Q(varyant__urun__urun_kodu__icontains=q)
        )

    context = {
        'title': f"Sayım Detayı — #{sayim.sayim_no}",
        'sayim': sayim,
        'detaylar': detaylar,
        'fark_tipi': fark_tipi,
        'q': q,
    }
    return render(request, 'urun/sayim_detay.html', context)


@require_POST
@login_required
def sayim_sil_view(request, sayim_id):
    """
    Sadece taslak durumdaki sayımları siler.
    Tamamlanmış sayımlar stok hareketleri oluşturduğu için silinemez.
    """
    sayim = get_object_or_404(StokSayimi, id=sayim_id)
    if sayim.durum != 'taslak':
        messages.error(request, 'Tamamlanmış veya kesinleşmiş sayımlar silinemez!')
        return redirect('urun:sayim_detay', sayim_id=sayim.id)

    sayim_no = sayim.sayim_no
    sayim.delete()
    messages.success(request, f'#{sayim_no} numaralı taslak sayım silindi.')
    return redirect('urun:sayim_listesi')
