"""Settings de test contra Postgres LOCAL (no SQLite).

Hereda de config.settings, que carga .env.local → BD Postgres local
(localhost:5433/erp). El runner crea una BD de test (test_erp) en ese servidor.

Igual que settings_test:
- URLconf vacía (evita importar el stack de ML ausente en dev).
- Migraciones deshabilitadas (syncdb desde los modelos) para NO replayar el
  historial de compras (deuda R4: 0002 y 0004 chocan en created_at).
- Crea a mano la tabla managed=False compras_ordencompradetalle tras el syncdb.
"""
from .settings import *  # noqa: F401,F403

ROOT_URLCONF = 'config.test_urls'


class _DisableMigrations:
    def __contains__(self, item):
        return True

    def __getitem__(self, item):
        return None


MIGRATION_MODULES = _DisableMigrations()


from django.db.models.signals import post_migrate  # noqa: E402


def _crear_tablas_unmanaged(sender, **kwargs):
    from django.db import connection
    from apps.compras.models import OrdenCompraDetalle

    tabla = OrdenCompraDetalle._meta.db_table
    if tabla not in connection.introspection.table_names():
        with connection.schema_editor() as schema_editor:
            schema_editor.create_model(OrdenCompraDetalle)


post_migrate.connect(_crear_tablas_unmanaged, dispatch_uid='test_pg_crear_unmanaged')
