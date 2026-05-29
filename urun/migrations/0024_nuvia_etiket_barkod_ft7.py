# Barkod ^FT7,289 (güncel ofis ZPL)

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
        ('urun', '0023_nuvia_etiket_barkod_sola'),
    ]

    operations = [
        migrations.RunPython(apply_layout, noop),
    ]
