"""fix/anular-venta — ANULAR ≠ ELIMINAR.

Bug de prod: el botón «Anular» llamaba ventasService.deleteVenta, que nunca
existió. Ahora POST /api/ventas/{id}/anular/ (solo admin, motivo obligatorio)
deja la venta con su número, la saca de CxC/KPIs y revierte stock y kárdex.
"""
import datetime
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.utils import timezone
from rest_framework.test import APITestCase

from apps.cotizaciones.models import Cotizacion
from apps.dashboard.services.metricas import MetricasService
from apps.empresas.models import Empresa
from apps.guias.models import GuiaRemision
from apps.inventario.models.almacen import Almacen
from apps.inventario.models.inventario_productos_terminados import InventarioProductosTerminados
from apps.inventario.models.movimiento_inventario import MovimientoInventario
from apps.inventario.models.producto import Producto
from apps.ventas.models import Cliente, DetalleVenta, PagoVenta, Venta

User = get_user_model()


class AnularVentaTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cache.set(f'tc_venta_{datetime.date.today().isoformat()}', '3.80', 3600)
        cls.emp = Empresa.objects.create(nombre='Anula SA', ruc='20666666661', modo_inventario='con_stock')
        cls.emp_b = Empresa.objects.create(nombre='Otra SA', ruc='20666666662')
        mk = lambda u, e, rol: User.objects.create_user(
            username=u, email=u, password='x', nombre='N', apellido='A', empresa=e, rol=rol)
        cls.admin = mk('admin@an.pe', cls.emp, 'admin')
        cls.operador = mk('op@an.pe', cls.emp, 'operador')
        cls.lector = mk('lee@an.pe', cls.emp, 'solo_lectura')
        cls.admin_b = mk('admin@b.pe', cls.emp_b, 'admin')
        cls.cli = Cliente.objects.create(empresa=cls.emp, nombre='Cliente A',
                                         documento='20666666663', tipo_documento='ruc')
        cls.alm = Almacen.objects.create(empresa=cls.emp, nombre='Central', direccion='x')
        cls.prod = Producto.objects.create(
            empresa=cls.emp, sku='AN-1', nombre='Producto stock', tipo_producto='FINISHED',
            controla_stock=True, stock_total=Decimal('10'), precio_venta=Decimal('100'),
            precio_compra=Decimal('60'), almacen=cls.alm)

    def setUp(self):
        cache.clear()
        cache.set(f'tc_venta_{datetime.date.today().isoformat()}', '3.80', 3600)
        self.client.force_authenticate(self.admin)

    # ── helpers ──────────────────────────────────────────────────────────────
    def _venta_credito(self, total='118.00'):
        r = self.client.post('/api/ventas/', {
            'cliente_id': self.cli.id, 'fecha_emision': timezone.localdate().isoformat(),
            'estado': 'pendiente', 'tipo_venta': 'credito_30', 'metodo_pago': 'transferencia',
            'moneda': 'PEN', 'igv_incluido': True,
            'detalles': [{'producto': None, 'descripcion': 'Servicio', 'cantidad': 1,
                          'precio_unitario': total}],
        }, format='json')
        self.assertEqual(r.status_code, 201, r.content[:300])
        return Venta.objects.get(pk=r.data['id'])

    def _anular(self, venta, motivo='El cliente desistió', user=None):
        if user:
            self.client.force_authenticate(user)
        return self.client.post(f'/api/ventas/{venta.id}/anular/', {'motivo': motivo}, format='json')

    # ── CxC, totales, KPIs ───────────────────────────────────────────────────
    def test_anular_saca_de_cxc_y_de_los_totales_conservando_el_numero(self):
        venta = self._venta_credito()
        numero = venta.numero
        hoy = timezone.localdate()
        m = MetricasService(self.emp, hoy.replace(day=1), hoy)
        self.assertEqual(m.ventas_qs().count(), 1)
        self.assertEqual(m.ventas_devengo('total')['total_pen'], Decimal('118.00'))

        r = self._anular(venta)
        self.assertEqual(r.status_code, 200, r.content[:300])
        venta.refresh_from_db()
        self.assertEqual(venta.estado, 'anulado')
        self.assertEqual(venta.numero, numero)                     # conserva el número
        self.assertEqual(venta.anulado_por, self.admin)
        self.assertIsNotNone(venta.anulado_en)
        self.assertEqual(venta.motivo_anulacion, 'El cliente desistió')

        m = MetricasService(self.emp, hoy.replace(day=1), hoy)
        self.assertEqual(m.ventas_qs().count(), 0)                 # ventas del mes / KPIs
        self.assertEqual(m.ventas_devengo('total')['total_pen'], 0)
        self.assertFalse(Venta.objects.filter(empresa=self.emp, estado='pendiente').exists())  # CxC

        # placeholder de crédito: anulado, NO borrado
        ph = PagoVenta.objects.get(venta=venta)
        self.assertTrue(ph.anulado)
        self.assertEqual(ph.metodo_pago, 'pendiente')

        # el correlativo nunca se reutiliza: la siguiente venta toma otro número
        otra = self._venta_credito()
        self.assertNotEqual(otra.numero, numero)

    def test_resumen_ventas_del_bot_excluye_anuladas(self):
        from apps.canales.nucleo import esquemas as E
        from apps.canales.nucleo.servicios import resumen_ventas
        venta = self._venta_credito()
        self._anular(venta)
        res = resumen_ventas(self.admin, E.ResumenVentas())
        self.assertEqual((res['n_ventas'], res['por_cobrar']), (0, '0.00'))

    def test_dashboard_se_invalida_al_anular(self):
        venta = self._venta_credito()
        self.client.get('/api/dashboard/resumen/')
        self.assertIsNotNone(cache.get(f'dashboard_mes_{self.emp.id}'))
        self._anular(venta)
        self.assertIsNone(cache.get(f'dashboard_mes_{self.emp.id}'))

    # ── reglas que bloquean ──────────────────────────────────────────────────
    def test_venta_con_pago_real_no_se_anula(self):
        venta = self._venta_credito()
        PagoVenta.objects.create(venta=venta, monto=Decimal('50'), metodo_pago='efectivo',
                                 fecha=timezone.localdate())
        r = self._anular(venta)
        self.assertEqual(r.status_code, 400)
        self.assertIn('Primero revierte los pagos', r.data['detail'])
        venta.refresh_from_db()
        self.assertEqual(venta.estado, 'pendiente')

    def test_anular_dos_veces_400(self):
        venta = self._venta_credito()
        self.assertEqual(self._anular(venta).status_code, 200)
        r = self._anular(venta)
        self.assertEqual(r.status_code, 400)
        self.assertIn('ya está anulada', r.data['detail'])

    def test_motivo_obligatorio(self):
        venta = self._venta_credito()
        r = self._anular(venta, motivo='   ')
        self.assertEqual(r.status_code, 400)
        self.assertIn('motivo', r.data['detail'])

    def test_guia_emitida_bloquea_y_borrador_se_cancela(self):
        venta = self._venta_credito()
        g = GuiaRemision.objects.create(
            empresa=self.emp, tipo='venta', motivo='venta', estado='emitida', numero='T001-1',
            cliente=self.cli, fecha_emision=timezone.localdate(), fecha_traslado=timezone.localdate(),
            observaciones=f'Generada automáticamente desde Venta {venta.numero}', creado_por=self.admin)
        r = self._anular(venta)
        self.assertEqual(r.status_code, 400)
        self.assertIn('T001-1', r.data['detail'])
        GuiaRemision.objects.filter(pk=g.pk).update(estado='borrador')
        r = self._anular(venta)
        self.assertEqual(r.status_code, 200, r.content[:300])
        g.refresh_from_db()
        self.assertEqual(g.estado, 'cancelada')

    # ── roles y aislamiento ─────────────────────────────────────────────────
    def test_operador_y_solo_lectura_403(self):
        venta = self._venta_credito()
        self.assertEqual(self._anular(venta, user=self.operador).status_code, 403)
        self.assertEqual(self._anular(venta, user=self.lector).status_code, 403)
        venta.refresh_from_db()
        self.assertEqual(venta.estado, 'pendiente')

    def test_empresa_b_no_puede_anular_ventas_de_a_404(self):
        venta = self._venta_credito()
        self.assertEqual(self._anular(venta, user=self.admin_b).status_code, 404)
        venta.refresh_from_db()
        self.assertEqual(venta.estado, 'pendiente')

    def test_delete_fisico_ya_no_existe_405(self):
        venta = self._venta_credito()
        r = self.client.delete(f'/api/ventas/{venta.id}/')
        self.assertEqual(r.status_code, 405)
        self.assertTrue(Venta.objects.filter(pk=venta.pk).exists())

    def test_cambiar_estado_a_anulado_redirige_al_camino_con_motivo(self):
        venta = self._venta_credito()
        r = self.client.post(f'/api/ventas/{venta.id}/cambiar_estado/', {'estado': 'anulado'}, format='json')
        self.assertEqual(r.status_code, 400)
        self.assertIn('/anular/', r.data['detail'])

    # ── stock y kárdex ─────────────────────────────────────────────────────
    def test_venta_entregada_revierte_stock_con_reversa_en_kardex(self):
        ipt = InventarioProductosTerminados.objects.create(
            empresa=self.emp, producto=self.prod, almacen=self.alm,
            cantidad_disponible=Decimal('10'), cantidad_reservada=Decimal('0'))
        v = Venta.objects.create(empresa=self.emp, cliente=self.cli,
                                 fecha_emision=timezone.localdate(), tipo_venta='contado')
        DetalleVenta.objects.create(venta=v, producto=self.prod, cantidad=Decimal('4'),
                                    precio_unitario=Decimal('100'), origen='stock')
        DetalleVenta.objects.create(venta=v, producto=None, descripcion='Instalación',
                                    cantidad=Decimal('1'), precio_unitario=Decimal('50'))
        Venta.objects.filter(pk=v.pk).update(estado='pendiente')   # sin pagos reales
        v.refresh_from_db()
        v.cambiar_estado_operativo('entregado', usuario=None)
        ipt.refresh_from_db()
        self.assertEqual(ipt.cantidad_disponible, Decimal('6'))

        r = self._anular(v, motivo='Devolución total')
        self.assertEqual(r.status_code, 200, r.content[:300])
        ipt.refresh_from_db()
        self.assertEqual(ipt.cantidad_disponible, Decimal('10'))     # reintegrado
        det = v.detalles.get(producto=self.prod)
        self.assertFalse(det.stock_descontado)
        rev = MovimientoInventario.objects.get(venta_id=v.id, tipo_movimiento='devolucion_venta')
        self.assertEqual(rev.cantidad_entrada, Decimal('4'))           # reversa, no borrado
        self.assertEqual(rev.numero_documento, v.numero)
        # la línea libre no se tocó y no generó movimientos
        self.assertEqual(MovimientoInventario.objects.filter(venta_id=v.id).count(), 1)

    def test_kardex_legado_salida_venta_se_revierte_sin_borrar(self):
        v = self._venta_credito()
        original = MovimientoInventario.objects.create(
            empresa=self.emp, producto=self.prod, almacen=self.alm, fecha=timezone.now(),
            tipo_movimiento='salida_venta', tipo_documento='venta', numero_documento=v.numero,
            cantidad_salida=Decimal('2'), costo_unitario=Decimal('60'), venta_id=v.id)
        self.assertEqual(self._anular(v).status_code, 200)
        self.assertTrue(MovimientoInventario.objects.filter(pk=original.pk).exists())   # intacto
        rev = MovimientoInventario.objects.get(venta_id=v.id, tipo_movimiento='devolucion_venta')
        self.assertEqual(rev.cantidad_entrada, Decimal('2'))

    # ── cotización de origen ───────────────────────────────────────────────
    def test_cotizacion_de_origen_vuelve_a_aceptada_y_se_puede_reconvertir(self):
        from apps.cotizaciones.services.conversion_service import convertir_cotizacion_a_venta
        cot = Cotizacion.objects.create(
            empresa=self.emp, cliente=self.cli, usuario_creador=self.admin, asunto='x',
            fecha_vencimiento=timezone.localdate() + timezone.timedelta(days=10))
        cot.detalles.create(producto=None, descripcion='Servicio', cantidad=Decimal('1'),
                            precio_unitario=Decimal('100'))
        venta = convertir_cotizacion_a_venta(cot)
        Venta.objects.filter(pk=venta.pk).update(estado='pendiente')
        r = self._anular(venta)
        self.assertEqual(r.status_code, 200, r.content[:300])
        self.assertTrue(any('aceptada' in a for a in r.data['avisos']))
        cot.refresh_from_db()
        self.assertEqual((cot.estado, cot.venta_id), ('aceptada', None))
        nueva = convertir_cotizacion_a_venta(cot)                    # NUEVA venta, no la anulada
        self.assertNotEqual(nueva.pk, venta.pk)
        self.assertNotEqual(nueva.numero, venta.numero)
