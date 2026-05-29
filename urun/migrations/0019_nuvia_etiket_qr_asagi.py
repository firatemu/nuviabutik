# QR ~3 mm aşağı (y 24→27); tuval 40 mm için kutu 13×13 mm

from django.db import migrations

from urun.nuvia_label_layout import NUVIA_PREMIUM_ELEMENTS


def apply_qr_shift(apps, schema_editor):
    EtiketSablonu = apps.get_model('urun', 'EtiketSablonu')
    for sablon in EtiketSablonu.objects.filter(ad='Nuvia Premium Wear'):
        sablon.tasarim_json = {'elements': NUVIA_PREMIUM_ELEMENTS}
        sablon.save()


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('urun', '0018_nuvia_etiket_tuval_hizasi'),
    ]

    operations = [
        migrations.RunPython(apply_qr_shift, noop),
    ]
