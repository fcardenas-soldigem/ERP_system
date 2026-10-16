"""
B2 — Los endpoints no devuelven str(e)/traceback de errores inesperados:
{"error": "<mensaje de negocio>"} + 500 + logger.exception. Los 400 de validación
conservan su mensaje útil.
"""
from datetime import date
from decimal import Decimal
from unittest import mock

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError as DjangoValidationError
from django.http import Http404
from django.test import SimpleTestCase, TestCase, override_settings
from rest_framework.exceptions import ValidationError as DRFValidationError
from rest_framework.test import APIClient

from apps.compras.models import Compra, Proveedor
from apps.core.errors import error_interno, mensaje_seguro, respuesta_error
from apps.empresas.models import Empresa
from apps.inventario.models.almacen import Almacen

User = get_user_model()


class HelperTests(SimpleTestCase):
    def test_error_interno_oculta_detalle_y_loguea(self):
        with self.assertLogs('tests.test_errores_genericos', level='ERROR') as cm:
            r = error_interno(RuntimeError('SECRETO interno'), 'Error al exportar')
        self.assertEqual(r.status_code, 500)
        self.assertEqual(r.data, {'error': 'Error al exportar'})
        self.assertNotIn('SECRETO', str(r.data))
        self.assertIn('SECRETO', '\n'.join(cm.output))  # el detalle va al log, con traceback

    def test_respuesta_error_clasifica(self):
        self.assertEqual(respuesta_error(ValueError('Stock insuficiente')).status_code, 400)
        self.assertEqual(respuesta_error(ValueError('Stock insuficiente')).data, {'error': 'Stock insuficiente'})
        r = respuesta_error(DjangoValidationError(['Falta el cliente']))
        self.assertEqual((r.status_code, r.data), (400, {'error': 'Falta el cliente'}))
        r = respuesta_error(DRFValidationError({'proveedor': ['Obligatorio']}))
        self.assertEqual((r.status_code, r.data), (400, {'proveedor': ['Obligatorio']}))
        self.assertEqual(respuesta_error(Proveedor.DoesNotExist()).data, {'error': 'Proveedor no encontrado'})
        self.assertEqual(respuesta_error(Proveedor.DoesNotExist()).status_code, 404)
        self.assertEqual(respuesta_error(Http404('x')).status_code, 404)
        with self.assertLogs('tests.test_errores_genericos', level='ERROR'):
            r = respuesta_error(KeyError('campo_interno'), 'Error al crear la compra', clave='detail')
        self.assertEqual((r.status_code, r.data), (500, {'detail': 'Error al crear la compra'}))

    def test_mensaje_seguro(self):
        self.assertEqual(mensaje_seguro(ValueError('Cantidad negativa')), 'Cantidad negativa')
        self.assertEqual(mensaje_seguro(Almacen.DoesNotExist()), 'Almacen no encontrado')
        with self.assertLogs('tests.test_errores_genericos', level='ERROR'):
            self.assertEqual(mensaje_seguro(TypeError('bug interno')), 'Error interno')


@override_settings(ROOT_URLCONF='config.urls',
                   CACHES={'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}})
class EndpointsErrorTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.A = Empresa.objects.create(nombre='Empresa A', ruc='20000000001')
        self.user = User(email='a@a.pe', username='a@a.pe', empresa=self.A); self.user.set_password('x'); self.user.save()
        self.prov = Proveedor.objects.create(empresa=self.A, razon_social='Prov A', ruc='20000000011')
        self.alm = Almacen.objects.create(empresa=self.A, nombre='Alm A')
        with mock.patch('apps.compras.models.Compra.asegurar_tipo_cambio', lambda self: None):
            self.compra = Compra.objects.create(empresa=self.A, proveedor=self.prov, almacen=self.alm, fecha_emision=date.today())
        self.client.force_authenticate(self.user)

    def test_error_inesperado_en_retrieve_es_500_generico(self):
        from apps.compras.views import CompraViewSet
        with mock.patch.object(CompraViewSet, 'get_serializer', side_effect=RuntimeError('SECRETO: tabla x')), \
             self.assertLogs('apps.compras.views', level='ERROR'):
            r = self.client.get(f'/api/compras/compras/{self.compra.pk}/')
        self.assertEqual(r.status_code, 500, r.content)
        self.assertEqual(r.json(), {'detail': 'Error al obtener la compra'})

    def test_validacion_conserva_mensaje(self):
        r = self.client.post('/api/compras/compras/', {'fecha_emision': str(date.today())}, format='json')
        self.assertEqual(r.status_code, 400, r.content)
        self.assertNotIn('Error al crear la compra', r.content.decode())  # mensaje de validación, no genérico
        self.assertTrue(r.json(), 'el 400 debe traer el detalle de validación')

    def test_dashboard_error_inesperado(self):
        with mock.patch('apps.dashboard.views.Venta.objects.filter', side_effect=RuntimeError('SECRETO')), \
             self.assertLogs('apps.dashboard.views', level='ERROR'):
            r = self.client.get('/api/dashboard/resumen/')
        self.assertNotEqual(r.status_code, 200)
        self.assertNotIn('SECRETO', r.content.decode())

    def test_fila_importacion_mensaje_util_sin_internos(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        csv = ('proveedor,almacen,fecha,sku,nombre_producto,cantidad,precio_unitario,subtotal,igv_incluido,estado,metodo_pago\n'
               'NO EXISTE,Alm A,2026-10-01,S1,P,1,1,1,si,pendiente,efectivo\n').encode()
        r = self.client.post('/api/compras/compras/importar_excel/', {'file': SimpleUploadedFile('c.csv', csv, content_type='text/csv')}, format='multipart')
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual(r.json()['errores'], ['Error en fila 2: Proveedor no encontrado'])
