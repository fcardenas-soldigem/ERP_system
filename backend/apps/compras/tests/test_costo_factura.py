"""
Costo de venta con prioridad de fuente + registrar-factura (fix/costo-venta-utilidad).

Regla: utilidad bruta = venta SIN IGV − costo SIN IGV, ambos en PEN con el TC
de cada documento. Costo 0 = sin dato. Prioridad:
factura > oc > cotizacion > catalogo > None.
"""
from datetime import date
from decimal import Decimal
from unittest import mock

from django.core.cache import cache
from django.test import TestCase

from apps.empresas.models import Empresa
from apps.ventas.models import Cliente, Venta, DetalleVenta
from apps.compras.models import Proveedor, OrdenCompra, OrdenCompraDetalle, Compra
from apps.inventario.models.producto import Producto
from apps.inventario.models.almacen import Almacen
from apps.cotizaciones.models import Cotizacion, DetalleCotizacion
from apps.cotizaciones.services.conversion_service import convertir_cotizacion_a_venta
from apps.compras.services.factura_service import registrar_factura, FacturaError
from apps.core.services import tipo_cambio as tc_mod
from apps.authentication.models import CustomUser


def _base(modo='sin_stock'):
    emp = Empresa.objects.create(nombre='E', ruc='20999999991', modo_inventario=modo)
    cli = Cliente.objects.create(empresa=emp, nombre='C', documento='12345678', tipo_documento='ruc')
    prov = Proveedor.objects.create(empresa=emp, ruc='20111111111', razon_social='ACME SAC',
                                    telefono='999', email='a@a.com', direccion='Av. 1')
    user = CustomUser(email='u@t.com', nombre='T', apellido='U', empresa=emp, is_superuser=True)
    user.set_password('x'); user.save()
    return emp, cli, prov, user


def _cotizacion_con_costo(emp, cli, prov, user, costo='600.00', precio='1000.00'):
    cot = Cotizacion.objects.create(
        empresa=emp, cliente=cli, usuario_creador=user, asunto='a',
        fecha_vencimiento=date(2099, 1, 1), estado='aceptada', moneda='PEN',
    )
    DetalleCotizacion.objects.create(
        cotizacion=cot, descripcion='Item texto libre', cantidad=2,
        precio_unitario=Decimal(precio), proveedor=prov,
        costo_unitario=Decimal(costo), orden=1,
    )
    return cot


class CostoPrioridadTests(TestCase):
    def setUp(self):
        cache.clear()
        self.emp, self.cli, self.prov, self.user = _base()

    def _convertir(self):
        with mock.patch.object(tc_mod, 'get_tc_venta', return_value=Decimal('1.0')):
            return convertir_cotizacion_a_venta(
                Cotizacion.objects.get(id=self.cot.id)
            )

    def test_conversion_copia_costo_a_detalleventa(self):
        self.cot = _cotizacion_con_costo(self.emp, self.cli, self.prov, self.user)
        venta = self._convertir()
        d = venta.detalles.first()
        self.assertEqual(d.costo_unitario, Decimal('600.00'))

    def test_prioridad_oc_sobre_cotizacion_y_factura_sobre_oc(self):
        self.cot = _cotizacion_con_costo(self.emp, self.cli, self.prov, self.user)
        venta = self._convertir()

        # OC recién creada está en BORRADOR → aún no es compromiso:
        # la fuente sigue siendo el snapshot de cotización.
        info = venta.costo_info()
        self.assertEqual(info['fuente'], 'cotizacion')
        self.assertEqual(info['costo_pen'], Decimal('1200.00'))

        # Aprobar la OC → fuente 'oc' (subtotal 1200 = 2×600, sin IGV)
        oc = venta.ordenes_compra.first()
        oc.estado = 'aprobada'
        oc.save()
        venta = Venta.objects.get(id=venta.id)
        info = venta.costo_info()
        self.assertEqual(info['fuente'], 'oc')
        self.assertEqual(info['costo_pen'], Decimal('1200.00'))

        # Registrar factura → fuente 'factura'
        registrar_factura(oc, numero_factura='F001-123', fecha_factura=date.today())
        venta = Venta.objects.get(id=venta.id)
        info = venta.costo_info()
        self.assertEqual(info['fuente'], 'factura')
        self.assertEqual(info['costo_pen'], Decimal('1200.00'))

        # Utilidad = subtotal sin IGV − costo sin IGV
        # Venta: 2×1000 con IGV incluido → subtotal = 2000/1.18 = 1694.92
        self.assertAlmostEqual(
            float(venta.utilidad_bruta_pen),
            float(venta.subtotal_pen - Decimal('1200.00')), places=2,
        )

    def test_sin_oc_usa_cotizacion_snapshot(self):
        self.cot = _cotizacion_con_costo(self.emp, self.cli, self.prov, self.user)
        venta = self._convertir()
        venta.ordenes_compra.all().delete()
        venta = Venta.objects.get(id=venta.id)
        info = venta.costo_info()
        self.assertEqual(info['fuente'], 'cotizacion')
        self.assertEqual(info['costo_pen'], Decimal('1200.00'))

    def test_costo_cero_es_sin_dato(self):
        """Costo 0 en cotización y catálogo → None, nunca margen 100%."""
        v = Venta.objects.create(
            empresa=self.emp, cliente=self.cli, fecha_emision=date.today(),
            tipo_venta='contado', moneda='PEN', estado='pendiente',
        )
        prod = Producto.objects.create(
            empresa=self.emp, sku='SKU-0', nombre='P0', tipo_producto='FINISHED',
            precio_venta=Decimal('100'), precio_compra=Decimal('0'),
        )
        DetalleVenta.objects.create(venta=v, producto=prod, cantidad=1,
                                    precio_unitario=Decimal('118'),
                                    costo_unitario=Decimal('0'))
        self.assertIsNone(v.costo_info())
        self.assertIsNone(v.utilidad_bruta_pen)

    def test_catalogo_solo_si_mayor_a_cero(self):
        v = Venta.objects.create(
            empresa=self.emp, cliente=self.cli, fecha_emision=date.today(),
            tipo_venta='contado', moneda='PEN', estado='pendiente',
        )
        prod = Producto.objects.create(
            empresa=self.emp, sku='SKU-60', nombre='P60', tipo_producto='FINISHED',
            precio_venta=Decimal('100'), precio_compra=Decimal('60'),
        )
        DetalleVenta.objects.create(venta=v, producto=prod, cantidad=2,
                                    precio_unitario=Decimal('118'))
        info = v.costo_info()
        self.assertEqual(info['fuente'], 'catalogo')
        self.assertEqual(info['costo_pen'], Decimal('120.00'))


class RegistrarFacturaTests(TestCase):
    def setUp(self):
        cache.clear()
        self.emp, self.cli, self.prov, self.user = _base()
        Almacen.objects.create(empresa=self.emp, nombre='Central', direccion='x')
        self.cot = _cotizacion_con_costo(self.emp, self.cli, self.prov, self.user)
        with mock.patch.object(tc_mod, 'get_tc_venta', return_value=Decimal('1.0')):
            self.venta = convertir_cotizacion_a_venta(self.cot)
        self.oc = self.venta.ordenes_compra.first()
        self.oc.estado = 'aprobada'
        self.oc.save()

    def test_crea_compra_vinculada_con_totales_y_tc_de_la_oc(self):
        compra = registrar_factura(self.oc, numero_factura='F001-9',
                                   fecha_factura=date.today())
        self.assertEqual(compra.orden_compra_id, self.oc.id)
        self.assertEqual(compra.subtotal, self.oc.subtotal)   # 1200 sin IGV
        self.assertEqual(compra.igv, self.oc.igv)             # 216
        self.assertEqual(compra.total, self.oc.total)         # 1416
        self.assertEqual(compra.tipo_cambio, self.oc.tipo_cambio)
        self.assertEqual(compra.moneda, self.oc.moneda)
        self.assertEqual(compra.estado, 'pendiente')          # cuenta por pagar
        self.assertEqual(compra.referencia, 'F001-9')

    def test_afecta_igv_neto_y_por_pagar(self):
        from apps.dashboard.services.metricas import MetricasService
        hoy = date.today()
        m = MetricasService(self.emp, hoy.replace(day=1), hoy)
        igv_antes = m.igv_devengo()
        registrar_factura(self.oc, numero_factura='F001-9', fecha_factura=hoy)
        igv_despues = m.igv_devengo()
        # Crédito fiscal: igv_compras sube en oc.igv → por_pagar baja
        self.assertAlmostEqual(
            igv_despues['igv_compras'] - igv_antes['igv_compras'],
            float(self.oc.igv), places=2,
        )
        # Cuenta por pagar: compra pendiente con el total de la factura
        pendientes = Compra.objects.filter(empresa=self.emp, estado='pendiente')
        self.assertEqual(pendientes.count(), 1)
        self.assertEqual(pendientes.first().total, self.oc.total)

    def test_idempotente_una_factura_por_oc(self):
        registrar_factura(self.oc, numero_factura='F001-9', fecha_factura=date.today())
        with self.assertRaises(FacturaError):
            registrar_factura(self.oc, numero_factura='F001-10', fecha_factura=date.today())
        self.assertEqual(Compra.objects.filter(orden_compra=self.oc).count(), 1)

    def test_borrador_no_facturable(self):
        self.oc.estado = 'borrador'
        self.oc.save()
        with self.assertRaises(FacturaError):
            registrar_factura(self.oc, numero_factura='F1', fecha_factura=date.today())
