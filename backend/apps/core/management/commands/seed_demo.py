"""
Siembra datos DEMO en la BD local. Idempotente. SOLO corre contra BD local
(aborta si el HOST contiene 'supabase'). Datos ficticios — NADA de producción.

Uso:  python manage.py seed_demo
"""
from decimal import Decimal

from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction

DEMO_PASSWORD = 'demo12345'


class Command(BaseCommand):
    help = 'Siembra 2 empresas demo (con/sin stock) con usuarios, proveedores, clientes y productos.'

    def handle(self, *args, **options):
        host = str(connection.settings_dict.get('HOST', '')).lower()
        if 'supabase' in host or 'pooler' in host:
            raise CommandError(f'ABORTADO: la BD no es local (HOST={host}). seed_demo solo corre en local.')

        self.stdout.write(f'BD local OK (HOST={host or "localhost"}). Sembrando...')
        with transaction.atomic():
            self._seed_empresa('Demo Sin Stock', '20000000011', 'sin_stock', 'demo-sinstock@local.dev')
            self._seed_empresa('Demo Con Stock', '20000000012', 'con_stock', 'demo-constock@local.dev')
        self.stdout.write(self.style.SUCCESS(
            f'\nListo. Usuarios demo (password "{DEMO_PASSWORD}"):\n'
            '  - demo-sinstock@local.dev  (Demo Sin Stock)\n'
            '  - demo-constock@local.dev  (Demo Con Stock)'
        ))

    def _seed_empresa(self, nombre, ruc, modo, email_usuario):
        from apps.empresas.models import Empresa
        from apps.authentication.models import CustomUser
        from apps.ventas.models import Cliente
        from apps.compras.models import Proveedor
        from apps.inventario.models.almacen import Almacen
        from apps.inventario.models.producto import Producto
        from apps.inventario.models.inventario_productos_terminados import InventarioProductosTerminados

        empresa, _ = Empresa.objects.get_or_create(
            ruc=ruc, defaults={'nombre': nombre, 'modo_inventario': modo},
        )
        # asegurar modo correcto (idempotente)
        if empresa.modo_inventario != modo or empresa.nombre != nombre:
            empresa.modo_inventario = modo
            empresa.nombre = nombre
            empresa.save(update_fields=['modo_inventario', 'nombre'])

        user = CustomUser.objects.filter(email=email_usuario).first()
        if not user:
            user = CustomUser(email=email_usuario, nombre='Demo', apellido=nombre,
                              empresa=empresa, is_staff=True)
            user.set_password(DEMO_PASSWORD)
            user.save()

        almacen, _ = Almacen.objects.get_or_create(
            empresa=empresa, nombre='Almacén Central', defaults={'direccion': 'Av. Demo 123'},
        )

        for i in range(1, 4):
            # telefono/email NOT NULL en BD (drift) → proveer valores.
            Proveedor.objects.get_or_create(
                empresa=empresa, ruc=f'206{ruc[-6:]}{i}'[:11],
                defaults={
                    'razon_social': f'Proveedor Demo {i} ({nombre})',
                    'telefono': f'99900{i:04d}', 'email': f'prov{i}@demo.local',
                    'direccion': 'Av. Proveedor 100',
                },
            )

        for i in range(1, 3):
            Cliente.objects.get_or_create(
                empresa=empresa, documento=f'10{ruc[-6:]}{i}'[:11],
                defaults={
                    'nombre': f'Cliente Demo {i} ({nombre})', 'tipo_documento': 'ruc',
                    'telefono': f'98800{i:04d}', 'email': f'cli{i}@demo.local',
                    'direccion': 'Av. Cliente 200',
                },
            )

        # 6 productos. En con_stock, perfiles variados; en sin_stock, genéricos.
        # (perfil, stock_total, stock_minimo, controla_stock)
        if modo == 'con_stock':
            perfiles = [
                ('Stock Alto A', '100', '5', True),
                ('Stock Alto B', '80', '5', True),
                ('Stock Bajo A', '2', '5', True),
                ('Stock Bajo B', '1', '5', True),
                ('Servicio Instalación', '0', '0', False),  # no controla stock
                ('Sin Stock', '0', '5', True),
            ]
        else:
            perfiles = [(f'Producto Demo {i}', '0', '0', True) for i in range(1, 7)]

        for idx, (etiqueta, stock_total, stock_min, controla) in enumerate(perfiles, start=1):
            sku = f'DEMO-{ruc[-4:]}-{idx:02d}'
            prod, creado = Producto.objects.get_or_create(
                empresa=empresa, sku=sku,
                defaults={
                    'nombre': f'{etiqueta}', 'tipo_producto': 'FINISHED',
                    'controla_stock': controla, 'stock_total': Decimal(stock_total),
                    'stock_minimo': Decimal(stock_min), 'stock_maximo': Decimal('1000'),
                    'precio_venta': Decimal('100.00'),
                    'precio_compra': Decimal('60.00'), 'almacen': almacen, 'moneda': 'PEN',
                },
            )
            if not creado:
                prod.controla_stock = controla
                prod.stock_total = Decimal(stock_total)
                prod.stock_minimo = Decimal(stock_min)
                prod.almacen = almacen
                prod.save(update_fields=['controla_stock', 'stock_total', 'stock_minimo', 'almacen'])

            # Inventario de PT para que la reserva/descuento funcione en con_stock.
            if modo == 'con_stock' and controla and Decimal(stock_total) > 0:
                ipt, ipt_creado = InventarioProductosTerminados.objects.get_or_create(
                    empresa=empresa, producto=prod, almacen=almacen,
                    defaults={'cantidad_disponible': Decimal(stock_total), 'cantidad_reservada': Decimal('0')},
                )
                if not ipt_creado:
                    ipt.cantidad_disponible = Decimal(stock_total)
                    ipt.cantidad_reservada = Decimal('0')
                    ipt.save(update_fields=['cantidad_disponible', 'cantidad_reservada'])

        self.stdout.write(f'  ✓ {nombre} ({modo}): 3 proveedores, 2 clientes, 6 productos.')
