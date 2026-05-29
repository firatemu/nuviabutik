# Yeni Ofis ZPL düzeni — tasarımcı öğeleri + birebir yazdırma (build_nuvia_exact_zpl)

from django.db import migrations

from urun.nuvia_label_layout import NUVIA_PREMIUM_ELEMENTS


def apply_layout(apps, schema_editor):
    EtiketSablonu = apps.get_model('urun', 'EtiketSablonu')
    for sablon in EtiketSablonu.objects.filter(ad='Nuvia Premium Wear'):
        sablon.genislik_mm = 54
        sablon.yukseklik_mm = 40
        sablon.tasarim_json = {
            'elements': NUVIA_PREMIUM_ELEMENTS,
            'zpl_engine': 'exact',
            'zpl_note': 'Yazdırma build_nuvia_exact_zpl ile sabit şablondur; tasarımcı yerleşim önizlemesidir.',
        }
        sablon.save()


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('urun', '0019_nuvia_etiket_qr_asagi'),
    ]

    operations = [
        migrations.RunPython(apply_layout, noop),
    ]
