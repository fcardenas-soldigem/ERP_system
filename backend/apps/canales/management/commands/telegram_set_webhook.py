"""
Registra el webhook del bot y sus comandos (A2).

    python manage.py telegram_set_webhook \
        --url https://erp-backend-25656632090.southamerica-west1.run.app

La URL es la de Cloud Run DIRECTA, nunca erp.soldigem.com.pe: Telegram no
necesita la cookie same-site y así el webhook no depende del rewrite de Vercel
(ni de su timeout ni de un deploy del frontend).

Usa TG_BOT_TOKEN y TG_WEBHOOK_SECRET del entorno. La cabecera secreta que
Telegram enviará en cada update es la MISMA que valida el webhook.
"""
import requests
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

COMANDOS = [
    {'command': 'cotizar', 'description': 'Preparar una cotización'},
    {'command': 'venta', 'description': 'Consultar una venta (estado y saldo)'},
    {'command': 'cobro', 'description': 'Registrar un cobro'},
    {'command': 'stock', 'description': 'Consultar stock de un producto'},
    {'command': 'ayuda', 'description': 'Qué puede hacer el asistente'},
]


class Command(BaseCommand):
    help = 'Registra la URL del webhook, la cabecera secreta y los comandos del bot.'

    def add_arguments(self, parser):
        parser.add_argument('--url', required=True, help='Base pública del backend (https://…)')
        parser.add_argument('--borrar', action='store_true', help='Elimina el webhook en vez de registrarlo')
        parser.add_argument('--forzar', action='store_true',
                            help='Permite una URL que no sea *.run.app (no recomendado)')

    def handle(self, *args, **opts):
        token = settings.TG_BOT_TOKEN
        secreto = settings.TG_WEBHOOK_SECRET
        if not token or not secreto:
            raise CommandError('Faltan TG_BOT_TOKEN y/o TG_WEBHOOK_SECRET en el entorno.')
        api = f'https://api.telegram.org/bot{token}'

        if opts['borrar']:
            r = requests.post(f'{api}/deleteWebhook', timeout=15)
            self.stdout.write(str(r.json()))
            return

        from urllib.parse import urlparse
        host = urlparse(opts['url']).hostname or ''
        if not host.endswith('.run.app') and not opts['forzar']:
            raise CommandError(
                f'La URL debe ser la de Cloud Run directa (*.run.app), no {host}: '
                'el webhook no debe pasar por el rewrite de Vercel. Usa --forzar si sabes lo que haces.')
        url = opts['url'].rstrip('/') + '/api/canales/telegram/'
        r = requests.post(f'{api}/setWebhook', json={
            'url': url,
            'secret_token': secreto,
            'allowed_updates': ['message', 'callback_query'],
            'drop_pending_updates': True,
        }, timeout=15)
        if not r.ok or not r.json().get('ok'):
            raise CommandError(f'setWebhook falló: {r.text}')
        self.stdout.write(self.style.SUCCESS(f'Webhook registrado: {url}'))

        r = requests.post(f'{api}/setMyCommands', json={'commands': COMANDOS}, timeout=15)
        self.stdout.write(self.style.SUCCESS('Comandos registrados.') if r.ok else self.style.WARNING(r.text))
