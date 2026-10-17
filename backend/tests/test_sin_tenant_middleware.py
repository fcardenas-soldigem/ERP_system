"""
El TenantMiddleware (SET app.current_empresa por petición) se eliminó: con JWT el usuario
es anónimo en la capa de middleware (DRF autentica dentro de la vista), así que nunca fijaba
el GUC; no existe RLS que lo consuma; y un SET de sesión con CONN_MAX_AGE>0 puede filtrarse
entre peticiones. Este test impide que vuelva "por accidente" y documenta la regla:
quien necesite el GUC debe usar SET LOCAL dentro de su propia transacción.
"""
import importlib.util

from django.conf import settings
from django.db import connection
from django.test import SimpleTestCase, TestCase


class SinTenantMiddlewareTests(SimpleTestCase):
    def test_no_esta_en_middleware(self):
        self.assertFalse(
            any('middleware.tenant' in m for m in settings.MIDDLEWARE),
            f'TenantMiddleware no debe estar en MIDDLEWARE: {settings.MIDDLEWARE}')

    def test_modulo_eliminado(self):
        self.assertIsNone(importlib.util.find_spec('apps.core.middleware.tenant'))


class GUCNoFijadoTests(TestCase):
    """Ninguna petición deja app.current_empresa fijado en la conexión (no hay quien lo haga
    y, si lo hubiera, debería ser SET LOCAL dentro de una transacción)."""

    def test_guc_vacio_tras_peticion_autenticada(self):
        if connection.vendor != 'postgresql':
            self.skipTest('GUC solo en Postgres')
        from django.contrib.auth import get_user_model
        from rest_framework.test import APIClient
        from apps.empresas.models import Empresa
        empresa = Empresa.objects.create(nombre='Empresa A', ruc='20000000001')
        user = get_user_model()(email='a@a.pe', username='a@a.pe', empresa=empresa)
        user.set_password('x'); user.save()
        client = APIClient(); client.force_authenticate(user)
        client.get('/api/auth/profile/')
        with connection.cursor() as cur:
            cur.execute("SELECT current_setting('app.current_empresa', true)")
            self.assertIn(cur.fetchone()[0], (None, ''))
