# Ofis ZPL v2: metin/kutu/barkod konumları + Code 128 ^FD >:kod>rakam

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
            'build_nuvia_exact_zpl: güncel ofis konumları; barkod ^FD>:urun_kodu>rakamlar.'
        )
        sablon.tasarim_json = tj
        sablon.save()


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('urun', '0021_nuvia_zpl_ofis_code128_kutu'),
    ]

    operations = [
        migrations.RunPython(apply_layout, noop),
    ]
