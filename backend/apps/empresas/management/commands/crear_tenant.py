"""
Alta de una empresa nueva + su usuario administrador.

    TENANT_ADMIN_PASSWORD='...' python manage.py crear_tenant \
        --nombre "Empresa SAC" --ruc 20123456789 \
        --email admin@empresa.pe --admin-nombre Ana --admin-apellido Pérez \
        [--sin-stock]

La contraseña se lee SOLO de la variable de entorno TENANT_ADMIN_PASSWORD (no va en
argv ni en el historial de shell). No crea superusuarios.
"""
import os

from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError

from apps.empresas.services import registrar_empresa


class Command(BaseCommand):
    help = 'Crea una empresa nueva (tenant) con su usuario administrador.'

    def add_arguments(self, parser):
        parser.add_argument('--nombre', required=True)
        parser.add_argument('--ruc', required=True)
        parser.add_argument('--email', required=True, help='Email del administrador.')
        parser.add_argument('--admin-nombre', required=True)
        parser.add_argument('--admin-apellido', required=True)
        parser.add_argument('--sin-stock', action='store_true',
                            help='Empresa back-to-back (no maneja inventario).')

    def handle(self, *args, **opts):
        password = os.environ.get('TENANT_ADMIN_PASSWORD')
        if not password:
            raise CommandError('Define TENANT_ADMIN_PASSWORD en el entorno (no se acepta por argv).')
        try:
            empresa, usuario = registrar_empresa(
                nombre=opts['nombre'], ruc=opts['ruc'], admin_email=opts['email'],
                admin_password=password, admin_nombre=opts['admin_nombre'],
                admin_apellido=opts['admin_apellido'],
                modo_inventario='sin_stock' if opts['sin_stock'] else 'con_stock',
            )
        except ValidationError as e:
            raise CommandError('; '.join(f'{k}: {" ".join(v)}' for k, v in e.message_dict.items()))
        self.stdout.write(self.style.SUCCESS(
            f'Empresa #{empresa.id} "{empresa.nombre}" creada; administrador #{usuario.id}.'))
