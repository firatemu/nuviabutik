# Ofis ZPL: tek kutu + Code 128 barkod (QR kaldırıldı); tasarımcı öğeleri güncellendi

from django.db import migrations

from urun.nuvia_label_layout import NUVIA_PREMIUM_ELEMENTS


def apply_layout(apps, schema_editor):
    EtiketSablonu = apps.get_model('urun', 'EtiketSablonu')
    for sablon in EtiketSablonu.objects.filter(ad='Nuvia Premium Wear'):
        sablon.genislik_mm = 54
        sablon.yukseklik_mm = 40
        tj = sablon.tasarim_json or {}
        tj['elements'] = NUVIA_PREMIUM_ELEMENTS
        tj['zpl_engine'] = 'exact'
        tj['zpl_note'] = (
            'Yazdırma build_nuvia_exact_zpl ile sabit şablondur; '
            'tasarımcı yerleşim önizlemesidir (Code 128 + orta kutu).'
        )
        sablon.tasarim_json = tj
        sablon.save()


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('urun', '0020_nuvia_zpl_ofis_tasarim'),
    ]

    operations = [
        migrations.RunPython(apply_layout, noop),
    ]
