"""M3: el Django admin (/admin/) es solo para superusuarios de plataforma.

Un usuario de un tenant (aunque tenga is_staff) NO debe poder entrar al admin, que
no aplica el filtrado por empresa y expondría datos de todos los tenants.
"""
from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings

from apps.empresas.models import Empresa

User = get_user_model()


@override_settings(
    ROOT_URLCONF='config.urls',
    # Storage de estáticos SIN manifest: el admin del superusuario renderiza sin
    # exigir collectstatic (el manifest no existe en el entorno de test).
    STORAGES={
        'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
        'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'},
    },
)
class AdminSoloSuperusuarioTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.empresa = Empresa.objects.create(nombre='A', ruc='20000000001')

    def _user(self, email, **flags):
        u = User(email=email, username=email, empresa=self.empresa, **flags)
        u.set_password('x')
        u.save()
        return u

    def test_staff_de_tenant_no_entra_al_admin(self):
        u = self._user('staff@a.pe', is_staff=True, is_superuser=False)
        self.client.force_login(u)
        r = self.client.get('/admin/')
        # has_permission(False) → el admin redirige al login (no 200).
        self.assertNotEqual(r.status_code, 200, 'un is_staff de tenant NO debe entrar al admin')

    def test_usuario_normal_no_entra_al_admin(self):
        u = self._user('normal@a.pe')  # ni staff ni superuser
        self.client.force_login(u)
        r = self.client.get('/admin/')
        self.assertNotEqual(r.status_code, 200)

    def test_superusuario_de_plataforma_si_entra(self):
        u = self._user('root@plataforma.pe', is_staff=True, is_superuser=True)
        self.client.force_login(u)
        r = self.client.get('/admin/')
        self.assertEqual(r.status_code, 200, 'un superusuario de plataforma SÍ debe entrar')
