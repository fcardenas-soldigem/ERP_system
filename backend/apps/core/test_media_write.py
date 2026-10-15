"""Tests de ESCRITURA del hotfix GCS: subir archivos sigue funcionando tras cambiar
los FileField crudos a SafeFileURLField (comprobantes) y a write_only (logo/firma).

Prueba el camino multipart real por HTTP:
  - POST comprobante de PagoCompra  → /api/compras/pagos/
  - POST comprobante de PagoVenta   → /api/ventas/{venta}/pagos/   (venta a crédito, pendiente)
  - PATCH logo de empresa           → /api/empresas/{id}/
y verifica que el archivo queda guardado en el storage.
"""
import io
import shutil
import tempfile
from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.files.storage import default_storage
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from PIL import Image
from rest_framework.test import APIClient

from apps.compras.models import Compra, PagoCompra, Proveedor
from apps.empresas.models import Empresa
from apps.inventario.models.almacen import Almacen
from apps.ventas.models import Cliente, PagoVenta, Venta

User = get_user_model()
_TMP = tempfile.mkdtemp(prefix='erp-media-write-')
PDF = b'%PDF-1.4 test'


def _png_bytes():
    """PNG 1x1 válido (ImageField valida con Pillow; un stub de bytes no basta)."""
    buf = io.BytesIO()
    Image.new('RGB', (1, 1), (0, 0, 0)).save(buf, 'PNG')
    return buf.getvalue()


@override_settings(MEDIA_ROOT=_TMP)
class EscrituraArchivosTests(TestCase):
    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(_TMP, ignore_errors=True)
        super().tearDownClass()

    def setUp(self):
        self.empresa = Empresa.objects.create(nombre='ACME', ruc='20100000900')
        self.user = User.objects.create_user(
            username='writer', email='w@x.pe', password='x', nombre='W', apellido='R',
        )
        # El signal create_user_empresa le crea una empresa; la reasignamos a la nuestra.
        self.user.empresa = self.empresa
        self.user.save(update_fields=['empresa'])
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def _assert_guardado(self, name):
        self.assertTrue(name)
        self.assertTrue(default_storage.exists(name), f'no se guardó el archivo: {name}')

    def test_pago_compra_sube_comprobante(self):
        prov = Proveedor.objects.create(empresa=self.empresa, razon_social='Prov SAC', ruc='20100000111')
        alm = Almacen.objects.create(empresa=self.empresa, nombre='Central')
        compra = Compra.objects.create(
            empresa=self.empresa, proveedor=prov, almacen=alm, fecha_emision=date(2026, 1, 15),
        )
        # Fijar total por fuera del save (evita recomputo desde detalles) → hay saldo.
        Compra.objects.filter(pk=compra.pk).update(total=Decimal('100.00'))

        resp = self.client.post(
            '/api/compras/pagos/',
            {
                'compra': compra.pk,
                'fecha': '2026-01-20',
                'monto': '50.00',
                'metodo_pago': 'efectivo',
                'comprobante': SimpleUploadedFile('rc.pdf', PDF, content_type='application/pdf'),
            },
            format='multipart',
        )

        self.assertEqual(resp.status_code, 201, resp.content)
        pago = PagoCompra.objects.get(compra=compra)
        self._assert_guardado(pago.comprobante.name)

    def test_pago_venta_sube_comprobante(self):
        cliente = Cliente.objects.create(empresa=self.empresa, nombre='Cliente X', documento='12345678')
        venta = Venta.objects.create(
            numero='V-TEST-1', empresa=self.empresa, cliente=cliente, fecha_emision=date(2026, 1, 15),
        )
        # Venta a crédito, pendiente y con total (pre_save pone totales en 0 al crear).
        Venta.objects.filter(pk=venta.pk).update(
            tipo_venta='credito_30', estado='pendiente', total=Decimal('100.00'),
        )

        resp = self.client.post(
            f'/api/ventas/{venta.pk}/pagos/',
            {
                'fecha': '2026-01-20',
                'monto': '50.00',
                'metodo_pago': 'efectivo',
                'comprobante': SimpleUploadedFile('rv.pdf', PDF, content_type='application/pdf'),
            },
            format='multipart',
        )

        self.assertEqual(resp.status_code, 201, resp.content)
        pago = PagoVenta.objects.get(venta=venta)
        self._assert_guardado(pago.comprobante.name)

    def test_patch_logo_empresa(self):
        resp = self.client.patch(
            f'/api/empresas/{self.empresa.pk}/',
            {'logo': SimpleUploadedFile('logo.png', _png_bytes(), content_type='image/png')},
            format='multipart',
        )

        self.assertEqual(resp.status_code, 200, resp.content)
        self.empresa.refresh_from_db()
        self._assert_guardado(self.empresa.logo.name)
