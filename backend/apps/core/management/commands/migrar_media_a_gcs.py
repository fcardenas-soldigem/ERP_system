"""
Sube los archivos locales de `MEDIA_ROOT` al storage por defecto (GCS en prod) con
las rutas nuevas `empresa_<id>/<tipo>/<uuid>.<ext>` y actualiza la BD.

Idempotente: los registros cuyo nombre ya empieza por `empresa_` se omiten. Lee
SIEMPRE desde el disco local (no desde el storage por defecto), así que correrlo
con GS_BUCKET_NAME definido copia disco local → bucket.

Uso:
    python manage.py migrar_media_a_gcs --dry-run
    python manage.py migrar_media_a_gcs
"""
import os

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.management.base import BaseCommand

from apps.core.media_registry import file_field_specs


class Command(BaseCommand):
    help = 'Migra los archivos de media locales al storage por defecto (GCS) con rutas por empresa.'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true',
                            help='No sube ni guarda nada; solo muestra qué haría.')

    def handle(self, *args, **opts):
        dry = opts['dry_run']
        media_root = settings.MEDIA_ROOT
        migrated = skipped = missing = 0

        for model, fname in file_field_specs():
            field = model._meta.get_field(fname)
            qs = (model.objects
                  .exclude(**{fname: ''})
                  .exclude(**{f'{fname}__isnull': True}))
            for obj in qs.iterator():
                old = getattr(obj, fname).name
                if not old:
                    continue
                if old.startswith('empresa_'):
                    skipped += 1
                    continue
                local = os.path.join(media_root, old)
                if not os.path.exists(local):
                    missing += 1
                    self.stdout.write(self.style.WARNING(
                        f'FALTA  {model.__name__}#{obj.pk}.{fname}: {old} (no está en disco local)'))
                    continue
                new_name = field.generate_filename(obj, os.path.basename(old))
                self.stdout.write(f'{"[dry] " if dry else ""}{model.__name__}#{obj.pk}.{fname}: {old} -> {new_name}')
                if dry:
                    migrated += 1
                    continue
                with open(local, 'rb') as fh:
                    saved = default_storage.save(new_name, ContentFile(fh.read()))
                setattr(getattr(obj, fname), 'name', saved)
                obj.save(update_fields=[fname])
                migrated += 1

        prefix = '(dry-run) ' if dry else ''
        self.stdout.write(self.style.SUCCESS(
            f'{prefix}Migrados: {migrated} | Ya migrados: {skipped} | Faltantes en disco: {missing}'))
