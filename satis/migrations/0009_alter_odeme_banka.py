from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('satis', '0008_alter_satissiparisidetay_siparis'),
    ]

    operations = [
        migrations.AlterField(
            model_name='odeme',
            name='banka',
            field=models.CharField(
                blank=True,
                choices=[
                    ('isbank', 'İŞBANKASI'),
                    ('ziraat', 'ZİRAAT BANKASI'),
                    ('yapikredi', 'YAPIKREDİ BANKASI'),
                    ('akbank', 'AKBANK'),
                    ('diger', 'Diğer'),
                ],
                max_length=20,
                null=True,
                verbose_name='Banka',
            ),
        ),
    ]
