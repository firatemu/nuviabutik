# Tuval 54×40 mm ile uyumlu öğe konumları (QR ve başlık taşması düzeltmesi)

from django.db import migrations

from urun.nuvia_label_layout import NUVIA_PREMIUM_ELEMENTS


def fix_layout(apps, schema_editor):
    EtiketSablonu = apps.get_model('urun', 'EtiketSablonu')
    for sablon in EtiketSablonu.objects.filter(ad='Nuvia Premium Wear'):
        sablon.genislik_mm = 54
        sablon.yukseklik_mm = 40
        sablon.tasarim_json = {'elements': NUVIA_PREMIUM_ELEMENTS}
        sablon.save()


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('urun', '0017_nuvia_premium_wear_etiket_sablon'),
    ]

    operations = [
        migrations.RunPython(fix_layout, noop_reverse),
    ]
