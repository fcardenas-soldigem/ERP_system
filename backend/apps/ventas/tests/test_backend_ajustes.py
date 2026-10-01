"""B1 (SLA facturado=35), B3 (entrega inmediata descuenta), B4 (serializers)."""
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from apps.empresas.models import Empresa
from apps.empresas.serializers import EmpresaSerializer
from apps.authentication.models import CustomUser
from apps.ventas.models import Cliente, Venta, DetalleVenta
from apps.inventario.models.almacen import Almacen
from apps.inventario.models.producto import Producto
from apps.inventario.models.inventario_productos_terminados import InventarioProductosTerminados
from apps.inventario.serializers import ProductoSerializer


class B1SlaTests(TestCase):
    def test_sla_facturado_35(self):
        self.assertEqual(Venta.SLA_OPERATIVO_DIAS['facturado'], 35)


class B3EntregaInmediataTests(TestCase):
    def test_entrega_inmediata_descuenta(self):
        emp = Empresa.objects.create(nombre='E', ruc='20300000001', modo_inventario='con_stock')
        cli = Cliente.objects.create(empresa=emp, nombre='C', documento='30000001', tipo_documento='ruc')
        alm = Almacen.objects.create(empresa=emp, nombre='Central', direccion='x')
        prod = Producto.objects.create(empresa=emp, sku='S1', nombre='P', tipo_producto='FINISHED',
                                       controla_stock=True, stock_total=Decimal('10'),
                                       precio_venta=Decimal('100'), precio_compra=Decimal('60'), almacen=alm)
        ipt = InventarioProductosTerminados.objects.create(empresa=emp, producto=prod, almacen=alm,
                                                           cantidad_disponible=Decimal('10'), cantidad_reservada=Decimal('0'))
        v = Venta.objects.create(empresa=emp, cliente=cli, fecha_emision=timezone.now().date(), tipo_venta='contado')
        DetalleVenta.objects.create(venta=v, producto=prod, cantidad=Decimal('4'),
                                    precio_unitario=Decimal('100'), origen='stock')

        # Lo que hace perform_create cuando entrega_inmediata=true (con_stock):
        v.cambiar_estado_operativo('entregado', usuario=None, nota='Entrega inmediata')

        v.refresh_from_db(); ipt.refresh_from_db()
        self.assertEqual(v.estado_operativo, 'entregado')
        self.assertEqual(ipt.cantidad_disponible, Decimal('6'))  # 10 - 4 (degradación a disponible)
        self.assertTrue(v.detalles.get().stock_descontado)


class B4SerializerTests(TestCase):
    def test_empresa_modo_inventario_escribible(self):
        emp = Empresa.objects.create(nombre='E', ruc='20400000001', modo_inventario='con_stock')
        ser = EmpresaSerializer(instance=emp, data={'modo_inventario': 'sin_stock'}, partial=True)
        self.assertTrue(ser.is_valid(), ser.errors)
        ser.save(); emp.refresh_from_db()
        self.assertEqual(emp.modo_inventario, 'sin_stock')

    def test_producto_controla_stock_escribible(self):
        emp = Empresa.objects.create(nombre='E', ruc='20400000002', modo_inventario='con_stock')
        prod = Producto.objects.create(empresa=emp, sku='S9', nombre='P', tipo_producto='FINISHED',
                                       controla_stock=True, precio_venta=Decimal('10'), precio_compra=Decimal('5'))
        self.assertIn('controla_stock', ProductoSerializer().fields)
        ser = ProductoSerializer(instance=prod, data={'controla_stock': False}, partial=True)
        self.assertTrue(ser.is_valid(), ser.errors)
        ser.save(); prod.refresh_from_db()
        self.assertFalse(prod.controla_stock)
