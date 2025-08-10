from django.apps import AppConfig

class ComprasConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.compras'

    def ready(self):
        try:
            import apps.compras.signals  # noqa
        except ImportError:
            pass
