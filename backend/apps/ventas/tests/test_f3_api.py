"""F3 — serializer expone estado operativo/historial/OCs; endpoint cambiar-estado-operativo."""
from datetime import date

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIRequestFactory, force_authenticate

from apps.empresas.models import Empresa
from apps.authentication.models import CustomUser
from apps.ventas.models import Cliente, Venta
from apps.compras.models import OrdenCompra
from apps.ventas.serializers import VentaSerializer
from apps.ventas.views import VentaViewSet


def _setup(ruc='20700000001'):
    emp = Empresa.objects.create(nombre='E', ruc=ruc, modo_inventario='con_stock')
    u = CustomUser(email=f'{ruc}@t.com', nombre='T', apellido='U', empresa=emp, is_superuser=True)
    u.set_password('x'); u.save()
    cli = Cliente.objects.create(empresa=emp, nombre='C', documento='10000001', tipo_documento='ruc')
    v = Venta.objects.create(empresa=emp, cliente=cli, fecha_emision=date.today(), tipo_venta='contado')
    return emp, u, cli, v


class F3SerializerTests(TestCase):
    def test_expone_campos_operativos_e_historial(self):
        emp, u, cli, v = _setup()
        v.cambiar_estado_operativo('comprado', usuario=u, nota='ok')
        OrdenCompra.objects.create(empresa=emp, venta=v, proveedor_nombre='ACME', fecha_entrega=date.today())
        v.refresh_from_db()

        data = VentaSerializer(v).data
        self.assertEqual(data['estado_operativo'], 'comprado')
        self.assertIn('estado_sla_operativo', data)
        self.assertIn('dias_en_estado_operativo', data)
        # La venta NO crea historial al nacer; solo las transiciones lo escriben.
        self.assertEqual(len(data['historial_operativo']), 1)
        self.assertEqual(data['historial_operativo'][0]['estado_nuevo'], 'comprado')
        self.assertEqual(data['historial_operativo'][0]['nota'], 'ok')
        self.assertEqual(len(data['ordenes_compra']), 1)
        self.assertTrue(data['ordenes_compra'][0]['numero'])


class F3EndpointTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.view = VentaViewSet.as_view({'post': 'cambiar_estado_operativo'})

    def _post(self, venta, user, body):
        req = self.factory.post('/x', body, format='json')
        force_authenticate(req, user=user)
        return self.view(req, pk=venta.id)

    def test_avanzar_estado(self):
        emp, u, cli, v = _setup('20700000002')
        resp = self._post(v, u, {'estado': 'comprado'})
        self.assertEqual(resp.status_code, 200)
        v.refresh_from_db()
        self.assertEqual(v.estado_operativo, 'comprado')

    def test_cobrado_no_elegible_400(self):
        emp, u, cli, v = _setup('20700000003')
        resp = self._post(v, u, {'estado': 'cobrado'})
        self.assertEqual(resp.status_code, 400)


class OCTrazabilidadTests(TestCase):
    def test_oc_expone_venta_y_cotizacion_origen(self):
        from apps.compras.serializers import OrdenCompraSerializer
        from apps.cotizaciones.models import Cotizacion
        emp, u, cli, v = _setup('20700000004')
        cot = Cotizacion.objects.create(empresa=emp, cliente=cli, usuario_creador=u,
                                        asunto='x', fecha_vencimiento=date.today())
        oc = OrdenCompra.objects.create(empresa=emp, venta=v, cotizacion_origen=cot,
                                        proveedor_nombre='ACME', fecha_entrega=date.today())
        data = OrdenCompraSerializer(oc).data
        self.assertEqual(data['venta_origen']['numero'], v.numero)
        self.assertEqual(data['cotizacion_origen_info']['numero'], cot.numero)
