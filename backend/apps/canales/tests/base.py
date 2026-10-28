"""
Base de pruebas del canal: Telegram SIEMPRE mockeado (nada sale a la red),
LLM mockeado por defecto, webhook en modo síncrono y caché locmem aislada.
"""
from datetime import timedelta
from decimal import Decimal
from unittest import mock

from django.contrib.auth import get_user_model
from django.test import override_settings
from django.utils import timezone
from rest_framework.test import APITestCase

from apps.ai_assistant.services.llm_client import LLMResponse, ToolCall
from apps.canales.models import VinculacionTelegram
from apps.empresas.models import Empresa
from apps.inventario.models.producto import Producto
from apps.ventas.models import Cliente, Venta

User = get_user_model()

SECRETO = 'secreto-webhook-prueba-local'

AJUSTES = dict(
    TG_BOT_TOKEN='000000:token-prueba',
    TG_WEBHOOK_SECRET=SECRETO,
    TG_BOT_USERNAME='SoldigemPruebaBot',
    CANALES_WEBHOOK_SINCRONO=True,
    CACHES={'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
                        'LOCATION': 'canales-tests'}},
)


def respuesta_llm(tool=None, argumentos=None, texto=''):
    """Fabrica una LLMResponse como la que devolvería el proveedor."""
    calls = [ToolCall(id='t1', name=tool, arguments=argumentos or {})] if tool else []
    return LLMResponse(text=texto, tool_calls=calls, tokens_entrada=50, tokens_salida=20, modelo='fake')


@override_settings(**AJUSTES)
class CanalTestCase(APITestCase):
    """Crea 2 empresas con usuarios vinculados y datos mínimos de negocio."""

    CHAT_A = 111111
    CHAT_B = 222222
    CHAT_LECTOR = 333333

    @classmethod
    def setUpTestData(cls):
        cls.empresa_a = Empresa.objects.create(nombre='Empresa A', ruc='20111111111')
        cls.empresa_b = Empresa.objects.create(nombre='Empresa B', ruc='20222222222')
        cls.vendedor = User.objects.create_user(
            username='vende@a.pe', email='vende@a.pe', password='x',
            nombre='Vendedor', apellido='A', empresa=cls.empresa_a, rol='operador')
        cls.lector = User.objects.create_user(
            username='lee@a.pe', email='lee@a.pe', password='x',
            nombre='Lector', apellido='A', empresa=cls.empresa_a, rol='solo_lectura')
        cls.vendedor_b = User.objects.create_user(
            username='vende@b.pe', email='vende@b.pe', password='x',
            nombre='Vendedor', apellido='B', empresa=cls.empresa_b, rol='operador')
        for usuario, chat in ((cls.vendedor, cls.CHAT_A), (cls.vendedor_b, cls.CHAT_B), (cls.lector, cls.CHAT_LECTOR)):
            VinculacionTelegram.objects.create(
                usuario=usuario, chat_id=chat,
                codigo_expira=timezone.now(), vinculado_at=timezone.now())

        cls.cliente = Cliente.objects.create(
            empresa=cls.empresa_a, nombre='Transportes Lima SAC', documento='20555555551',
            tipo_documento='ruc')
        cls.producto = Producto.objects.create(
            empresa=cls.empresa_a, sku='JB-750', nombre='Auricular Jabra Evolve2 750',
            precio_compra=Decimal('300'), precio_venta=Decimal('450'))
        cls.venta = Venta.objects.create(
            empresa=cls.empresa_a, cliente=cls.cliente, tipo_venta='credito_30',
            fecha_emision=timezone.localdate(),
            metodo_pago='transferencia', moneda='USD')
        # pre_save pone totales en 0 al crear: fijarlos con update()
        Venta.objects.filter(pk=cls.venta.pk).update(
            total=Decimal('1000'), subtotal=Decimal('847.46'),
            estado='pendiente', pagos_total=0)
        cls.venta.refresh_from_db()

    def setUp(self):
        super().setUp()
        from django.core.cache import cache
        cache.clear()
        # Telegram mockeado: capturamos cada respuesta del bot
        parche = mock.patch('apps.canales.telegram.requests')
        self.tg_requests = parche.start()
        self.tg_requests.post.return_value.ok = True
        self.addCleanup(parche.stop)

    # ── helpers ──────────────────────────────────────────────────────────────
    def post_update(self, payload, secreto=SECRETO):
        headers = {'HTTP_X_TELEGRAM_BOT_API_SECRET_TOKEN': secreto} if secreto else {}
        return self.client.post('/api/canales/telegram/', payload, format='json', **headers)

    _update_id = 1000

    def update_texto(self, chat_id, texto):
        CanalTestCase._update_id += 1
        return {'update_id': CanalTestCase._update_id,
                'message': {'chat': {'id': chat_id}, 'from': {'first_name': 'Test'}, 'text': texto}}

    def update_callback(self, chat_id, data):
        CanalTestCase._update_id += 1
        return {'update_id': CanalTestCase._update_id,
                'callback_query': {'id': 'cb1', 'data': data,
                                   'from': {'first_name': 'Test'},
                                   'message': {'chat': {'id': chat_id}}}}

    def respuestas_bot(self):
        """[(chat_id, texto, botones)] de todos los sendMessage capturados."""
        out = []
        for llamada in self.tg_requests.post.call_args_list:
            url = llamada.args[0] if llamada.args else ''
            if 'sendMessage' not in url:
                continue
            data = llamada.kwargs.get('json', {})
            botones = [
                b['callback_data'] for fila in data.get('reply_markup', {}).get('inline_keyboard', [])
                for b in fila
            ]
            out.append((str(data.get('chat_id')), data.get('text', ''), botones))
        return out

    def ultima_respuesta(self):
        rs = self.respuestas_bot()
        return rs[-1] if rs else (None, '', [])

    def mock_llm(self, tool, argumentos):
        """El modelo pide esta tool y, si recibe un resultado, contesta texto
        (como el real): el bucle de tools termina en la ronda 2."""
        parche = mock.patch('apps.canales.nucleo.interprete.get_llm_client')
        m = parche.start()
        self.programar_llm(m, tool, argumentos)
        self.addCleanup(parche.stop)
        return m

    @staticmethod
    def programar_llm(m, tool, argumentos):
        m.return_value.chat.side_effect = (
            [respuesta_llm(tool, argumentos)] + [respuesta_llm(None, texto='listo')] * 10)
