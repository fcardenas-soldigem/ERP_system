"""
MetricasService — definiciones de negocio (devengo/caja) decididas 2026-10-09.

VENTAS = devengo (emitidas, sin borrador/anulado, independiente del pago).
COBROS = caja (PagoVenta por fecha, valorizado con el TC de SU venta).
STOCK  = solo empresas que manejan stock.
MARGEN = null sin costos registrados, nunca 0%.
"""
from datetime import date
from decimal import Decimal
from unittest import mock

from django.core.cache import cache
from django.test import TestCase

from apps.empresas.models import Empresa
from apps.ventas.models import Cliente, Venta, PagoVenta, DetalleVenta
from apps.inventario.models.producto import Producto
from apps.core.services import tipo_cambio as tc_mod
from apps.dashboard.services.metricas import MetricasService


def _empresa(modo='con_stock'):
    return Empresa.objects.create(
        nombre=f'E-{modo}', ruc=f'20{abs(hash(modo)) % 10**9:09d}', modo_inventario=modo,
    )


def _cliente(emp):
    return Cliente.objects.create(empresa=emp, nombre='C', documento='12345678', tipo_documento='ruc')


def _venta(emp, cli, fecha, moneda, total, estado, tc=None):
    """Crea venta y fija totales directo (el pre_save los pone en 0)."""
    with mock.patch.object(tc_mod, 'get_tc_venta', return_value=tc or Decimal('3.50')):
        v = Venta.objects.create(
            empresa=emp, cliente=cli, fecha_emision=fecha,
            tipo_venta='contado', moneda=moneda, estado=estado,
        )
    total_d = Decimal(str(total))
    subtotal = (total_d / Decimal('1.18')).quantize(Decimal('0.01'))
    Venta.objects.filter(id=v.id).update(
        total=total_d, subtotal=subtotal, igv=total_d - subtotal, estado=estado,
    )
    v.refresh_from_db()
    return v


class VentasDevengoTests(TestCase):
    def setUp(self):
        cache.clear()
        self.emp = _empresa()
        self.cli = _cliente(self.emp)
        self.svc = MetricasService(self.emp, date(2026, 10, 1), date(2026, 10, 31))

    def test_venta_pendiente_de_octubre_cuenta_en_ventas_del_mes(self):
        """BUG prod: 'Ventas del mes: S/ 0' con ventas emitidas pendientes de pago."""
        _venta(self.emp, self.cli, date(2026, 10, 1), 'PEN', '13921.20', 'pendiente')
        _venta(self.emp, self.cli, date(2026, 10, 5), 'PEN', '1000.00', 'pagado')
        _venta(self.emp, self.cli, date(2026, 10, 6), 'PEN', '500.00', 'borrador')   # NO cuenta
        _venta(self.emp, self.cli, date(2026, 10, 7), 'PEN', '700.00', 'anulado')    # NO cuenta

        d = self.svc.ventas_devengo('total')
        self.assertEqual(d['cantidad'], 2)                      # pendiente + pagado
        self.assertAlmostEqual(d['total_pen'], 14921.20, places=2)

    def test_pago_usd_convierte_con_tc_de_la_venta(self):
        """BUG prod: 'Tu caja S/ 6,371.68' era un pago de $6,371.68 sin convertir."""
        v = _venta(self.emp, self.cli, date(2026, 9, 15), 'USD', '6371.68',
                   'pagado', tc=Decimal('3.40'))
        PagoVenta.objects.create(venta=v, fecha=date(2026, 10, 3),
                                 monto=Decimal('6371.68'), metodo_pago='transferencia')

        cobros = self.svc.cobros()
        # $6,371.68 × 3.40 (TC de la venta, no el de hoy) = S/ 21,663.71
        self.assertAlmostEqual(cobros['total_pen'], float(Decimal('6371.68') * Decimal('3.40')), places=2)
        self.assertEqual(cobros['usd'], 6371.68)
        self.assertTrue(cobros['tiene_usd'])

    def test_margen_sin_costos_es_none_no_cero(self):
        """Sin producto.precio_compra no hay margen: None (el front muestra 'Sin datos de costo')."""
        v = _venta(self.emp, self.cli, date(2026, 10, 2), 'PEN', '1180.00', 'pendiente')
        prod = Producto.objects.create(
            empresa=self.emp, sku='SKU-SIN-COSTO', nombre='P', tipo_producto='FINISHED',
            precio_venta=Decimal('1000'), precio_compra=Decimal('0'),
        )
        DetalleVenta.objects.create(venta=v, producto=prod, cantidad=1,
                                    precio_unitario=Decimal('1180'))
        self.assertIsNone(self.svc.margen())

    def test_margen_con_costos_calcula_sobre_lineas_con_costo(self):
        v = _venta(self.emp, self.cli, date(2026, 10, 2), 'PEN', '1180.00', 'pagado')
        prod = Producto.objects.create(
            empresa=self.emp, sku='SKU-CON-COSTO', nombre='P2', tipo_producto='FINISHED',
            precio_venta=Decimal('1000'), precio_compra=Decimal('600'),
        )
        # igv_incluido=True por defecto → neto = 1180/1.18 = 1000; cogs = 600
        DetalleVenta.objects.create(venta=v, producto=prod, cantidad=1,
                                    precio_unitario=Decimal('1180'))
        m = self.svc.margen()
        self.assertIsNotNone(m)
        self.assertAlmostEqual(m['margen_bruto_pct'], 40.0, places=1)


class StockGatingTests(TestCase):
    def setUp(self):
        cache.clear()

    def test_sin_stock_no_maneja_stock(self):
        emp = _empresa('sin_stock')
        svc = MetricasService(emp, date(2026, 10, 1), date(2026, 10, 31))
        self.assertFalse(svc.maneja_stock())

    def test_con_stock_si_maneja(self):
        emp = _empresa('con_stock')
        svc = MetricasService(emp, date(2026, 10, 1), date(2026, 10, 31))
        self.assertTrue(svc.maneja_stock())


class TopProductosTests(TestCase):
    def setUp(self):
        cache.clear()
        self.emp = _empresa()
        self.cli = _cliente(self.emp)

    def test_sin_datos_del_mes_cae_a_90_dias_con_etiqueta(self):
        # Venta de hace 2 meses (fuera del mes actual, dentro de 90 días)
        hoy = date.today()
        hace_60 = hoy.replace(day=1)  # placeholder base
        from datetime import timedelta
        fecha_vieja = hoy - timedelta(days=60)
        v = _venta(self.emp, self.cli, fecha_vieja, 'PEN', '1180.00', 'pagado')
        prod = Producto.objects.create(
            empresa=self.emp, sku='SKU-TOP', nombre='Top', tipo_producto='FINISHED',
            precio_venta=Decimal('100'), precio_compra=Decimal('0'),
        )
        DetalleVenta.objects.create(venta=v, producto=prod, cantidad=3,
                                    precio_unitario=Decimal('100'))

        # Período = mes actual, sin ventas → fallback
        svc = MetricasService(self.emp, hoy.replace(day=1), hoy)
        top = svc.top_productos()
        self.assertEqual(top['periodo'], 'ultimos_90_dias')
        self.assertEqual(top['labels'], ['Top'])
