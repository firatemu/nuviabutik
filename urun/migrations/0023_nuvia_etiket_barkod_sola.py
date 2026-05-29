# Tasarımcı: barkod X 6mm -> 5mm (ZPL ^FT40,289 ile uyumlu)

from django.db import migrations

from urun.nuvia_label_layout import NUVIA_PREMIUM_ELEMENTS


def apply_layout(apps, schema_editor):
    EtiketSablonu = apps.get_model('urun', 'EtiketSablonu')
    for sablon in EtiketSablonu.objects.filter(ad='Nuvia Premium Wear'):
        tj = sablon.tasarim_json or {}
        tj['elements'] = NUVIA_PREMIUM_ELEMENTS
        sablon.tasarim_json = tj
        sablon.save()


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('urun', '0022_nuvia_zpl_ofis_konum_v2'),
    ]

    operations = [
        migrations.RunPython(apply_layout, noop),
    ]
