"""
0.3 (revisado) — mismo origen vía rewrite de Vercel.

El navegador habla con erp.soldigem.com.pe/api/…; Vercel reenvía a Cloud Run
con Host = *.run.app y X-Forwarded-Host = erp.soldigem.com.pe. Como
settings.USE_X_FORWARDED_HOST = True, Django valida el host REENVIADO:
erp.soldigem.com.pe tiene que estar en DJANGO_ALLOWED_HOSTS o todo /api/
responde 400 (DisallowedHost).
"""
from io import StringIO
from unittest import mock

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management import CommandError, call_command
from django.test import TestCase, override_settings

from apps.empresas.models import Empresa

User = get_user_model()

RUN_APP = 'erp-backend-25656632090.southamerica-west1.run.app'
ERP = 'erp.soldigem.com.pe'


class HostReenviadoTests(TestCase):
    def test_django_valida_el_host_reenviado(self):
        self.assertTrue(settings.USE_X_FORWARDED_HOST)

    @override_settings(ALLOWED_HOSTS=[RUN_APP])
    def test_sin_erp_en_allowed_hosts_el_rewrite_da_400(self):
        r = self.client.get('/api/core/token/', HTTP_HOST=RUN_APP, HTTP_X_FORWARDED_HOST=ERP)
        self.assertEqual(r.status_code, 400)

    @override_settings(ALLOWED_HOSTS=[RUN_APP, ERP])
    def test_con_erp_en_allowed_hosts_el_rewrite_llega(self):
        r = self.client.get('/api/core/token/', HTTP_HOST=RUN_APP, HTTP_X_FORWARDED_HOST=ERP)
        self.assertNotEqual(r.status_code, 400)

    @override_settings(ALLOWED_HOSTS=[RUN_APP, ERP])
    def test_llamada_directa_a_cloud_run_sigue_valida(self):
        """Subidas directas y webhook de Telegram llegan sin X-Forwarded-Host."""
        r = self.client.get('/api/core/token/', HTTP_HOST=RUN_APP)
        self.assertNotEqual(r.status_code, 400)


@override_settings(DEBUG=False, ALLOWED_HOSTS=['testserver'])
class CookieRefreshTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        emp = Empresa.objects.create(nombre='Emp Cookie', ruc='20777777771')
        User.objects.create_user(username='c@x.pe', email='c@x.pe', password='clave-123',
                                 nombre='C', apellido='X', empresa=emp, rol='admin')

    def _login(self):
        r = self.client.post('/api/token/', {'email': 'c@x.pe', 'password': 'clave-123'},
                             content_type='application/json', secure=True)
        self.assertEqual(r.status_code, 200, r.content)
        return r.cookies['refresh_token']

    def test_cookie_host_only_lax_secure_path_api(self):
        c = self._login()
        self.assertEqual(c['domain'], '')          # host-only: sin Domain
        self.assertEqual(c['samesite'], 'Lax')
        self.assertTrue(c['secure'])
        self.assertTrue(c['httponly'])
        self.assertEqual(c['path'], '/api/')

    def test_refresh_rota_con_los_mismos_atributos(self):
        self._login()
        r = self.client.post('/api/token/refresh/', {}, content_type='application/json', secure=True)
        self.assertEqual(r.status_code, 200, r.content)
        c = r.cookies['refresh_token']
        self.assertEqual((c['domain'], c['samesite'], c['path']), ('', 'Lax', '/api/'))

    def test_logout_borra_con_el_mismo_path(self):
        self._login()
        token = self.client.post('/api/token/refresh/', {}, content_type='application/json',
                                 secure=True).json()['access']
        r = self.client.post('/api/auth/logout/', {}, content_type='application/json', secure=True,
                             HTTP_AUTHORIZATION=f'Bearer {token}')
        c = r.cookies['refresh_token']
        self.assertEqual(c['path'], '/api/')   # si difiere del de creación, no se borra
        self.assertEqual(c['max-age'], 0)


@override_settings(TG_BOT_TOKEN='000:x', TG_WEBHOOK_SECRET='s')
class WebhookUrlTests(TestCase):
    def test_rechaza_registrar_contra_el_dominio_del_erp(self):
        with self.assertRaises(CommandError) as cm:
            call_command('telegram_set_webhook', url=f'https://{ERP}', stdout=StringIO())
        self.assertIn('run.app', str(cm.exception))

    def test_registra_contra_cloud_run_directo(self):
        with mock.patch('apps.canales.management.commands.telegram_set_webhook.requests') as req:
            req.post.return_value.ok = True
            req.post.return_value.json.return_value = {'ok': True}
            call_command('telegram_set_webhook', url=f'https://{RUN_APP}', stdout=StringIO())
        enviado = req.post.call_args_list[0].kwargs['json']
        self.assertEqual(enviado['url'], f'https://{RUN_APP}/api/canales/telegram/')
        self.assertEqual(enviado['secret_token'], 's')


@override_settings(CORS_ALLOWED_ORIGINS=[f'https://{ERP}'])
class CorsBinariosDirectosTests(TestCase):
    """Subidas/descargas van directo a Cloud Run desde erp.soldigem.com.pe."""

    def test_preflight_permite_authorization(self):
        r = self.client.options('/api/ventas/1/pagos/', HTTP_ORIGIN=f'https://{ERP}',
                                HTTP_ACCESS_CONTROL_REQUEST_METHOD='POST',
                                HTTP_ACCESS_CONTROL_REQUEST_HEADERS='authorization')
        self.assertEqual(r['access-control-allow-origin'], f'https://{ERP}')
        self.assertIn('authorization', r['access-control-allow-headers'].lower())

    def test_expone_content_disposition(self):
        r = self.client.get('/api/ventas/exportar_excel/', HTTP_ORIGIN=f'https://{ERP}')
        self.assertIn('content-disposition', r['access-control-expose-headers'].lower())

    def test_otro_origen_no_recibe_cors(self):
        r = self.client.get('/api/ventas/', HTTP_ORIGIN='https://evil.example')
        self.assertNotIn('access-control-allow-origin', r)
