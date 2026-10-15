"""
Tests de la migración de media a GCS (rutas por empresa, validación, tolerancia a
archivos faltantes). Corren con FileSystemStorage (MEDIA_ROOT temporal); la firma
de URLs de GCS es config-driven y no requiere bucket aquí.
"""
import shutil
import tempfile

from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings

from apps.core.uploads import (
    UploadToEmpresa, validate_upload, field_url_safe, read_field_bytes,
)
from apps.empresas.models import Empresa
from apps.empresas.serializers import EmpresaSerializer

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
