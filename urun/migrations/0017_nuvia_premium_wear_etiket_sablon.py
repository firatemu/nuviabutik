# Generated manually — Nuvia Premium Wear kayıtlı şablon + QR konumu (tasarımcı ile düzenlenebilir)

from django.db import migrations

NUVIA_PREMIUM_ELEMENTS = [
    {'id': 1, 'type': 'text', 'x': 16.875, 'y': 8.875, 'width': 30.0, 'height': 10.0,
     'content': 'NUVIA', 'dataField': '', 'fontFamily': 'Arial', 'fontSize': 33,
     'fontColor': '#000000', 'bgColor': '#ffffff', 'bold': True, 'rotation': 0},
    {'id': 2, 'type': 'text', 'x': 1.75, 'y': 12.875, 'width': 50.0, 'height': 4.0,
     'content': 'PREMIUM WEAR MAN & WOMAN', 'dataField': '', 'fontSize': 14,
     'fontColor': '#000000', 'bgColor': '#ffffff', 'bold': False, 'rotation': 0},
    {'id': 3, 'type': 'text', 'x': 4.25, 'y': 22.625, 'width': 10.0, 'height': 3.5,
     'content': 'Beden', 'dataField': '', 'fontSize': 13, 'rotation': 0},
    {'id': 4, 'type': 'text', 'x': 14.875, 'y': 22.625, 'width': 14.0, 'height': 3.5,
     'content': 'Beden', 'dataField': '{beden}', 'fontSize': 13, 'rotation': 0},
    {'id': 5, 'type': 'text', 'x': 29.0, 'y': 18.125, 'width': 12.0, 'height': 3.5,
     'content': 'Pesin', 'dataField': '', 'fontSize': 13, 'rotation': 0},
    {'id': 6, 'type': 'text', 'x': 39.625, 'y': 18.125, 'width': 12.0, 'height': 3.5,
     'content': 'Peşin', 'dataField': '{pesin_fiyat}', 'fontSize': 13, 'rotation': 0},
    {'id': 7, 'type': 'text', 'x': 47.625, 'y': 18.125, 'width': 6.0, 'height': 3.5,
     'content': 'TL', 'dataField': '', 'fontSize': 13, 'rotation': 0},
    {'id': 8, 'type': 'text', 'x': 11.0, 'y': 18.125, 'width': 16.0, 'height': 3.5,
     'content': 'Ürün kodu', 'dataField': '{urun_kodu}', 'fontSize': 13, 'rotation': 0},
    {'id': 9, 'type': 'text', 'x': 4.25, 'y': 18.125, 'width': 8.0, 'height': 3.5,
     'content': 'Kod', 'dataField': '', 'fontSize': 13, 'rotation': 0},
    {'id': 10, 'type': 'barcode_2d', 'x': 20.5, 'y': 35.25, 'width': 18.0, 'height': 18.0,
     'content': '', 'dataField': '{barkod}', 'qrModule': 5, 'rotation': 0},
    {'id': 11, 'type': 'text', 'x': 29.0, 'y': 22.625, 'width': 14.0, 'height': 3.5,
     'content': 'Taksitli', 'dataField': '', 'fontSize': 13, 'rotation': 0},
    {'id': 12, 'type': 'text', 'x': 39.625, 'y': 22.625, 'width': 12.0, 'height': 3.5,
     'content': 'Taksitli', 'dataField': '{taksitli_fiyat}', 'fontSize': 13, 'rotation': 0},
    {'id': 13, 'type': 'text', 'x': 47.625, 'y': 22.875, 'width': 6.0, 'height': 3.5,
     'content': 'TL', 'dataField': '', 'fontSize': 13, 'rotation': 0},
    {'id': 14, 'type': 'rectangle', 'x': 2.0, 'y': 13.5, 'width': 49.625, 'height': 11.125,
     'bgColor': 'transparent', 'borderMm': 3, 'rotation': 0},
]


def create_nuvia_sablon(apps, schema_editor):
    EtiketSablonu = apps.get_model('urun', 'EtiketSablonu')
    EtiketSablonu.objects.update(varsayilan=False)
    EtiketSablonu.objects.update_or_create(
        ad='Nuvia Premium Wear',
        defaults={
            'genislik_mm': 54,
            'yukseklik_mm': 40,
            'varsayilan': True,
            'tasarim_json': {'elements': NUVIA_PREMIUM_ELEMENTS},
            'kategori': None,
            'olusturan': None,
        },
    )


def remove_nuvia_sablon(apps, schema_editor):
    EtiketSablonu = apps.get_model('urun', 'EtiketSablonu')
    EtiketSablonu.objects.filter(ad='Nuvia Premium Wear').delete()


class Migration(migrations.Migration):

    dependencies = [
        ('urun', '0016_etiket_sablon_default_boyut_nuvia'),
    ]

    operations = [
        migrations.RunPython(create_nuvia_sablon, remove_nuvia_sablon),
    ]
