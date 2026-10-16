from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.core'
    label = 'core'
    verbose_name = 'Core'

    def ready(self):
        try:
            import apps.core.signals  # noqa F401
        except ImportError:
            pass

        # M3: el Django admin es SOLO para superusuarios de plataforma. Por defecto
        # AdminSite.has_permission admite cualquier is_staff, que vería datos de TODOS
        # los tenants (el admin no aplica el filtrado por empresa). Lo restringimos a
        # is_superuser para que ningún usuario de un tenant acceda a /admin/.
        from django.contrib import admin

        def _solo_superuser_plataforma(request):
            u = getattr(request, 'user', None)
            return bool(u and u.is_active and u.is_superuser)

        admin.site.has_permission = _solo_superuser_plataforma
