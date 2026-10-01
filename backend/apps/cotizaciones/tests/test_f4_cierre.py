"""
F4 — cierre de cotizaciones no ganadas + alertas de dashboard.

Rechazo con motivo obligatorio, esta_vencida (derivado), filtro ?vencida, y que
el dashboard NO alerte ventas históricas sin historial operativo (H3/punto 10).
"""
from datetime import timedelta
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIRequestFactory, force_authenticate

from apps.empresas.models import Empresa
from apps.authentication.models import CustomUser
from apps.ventas.models import Cliente, Venta, DetalleVenta, HistorialEstadoVenta
from apps.cotizaciones.models import Cotizacion
from apps.cotizaciones.views import CotizacionViewSet


class F4Base(TestCase):
    _seq = 0

    def _next(self):
        F4Base._seq += 1
        return F4Base._seq

    def _empresa(self, modo='con_stock'):
        n = self._next()
        return Empresa.objects.create(nombre=f'E{n}', ruc=f'20{n:09d}', modo_inventario=modo)

    def _user(self, empresa):
        n = self._next()
        u = CustomUser(email=f'u{n}@t.com', nombre='T', apellido='U', empresa=empresa, is_superuser=True)
        u.set_password('x'); u.save()
        return u

    def _cliente(self, empresa):
        n = self._next()
        return Cliente.objects.create(empresa=empresa, nombre='C', documento=f'{n:08d}', tipo_documento='ruc')

    def _cotizacion(self, empresa, user, cliente, estado='enviada', vence_en_dias=30):
        return Cotizacion.objects.create(
            empresa=empresa, cliente=cliente, usuario_creador=user, asunto='Cot',
            fecha_vencimiento=timezone.now().date() + timedelta(days=vence_en_dias),
            estado=estado,
        )


class RechazoTests(F4Base):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.view = CotizacionViewSet.as_view({'post': 'cambiar_estado'})

    def _rechazar(self, cot, user, body):
        req = self.factory.post('/x', body, format='json')
        force_authenticate(req, user=user)
        return self.view(req, pk=cot.id)

    def test_rechazo_sin_motivo_400(self):
        emp = self._empresa(); u = self._user(emp); cli = self._cliente(emp)
        cot = self._cotizacion(emp, u, cli)
        resp = self._rechazar(cot, u, {'estado': 'rechazada'})
        self.assertEqual(resp.status_code, 400)
        cot.refresh_from_db()
        self.assertEqual(cot.estado, 'enviada')  # no cambió

    def test_rechazo_con_motivo_ok(self):
        emp = self._empresa(); u = self._user(emp); cli = self._cliente(emp)
        cot = self._cotizacion(emp, u, cli)
        resp = self._rechazar(cot, u, {'estado': 'rechazada', 'motivo_rechazo': 'precio'})
        self.assertEqual(resp.status_code, 200)
        cot.refresh_from_db()
        self.assertEqual(cot.estado, 'rechazada')
        self.assertEqual(cot.motivo_rechazo, 'precio')

    def test_rechazo_otro_sin_nota_400(self):
        emp = self._empresa(); u = self._user(emp); cli = self._cliente(emp)
        cot = self._cotizacion(emp, u, cli)
        resp = self._rechazar(cot, u, {'estado': 'rechazada', 'motivo_rechazo': 'otro'})
        self.assertEqual(resp.status_code, 400)

    def test_rechazo_otro_con_nota_ok(self):
        emp = self._empresa(); u = self._user(emp); cli = self._cliente(emp)
        cot = self._cotizacion(emp, u, cli)
        resp = self._rechazar(cot, u, {'estado': 'rechazada', 'motivo_rechazo': 'otro', 'motivo_rechazo_nota': 'detalle'})
        self.assertEqual(resp.status_code, 200)
        cot.refresh_from_db()
        self.assertEqual(cot.motivo_rechazo_nota, 'detalle')


class VencidaTests(F4Base):
    def test_esta_vencida_derivado(self):
        emp = self._empresa(); u = self._user(emp); cli = self._cliente(emp)
        cot = self._cotizacion(emp, u, cli, estado='enviada', vence_en_dias=-1)
        self.assertTrue(cot.esta_vencida)
        # rechazada no se considera vencida
        cot_r = self._cotizacion(emp, u, cli, estado='rechazada', vence_en_dias=-1)
        self.assertFalse(cot_r.esta_vencida)

    def test_filtro_vencida_en_queryset(self):
        emp = self._empresa(); u = self._user(emp); cli = self._cliente(emp)
        vencida = self._cotizacion(emp, u, cli, estado='enviada', vence_en_dias=-5)
        vigente = self._cotizacion(emp, u, cli, estado='enviada', vence_en_dias=10)

        factory = APIRequestFactory()
        view = CotizacionViewSet.as_view({'get': 'list'})
        req = factory.get('/x', {'vencida': 'true'})
        force_authenticate(req, user=u)
        resp = view(req)
        results = resp.data['results'] if isinstance(resp.data, dict) and 'results' in resp.data else resp.data
        ids = [r['id'] for r in results]
        self.assertIn(vencida.id, ids)
        self.assertNotIn(vigente.id, ids)


class DashboardAlertasTests(F4Base):
    def _venta(self, empresa, cliente, estado_operativo, con_historial, dias_viejo=10):
        v = Venta.objects.create(empresa=empresa, cliente=cliente,
                                 fecha_emision=timezone.now().date(), tipo_venta='contado')
        Venta.objects.filter(pk=v.pk).update(
            estado_operativo=estado_operativo,
            estado_operativo_actualizado=timezone.now() - timedelta(days=dias_viejo),
        )
        if con_historial:
            HistorialEstadoVenta.objects.create(venta=v, estado_anterior='', estado_nuevo=estado_operativo)
        v.refresh_from_db()
        return v

    def test_dashboard_no_alerta_ventas_sin_historial(self):
        # Replica la lógica de DashboardResumen (#13) para validar el filtro
        # historial_operativo__isnull=False sin depender de la red (tipo de cambio).
        emp = self._empresa('con_stock'); u = self._user(emp); cli = self._cliente(emp)

        # Histórica (sin historial) con estado viejo → NO debe alertar.
        self._venta(emp, cli, 'comprado', con_historial=False, dias_viejo=30)
        # Nueva (con historial) vencida → SÍ debe alertar.
        self._venta(emp, cli, 'comprado', con_historial=True, dias_viejo=30)

        ventas_con_historial = Venta.objects.filter(
            empresa=emp, historial_operativo__isnull=False,
        ).distinct()
        ventas_fuera_sla = sum(1 for v in ventas_con_historial if v.estado_sla_operativo == 'vencido')
        self.assertEqual(ventas_fuera_sla, 1)

    def test_cotizaciones_sin_respuesta_cuenta(self):
        emp = self._empresa(); u = self._user(emp); cli = self._cliente(emp)
        vieja = self._cotizacion(emp, u, cli, estado='enviada')
        Cotizacion.objects.filter(pk=vieja.pk).update(fecha_emision=timezone.now().date() - timedelta(days=10))
        self._cotizacion(emp, u, cli, estado='enviada')  # reciente → no cuenta

        limite = timezone.now().date() - timedelta(days=7)
        count = Cotizacion.objects.filter(empresa=emp, estado='enviada', fecha_emision__lt=limite).count()
        self.assertEqual(count, 1)
