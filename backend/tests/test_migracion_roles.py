"""
A3 — authentication.0003_simplificar_roles nunca degrada a quien administra:
- superusuarios e is_staff → admin;
- ninguna empresa queda sin admin: su usuario más antiguo (activo si lo hay)
  pasa a admin.
Se ejecuta la función de la migración sobre usuarios con los roles VIEJOS.
"""
import datetime as dt
import importlib

from django.apps import apps as django_apps
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.empresas.models import Empresa

User = get_user_model()
migracion = importlib.import_module('apps.authentication.migrations.0003_simplificar_roles')


def _usuario(email, empresa, rol, dias=0, **extra):
    u = User.objects.create_user(username=email, email=email, password='x', nombre='N', apellido='A',
                                 empresa=empresa, **extra)
    # rol viejo y antigüedad: update() salta las choices nuevas del modelo
    User.objects.filter(pk=u.pk).update(rol=rol, date_joined=timezone.now() - dt.timedelta(days=dias))
    return u


class MigracionRolesTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.a = Empresa.objects.create(nombre='A sin admin', ruc='20100000101')
        cls.b = Empresa.objects.create(nombre='B con admin', ruc='20100000102')
        cls.c = Empresa.objects.create(nombre='C solo readonly', ruc='20100000103')
        cls.d = Empresa.objects.create(nombre='D antiguo inactivo', ruc='20100000104')
        cls.super = _usuario('root@x.pe', None, 'readonly', is_superuser=True, is_staff=True)
        cls.staff = _usuario('staff@x.pe', cls.b, 'contador', is_staff=True)
        # A: nadie es admin → el más antiguo (comercial, 300 días) asciende
        cls.a_viejo = _usuario('viejo@a.pe', cls.a, 'comercial', dias=300)
        cls.a_nuevo = _usuario('nuevo@a.pe', cls.a, 'readonly', dias=10)
        # B: ya tiene admin → nadie asciende
        cls.b_admin = _usuario('admin@b.pe', cls.b, 'admin', dias=5)
        cls.b_lector = _usuario('lector@b.pe', cls.b, 'readonly', dias=400)
        # C: un único usuario readonly → admin (si no, la empresa queda sin admin)
        cls.c_unico = _usuario('unico@c.pe', cls.c, 'readonly')
        # D: el más antiguo está inactivo → asciende el activo más antiguo
        cls.d_inactivo = _usuario('ex@d.pe', cls.d, 'almacen', dias=900, is_active=False)
        cls.d_activo = _usuario('activo@d.pe', cls.d, 'personalizado', dias=50)
        cls.d_reciente = _usuario('reciente@d.pe', cls.d, 'readonly', dias=1)
        migracion.adelante(django_apps, None)

    def _rol(self, u):
        return User.objects.get(pk=u.pk).rol

    def test_superusuario_nunca_queda_solo_lectura(self):
        self.assertEqual(self._rol(self.super), 'admin')

    def test_staff_pasa_a_admin(self):
        self.assertEqual(self._rol(self.staff), 'admin')

    def test_empresa_sin_admin_asciende_al_mas_antiguo(self):
        self.assertEqual(self._rol(self.a_viejo), 'admin')
        self.assertEqual(self._rol(self.a_nuevo), 'solo_lectura')

    def test_empresa_con_admin_no_asciende_a_nadie(self):
        self.assertEqual(self._rol(self.b_admin), 'admin')
        self.assertEqual(self._rol(self.b_lector), 'solo_lectura')   # aunque sea el más antiguo

    def test_usuario_unico_readonly_queda_admin(self):
        self.assertEqual(self._rol(self.c_unico), 'admin')

    def test_prefiere_al_activo_mas_antiguo(self):
        self.assertEqual(self._rol(self.d_activo), 'admin')
        self.assertEqual(self._rol(self.d_inactivo), 'operador')
        self.assertEqual(self._rol(self.d_reciente), 'solo_lectura')

    def test_ninguna_empresa_queda_sin_admin_activo(self):
        for e in (self.a, self.b, self.c, self.d):
            self.assertTrue(User.objects.filter(empresa=e, rol='admin', is_active=True).exists(), e.nombre)

    def test_es_idempotente(self):
        antes = dict(User.objects.values_list('email', 'rol'))
        migracion.adelante(django_apps, None)
        self.assertEqual(dict(User.objects.values_list('email', 'rol')), antes)


class SuperusuarioEscribeTests(TestCase):
    def test_superusuario_con_rol_solo_lectura_igual_escribe(self):
        """Defensa adicional en RolEscritura: un rol mal asignado no bloquea al superusuario."""
        e = Empresa.objects.create(nombre='E', ruc='20100000105')
        su = User.objects.create_user(username='su@x.pe', email='su@x.pe', password='x', nombre='S',
                                      apellido='U', empresa=e, rol='solo_lectura', is_superuser=True)
        c = APIClient()
        c.force_authenticate(su)
        r = c.post('/api/ventas/clientes/', {'nombre': 'Cli', 'documento': '45678913',
                                             'tipo_documento': 'dni'}, format='json')
        self.assertIn(r.status_code, (200, 201), r.content)
