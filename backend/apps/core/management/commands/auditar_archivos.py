"""
Lista los registros cuyo archivo NO existe en el storage (los perdidos en deploys
anteriores, cuando media vivía en disco efímero). Solo reporta; no modifica nada.

Uso:
    python manage.py auditar_archivos
"""
from django.core.management.base import BaseCommand

from apps.core.media_registry import file_field_specs


class Command(BaseCommand):
    help = 'Reporta los registros con archivo referenciado pero ausente del storage.'

    def handle(self, *args, **opts):
        total = faltantes = 0
        for model, fname in file_field_specs():
            qs = (model.objects
                  .exclude(**{fname: ''})
                  .exclude(**{f'{fname}__isnull': True}))
            for obj in qs.iterator():
                ff = getattr(obj, fname)
                if not ff.name:
                    continue
                total += 1
                try:
                    exists = ff.storage.exists(ff.name)
                except Exception:
                    exists = False
                if not exists:
                    faltantes += 1
                    self.stdout.write(self.style.ERROR(
                        f'FALTA  {model.__name__}#{obj.pk}.{fname}: {ff.name}'))

        self.stdout.write(self.style.SUCCESS(f'Revisados: {total} | Faltantes: {faltantes}'))
