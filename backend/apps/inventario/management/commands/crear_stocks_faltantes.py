from django.core.management.base import BaseCommand
from apps.inventario.models import Producto, Stock

class Command(BaseCommand):
    help = 'Crea registros de stock para productos existentes que no tienen stock'

    def handle(self, *args, **kwargs):
        productos = Producto.objects.all()
        stocks_creados = 0

        for producto in productos:
            if producto.almacen and not producto.stocks.exists():
                Stock.objects.create(
                    empresa=producto.empresa,
                    producto=producto,
                    almacen=producto.almacen,
                    cantidad=producto.stock_total or 0
                )
                stocks_creados += 1

        self.stdout.write(
            self.style.SUCCESS(
                f'Se crearon {stocks_creados} registros de stock para productos existentes'
            )
        ) 