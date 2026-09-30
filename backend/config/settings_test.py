"""Settings para correr tests localmente.

Hereda de config.settings y aísla dos problemas PREEXISTENTES del entorno/
historial de migraciones (ajenos a Fase 1):

1) URLconf vacía: los system checks no importan el stack de ML (joblib/sklearn),
   ausente en desarrollo.
2) Migraciones deshabilitadas: el historial de `compras` no replaya desde cero
   (0002 y 0004 ambas hacen AddField created_at a pagocompra — deuda R4). Se
   crea el esquema directo desde los modelos (syncdb). La tabla managed=False
   `compras_ordencompradetalle` se crea a mano tras el syncdb.

No afecta producción.
"""
from .settings import *  # noqa: F401,F403

ROOT_URLCONF = 'config.test_urls'

# La BD configurada en settings es Supabase REMOTA. Los tests NO deben tocarla:
# se usa SQLite local en memoria (solo hay JSONField, compatible en Django 4.2).
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }
}


class _DisableMigrations:
    def __contains__(self, item):
        return True

    def __getitem__(self, item):
        return None


MIGRATION_MODULES = _DisableMigrations()


# Crear la tabla del modelo managed=False (no la crea syncdb).
from django.db.models.signals import post_migrate  # noqa: E402


def _crear_tablas_unmanaged(sender, **kwargs):
    from django.db import connection
    from apps.compras.models import OrdenCompraDetalle

    tabla = OrdenCompraDetalle._meta.db_table
    if tabla not in connection.introspection.table_names():
        with connection.schema_editor() as schema_editor:
            schema_editor.create_model(OrdenCompraDetalle)


post_migrate.connect(_crear_tablas_unmanaged, dispatch_uid='test_crear_unmanaged')
