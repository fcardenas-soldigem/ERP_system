"""
Consistencia Dashboard ↔ Finanzas (fix/consistencia-finanzas).

#1 Por cobrar: UNA definición — ventas no anuladas/borrador con saldo > 0,
   en PEN con TC del documento. Dashboard y Finanzas leen la misma.
#3 Comparar contra 0 → None (el front muestra "—"); salud financiera con
   margen None → incompleto, nunca 100 "saludable".
"""
from datetime import date
from decimal import Decimal
from unittest import mock

from django.core.cache import cache
from django.test import TestCase

from apps.empresas.models import Empresa
from apps.ventas.models import Cliente, Venta
from apps.dashboard.services.metricas import MetricasService
from apps.finanzas.services import FinanzasService
from apps.core.services import tipo_cambio as tc_mod


def _base():
    emp = Empresa.objects.create(nombre='E', ruc='20888888881', modo_inventario='sin_stock')
    cli = Cliente.objects.create(empresa=emp, nombre='C', documento='12345678', tipo_documento='ruc')
    return emp, cli


def _venta(emp, cli, *, fecha=None, moneda='PEN', total='1000', estado='pendiente',
           tipo='contado', pagos='0', tc=None):
    with mock.patch.object(tc_mod, 'get_tc_venta', return_value=tc or Decimal('3.50')):
        v = Venta.objects.create(
            empresa=emp, cliente=cli, fecha_emision=fecha or date.today(),
            tipo_venta=tipo, moneda=moneda, estado=estado,
        )
    Venta.objects.filter(id=v.id).update(
        total=Decimal(total), subtotal=(Decimal(total) / Decimal('1.18')).quantize(Decimal('0.01')),
        estado=estado, pagos_total=Decimal(pagos),
    )
    v.refresh_from_db()
    return v


class PorCobrarUnificadoTests(TestCase):
    def setUp(self):
        cache.clear()
        self.emp, self.cli = _base()
        hoy = date.today()
        self.m = MetricasService(self.emp, hoy.replace(day=1), hoy)

    def test_contado_pendiente_cuenta(self):
        """El bug de prod: una venta contado pendiente (V-000073) debe contar."""
        _venta(self.emp, self.cli, total='560', tipo='contado')
        cxc = self.m.cuentas_por_cobrar()
        self.assertEqual(cxc['total_pen'], 560.0)
        self.assertEqual(cxc['cantidad'], 1)

    def test_pago_parcial_resta_del_saldo(self):
        _venta(self.emp, self.cli, total='1000', tipo='credito_30', pagos='400')
        cxc = self.m.cuentas_por_cobrar()
        self.assertEqual(cxc['total_pen'], 600.0)

    def test_anulada_y_borrador_no_cuentan(self):
        _venta(self.emp, self.cli, total='500', estado='anulado')
        _venta(self.emp, self.cli, total='700', estado='borrador')
        cxc = self.m.cuentas_por_cobrar()
        self.assertEqual(cxc['total_pen'], 0.0)

    def test_usd_valoriza_con_tc_del_documento(self):
        _venta(self.emp, self.cli, total='100', moneda='USD', tc=Decimal('3.40'))
        cxc = self.m.cuentas_por_cobrar()
        self.assertEqual(cxc['total_pen'], 340.0)

    def test_dashboard_y_finanzas_misma_cifra(self):
        """La prueba del bug: ambas pantallas leen la MISMA definición."""
        _venta(self.emp, self.cli, total='560', tipo='contado')                 # contado pendiente
        _venta(self.emp, self.cli, total='1000', tipo='credito_30', pagos='400')  # crédito parcial
        hoy = date.today()
        cxc_metricas = self.m.cuentas_por_cobrar()['total_pen']
        svc = FinanzasService(self.emp, hoy.replace(day=1), hoy)
        flujo = svc.calcular_flujo_caja()
        self.assertEqual(cxc_metricas, 1160.0)
        self.assertEqual(flujo['cxc_pendiente'], cxc_metricas)


class ComparacionesContraCeroTests(TestCase):
    def setUp(self):
        cache.clear()
        self.emp, self.cli = _base()

    def test_crecimiento_sin_mes_anterior_es_none(self):
        """Mes anterior en 0 → None (el front muestra '—'), nunca '+0.0%'."""
        _venta(self.emp, self.cli, total='1180', estado='pagado')
        hoy = date.today()
        svc = FinanzasService(self.emp, hoy.replace(day=1), hoy)
        cre = svc.calcular_crecimiento()
        self.assertIsNone(cre['revenue_growth_pct'])
        self.assertIsNone(cre['ticket_variacion_pct'])

    def test_semaforo_con_margen_none_es_incompleto(self):
        """Sin costos el score no puede ser un 100 'saludable'."""
        _venta(self.emp, self.cli, total='1180', estado='pagado')  # sin costo
        hoy = date.today()
        svc = FinanzasService(self.emp, hoy.replace(day=1), hoy)
        rent = svc.calcular_rentabilidad()
        self.assertTrue(rent['sin_datos_costo'])
        flujo = svc.calcular_flujo_caja()
        cxc = svc.calcular_cuentas_cobrar()
        cxp = svc.calcular_cuentas_pagar()
        sem = svc.calcular_semaforo(flujo, rent, cxc, cxp)
        self.assertTrue(sem['incompleto'])
        self.assertLess(sem['puntuacion'], 100)
        self.assertIn('faltan costos', sem['mensaje'].lower())
