"""
F3 — estado operativo de la venta + gatillo de stock en 'entregado' (§4.4).

Cubre: transiciones en ambos modos, descuento único al entregar, reversión,
no-descuento de históricas, sin_stock nunca mueve, y sincronización pago↔cobrado.
Corre contra Postgres local (settings_test_pg).
"""
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone
from django.core.exceptions import ValidationError

from apps.empresas.models import Empresa
from apps.authentication.models import CustomUser
from apps.ventas.models import Cliente, Venta, DetalleVenta, HistorialEstadoVenta
from apps.inventario.models.almacen import Almacen
from apps.inventario.models.producto import Producto
from apps.inventario.models.inventario_productos_terminados import InventarioProductosTerminados


class EstadoOperativoBase(TestCase):
    _seq = 0

    def _next(self):
        EstadoOperativoBase._seq += 1
        return EstadoOperativoBase._seq

    def _empresa(self, modo='con_stock'):
        n = self._next()
        return Empresa.objects.create(nombre=f'Emp{n}', ruc=f'20{n:09d}', modo_inventario=modo)

    def _user(self, empresa):
        n = self._next()
        u = CustomUser(email=f'u{n}@t.com', nombre='T', apellido='U', empresa=empresa, is_superuser=True)
        u.set_password('x'); u.save()
        return u

    def _cliente(self, empresa):
        n = self._next()
        return Cliente.objects.create(empresa=empresa, nombre='C', documento=f'{n:08d}', tipo_documento='ruc')

    def _almacen(self, empresa):
        return Almacen.objects.create(empresa=empresa, nombre='Central', direccion='x')

    def _producto(self, empresa, almacen, controla_stock=True, stock_total='10'):
        n = self._next()
        return Producto.objects.create(
            empresa=empresa, sku=f'SKU{n}', nombre='P', tipo_producto='FINISHED',
            controla_stock=controla_stock, stock_total=Decimal(stock_total),
            precio_venta=Decimal('100'), precio_compra=Decimal('60'), almacen=almacen,
        )

    def _ipt(self, empresa, producto, almacen, disponible='0', reservada='0'):
        return InventarioProductosTerminados.objects.create(
            empresa=empresa, producto=producto, almacen=almacen,
            cantidad_disponible=Decimal(disponible), cantidad_reservada=Decimal(reservada),
        )

    def _venta(self, empresa, cliente, estado='pendiente', estado_operativo='pendiente_compra'):
        v = Venta.objects.create(
            empresa=empresa, cliente=cliente, fecha_emision=timezone.now().date(),
            estado=estado, tipo_venta='contado',
        )
        if estado_operativo != 'pendiente_compra':
            Venta.objects.filter(pk=v.pk).update(estado_operativo=estado_operativo)
            v.refresh_from_db()
        return v

    def _linea(self, venta, producto=None, origen='stock', cantidad='5', stock_descontado=False):
        return DetalleVenta.objects.create(
            venta=venta, producto=producto, cantidad=Decimal(cantidad),
            precio_unitario=Decimal('100'), origen=origen, stock_descontado=stock_descontado,
            descripcion=None if producto else 'Libre',
        )


class EntregaStockTests(EstadoOperativoBase):
    def test_entregado_descuenta_una_sola_vez(self):
        emp = self._empresa('con_stock'); u = self._user(emp); cli = self._cliente(emp)
        alm = self._almacen(emp); prod = self._producto(emp, alm, stock_total='10')
        ipt = self._ipt(emp, prod, alm, disponible='5', reservada='5')  # reservado por la conversión
        v = self._venta(emp, cli); d = self._linea(v, producto=prod, origen='stock', cantidad='5')

        v.cambiar_estado_operativo('comprado', u)
        v.cambiar_estado_operativo('recibido', u)
        v.cambiar_estado_operativo('entregado', u)

        d.refresh_from_db(); ipt.refresh_from_db()
        self.assertTrue(d.stock_descontado)
        self.assertEqual(ipt.cantidad_reservada, Decimal('0'))   # consumió la reserva
        self.assertEqual(ipt.cantidad_disponible, Decimal('5'))  # intacto

        # Reintento directo: NO vuelve a descontar.
        v.aplicar_entrega_stock()
        ipt.refresh_from_db()
        self.assertEqual(ipt.cantidad_reservada, Decimal('0'))

    def test_reversion_reintegra(self):
        emp = self._empresa('con_stock'); u = self._user(emp); cli = self._cliente(emp)
        alm = self._almacen(emp); prod = self._producto(emp, alm, stock_total='10')
        ipt = self._ipt(emp, prod, alm, disponible='5', reservada='5')
        v = self._venta(emp, cli); d = self._linea(v, producto=prod, origen='stock', cantidad='5')

        v.cambiar_estado_operativo('entregado', u)
        v.cambiar_estado_operativo('recibido', u)  # retroceso → reintegra

        d.refresh_from_db(); ipt.refresh_from_db()
        self.assertFalse(d.stock_descontado)
        self.assertEqual(ipt.cantidad_disponible, Decimal('10'))  # 5 reintegrados

    def test_historica_pagada_no_descuenta_al_entregar(self):
        # Línea ya marcada stock_descontado=True (backfill #9) → no re-descuenta.
        emp = self._empresa('con_stock'); u = self._user(emp); cli = self._cliente(emp)
        alm = self._almacen(emp); prod = self._producto(emp, alm, stock_total='10')
        ipt = self._ipt(emp, prod, alm, disponible='10', reservada='0')
        v = self._venta(emp, cli); self._linea(v, producto=prod, origen='stock', cantidad='5', stock_descontado=True)

        v.aplicar_entrega_stock()
        ipt.refresh_from_db()
        self.assertEqual(ipt.cantidad_disponible, Decimal('10'))  # sin cambio

    def test_sin_stock_ninguna_transicion_mueve(self):
        emp = self._empresa('sin_stock'); u = self._user(emp); cli = self._cliente(emp)
        alm = self._almacen(emp); prod = self._producto(emp, alm, stock_total='10')
        ipt = self._ipt(emp, prod, alm, disponible='10', reservada='0')
        v = self._venta(emp, cli)
        # Aun con producto "de stock", en sin_stock la línea es pedido_proveedor.
        d = self._linea(v, producto=prod, origen='pedido_proveedor', cantidad='5')

        for estado in ['comprado', 'recibido', 'entregado', 'esperando_oc_nr', 'facturado']:
            v.cambiar_estado_operativo(estado, u)

        ipt.refresh_from_db(); d.refresh_from_db()
        self.assertEqual(ipt.cantidad_disponible, Decimal('10'))
        self.assertFalse(d.stock_descontado)


class TransicionesYSyncTests(EstadoOperativoBase):
    def test_transiciones_escriben_historial(self):
        emp = self._empresa('con_stock'); u = self._user(emp); cli = self._cliente(emp)
        v = self._venta(emp, cli)
        for estado in ['comprado', 'recibido', 'entregado', 'esperando_oc_nr', 'facturado']:
            v.cambiar_estado_operativo(estado, u)
        self.assertEqual(v.estado_operativo, 'facturado')
        self.assertEqual(HistorialEstadoVenta.objects.filter(venta=v).count(), 5)

    def test_cobrado_no_elegible_manual(self):
        emp = self._empresa('con_stock'); u = self._user(emp); cli = self._cliente(emp)
        v = self._venta(emp, cli)
        with self.assertRaises(ValidationError):
            v.cambiar_estado_operativo('cobrado', u)

    def test_sync_pago_cobrado_ida_y_vuelta(self):
        emp = self._empresa('con_stock'); u = self._user(emp); cli = self._cliente(emp)
        v = self._venta(emp, cli, estado='pendiente', estado_operativo='facturado')

        # pago → pagado ⇒ cobrado
        v.estado = 'pagado'; v.save(); v._sincronizar_estado_operativo_pago(u)
        v.refresh_from_db()
        self.assertEqual(v.estado_operativo, 'cobrado')

        # pago revertido ⇒ facturado
        v.estado = 'pendiente'; v.save(); v._sincronizar_estado_operativo_pago(u)
        v.refresh_from_db()
        self.assertEqual(v.estado_operativo, 'facturado')

        # historial registró ambos saltos de sync
        notas = list(HistorialEstadoVenta.objects.filter(venta=v).values_list('estado_nuevo', flat=True))
        self.assertIn('cobrado', notas)
        self.assertIn('facturado', notas)

    def test_estado_sla_vencido(self):
        emp = self._empresa('con_stock'); u = self._user(emp); cli = self._cliente(emp)
        v = self._venta(emp, cli)
        v.cambiar_estado_operativo('comprado', u)  # SLA comprado = 5 días
        # forzar antigüedad del estado
        viejo = timezone.now() - timezone.timedelta(days=10)
        Venta.objects.filter(pk=v.pk).update(estado_operativo_actualizado=viejo)
        v.refresh_from_db()
        self.assertEqual(v.estado_sla_operativo, 'vencido')
        self.assertTrue(v.tiene_historial_operativo)
