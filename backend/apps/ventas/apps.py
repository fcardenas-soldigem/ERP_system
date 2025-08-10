from django.apps import AppConfig

class VentasConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.ventas'

    def ready(self):
        try:
            import apps.ventas.signals  # noqa
        except ImportError:
            pass
