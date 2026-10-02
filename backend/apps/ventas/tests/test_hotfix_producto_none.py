"""Hotfix prod: GET /api/ventas/ daba 500 cuando una venta tenía una línea de
texto libre (DetalleVenta.producto=None, D1). get_productos_stock_bajo asumía
producto siempre presente. Regresión: el endpoint responde 200 en ambos modos."""
from datetime import date

from django.test import TestCase
from rest_framework.test import APIRequestFactory, force_authenticate

from apps.empresas.models import Empresa
from apps.authentication.models import CustomUser
from apps.ventas.models import Cliente, Venta, DetalleVenta
from apps.ventas.views import VentaViewSet


def _setup(ruc, modo):
    emp = Empresa.objects.create(nombre='E', ruc=ruc, modo_inventario=modo)
    u = CustomUser(email=f'{ruc}@t.com', nombre='T', apellido='U', empresa=emp, is_superuser=True)
    u.set_password('x'); u.save()
    cli = Cliente.objects.create(empresa=emp, nombre='C', documento='10000001', tipo_documento='ruc')
    v = Venta.objects.create(empresa=emp, cliente=cli, fecha_emision=date.today(), tipo_venta='contado')
    # Línea de texto libre (D1): sin producto.
    DetalleVenta.objects.create(
        venta=v, producto=None, descripcion='Servicio de instalación',
        cantidad=1, precio_unitario=100,
    )
    return emp, u, v


class ListaVentasConLineaSinProductoTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.list_view = VentaViewSet.as_view({'get': 'list'})

    def _get_list(self, user):
        req = self.factory.get('/api/ventas/')
        force_authenticate(req, user=user)
        return self.list_view(req)

    def _assert_ok(self, ruc, modo):
        emp, u, v = _setup(ruc, modo)
        resp = self._get_list(u)
        resp.render()
        self.assertEqual(resp.status_code, 200, resp.content)
        # La venta con línea sin producto no debe reventar; stock_bajo = [].
        results = resp.data['results'] if isinstance(resp.data, dict) and 'results' in resp.data else resp.data
        venta = next(r for r in results if r['id'] == v.id)
        self.assertEqual(venta['productos_stock_bajo'], [])

    def test_lista_200_empresa_con_stock(self):
        self._assert_ok('20700000010', 'con_stock')

    def test_lista_200_empresa_sin_stock(self):
        self._assert_ok('20700000011', 'sin_stock')
