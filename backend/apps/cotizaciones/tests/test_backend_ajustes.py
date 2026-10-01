"""B2 — proveedor/costo_unitario escribibles en la cotización; margen read-only;
el PDF del cliente no expone costo ni proveedor."""
import os
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIRequestFactory

from apps.empresas.models import Empresa
from apps.authentication.models import CustomUser
from apps.ventas.models import Cliente
from apps.compras.models import Proveedor
from apps.cotizaciones.serializers import CotizacionCreateSerializer, DetalleCotizacionSerializer


class B2CosteoEscribibleTests(TestCase):
    def setUp(self):
        self.emp = Empresa.objects.create(nombre='E', ruc='20100000001', modo_inventario='con_stock')
        self.user = CustomUser(email='b2@t.com', nombre='T', apellido='U', empresa=self.emp, is_superuser=True)
        self.user.set_password('x'); self.user.save()
        self.cli = Cliente.objects.create(empresa=self.emp, nombre='C', documento='10000001', tipo_documento='ruc')
        self.prov = Proveedor.objects.create(empresa=self.emp, razon_social='ACME', ruc='20100000002')

    def test_proveedor_y_costo_persisten_y_margen_calculado(self):
        factory = APIRequestFactory()
        req = factory.post('/x'); req.user = self.user
        data = {
            'cliente': self.cli.id,
            'asunto': 'Cot',
            'fecha_vencimiento': str(timezone.now().date()),
            'detalles': [{
                'descripcion': 'Item', 'cantidad': '2', 'precio_unitario': '100',
                'proveedor': self.prov.id, 'costo_unitario': '60',
            }],
        }
        ser = CotizacionCreateSerializer(data=data, context={'request': req})
        self.assertTrue(ser.is_valid(), ser.errors)
        cot = ser.save()
        d = cot.detalles.get()
        self.assertEqual(d.proveedor_id, self.prov.id)   # proveedor escribible
        self.assertEqual(d.costo_unitario, Decimal('60'))  # costo escribible
        self.assertEqual(d.margen_unitario, Decimal('40'))  # 100 - 60 (calculado)
        self.assertEqual(d.margen_pct, Decimal('40.00'))

    def test_margen_es_read_only(self):
        f = DetalleCotizacionSerializer()
        self.assertIn('margen_unitario', f.fields)
        self.assertTrue(f.fields['margen_unitario'].read_only)
        self.assertTrue(f.fields['margen_pct'].read_only)
        # proveedor y costo NO son read-only
        self.assertFalse(f.fields['proveedor'].read_only)
        self.assertFalse(f.fields['costo_unitario'].read_only)

    def test_pdf_no_expone_costo_ni_proveedor(self):
        # Regresión estática: el generador de PDF no referencia costo/proveedor.
        ruta = os.path.join(os.path.dirname(__file__), '..', 'utils', 'pdf_generator.py')
        with open(os.path.abspath(ruta), encoding='utf-8') as fh:
            src = fh.read()
        self.assertNotIn('costo_unitario', src)
        self.assertNotIn('proveedor', src)
