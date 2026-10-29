"""Regresión de la WEB tras extraer creacion_venta (ajuste pre-deploy, punto 4):
POST /api/ventas/ al contado y a crédito deben producir EXACTAMENTE el mismo
resultado que antes del refactor: estado, PagoVenta placeholder, vencimiento y
numeración. Si alguien cambia el servicio compartido, esto lo detecta."""
import datetime
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.utils import timezone
from rest_framework.test import APITestCase

from apps.empresas.models import Empresa
from apps.inventario.models.producto import Producto
from apps.ventas.models import Cliente, PagoVenta, Venta

User = get_user_model()


class CreacionVentaWebRegresionTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cache.set(f'tc_venta_{datetime.date.today().isoformat()}', '3.80', 3600)
        cls.empresa = Empresa.objects.create(nombre='Web Regresión SA', ruc='20777777771')
        cls.usuario = User.objects.create_user(
            username='web@r.pe', email='web@r.pe', password='x',
            nombre='Web', apellido='R', empresa=cls.empresa, rol='admin')
        cls.cliente = Cliente.objects.create(
            empresa=cls.empresa, nombre='Cliente Web', documento='20777777772',
            tipo_documento='ruc')
        cls.producto = Producto.objects.create(
            empresa=cls.empresa, sku='WR-1', nombre='Producto Web',
            precio_compra=Decimal('50'), precio_venta=Decimal('100'),
            tipo_producto='FINISHED')

    def setUp(self):
        self.client.force_authenticate(user=self.usuario)
        cache.set(f'tc_venta_{datetime.date.today().isoformat()}', '3.80', 3600)

    def _post(self, **extra):
        data = {
            'cliente_id': self.cliente.id,
            'fecha_emision': timezone.localdate().isoformat(),
            'estado': 'pagado', 'tipo_venta': 'contado', 'metodo_pago': 'efectivo',
            'moneda': 'PEN', 'igv_incluido': False,
            'detalles': [{'producto': self.producto.id, 'cantidad': 2, 'precio_unitario': 100}],
            **extra,
        }
        return self.client.post('/api/ventas/', data, format='json')

    def test_contado_igual_que_antes_del_refactor(self):
        r = self._post()
        self.assertEqual(r.status_code, 201, r.content[:300])
        venta = Venta.objects.get()
        # exactamente lo de siempre: pagado, totales con IGV agregado, V-, sin pagos
        self.assertEqual(venta.estado, 'pagado')
        self.assertEqual(venta.tipo_venta, 'contado')
        self.assertEqual(venta.metodo_pago, 'efectivo')
        self.assertEqual(venta.total, Decimal('236.00'))           # 200 + 18%
        self.assertTrue(venta.numero.startswith('V-'))
        self.assertEqual(len(venta.numero), 2 + 6)                 # V-xxxxxx
        self.assertIsNone(venta.fecha_vencimiento)
        self.assertEqual(PagoVenta.objects.count(), 0)             # nada inventado
        # pagado → estado operativo sincronizado (comportamiento previo)
        self.assertEqual(venta.estado_operativo, 'cobrado')

    def test_credito_30_igual_que_antes_del_refactor(self):
        r = self._post(estado='pendiente', tipo_venta='credito_30', metodo_pago='transferencia')
        self.assertEqual(r.status_code, 201, r.content[:300])
        venta = Venta.objects.get()
        self.assertEqual(venta.estado, 'pendiente')
        self.assertEqual(venta.fecha_vencimiento,
                         venta.fecha_emision + timezone.timedelta(days=30))
        placeholder = PagoVenta.objects.get(venta=venta)
        self.assertEqual(placeholder.metodo_pago, 'pendiente')
        self.assertEqual(placeholder.monto, venta.total)
        self.assertEqual(placeholder.fecha, venta.fecha_emision)
        self.assertIn('30 días', placeholder.notas)

    def test_credito_60_igual_que_antes_del_refactor(self):
        r = self._post(estado='pendiente', tipo_venta='credito_60')
        self.assertEqual(r.status_code, 201, r.content[:300])
        venta = Venta.objects.get()
        self.assertEqual(venta.fecha_vencimiento,
                         venta.fecha_emision + timezone.timedelta(days=60))
        self.assertIn('60 días', PagoVenta.objects.get(venta=venta).notas)
