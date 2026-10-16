"""
Suite de aislamiento multi-empresa (tenant isolation).

Un usuario de la empresa A NUNCA debe poder leer/modificar/saltar a datos de B.
Esta suite es permanente y debe correr en cada deploy.

Cobertura actual (crece con cada fix de la auditoría):
- C1 (CRÍTICO, corregido): un usuario NO puede cambiar su propia empresa vía el
  serializer de perfil ni vía PATCH /api/auth/profile/.
- Aislamiento de lista/detalle en ventas (representativo del patrón get_queryset).

Pendiente de ampliar (ver AUDITORIA_AISLAMIENTO_TENANTS.md, fases 2-3): recorrido
dinámico de TODO el router + ataques de FK cruzada en cotizaciones/servicios/OCS,
importar_excel, numeración concurrente y caché.
"""
from datetime import date
from decimal import Decimal

from unittest import mock

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from rest_framework.test import APIClient, APIRequestFactory

from apps.authentication.serializers import UserSerializer
from apps.empresas.models import Empresa
from apps.ventas.models import Cliente, Venta
from apps.inventario.models.producto import Producto
from apps.finanzas.models import CategoriaGasto
from apps.cotizaciones.serializers import DetalleCotizacionSerializer
from apps.servicios.serializers import OrdenServicioSerializer
from apps.finanzas.serializers import GastoOperativoSerializer

User = get_user_model()
_factory = APIRequestFactory()


def _req(user):
    r = _factory.post('/')
    r.user = user
    return r


class TenantSetup(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.A = Empresa.objects.create(nombre='Empresa A', ruc='20000000001')
        self.B = Empresa.objects.create(nombre='Empresa B', ruc='20000000002')
        self.user_a = self._user('a@a.pe', self.A)
        self.user_b = self._user('b@b.pe', self.B)
        # Datos de B que A no debe poder ver/tocar.
        self.cli_b = Cliente.objects.create(
            empresa=self.B, nombre='Cliente B', documento='10000000002', tipo_documento='ruc')
        self.venta_b = Venta.objects.create(
            empresa=self.B, numero='V-B-1', cliente=self.cli_b, fecha_emision=date.today(),
            total=Decimal('100.00'), moneda='PEN')
        self.prod_b = Producto.objects.create(empresa=self.B, sku='SKU-B', nombre='Prod B')
        self.catgasto_b = CategoriaGasto.objects.create(empresa=self.B, nombre='CatGasto B')
        # Objetos propios de A (controles positivos).
        self.cli_a = Cliente.objects.create(
            empresa=self.A, nombre='Cliente A', documento='10000000001', tipo_documento='ruc')
        self.prod_a = Producto.objects.create(empresa=self.A, sku='SKU-A', nombre='Prod A')

    def _user(self, email, empresa):
        u = User(email=email, username=email)
        u.set_password('x')
        u.empresa = empresa
        u.save()
        return u


class TenantJumpTests(TenantSetup):
    """C1 (CRÍTICO): el usuario no puede cambiar su empresa."""

    def test_serializer_empresa_es_read_only(self):
        s = UserSerializer(self.user_a, data={'empresa': self.B.id, 'nombre': 'Hack'}, partial=True)
        self.assertTrue(s.is_valid(), s.errors)
        s.save()
        self.user_a.refresh_from_db()
        self.assertEqual(self.user_a.empresa_id, self.A.id, 'la empresa NO debe cambiar')

    def test_profile_put_no_salta_de_empresa(self):
        self.client.force_authenticate(self.user_a)
        self.client.put('/api/auth/profile/', {'empresa': self.B.id}, format='json')
        self.user_a.refresh_from_db()
        self.assertEqual(self.user_a.empresa_id, self.A.id)


class VentasIsolationTests(TenantSetup):
    def test_detalle_propia_ok_vs_de_B_404(self):
        # Control positivo determinista (a prueba de contaminación de la suite):
        # A SÍ ve su propia venta por detalle; la de B da 404. Juntos = aislamiento.
        venta_a = Venta.objects.create(
            empresa=self.A, cliente=self.cli_a, fecha_emision=date.today(),
            total=Decimal('50.00'), moneda='PEN')
        self.client.force_authenticate(self.user_a)
        self.assertEqual(self.client.get(f'/api/ventas/{venta_a.id}/').status_code, 200)
        self.assertEqual(self.client.get(f'/api/ventas/{self.venta_b.id}/').status_code, 404)

    def test_detalle_de_B_da_404_no_403(self):
        # 404 (no revelar que existe), no 403.
        self.client.force_authenticate(self.user_a)
        r = self.client.get(f'/api/ventas/{self.venta_b.id}/')
        self.assertEqual(r.status_code, 404)

    def test_put_sobre_venta_de_B_404_y_queda_intacta(self):
        self.client.force_authenticate(self.user_a)
        r = self.client.patch(f'/api/ventas/{self.venta_b.id}/', {'notas': 'hackeado'}, format='json')
        self.assertEqual(r.status_code, 404)
        self.venta_b.refresh_from_db()
        self.assertNotEqual(self.venta_b.notas, 'hackeado')

    def test_delete_sobre_venta_de_B_no_la_borra(self):
        self.client.force_authenticate(self.user_a)
        r = self.client.delete(f'/api/ventas/{self.venta_b.id}/')
        # Lo esencial: NO se borra (status 404/400/403, nunca 204/200).
        self.assertNotIn(r.status_code, (200, 204), 'no debe permitir borrar la venta de B')
        self.assertTrue(Venta.objects.filter(pk=self.venta_b.pk).exists())


class FKScopingTests(TenantSetup):
    """Patrón único §6: una FK con id de B → serializer inválido (→ 400)."""

    def test_detalle_cotizacion_producto_de_B_rechazado(self):
        ser = DetalleCotizacionSerializer(
            data={'producto': self.prod_b.id, 'cantidad': 1, 'precio_unitario': 10},
            context={'request': _req(self.user_a)})
        self.assertFalse(ser.is_valid())
        self.assertIn('producto', ser.errors)

    def test_detalle_cotizacion_producto_propio_ok(self):
        ser = DetalleCotizacionSerializer(
            data={'producto': self.prod_a.id, 'descripcion': 'Item A', 'cantidad': 1, 'precio_unitario': 10},
            context={'request': _req(self.user_a)})
        self.assertTrue(ser.is_valid(), ser.errors)

    def test_orden_servicio_cliente_de_B_rechazado(self):
        ser = OrdenServicioSerializer(
            data={'cliente': self.cli_b.id, 'fecha_ingreso': str(date.today())},
            context={'request': _req(self.user_a)})
        self.assertFalse(ser.is_valid())
        self.assertIn('cliente', ser.errors)

    def test_gasto_categoria_de_B_rechazada(self):
        ser = GastoOperativoSerializer(
            data={'categoria': self.catgasto_b.id, 'descripcion': 'x', 'monto': '10',
                  'fecha': str(date.today())},
            context={'request': _req(self.user_a)})
        self.assertFalse(ser.is_valid())
        self.assertIn('categoria', ser.errors)


class PrivilegeEscalationTests(TenantSetup):
    def test_profile_no_puede_setear_is_staff(self):
        self.assertFalse(self.user_a.is_staff)
        s = UserSerializer(self.user_a, data={'is_staff': True}, partial=True)
        self.assertTrue(s.is_valid(), s.errors)
        s.save()
        self.user_a.refresh_from_db()
        self.assertFalse(self.user_a.is_staff, 'is_staff no debe poder activarse vía perfil')


@override_settings(ROOT_URLCONF='config.urls')
class ResumenComprasAislamientoTests(TenantSetup):
    """/api/compras/resumen/: B nunca ve los totales de compras de A."""

    def test_B_no_ve_totales_de_A(self):
        from decimal import Decimal
        from datetime import date
        from apps.compras.models import Compra, Proveedor
        from apps.inventario.models.almacen import Almacen

        prov_a = Proveedor.objects.create(empresa=self.A, razon_social='Prov A', ruc='20000000011')
        alm_a = Almacen.objects.create(empresa=self.A, nombre='Alm A')
        with mock.patch('apps.compras.models.Compra.asegurar_tipo_cambio', lambda self: None):
            compra_a = Compra.objects.create(
                empresa=self.A, proveedor=prov_a, almacen=alm_a, fecha_emision=date.today())
        Compra.objects.filter(pk=compra_a.pk).update(total=Decimal('777.00'))

        # B consulta el resumen: no debe ver NI el conteo NI el monto de A.
        self.client.force_authenticate(self.user_b)
        rb = self.client.get('/api/compras/resumen/')
        self.assertEqual(rb.status_code, 200, rb.content)
        self.assertEqual(rb.json()['total_compras'], 0, 'B ve el conteo de compras de A')
        self.assertEqual(rb.json()['monto_total'], 0.0, 'B ve el monto de compras de A')

        # Control positivo: A sí ve su propio total.
        self.client.force_authenticate(self.user_a)
        ra = self.client.get('/api/compras/resumen/')
        self.assertEqual(ra.json()['monto_total'], 777.0)


@override_settings(ROOT_URLCONF='config.urls')
class AIMessagesAislamientoTests(TenantSetup):
    """/api/ai/.../messages/: B nunca accede a las conversaciones ni mensajes de A."""

    def _seed_conv_a(self):
        from apps.ai_assistant.models import Conversation, Message
        conv = Conversation.objects.create(empresa=self.A, usuario=self.user_a, title='Conv A')
        msg = Message.objects.create(conversation=conv, content='secreto de A', role='user')
        return conv, msg

    def test_B_no_lee_mensajes_de_A(self):
        conv_a, msg_a = self._seed_conv_a()
        self.client.force_authenticate(self.user_b)

        # Ruta anidada: mensajes de la conversación de A → no deben verse.
        r = self.client.get(f'/api/ai/conversations/{conv_a.pk}/messages/')
        self.assertNotEqual(r.status_code, 500, r.content)
        if r.status_code == 200:
            cuerpo = r.json()
            items = cuerpo['results'] if isinstance(cuerpo, dict) and 'results' in cuerpo else cuerpo
            self.assertEqual(items, [], f'FUGA: B ve mensajes de A: {items}')

        # Detalle de la conversación de A → 404 (no pertenece a B).
        rc = self.client.get(f'/api/ai/conversations/{conv_a.pk}/')
        self.assertIn(rc.status_code, (403, 404), rc.content)

    def test_B_no_escribe_en_conversacion_de_A(self):
        conv_a, _ = self._seed_conv_a()
        self.client.force_authenticate(self.user_b)
        r = self.client.post(
            f'/api/ai/conversations/{conv_a.pk}/messages/',
            {'content': 'intruso', 'role': 'user'}, format='json')
        self.assertIn(r.status_code, (403, 404), r.content)
        from apps.ai_assistant.models import Message
        self.assertFalse(
            Message.objects.filter(conversation=conv_a, content='intruso').exists(),
            'FUGA: B escribió en la conversación de A')


@override_settings(ROOT_URLCONF='config.urls')
class AIConversacionesPorUsuarioTests(TenantSetup):
    """A1: las conversaciones con la IA son privadas POR USUARIO. Dos usuarios de la
    MISMA empresa no se ven las conversaciones ni los mensajes entre sí."""

    def setUp(self):
        super().setUp()
        self.user_a2 = self._user('a2@a.pe', self.A)  # mismo tenant que user_a
        from apps.ai_assistant.models import Conversation, Message
        self.conv_a1 = Conversation.objects.create(empresa=self.A, usuario=self.user_a, title='Privada A1')
        self.msg_a1 = Message.objects.create(conversation=self.conv_a1, content='secreto de a1', role='user')

    def _items(self, r):
        cuerpo = r.json()
        return cuerpo['results'] if isinstance(cuerpo, dict) and 'results' in cuerpo else cuerpo

    def test_mismo_tenant_no_lista_conversaciones_ajenas(self):
        self.client.force_authenticate(self.user_a2)
        r = self.client.get('/api/ai/conversations/')
        self.assertEqual(r.status_code, 200, r.content)
        ids = [c['id'] for c in self._items(r)]
        self.assertNotIn(self.conv_a1.pk, ids, 'FUGA: a2 lista la conversación de a1')
        # Detalle directo → 404.
        rd = self.client.get(f'/api/ai/conversations/{self.conv_a1.pk}/')
        self.assertEqual(rd.status_code, 404, rd.content)

    def test_mismo_tenant_no_lee_ni_escribe_mensajes_ajenos(self):
        self.client.force_authenticate(self.user_a2)
        r = self.client.get(f'/api/ai/conversations/{self.conv_a1.pk}/messages/')
        self.assertNotEqual(r.status_code, 500, r.content)
        if r.status_code == 200:
            self.assertEqual(self._items(r), [], 'FUGA: a2 lee mensajes de a1')
        # Ruta plana /messages/ tampoco expone el mensaje.
        rp = self.client.get('/api/ai/messages/')
        self.assertEqual(rp.status_code, 200, rp.content)
        self.assertNotIn(self.msg_a1.pk, [m['id'] for m in self._items(rp)])
        rm = self.client.get(f'/api/ai/messages/{self.msg_a1.pk}/')
        self.assertEqual(rm.status_code, 404, rm.content)
        # Escritura en conversación ajena → 404 y no persiste.
        from apps.ai_assistant.models import Message
        rw = self.client.post(f'/api/ai/conversations/{self.conv_a1.pk}/messages/',
                              {'content': 'intruso', 'role': 'user'}, format='json')
        self.assertEqual(rw.status_code, 404, rw.content)
        self.assertFalse(Message.objects.filter(conversation=self.conv_a1, content='intruso').exists())

    def test_dueno_si_ve_lo_suyo(self):
        self.client.force_authenticate(self.user_a)
        r = self.client.get('/api/ai/conversations/')
        self.assertIn(self.conv_a1.pk, [c['id'] for c in self._items(r)])
        rm = self.client.get(f'/api/ai/conversations/{self.conv_a1.pk}/messages/')
        self.assertEqual(rm.status_code, 200, rm.content)
        self.assertEqual([m['id'] for m in self._items(rm)], [self.msg_a1.pk])


@override_settings(ROOT_URLCONF='config.urls')
class VentasPendientesEndpointTests(TenantSetup):
    """A2: el frontend (Cuentas por Cobrar → ventas.service.getVentasPendientes) consume
    GET /api/ventas/ventas_pendientes/ (VentaViewSet). La acción duplicada que se
    eliminó vivía en /api/ventas/{venta_pk}/pagos/ventas_pendientes/ (PagoVentaViewSet)
    y ningún cliente la usaba. Este test fija el contrato del endpoint vivo."""

    def test_endpoint_vivo_y_aislado(self):
        Venta.objects.create(
            empresa=self.B, numero='V-B-CR', cliente=self.cli_b, fecha_emision=date.today(),
            total=Decimal('500.00'), moneda='PEN', tipo_venta='credito_30', estado='pendiente')
        self.client.force_authenticate(self.user_a)
        r = self.client.get('/api/ventas/ventas_pendientes/')
        self.assertEqual(r.status_code, 200, r.content)
        cuerpo = r.json()
        ventas = cuerpo.get('ventas', cuerpo) if isinstance(cuerpo, dict) else cuerpo
        numeros = [v.get('numero') for v in ventas] if isinstance(ventas, list) else []
        self.assertNotIn('V-B-CR', numeros, 'FUGA: A ve ventas pendientes de B')
        # La ruta eliminada no existe (404), confirmando que no queda un duplicado.
        r2 = self.client.get(f'/api/ventas/{self.venta_b.pk}/pagos/ventas_pendientes/')
        self.assertEqual(r2.status_code, 404)
