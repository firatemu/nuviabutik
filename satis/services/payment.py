"""Payment application for checkout — ödeme kayıtları ve kasa hareketleri."""
from decimal import Decimal, ROUND_HALF_UP

from satis.models import Odeme
from kasa.models import Kasa, KasaHareket
from satis.services.exceptions import CheckoutError


def apply_payments(*, satis, user, musteri, genel_toplam, odeme_detaylari, data):
    data = data or {}
    if odeme_detaylari.get('tip') == 'karma':
        _apply_karma_payment(satis, user, musteri, genel_toplam, odeme_detaylari, data)
    elif odeme_detaylari.get('odeme_yontemi') == 'acik_hesap':
        _apply_acik_hesap(satis, user, musteri, genel_toplam)
    else:
        _apply_single_payment(satis, user, genel_toplam, odeme_detaylari, data)


def _apply_karma_payment(satis, user, musteri, genel_toplam, odeme_detaylari, data):
    karma_detay = odeme_detaylari.get('karma_detay', {})
    nakit_tutar = Decimal(str(karma_detay.get('nakit', 0)))
    kart_tutar = Decimal(str(karma_detay.get('kart', 0)))
    havale_tutar = Decimal(str(karma_detay.get('havale', 0)))
    hediye_ceki_tutar = Decimal(str(karma_detay.get('hediye_ceki', 0)))
    karma_kart_taksit = odeme_detaylari.get('karma_kart_taksit', 1)
    karma_kart_banka = odeme_detaylari.get('karma_kart_banka')

    if kart_tutar > 0 and not karma_kart_banka:
        raise CheckoutError('Karma ödemede kredi kartı için banka seçimi zorunludur!')

    toplam_odeme = nakit_tutar + kart_tutar + havale_tutar + hediye_ceki_tutar
    if abs(toplam_odeme - genel_toplam) > Decimal('0.01'):
        raise CheckoutError(
            f'Ödeme tutarları eşleşmiyor! Toplam: {genel_toplam}, Ödenen: {toplam_odeme}'
        )

    if nakit_tutar > 0:
        Odeme.objects.create(satis=satis, odeme_tipi='nakit', tutar=nakit_tutar)
        _kasa_giris('nakit', nakit_tutar, satis, user, 'Nakit Ödeme')

    if kart_tutar > 0:
        odeme_data = {'satis': satis, 'odeme_tipi': 'kart', 'tutar': kart_tutar}
        if karma_kart_taksit > 1:
            odeme_data['taksit_sayisi'] = karma_kart_taksit
        if karma_kart_banka:
            odeme_data['banka'] = karma_kart_banka
        Odeme.objects.create(**odeme_data)
        _kasa_giris('pos', kart_tutar, satis, user, 'Kart Ödeme')

    if havale_tutar > 0:
        Odeme.objects.create(satis=satis, odeme_tipi='havale', tutar=havale_tutar)
        _kasa_giris('banka', havale_tutar, satis, user, 'Havale Ödeme')

    if hediye_ceki_tutar > 0 and data.get('hediye_ceki'):
        _redeem_gift_card(
            satis, user, data['hediye_ceki'], hediye_ceki_tutar,
            f'Satış #{satis.satis_no} - Karma Ödeme',
            durum_filter='aktif',
        )


def _apply_acik_hesap(satis, user, musteri, genel_toplam):
    if not musteri:
        raise CheckoutError('Açık hesap satışı için müşteri seçmelisiniz!')
    musteri.borc_hareket_ekle(
        tutar=genel_toplam,
        aciklama=f'Açık Hesap Satış - {satis.satis_no}',
        satis_id=satis.id,
        user=user,
    )
    Odeme.objects.create(
        satis=satis,
        odeme_tipi='acik_hesap',
        tutar=genel_toplam,
        aciklama=f'Açık hesap borcu - {musteri.ad} {musteri.soyad}',
    )


def _apply_single_payment(satis, user, genel_toplam, odeme_detaylari, data):
    odeme_yontemi = odeme_detaylari.get('odeme_yontemi', 'nakit')
    taksit_sayisi = odeme_detaylari.get('taksit_sayisi', 1)
    banka = odeme_detaylari.get('banka')

    if odeme_yontemi in ('kart', 'kredi_karti'):
        if not banka:
            raise CheckoutError('Kredi kartı ile ödemelerde banka seçimi zorunludur!')
        if not taksit_sayisi:
            raise CheckoutError('Kredi kartı ile ödemelerde taksit miktarı zorunludur!')
        odeme_tipi = 'kart'
    elif odeme_yontemi == 'havale':
        odeme_tipi = 'havale'
    elif odeme_yontemi == 'hediye_ceki':
        odeme_tipi = 'hediye_ceki'
    elif odeme_yontemi == 'acik_hesap':
        odeme_tipi = 'acik_hesap'
        if satis.musteri:
            satis.musteri.borc_hareket_ekle(
                tutar=genel_toplam,
                aciklama=f'Veresiye Satış - {satis.satis_no}',
                satis_id=satis.id,
                user=user,
            )
    else:
        odeme_tipi = 'nakit'

    if odeme_tipi == 'acik_hesap':
        return

    if odeme_tipi == 'hediye_ceki':
        hediye_ceki_data = data.get('hediye_ceki') or {}
        kod = (hediye_ceki_data.get('kod') or '').strip()
        if not kod:
            raise CheckoutError('Hediye çeki kodu gerekli.')
        _redeem_gift_card_full_balance(satis, user, kod, genel_toplam)
        return

    odeme_data = {'satis': satis, 'odeme_tipi': odeme_tipi, 'tutar': genel_toplam}
    if odeme_tipi == 'kart':
        odeme_data['taksit_sayisi'] = taksit_sayisi if taksit_sayisi > 1 else None
        if banka:
            odeme_data['banka'] = banka
    Odeme.objects.create(**odeme_data)

    kasa_tip = {'nakit': 'nakit', 'kart': 'pos', 'havale': 'banka'}.get(odeme_tipi)
    label = {'nakit': 'Nakit', 'kart': 'Kart', 'havale': 'Havale'}.get(odeme_tipi, 'Ödeme')
    if kasa_tip:
        _kasa_giris(kasa_tip, genel_toplam, satis, user, f'{label} Ödeme')


def _kasa_giris(tip, tutar, satis, user, label_suffix):
    kasa = Kasa.objects.filter(tip=tip, aktif=True).first()
    if kasa:
        KasaHareket.objects.create(
            kasa=kasa,
            tip='giris',
            kaynak='satis',
            tutar=tutar,
            aciklama=f'Satış #{satis.satis_no} - {label_suffix}',
            satis_id=satis.id,
            kullanici=user,
        )


def _redeem_gift_card(satis, user, hediye_ceki_data, tutar, aciklama, durum_filter='aktif'):
    from hediye.models import HediyeCeki, HediyeCekiKullanim
    from django.utils import timezone
    
    try:
        hediye_ceki = HediyeCeki.objects.get(kod=hediye_ceki_data['kod'], aktif=True, durum=durum_filter)
    except HediyeCeki.DoesNotExist:
        raise CheckoutError(f'Hediye çeki bulunamadı veya kullanılamaz: {hediye_ceki_data["kod"]}')

    # Validasyon kontrolleri
    if not hediye_ceki.kullanilabilir_mi:
        reasons = []
        if hediye_ceki.durum != 'aktif':
            reasons.append(f"Durum: {hediye_ceki.get_durum_display()}")
        if hediye_ceki.kalan_tutar <= 0:
            reasons.append("Bakiye kalmamış")
        if hediye_ceki.gecerlilik_tarihi < timezone.now().date():
            reasons.append("Süresi dolmuş")
        raise CheckoutError(f"Hediye çeki kullanılamaz: {', '.join(reasons)}")

    if hediye_ceki.kalan_tutar < tutar:
        raise CheckoutError(f'Hediye çeki bakiyesi yetersiz. Kalan: {hediye_ceki.kalan_tutar} ₺, Gerekli: {tutar} ₺')

    # Kullanım kaydı oluştur
    HediyeCekiKullanim.objects.create(
        hediye_ceki=hediye_ceki,
        kullanilan_tutar=tutar,
        satis_id=satis.id,
        kullanan=user,
        aciklama=aciklama,
    )
    
    # Bakiyeden düş
    hediye_ceki.kalan_tutar -= tutar
    if hediye_ceki.kalan_tutar <= 0:
        hediye_ceki.kalan_tutar = Decimal('0')
        hediye_ceki.durum = 'kullanilmis'
    hediye_ceki.save()
    
    # Ödeme kaydı oluştur
    Odeme.objects.create(
        satis=satis,
        odeme_tipi='hediye_ceki',
        tutar=tutar,
        hediye_ceki_kodu=hediye_ceki.kod,
        aciklama=aciklama,
    )


def _redeem_gift_card_full_balance(satis, user, kod, genel_toplam):
    from hediye.models import HediyeCeki, HediyeCekiKullanim
    from django.utils import timezone
    
    try:
        hediye_ceki = HediyeCeki.objects.get(kod=kod, aktif=True)
    except HediyeCeki.DoesNotExist:
        raise CheckoutError('Hediye çeki bulunamadı veya kullanılamaz.')

    # Validasyon kontrolleri
    if not hediye_ceki.kullanilabilir_mi:
        reasons = []
        if hediye_ceki.durum != 'aktif':
            reasons.append(f"Durum: {hediye_ceki.get_durum_display()}")
        if hediye_ceki.kalan_tutar <= 0:
            reasons.append("Bakiye kalmamış")
        if hediye_ceki.gecerlilik_tarihi < timezone.now().date():
            reasons.append("Süresi dolmuş")
        raise CheckoutError(f"Hediye çeki kullanılamaz: {', '.join(reasons)}")

    kullanilan = genel_toplam.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    kalan = hediye_ceki.kalan_tutar.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    if kalan < kullanilan:
        raise CheckoutError(
            f'Hediye çeki bakiyesi yetersiz. Kalan: {kalan} ₺, sepet: {kullanilan} ₺'
        )

    # Kullanım kaydı oluştur
    HediyeCekiKullanim.objects.create(
        hediye_ceki=hediye_ceki,
        kullanilan_tutar=kullanilan,
        satis_id=satis.id,
        kullanan=user,
        aciklama=f'Satış #{satis.satis_no} - Hediye çeki ödemesi',
    )
    
    # Bakiyeden düş
    hediye_ceki.kalan_tutar = kalan - kullanilan
    if hediye_ceki.kalan_tutar <= 0:
        hediye_ceki.kalan_tutar = Decimal('0')
        hediye_ceki.durum = 'kullanilmis'
    hediye_ceki.save()
    
    # Ödeme kaydı oluştur
    Odeme.objects.create(
        satis=satis,
        odeme_tipi='hediye_ceki',
        tutar=kullanilan,
        hediye_ceki_kodu=hediye_ceki.kod,
        aciklama=f"Hediye Çeki: {hediye_ceki.kod}",
    )
