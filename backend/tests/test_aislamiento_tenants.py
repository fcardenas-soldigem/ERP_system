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

from django.contrib.auth import get_user_model
from django.test import TestCase
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
