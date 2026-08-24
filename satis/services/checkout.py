"""Checkout service — satış tamamlama iş mantığı."""
import json
import logging
from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime

from satis.models import Satis, SatisDetay, Odeme
from urun.models import Urun, UrunVaryanti, StokHareket
from musteri.models import Musteri
from kasa.models import Kasa, KasaHareket
from satis.services import payment as payment_service
from satis.services.exceptions import CheckoutError

logger = logging.getLogger('satis.checkout')


def parse_request_payload(request):
    if request.content_type == 'application/json':
        data = json.loads(request.body)
        return (
            data.get('sepet', []),
            data.get('musteri_id'),
            data.get('odeme_detaylari', {}),
            data,
        )
    return (
        request.session.get('sepet', {}),
        request.POST.get('musteri_id'),
        {'tip': 'tek', 'odeme_yontemi': request.POST.get('odeme_yontemi', 'nakit')},
        {},
    )


def complete_checkout(user, sepet_data, musteri_id, odeme_detaylari, data=None, session=None):
    """Run checkout; returns success dict. Raises CheckoutError on validation failure."""
    data = data or {}
    if not sepet_data:
        raise CheckoutError('Sepet boş!')

    musteri = None
    if musteri_id:
        try:
            musteri = Musteri.objects.get(pk=musteri_id, aktif=True)
        except Musteri.DoesNotExist:
            pass

    ara_toplam, toplam_urun_indirimi, sepet_satirlari = _build_cart_lines(sepet_data)
    genel_indirim = Decimal(str(data.get('genel_indirim', 0)))
    if genel_indirim < 0:
        genel_indirim = Decimal('0')

    genel_paylar_c, genel_indirim, toplam_indirim, genel_toplam = _apply_discounts(
        sepet_satirlari, toplam_urun_indirimi, genel_indirim, ara_toplam
    )

    aciklama = data.get('aciklama', '').strip() if data else ''
    satici = _resolve_satici(user, data.get('satici_id'))

    satis = Satis.objects.create(
        musteri=musteri,
        ara_toplam=ara_toplam,
        indirim_tutari=toplam_indirim,
        kdv_orani=Decimal('0'),
        kdv_tutari=Decimal('0'),
        genel_toplam=genel_toplam,
        toplam_tutar=genel_toplam,
        durum='tamamlandi',
        satici=satici,
        satis_tarihi=datetime.now(),
        notlar=aciklama,
    )

    try:
        _create_sale_lines(satis, sepet_satirlari, genel_paylar_c, user)
        payment_service.apply_payments(
            satis=satis,
            user=user,
            musteri=musteri,
            genel_toplam=genel_toplam,
            odeme_detaylari=odeme_detaylari,
            data=data,
        )
    except CheckoutError:
        satis.delete()
        raise

    if session and 'sepet' in session:
        del session['sepet']

    logger.info(
        'checkout_ok satis_id=%s user=%s total=%s',
        satis.id,
        user.username,
        genel_toplam,
    )
    return {
        'success': True,
        'message': 'Satış başarıyla tamamlandı!',
        'satis_id': satis.id,
        'siparis_no': satis.siparis_no,
        'satis_no': satis.satis_no,
        'toplam': str(genel_toplam),
    }


def _dec_to_cents(d):
    q = (d or Decimal('0')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    return int(q * 100)


def _cents_to_dec(c):
    return (Decimal(int(c or 0)) / Decimal('100')).quantize(Decimal('0.01'))


def _build_cart_lines(sepet_data):
    ara_toplam = Decimal('0')
    toplam_urun_indirimi = Decimal('0')
    sepet_satirlari = []
    for item in sepet_data:
        if isinstance(item, dict):
            fiyat = Decimal(str(item['fiyat']))
            miktar = int(item['miktar'])
            urun_indirimi = Decimal(str(item.get('urun_indirim', item.get('indirim', 0))))
            toplam_urun_indirimi += urun_indirimi
            ara_toplam += fiyat * miktar
            sepet_satirlari.append({
                'urun_id': item.get('id'),
                'varyant_id': item.get('varyant_id'),
                'miktar': miktar,
                'birim_fiyat': fiyat,
                'urun_indirimi': urun_indirimi,
            })
        else:
            fiyat = Decimal(str(sepet_data[item]['fiyat']))
            miktar = int(sepet_data[item]['miktar'])
            ara_toplam += fiyat * miktar
            sepet_satirlari.append({
                'urun_id': int(item),
                'varyant_id': sepet_data[item].get('varyant_id'),
                'miktar': miktar,
                'birim_fiyat': fiyat,
                'urun_indirimi': Decimal('0'),
            })
    return ara_toplam, toplam_urun_indirimi, sepet_satirlari


def _apply_discounts(sepet_satirlari, toplam_urun_indirimi, genel_indirim, ara_toplam):
    satir_kapasiteleri = []
    toplam_kapasite_c = 0
    for s in sepet_satirlari:
        normal = (s['birim_fiyat'] * s['miktar']).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        urun_ind = (s['urun_indirimi'] or Decimal('0')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        if urun_ind < 0:
            urun_ind = Decimal('0')
        if urun_ind > normal:
            urun_ind = normal
            s['urun_indirimi'] = urun_ind
        kapasite_c = max(0, _dec_to_cents(normal - urun_ind))
        satir_kapasiteleri.append(kapasite_c)
        toplam_kapasite_c += kapasite_c

    genel_indirim_c = _dec_to_cents(genel_indirim)
    if genel_indirim_c > toplam_kapasite_c:
        genel_indirim_c = toplam_kapasite_c
        genel_indirim = _cents_to_dec(genel_indirim_c)

    n = len(sepet_satirlari)
    genel_paylar_c = [0] * n
    if n > 0 and genel_indirim_c > 0:
        pay = genel_indirim_c // n
        rem = genel_indirim_c - (pay * n)
        hedefler = [pay + (1 if i < rem else 0) for i in range(n)]
        dagitilmayan = 0
        for i in range(n):
            ver = min(hedefler[i], satir_kapasiteleri[i])
            genel_paylar_c[i] = ver
            dagitilmayan += (hedefler[i] - ver)
        while dagitilmayan > 0:
            ilerleme = False
            for i in range(n):
                if dagitilmayan <= 0:
                    break
                bos = satir_kapasiteleri[i] - genel_paylar_c[i]
                if bos <= 0:
                    continue
                ver = min(bos, dagitilmayan)
                genel_paylar_c[i] += ver
                dagitilmayan -= ver
                ilerleme = True
            if not ilerleme:
                break

    toplam_genel_pay = _cents_to_dec(sum(genel_paylar_c))
    toplam_indirim = (toplam_urun_indirimi + toplam_genel_pay).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    genel_toplam = ara_toplam - toplam_indirim
    return genel_paylar_c, genel_indirim, toplam_indirim, genel_toplam


def _resolve_satici(user, satici_id):
    if not satici_id:
        return user
    from kullanici.models import CustomUser
    try:
        return CustomUser.objects.get(pk=satici_id)
    except CustomUser.DoesNotExist:
        return user


def _create_sale_lines(satis, sepet_satirlari, genel_paylar_c, user):
    for idx, satir in enumerate(sepet_satirlari):
        urun = Urun.objects.get(pk=satir['urun_id'])
        varyant_id = satir.get('varyant_id')
        miktar = int(satir['miktar'])
        birim_fiyat = Decimal(str(satir['birim_fiyat']))
        urun_indirim = Decimal(str(satir.get('urun_indirimi', 0)))
        genel_pay = _cents_to_dec(genel_paylar_c[idx]) if idx < len(genel_paylar_c) else Decimal('0.00')
        indirim_tutari = (urun_indirim + genel_pay).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        toplam_fiyat = birim_fiyat * miktar - indirim_tutari

        varyant = None
        if varyant_id:
            try:
                varyant = UrunVaryanti.objects.get(pk=varyant_id, aktif=True)
                if varyant.stok_miktari < miktar:
                    raise CheckoutError(
                        f'{urun.ad} ({varyant.varyasyon_adi}) için yeterli stok yok! Mevcut: {varyant.stok_miktari}'
                    )
            except UrunVaryanti.DoesNotExist:
                raise CheckoutError(f'{urun.ad} için geçerli varyant bulunamadı!')
        elif urun.toplam_stok < miktar:
            raise CheckoutError(f'{urun.ad} için yeterli stok yok! Mevcut: {urun.toplam_stok}')

        SatisDetay.objects.create(
            satis=satis,
            urun=urun,
            varyant=varyant if varyant_id else None,
            miktar=miktar,
            birim_fiyat=birim_fiyat,
            indirim_tutari=indirim_tutari,
            toplam_fiyat=toplam_fiyat,
        )

        if varyant_id:
            onceki_stok = varyant.stok_miktari
            varyant.stok_miktari -= miktar
            varyant.save(stok_hareket_guncelleme=True)
            StokHareket.objects.create(
                varyant=varyant,
                hareket_tipi='cikis',
                miktar=miktar,
                onceki_stok=onceki_stok,
                yeni_stok=varyant.stok_miktari,
                aciklama=f'Satış: {satis.satis_no}',
                referans_id=str(satis.id),
                kullanici=user,
            )
        else:
            first_variant = urun.varyantlar.filter(aktif=True, stok_miktari__gt=0).first()
            if first_variant:
                onceki_stok = first_variant.stok_miktari
                first_variant.stok_miktari -= miktar
                first_variant.save(stok_hareket_guncelleme=True)
                StokHareket.objects.create(
                    varyant=first_variant,
                    hareket_tipi='cikis',
                    miktar=miktar,
                    onceki_stok=onceki_stok,
                    yeni_stok=first_variant.stok_miktari,
                    aciklama=f'Satış: {satis.satis_no}',
                    referans_id=str(satis.id),
                    kullanici=user,
                )
