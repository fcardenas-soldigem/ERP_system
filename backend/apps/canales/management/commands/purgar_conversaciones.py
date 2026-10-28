"""Retención de la memoria del chat (C1).

Borra los MensajeConversacion con más de CANALES_RETENCION_DIAS días (30 por
defecto). Idempotente: correrlo dos veces seguidas borra 0 la segunda. El
contexto del agente solo usa los últimos 10 mensajes, así que purgar no cambia
el comportamiento del bot; es higiene de datos (texto libre de los usuarios).

    python manage.py purgar_conversaciones            # usa el setting
    python manage.py purgar_conversaciones --dias 7   # override puntual

En prod corre como Cloud Run Job diario (DEPLOY.md §13).
"""
from datetime import timedelta

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.canales.models import MensajeConversacion


class Command(BaseCommand):
    help = 'Borra los mensajes de conversación del bot con más de N días (retención).'

    def add_arguments(self, parser):
        parser.add_argument('--dias', type=int, default=None,
                            help='override de CANALES_RETENCION_DIAS (por defecto 30)')

    def handle(self, *args, **opts):
        dias = opts['dias'] if opts['dias'] is not None else int(
            getattr(settings, 'CANALES_RETENCION_DIAS', 30))
        if dias < 1:
            self.stderr.write(self.style.ERROR('--dias debe ser ≥ 1'))
            raise SystemExit(1)
        limite = timezone.now() - timedelta(days=dias)
        borrados, _ = MensajeConversacion.objects.filter(created_at__lt=limite).delete()
        self.stdout.write(self.style.SUCCESS(
            f'purga de conversaciones: {borrados} mensaje(s) con más de {dias} días borrados.'))
