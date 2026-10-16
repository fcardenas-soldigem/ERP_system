"""Hotfix: el chat IA sin OPENAI_API_KEY no debe responder 500.

Reproduce el log de prod (revisión erp-backend-00036-clq):
    POST /api/ai/threads-tools/ → OpenAIServiceWithTools.__init__
    → openai.OpenAIError: The api_key client option must be set ...
    → 500 "Error al crear la conversación".

La causa es de configuración (la revisión no tiene el secreto OPENAI_API_KEY),
pero el backend debe decirlo como 503 "asistente no configurado", sin
traceback ni 500 que disparen la alerta de 5xx.
"""
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from apps.empresas.models import Empresa

User = get_user_model()


@override_settings(ROOT_URLCONF='config.urls', OPENAI_API_KEY=None)
class ChatIASinApiKeyTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.empresa = Empresa.objects.create(nombre='Empresa A', ruc='20000000001')
        self.user = User(email='a@a.pe', username='a@a.pe')
        self.user.set_password('x')
        self.user.empresa = self.empresa
        self.user.save()
        self.client.force_authenticate(self.user)

    def _assert_503_sin_detalle(self, r):
        self.assertEqual(r.status_code, 503, r.content)
        cuerpo = r.json()
        self.assertIn('error', cuerpo)
        self.assertIn('no está configurado', cuerpo['error'])
        # Nada del SDK ni de la variable de entorno se filtra al cliente.
        self.assertNotIn('api_key', r.content.decode().lower())
        self.assertNotIn('OPENAI', r.content.decode())

    def test_crear_thread_sin_api_key_es_503_no_500(self):
        """El caso exacto del log de prod."""
        r = self.client.post('/api/ai/threads-tools/')
        self._assert_503_sin_detalle(r)

    def test_enviar_mensaje_sin_api_key_es_503_no_500(self):
        r = self.client.post('/api/ai/threads-tools/thread_x/messages/',
                             {'content': 'hola'}, format='json')
        self._assert_503_sin_detalle(r)

    def test_listar_mensajes_sin_api_key_es_503_no_500(self):
        r = self.client.get('/api/ai/threads-tools/thread_x/messages/')
        self._assert_503_sin_detalle(r)

    @override_settings(OPENAI_API_KEY='')
    def test_api_key_vacia_tambien_es_503(self):
        """Cadena vacía (secreto mal cargado) se trata igual que ausente."""
        r = self.client.post('/api/ai/threads-tools/')
        self._assert_503_sin_detalle(r)
