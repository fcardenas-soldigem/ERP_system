"""
Tests de la migración de media a GCS (rutas por empresa, validación, tolerancia a
archivos faltantes). Corren con FileSystemStorage (MEDIA_ROOT temporal); la firma
de URLs de GCS es config-driven y no requiere bucket aquí.
"""
import shutil
import tempfile
from datetime import date
from unittest import mock

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.files.storage import FileSystemStorage
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from rest_framework import serializers
from rest_framework.test import APIClient

from apps.core.uploads import (
    UploadToEmpresa, validate_upload, field_url_safe, read_field_bytes,
)
from apps.core.serializer_fields import SafeFileURLField
from apps.empresas.models import Empresa
from apps.empresas.serializers import EmpresaSerializer

User = get_user_model()

# Reproduce el error EXACTO de prod (Cloud Run): la SA por metadata no tiene llave
# privada, así que firmar la URL lanza. google-auth lo lanza como AttributeError.
_GCS_SIGN_ERROR = AttributeError(
    'you need a private key to sign credentials. The credentials you are currently '
    'using google.auth.compute_engine.credentials.Credentials just contains a token.'
)


def _url_raises():
    """Context manager: todo FieldFile.url (vía storage) lanza el error de firma de GCS."""
    return mock.patch.object(FileSystemStorage, 'url', side_effect=_GCS_SIGN_ERROR)

_TMP_MEDIA = tempfile.mkdtemp(prefix='erp-media-test-')
PNG = b'\x89PNG\r\n\x1a\n' + b'0' * 32


@override_settings(MEDIA_ROOT=_TMP_MEDIA)
class UploadPathTests(TestCase):
    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(_TMP_MEDIA, ignore_errors=True)
        super().tearDownClass()

    def _empresa(self, ruc):
        return Empresa.objects.create(nombre='ACME', ruc=ruc)

    def test_ruta_aislada_por_empresa(self):
        emp = self._empresa('20100000001')
        emp.logo = SimpleUploadedFile('logo.png', PNG, content_type='image/png')
        emp.save()
        # empresa_<id>/logos/<uuid>.png
        self.assertTrue(emp.logo.name.startswith(f'empresa_{emp.pk}/logos/'),
                        f'ruta inesperada: {emp.logo.name}')
        self.assertTrue(emp.logo.name.endswith('.png'))
        # el nombre del archivo es un uuid (no el nombre original)
        self.assertNotIn('logo.png', emp.logo.name)

    def test_dos_empresas_no_comparten_prefijo(self):
        a = self._empresa('20100000002')
        a.logo = SimpleUploadedFile('a.png', PNG, content_type='image/png')
        a.save()
        b = self._empresa('20100000003')
        b.logo = SimpleUploadedFile('b.png', PNG, content_type='image/png')
        b.save()
        self.assertTrue(a.logo.name.startswith(f'empresa_{a.pk}/'))
        self.assertTrue(b.logo.name.startswith(f'empresa_{b.pk}/'))
        self.assertNotEqual(a.logo.name.split('/')[0], b.logo.name.split('/')[0])

    def test_upload_devuelve_url(self):
        emp = self._empresa('20100000004')
        emp.logo = SimpleUploadedFile('x.png', PNG, content_type='image/png')
        emp.save()
        url = field_url_safe(emp.logo)
        self.assertTrue(url)  # en prod es una URL firmada de GCS; en local /media/...
        self.assertIn(emp.logo.name, url)
        self.assertEqual(read_field_bytes(emp.logo), PNG)


class UploadToResolverTests(TestCase):
    def test_tipo_en_la_ruta(self):
        emp = Empresa.objects.create(nombre='X', ruc='20100000010')
        name = UploadToEmpresa('firmas')(emp, 'firma.PNG')
        self.assertEqual(name.split('/')[:2], [f'empresa_{emp.pk}', 'firmas'])
        self.assertTrue(name.endswith('.png'))  # extensión normalizada a minúsculas

    def test_sin_empresa_usa_fallback(self):
        # Un objeto suelto sin forma de resolver empresa -> 'sin_empresa'
        name = UploadToEmpresa('otros')(object(), 'f.pdf')
        self.assertTrue(name.startswith('empresa_sin_empresa/otros/'))


class ValidatorTests(TestCase):
    def test_tipo_permitido(self):
        validate_upload(SimpleUploadedFile('a.pdf', b'%PDF-1.4'))  # no lanza

    def test_tipo_no_permitido(self):
        with self.assertRaises(ValidationError):
            validate_upload(SimpleUploadedFile('a.txt', b'hola'))

    def test_tamano_maximo(self):
        grande = type('F', (), {'size': 20 * 1024 * 1024, 'name': 'a.pdf'})()
        with self.assertRaises(ValidationError):
            validate_upload(grande)


@override_settings(MEDIA_ROOT=_TMP_MEDIA)
class MissingFileTolerantTests(TestCase):
    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(_TMP_MEDIA, ignore_errors=True)
        super().tearDownClass()

    def test_field_url_safe_nunca_lanza(self):
        class Boom:
            def __bool__(self):
                return True

            @property
            def url(self):
                raise RuntimeError('boom')

        self.assertIsNone(field_url_safe(Boom()))
        self.assertIsNone(field_url_safe(None))

    def test_serializer_no_rompe_con_archivo_faltante(self):
        # El registro referencia un archivo que no existe en el storage.
        emp = Empresa.objects.create(nombre='Y', ruc='20100000020')
        emp.logo.name = f'empresa_{emp.pk}/logos/inexistente.png'
        emp.save(update_fields=['logo'])
        data = EmpresaSerializer(emp, context={'request': None}).data  # no debe lanzar
        self.assertIn('logo_url', data)  # la clave existe; la UI mostrará "no disponible"


@override_settings(MEDIA_ROOT=_TMP_MEDIA)
class FirmaUrlFallaNoTumbaEndpointTests(TestCase):
    """Hotfix GCS: si firmar la URL lanza (SA sin llave privada), NINGÚN endpoint
    devuelve 500 — la URL del archivo sale como null. Cubre el endpoint de login
    (el caído en prod) y un endpoint por cada tipo de archivo."""

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(_TMP_MEDIA, ignore_errors=True)
        super().tearDownClass()

    def _png(self, name='logo.png'):
        return SimpleUploadedFile(name, PNG, content_type='image/png')

    def test_profile_responde_200_con_logo_url_null(self):
        # /api/auth/profile/ — el endpoint que tumbaba el login en producción.
        user = User.objects.create_user(
            username='hotfix', email='hot@fix.pe', password='x', nombre='Hot', apellido='Fix',
        )
        user.refresh_from_db()
        emp = user.empresa  # creada por el signal create_user_empresa
        emp.logo = self._png()
        emp.firma_elaborado = self._png('firma.png')
        emp.save()

        client = APIClient()
        client.force_authenticate(user)
        with _url_raises():
            resp = client.get('/api/auth/profile/')

        self.assertEqual(resp.status_code, 200)  # antes: 500 → login bloqueado
        data = resp.json()
        # UserSerializer._url (empresa_info) y EmpresaSerializer (empresa_data): null, sin lanzar.
        self.assertIsNone(data['empresa_info']['logo_url'])
        self.assertIsNone(data['empresa_info']['firma_elaborado_url'])
        self.assertIsNone(data['empresa_data']['logo_url'])
        # El FileField crudo es write_only: no se serializa en lectura (no se llama .url).
        self.assertNotIn('logo', data['empresa_data'])

    def test_empresa_serializer_logo_url_null(self):  # tipo de archivo: logo/firma (empresa)
        emp = Empresa.objects.create(nombre='E', ruc='20100000032')
        emp.logo = self._png()
        emp.save()
        with _url_raises():
            data = EmpresaSerializer(emp, context={'request': None}).data
        self.assertIsNone(data['logo_url'])
        self.assertNotIn('logo', data)  # write_only

    def test_safefileurlfield_devuelve_null(self):
        # Mecanismo compartido por comprobante (compras/ventas) y archivo (ComprobantePago):
        # SafeFileURLField.to_representation nunca propaga la excepción de firma.
        class _S(serializers.Serializer):
            archivo = SafeFileURLField()

        emp = Empresa.objects.create(nombre='C', ruc='20100000030')
        emp.logo = self._png()
        emp.save()
        obj = type('Obj', (), {'archivo': emp.logo})()
        with _url_raises():
            data = _S(obj, context={'request': None}).data
        self.assertIsNone(data['archivo'])

    def test_gasto_operativo_archivo_adjunto_null(self):  # tipo de archivo: adjunto (gastos)
        from apps.finanzas.models import CategoriaGasto, GastoOperativo
        from apps.finanzas.serializers import GastoOperativoSerializer

        emp = Empresa.objects.create(nombre='G', ruc='20100000031')
        cat = CategoriaGasto.objects.create(empresa=emp, nombre='Servicios')
        gasto = GastoOperativo.objects.create(
            empresa=emp, categoria=cat, descripcion='Internet', monto=120,
            fecha=date(2026, 1, 15),
            archivo_adjunto=SimpleUploadedFile('recibo.pdf', b'%PDF-1.4'),
        )
        with _url_raises():
            data = GastoOperativoSerializer(gasto, context={'request': None}).data
        self.assertIsNone(data['archivo_adjunto'])  # null, no 500
