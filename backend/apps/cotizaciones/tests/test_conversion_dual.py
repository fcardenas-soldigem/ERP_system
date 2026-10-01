"""
Tests de conversión Cotización → Venta (+ OC) para el modelo dual (D6).

Cubre la tabla de comportamiento §4.6 de FASE1_SPEC.md:
- empresa sin_stock  → todo pedido_proveedor, nunca reserva
- empresa con_stock:
    · producto controla stock y disponible >= cantidad → 'stock' (reserva)
    · stock insuficiente → 'pedido_proveedor' (línea completa)
    · stock reservado por OTRA venta → 'pedido_proveedor' (OD-A)
    · producto no controla stock (servicio) → 'pedido_proveedor'
    · sin producto (texto libre) → 'pedido_proveedor'
- línea pedido_proveedor sin proveedor → aviso, sin OC
- doble conversión → idempotente (no duplica venta ni OCs)
- guarda defensiva H1 (sin_stock nunca mueve stock)
"""
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from apps.empresas.models import Empresa
from apps.authentication.models import CustomUser
from apps.ventas.models import Cliente, Venta
from apps.compras.models import Proveedor, OrdenCompra, OrdenCompraDetalle
from apps.inventario.models.almacen import Almacen
from apps.inventario.models.producto import Producto
from apps.inventario.models.inventario_productos_terminados import InventarioProductosTerminados
from apps.cotizaciones.models import Cotizacion, DetalleCotizacion
from apps.cotizaciones.services.conversion_service import convertir_cotizacion_a_venta


class ConversionDualBase(TestCase):
    _ruc_seq = 0

    def _empresa(self, modo='con_stock', ruc=None):
        ConversionDualBase._ruc_seq += 1
        ruc = ruc or f'20{ConversionDualBase._ruc_seq:09d}'
        return Empresa.objects.create(nombre=f'Emp {ruc}', ruc=ruc, modo_inventario=modo)

    def _user(self, empresa):
        ConversionDualBase._ruc_seq += 1
        u = CustomUser(
            email=f'u{ConversionDualBase._ruc_seq}@t.com',
            nombre='T', apellido='U', empresa=empresa,
        )
        u.set_password('x')
        u.save()
        return u

    def _cliente(self, empresa):
        ConversionDualBase._ruc_seq += 1
        return Cliente.objects.create(
            empresa=empresa, nombre='Cliente', documento=f'{ConversionDualBase._ruc_seq:08d}',
            tipo_documento='ruc',
        )

    def _proveedor(self, empresa, nombre='ACME'):
        ConversionDualBase._ruc_seq += 1
        return Proveedor.objects.create(
            empresa=empresa, razon_social=nombre, ruc=f'20{ConversionDualBase._ruc_seq:09d}',
        )

    def _almacen(self, empresa):
        return Almacen.objects.create(empresa=empresa, nombre='Central', direccion='x')

    def _producto(self, empresa, controla_stock=True, stock_total='0', almacen=None):
        ConversionDualBase._ruc_seq += 1
        return Producto.objects.create(
            empresa=empresa, sku=f'SKU{ConversionDualBase._ruc_seq}', nombre='Prod',
            tipo_producto='FINISHED', controla_stock=controla_stock,
            stock_total=Decimal(stock_total), precio_venta=Decimal('100'),
            precio_compra=Decimal('60'), almacen=almacen,
        )

    def _ipt(self, empresa, producto, almacen, disponible='0', reservada='0'):
        return InventarioProductosTerminados.objects.create(
            empresa=empresa, producto=producto, almacen=almacen,
            cantidad_disponible=Decimal(disponible), cantidad_reservada=Decimal(reservada),
        )

    def _cotizacion(self, empresa, user, cliente):
        return Cotizacion.objects.create(
            empresa=empresa, cliente=cliente, usuario_creador=user,
            asunto='Cot', fecha_vencimiento=timezone.now().date(),
            forma_pago='Contado',
        )

    def _detalle(self, cot, producto=None, proveedor=None, costo=None,
                 cantidad='1', precio='100', descripcion='Item'):
        return DetalleCotizacion.objects.create(
            cotizacion=cot, producto=producto, proveedor=proveedor,
            costo_unitario=Decimal(costo) if costo is not None else None,
            cantidad=Decimal(cantidad), precio_unitario=Decimal(precio),
            descripcion=descripcion,
        )


class ConversionSinStockTests(ConversionDualBase):
    def test_todo_pedido_proveedor_y_no_reserva(self):
        emp = self._empresa(modo='sin_stock')
        user = self._user(emp)
        cli = self._cliente(emp)
        alm = self._almacen(emp)
        prov = self._proveedor(emp)
        prod = self._producto(emp, controla_stock=True, stock_total='100', almacen=alm)
        ipt = self._ipt(emp, prod, alm, disponible='100', reservada='0')
        cot = self._cotizacion(emp, user, cli)
        # Producto con stock de sobra, pero empresa sin_stock → pedido_proveedor.
        self._detalle(cot, producto=prod, proveedor=prov, cantidad='5', precio='100')

        venta = convertir_cotizacion_a_venta(cot)

        self.assertTrue(all(d.origen == 'pedido_proveedor' for d in venta.detalles.all()))
        ipt.refresh_from_db()
        self.assertEqual(ipt.cantidad_reservada, Decimal('0'))  # nunca reservó
        self.assertEqual(OrdenCompra.objects.filter(venta=venta).count(), 1)

    def test_guarda_h1_no_mueve_stock(self):
        emp = self._empresa(modo='sin_stock')
        user = self._user(emp)
        cli = self._cliente(emp)
        alm = self._almacen(emp)
        prod = self._producto(emp, controla_stock=True, stock_total='100', almacen=alm)
        cot = self._cotizacion(emp, user, cli)
        self._detalle(cot, producto=prod, proveedor=self._proveedor(emp), cantidad='5')
        venta = convertir_cotizacion_a_venta(cot)
        # La regla estricta NO mueve stock en empresa sin_stock.
        for d in venta.detalles.all():
            self.assertFalse(venta._debe_mover_stock(d))


class ConversionConStockTests(ConversionDualBase):
    def test_stock_suficiente_reserva_y_sin_oc(self):
        emp = self._empresa(modo='con_stock')
        user = self._user(emp)
        cli = self._cliente(emp)
        alm = self._almacen(emp)
        prod = self._producto(emp, controla_stock=True, stock_total='10', almacen=alm)
        ipt = self._ipt(emp, prod, alm, disponible='10', reservada='0')
        cot = self._cotizacion(emp, user, cli)
        self._detalle(cot, producto=prod, proveedor=self._proveedor(emp), cantidad='4', precio='100')

        venta = convertir_cotizacion_a_venta(cot)

        d = venta.detalles.get()
        self.assertEqual(d.origen, 'stock')
        self.assertEqual(OrdenCompra.objects.filter(venta=venta).count(), 0)
        ipt.refresh_from_db()
        self.assertEqual(ipt.cantidad_reservada, Decimal('4'))
        self.assertEqual(ipt.cantidad_disponible, Decimal('6'))
        self.assertEqual(venta.conversion_info['lineas_stock_reservadas'], 1)

    def test_stock_insuficiente_va_a_oc(self):
        emp = self._empresa(modo='con_stock')
        user = self._user(emp)
        cli = self._cliente(emp)
        alm = self._almacen(emp)
        prov = self._proveedor(emp)
        prod = self._producto(emp, controla_stock=True, stock_total='3', almacen=alm)
        self._ipt(emp, prod, alm, disponible='3', reservada='0')
        cot = self._cotizacion(emp, user, cli)
        self._detalle(cot, producto=prod, proveedor=prov, cantidad='5', precio='100')

        venta = convertir_cotizacion_a_venta(cot)

        self.assertEqual(venta.detalles.get().origen, 'pedido_proveedor')
        self.assertEqual(OrdenCompra.objects.filter(venta=venta).count(), 1)

    def test_stock_reservado_por_otra_venta_va_a_oc(self):
        # OD-A: disponible = stock_total − reservas activas. 10 − 8 = 2 < 5.
        emp = self._empresa(modo='con_stock')
        user = self._user(emp)
        cli = self._cliente(emp)
        alm = self._almacen(emp)
        prov = self._proveedor(emp)
        prod = self._producto(emp, controla_stock=True, stock_total='10', almacen=alm)
        ipt = self._ipt(emp, prod, alm, disponible='2', reservada='8')
        cot = self._cotizacion(emp, user, cli)
        self._detalle(cot, producto=prod, proveedor=prov, cantidad='5', precio='100')

        venta = convertir_cotizacion_a_venta(cot)

        self.assertEqual(venta.detalles.get().origen, 'pedido_proveedor')
        ipt.refresh_from_db()
        self.assertEqual(ipt.cantidad_reservada, Decimal('8'))  # intacta

    def test_producto_no_controla_stock_va_a_oc(self):
        emp = self._empresa(modo='con_stock')
        user = self._user(emp)
        cli = self._cliente(emp)
        alm = self._almacen(emp)
        prov = self._proveedor(emp)
        prod = self._producto(emp, controla_stock=False, stock_total='100', almacen=alm)
        cot = self._cotizacion(emp, user, cli)
        self._detalle(cot, producto=prod, proveedor=prov, cantidad='5')

        venta = convertir_cotizacion_a_venta(cot)
        self.assertEqual(venta.detalles.get().origen, 'pedido_proveedor')

    def test_texto_libre_sin_producto_va_a_oc(self):
        emp = self._empresa(modo='con_stock')
        user = self._user(emp)
        cli = self._cliente(emp)
        prov = self._proveedor(emp)
        cot = self._cotizacion(emp, user, cli)
        self._detalle(cot, producto=None, proveedor=prov, cantidad='2',
                      precio='50', descripcion='Servicio suelto')

        venta = convertir_cotizacion_a_venta(cot)

        d = venta.detalles.get()
        self.assertEqual(d.origen, 'pedido_proveedor')
        self.assertIsNone(d.producto_id)
        self.assertEqual(d.descripcion, 'Servicio suelto')
        self.assertEqual(OrdenCompra.objects.filter(venta=venta).count(), 1)

    def test_degradacion_sin_ipt_mantiene_stock(self):
        # OD-B: controla stock y hay stock_total, pero no existe registro IPT.
        emp = self._empresa(modo='con_stock')
        user = self._user(emp)
        cli = self._cliente(emp)
        alm = self._almacen(emp)
        prod = self._producto(emp, controla_stock=True, stock_total='10', almacen=alm)
        cot = self._cotizacion(emp, user, cli)
        self._detalle(cot, producto=prod, proveedor=self._proveedor(emp), cantidad='4')

        venta = convertir_cotizacion_a_venta(cot)  # no debe reventar
        self.assertEqual(venta.detalles.get().origen, 'stock')


class ConversionAvisosEIdempotenciaTests(ConversionDualBase):
    def test_pedido_sin_proveedor_es_aviso_sin_oc(self):
        emp = self._empresa(modo='sin_stock')
        user = self._user(emp)
        cli = self._cliente(emp)
        cot = self._cotizacion(emp, user, cli)
        self._detalle(cot, producto=None, proveedor=None, descripcion='Sin prov')

        venta = convertir_cotizacion_a_venta(cot)

        self.assertEqual(OrdenCompra.objects.filter(venta=venta).count(), 0)
        avisos = venta.conversion_info['lineas_sin_proveedor']
        self.assertEqual(len(avisos), 1)
        self.assertEqual(avisos[0]['descripcion'], 'Sin prov')

    def test_una_oc_por_proveedor_agrupa_lineas(self):
        emp = self._empresa(modo='sin_stock')
        user = self._user(emp)
        cli = self._cliente(emp)
        p1 = self._proveedor(emp, 'ACME')
        p2 = self._proveedor(emp, 'GLOBEX')
        cot = self._cotizacion(emp, user, cli)
        self._detalle(cot, proveedor=p1, descripcion='A1')
        self._detalle(cot, proveedor=p1, descripcion='A2')
        self._detalle(cot, proveedor=p2, descripcion='B1')

        venta = convertir_cotizacion_a_venta(cot)

        ocs = OrdenCompra.objects.filter(venta=venta)
        self.assertEqual(ocs.count(), 2)
        oc_acme = ocs.get(proveedor=p1)
        self.assertEqual(OrdenCompraDetalle.objects.filter(orden=oc_acme).count(), 2)

    def test_doble_conversion_es_idempotente(self):
        emp = self._empresa(modo='sin_stock')
        user = self._user(emp)
        cli = self._cliente(emp)
        prov = self._proveedor(emp)
        cot = self._cotizacion(emp, user, cli)
        self._detalle(cot, proveedor=prov, descripcion='A1')

        v1 = convertir_cotizacion_a_venta(cot)
        cot.refresh_from_db()
        v2 = convertir_cotizacion_a_venta(cot)

        self.assertEqual(v1.id, v2.id)
        self.assertEqual(Venta.objects.filter(cliente=cli).count(), 1)
        self.assertEqual(OrdenCompra.objects.filter(venta=v1).count(), 1)
        self.assertTrue(v2.conversion_info['reused'])

    def test_no_llama_actualizar_stock_en_conversion(self):
        # La conversión NUNCA descuenta: el detalle queda stock_descontado=False.
        emp = self._empresa(modo='con_stock')
        user = self._user(emp)
        cli = self._cliente(emp)
        alm = self._almacen(emp)
        prod = self._producto(emp, controla_stock=True, stock_total='10', almacen=alm)
        self._ipt(emp, prod, alm, disponible='10', reservada='0')
        cot = self._cotizacion(emp, user, cli)
        self._detalle(cot, producto=prod, proveedor=self._proveedor(emp), cantidad='4')

        venta = convertir_cotizacion_a_venta(cot)
        self.assertFalse(any(d.stock_descontado for d in venta.detalles.all()))
