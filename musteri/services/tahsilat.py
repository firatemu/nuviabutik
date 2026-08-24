"""Tahsilat iş mantığı — tahsilat_views'dan aşamalı taşınacak."""
from decimal import Decimal

from musteri.models import Tahsilat, Musteri


def parse_tutar(raw):
    """POST tutar alanını Decimal'e çevirir."""
    from musteri.tahsilat_views import _parse_post_tutar
    return _parse_post_tutar(raw)


def musteri_borc_ozet(musteri):
    """Müşteri açık hesap özeti."""
    return {
        'bakiye': musteri.acik_hesap_bakiye or Decimal('0'),
        'limit': musteri.acik_hesap_limit or Decimal('0'),
    }


def tahsilat_olustur(musteri, tutar, odeme_tipi, user, **extra):
    """Yeni tahsilat kaydı oluşturur (stub — view katmanı form doğrulaması yapar)."""
    return Tahsilat.objects.create(
        musteri=musteri,
        tutar=tutar,
        odeme_tipi=odeme_tipi,
        olusturan=user,
        **extra,
    )
