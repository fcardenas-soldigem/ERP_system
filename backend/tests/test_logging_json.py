"""B3 — logging estructurado: JSON con severity/message/request_id/path/empresa_id/user_id."""
import json
import logging

from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase, override_settings
from rest_framework.test import APIClient, APIRequestFactory
from rest_framework_simplejwt.tokens import RefreshToken

from apps.core.logging_json import (JSONFormatter, RequestContextFilter, contexto_actual,
                                    iniciar_contexto, limpiar_contexto, set_usuario_actual)
from apps.empresas.models import Empresa

User = get_user_model()


class FormatterTests(SimpleTestCase):
    def _record(self, msg, level=logging.INFO, exc_info=None):
        rec = logging.LogRecord('apps.x', level, __file__, 1, msg, None, exc_info)
        RequestContextFilter().filter(rec)
        return rec

    def test_json_con_campos_de_cloud_logging_y_contexto(self):
        iniciar_contexto('req-123', '/api/ventas/')
        try:
            doc = json.loads(JSONFormatter().format(self._record('hola')))
        finally:
            limpiar_contexto()
        self.assertEqual(doc['severity'], 'INFO')
        self.assertEqual(doc['message'], 'hola')
        self.assertEqual(doc['request_id'], 'req-123')
        self.assertEqual(doc['path'], '/api/ventas/')
        self.assertIn('empresa_id', doc); self.assertIn('user_id', doc); self.assertIn('timestamp', doc)

    def test_excepcion_incluye_traceback(self):
        try:
            raise RuntimeError('detalle interno')
        except RuntimeError:
            import sys
            doc = json.loads(JSONFormatter().format(self._record('fallo', logging.ERROR, sys.exc_info())))
        self.assertEqual(doc['severity'], 'ERROR')
        self.assertIn('RuntimeError: detalle interno', doc['exception'])

    def test_sin_contexto_no_rompe(self):
        limpiar_contexto()
        doc = json.loads(JSONFormatter().format(self._record('x')))
        self.assertIsNone(doc['request_id']); self.assertIsNone(doc['empresa_id'])


@override_settings(ROOT_URLCONF='config.urls',
                   CACHES={'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}})
class ContextoPeticionTests(TestCase):
    def setUp(self):
        self.A = Empresa.objects.create(nombre='Empresa A', ruc='20000000001')
        self.user = User(email='a@a.pe', username='a@a.pe', empresa=self.A); self.user.set_password('x'); self.user.save()

    def test_jwt_fija_user_y_empresa_en_contexto(self):
        from apps.core.authentication import JWTAuthenticationConContexto
        token = str(RefreshToken.for_user(self.user).access_token)
        req = APIRequestFactory().get('/api/auth/profile/', HTTP_AUTHORIZATION=f'Bearer {token}')
        limpiar_contexto()
        user, _ = JWTAuthenticationConContexto().authenticate(req)
        self.assertEqual(user, self.user)
        ctx = contexto_actual()
        self.assertEqual((ctx['user_id'], ctx['empresa_id']), (self.user.id, self.A.id))
        limpiar_contexto()

    def test_middleware_pone_request_id_y_lo_devuelve(self):
        client = APIClient()
        r = client.get('/api/health/', HTTP_X_REQUEST_ID='abc-1')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r['X-Request-ID'], 'abc-1')
        r2 = client.get('/api/health/')
        self.assertTrue(r2['X-Request-ID'])
        self.assertIsNone(contexto_actual()['request_id'], 'el contexto debe limpiarse al terminar')

    def test_log_de_login_sin_email_y_con_contexto(self):
        client = APIClient()
        # El filtro va a nivel de logger para que los records capturados lleven el contexto.
        lg = logging.getLogger('apps.authentication.views'); f = RequestContextFilter()
        lg.addFilter(f); self.addCleanup(lg.removeFilter, f)
        with self.assertLogs('apps.authentication.views', level='INFO') as cm:
            r = client.post('/api/auth/login/', {'email': 'a@a.pe', 'password': 'x'}, format='json')
        self.assertEqual(r.status_code, 200, r.content)
        salida = '\n'.join(cm.output)
        self.assertNotIn('a@a.pe', salida, 'el email no debe ir a los logs')
        self.assertIn(f'user_id={self.user.id}', salida)
        rec = cm.records[-1]
        self.assertEqual(rec.path, '/api/auth/login/')
        self.assertTrue(rec.request_id)
