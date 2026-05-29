from django.apps import AppConfig


class UrunConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'urun'
    verbose_name = 'Ürün Yönetimi'

    def ready(self):
        """Uygulama hazır olduğunda signals'ları yükle"""
        import urun.signals  # noqa
