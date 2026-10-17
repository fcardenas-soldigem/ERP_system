"""
Capa LLM propia (feat/llm-agnostico): respuesta, tool call, 503, 502, aislamiento,
historial acotado, tabla de uso y sin contenido en logs. Todo mockeado: ningún test
llama a un proveedor real.
"""
import json
import logging
from types import SimpleNamespace
from unittest import mock

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from apps.ai_assistant.models import Conversation, Message, UsoLLM
from apps.ai_assistant.services import llm_client as lc
from apps.ai_assistant.services.tool_specs import schema_de_pydantic
from apps.empresas.models import Empresa

User = get_user_model()


class FakeLLM(lc.LLMClient):
    """Cliente con guion: cada llamada devuelve el siguiente LLMResponse (o lanza)."""
    proveedor = 'fake'

    def __init__(self, guion):
        super().__init__(modelo='fake-model', timeout=1)
        self.guion = list(guion)
        self.llamadas = []  # (system, messages, tools)

    def chat(self, system, messages, tools, temperature=0.2):
        self.llamadas.append((system, list(messages), list(tools)))
        paso = self.guion.pop(0)
        if isinstance(paso, Exception):
            raise paso
        return paso


def texto(t, tin=11, tout=7):
    return lc.LLMResponse(text=t, tool_calls=[], tokens_entrada=tin, tokens_salida=tout, modelo='fake-model')


def tool(nombre, args, tin=13, tout=5):
    return lc.LLMResponse(text='', tool_calls=[lc.ToolCall(id='c1', name=nombre, arguments=args)],
                          tokens_entrada=tin, tokens_salida=tout, modelo='fake-model')


def _user(email, empresa):
    u = User(email=email, username=email)
    u.set_password('x')
    u.empresa = empresa
    u.save()
    return u


@override_settings(ROOT_URLCONF='config.urls', LLM_HISTORIAL_N=20)
class AsistenteBase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.A = Empresa.objects.create(nombre='Empresa A', ruc='20000000001')
        self.B = Empresa.objects.create(nombre='Empresa B', ruc='20000000002')
        self.user_a = _user('a@a.pe', self.A)
        self.user_a2 = _user('a2@a.pe', self.A)
        self.user_b = _user('b@b.pe', self.B)
        self.client.force_authenticate(self.user_a)

    def _con_fake(self, guion):
        fake = FakeLLM(guion)
        patcher = mock.patch('apps.ai_assistant.services.chat.get_llm_client', return_value=fake)
        patcher.start()
        self.addCleanup(patcher.stop)
        return fake

    def _thread(self):
        r = self.client.post('/api/ai/threads-tools/')
        self.assertEqual(r.status_code, 200, r.content)
        return r.json()


class RespuestaYToolsTests(AsistenteBase):
    def test_contrato_crear_thread(self):
        datos = self._thread()
        self.assertEqual(set(datos), {'thread_id', 'conversation_id', 'message'})
        conv = Conversation.objects.get(id=datos['conversation_id'])
        self.assertEqual((conv.empresa_id, conv.usuario_id, conv.perfil), (self.A.id, self.user_a.id, 'jorge'))
        self.assertTrue(conv.thread_id.startswith('conv_'))
        self.assertEqual(conv.messages.count(), 1)  # bienvenida

    def test_respuesta_simple_guarda_historial_y_uso(self):
        fake = self._con_fake([texto('Las ventas van bien.')])
        tid = self._thread()['thread_id']
        r = self.client.post(f'/api/ai/threads-tools/{tid}/messages/', {'content': 'hola'}, format='json')
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual(r.json(), {'message': 'Las ventas van bien.'})
        roles = list(Message.objects.filter(conversation__thread_id=tid).order_by('id').values_list('role', flat=True))
        self.assertEqual(roles, ['assistant', 'user', 'assistant'])
        # El modelo recibió system prompt con la empresa y el historial (bienvenida + pregunta).
        system, msgs, tools = fake.llamadas[0]
        self.assertIn('Empresa A', system)
        self.assertEqual([m.role for m in msgs], ['assistant', 'user'])
        self.assertEqual({t.name for t in tools}, {'analizar_ventas', 'analizar_inventario', 'analizar_clientes', 'consulta_libre'})
        uso = UsoLLM.objects.get(empresa=self.A, modelo='fake-model')
        self.assertEqual((uso.tokens_entrada, uso.tokens_salida, uso.llamadas), (11, 7, 1))
        # GET devuelve el historial desde la BD
        g = self.client.get(f'/api/ai/threads-tools/{tid}/messages/')
        self.assertEqual([m['role'] for m in g.json()['messages']], roles)

    def test_tool_call_se_ejecuta_con_la_empresa_del_servidor(self):
        fake = self._con_fake([tool('analizar_inventario', {'stock_minimo': 5}), texto('Hay 2 productos bajos.')])
        capturado = {}

        def falso_inventario(self_exec, **kwargs):
            capturado['empresa'] = self_exec.empresa
            capturado['kwargs'] = kwargs
            return {'success': True, 'productos_bajo_stock': 2}

        with mock.patch('apps.ai_assistant.services.analista_executor.AnalistaExecutor.analizar_inventario',
                        falso_inventario):
            tid = self._thread()['thread_id']
            r = self.client.post(f'/api/ai/threads-tools/{tid}/messages/', {'content': '¿stock bajo?'}, format='json')
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual(r.json()['message'], 'Hay 2 productos bajos.')
        # La empresa sale del usuario autenticado; el modelo no la pasa.
        self.assertEqual(capturado['empresa'], self.A)
        self.assertEqual(capturado['kwargs'], {'stock_minimo': 5})
        self.assertNotIn('empresa', capturado['kwargs'])
        # Segunda llamada al modelo lleva el turno assistant con tool_calls y el resultado como tool.
        _, msgs2, _ = fake.llamadas[1]
        self.assertEqual(msgs2[-2].role, 'assistant')
        self.assertEqual(msgs2[-2].tool_calls[0].name, 'analizar_inventario')
        self.assertEqual(msgs2[-1].role, 'tool')
        self.assertEqual(json.loads(msgs2[-1].content)['productos_bajo_stock'], 2)
        uso = UsoLLM.objects.get(empresa=self.A)
        self.assertEqual((uso.tokens_entrada, uso.tokens_salida), (13 + 11, 5 + 7))

    def test_tool_desconocida_no_rompe_el_turno(self):
        self._con_fake([tool('borrar_todo', {}), texto('No puedo hacer eso.')])
        tid = self._thread()['thread_id']
        r = self.client.post(f'/api/ai/threads-tools/{tid}/messages/', {'content': 'borra todo'}, format='json')
        self.assertEqual(r.status_code, 200, r.content)

    def test_historial_acotado_a_n_mensajes(self):
        fake = self._con_fake([texto('ok')])
        tid = self._thread()['thread_id']
        conv = Conversation.objects.get(thread_id=tid)
        for i in range(40):
            Message.objects.create(conversation=conv, role='user' if i % 2 else 'assistant', content=f'm{i}')
        self.client.post(f'/api/ai/threads-tools/{tid}/messages/', {'content': 'última'}, format='json')
        _, msgs, _ = fake.llamadas[0]
        self.assertEqual(len(msgs), 20)
        self.assertEqual(msgs[-1].content, 'última')

    def test_no_se_loguea_contenido(self):
        self._con_fake([texto('RESPUESTA-SECRETA-XYZ')])
        tid = self._thread()['thread_id']
        with self.assertLogs('apps.ai_assistant', level='DEBUG') as cm:
            logging.getLogger('apps.ai_assistant').debug('marca')  # garantiza al menos un registro
            self.client.post(f'/api/ai/threads-tools/{tid}/messages/', {'content': 'PREGUNTA-SECRETA-ABC'}, format='json')
        salida = '\n'.join(cm.output)
        self.assertNotIn('PREGUNTA-SECRETA-ABC', salida)
        self.assertNotIn('RESPUESTA-SECRETA-XYZ', salida)

    def test_content_vacio_400(self):
        self._con_fake([])
        tid = self._thread()['thread_id']
        r = self.client.post(f'/api/ai/threads-tools/{tid}/messages/', {'content': '  '}, format='json')
        self.assertEqual(r.status_code, 400)


class WriteToolsFlagTests(AsistenteBase):
    """LLM_WRITE_TOOLS (default False): crear_venta/crear_compra fuera del schema y rechazadas."""

    def _tools_enviadas_ventas(self):
        fake = self._con_fake([texto('ok')])
        v = self.client.post('/api/ai/ventas-assistant/').json()
        self.client.post(f"/api/ai/ventas-assistant/{v['thread_id']}/messages/", {'message': 'hola'}, format='json')
        return {t.name for t in fake.llamadas[0][2]}

    def test_por_defecto_sin_tools_de_escritura_en_el_schema(self):
        from django.conf import settings
        self.assertFalse(settings.LLM_WRITE_TOOLS)
        nombres = self._tools_enviadas_ventas()
        self.assertEqual(nombres, {'buscar_productos', 'buscar_clientes'})
        from apps.ai_assistant.services.perfiles import PERFILES
        self.assertEqual({t.name for t in PERFILES['compras'].tools_activas()},
                         {'buscar_productos', 'buscar_proveedores', 'buscar_almacenes'})

    @override_settings(LLM_WRITE_TOOLS=True)
    def test_con_flag_se_exponen(self):
        nombres = self._tools_enviadas_ventas()
        self.assertEqual(nombres, {'crear_venta', 'buscar_productos', 'buscar_clientes'})

    def test_ejecutor_rechaza_crear_venta_con_flag_apagada(self):
        self._con_fake([tool('crear_venta', {'cliente_id': 1, 'tipo_venta': 'contado', 'metodo_pago': 'efectivo',
                                             'productos': [{'producto_sku': 'X', 'cantidad': 1, 'precio_unitario': 1}]}),
                        texto('No puedo registrar ventas.')])
        with mock.patch('apps.ai_assistant.services.ventas_executor.VentasExecutor.crear_venta') as cv:
            v = self.client.post('/api/ai/ventas-assistant/').json()
            r = self.client.post(f"/api/ai/ventas-assistant/{v['thread_id']}/messages/", {'message': 'crea la venta'},
                                 format='json')
        self.assertEqual(r.status_code, 200, r.content)
        cv.assert_not_called()
        from apps.ventas.models import Venta
        self.assertEqual(Venta.objects.filter(empresa=self.A).count(), 0)

    @override_settings(LLM_WRITE_TOOLS=True)
    def test_con_flag_el_ejecutor_si_llama(self):
        self._con_fake([tool('crear_venta', {'cliente_id': 1}), texto('Venta creada.')])
        with mock.patch('apps.ai_assistant.services.ventas_executor.VentasExecutor.crear_venta',
                        return_value={'success': True}) as cv:
            v = self.client.post('/api/ai/ventas-assistant/').json()
            self.client.post(f"/api/ai/ventas-assistant/{v['thread_id']}/messages/", {'message': 'crea la venta'},
                             format='json')
        cv.assert_called_once_with(cliente_id=1)


class ErroresProveedorTests(AsistenteBase):
    def test_sin_credenciales_503(self):
        self._con_fake([lc.LLMNoConfigurado('DefaultCredentialsError')])
        tid = self._thread()['thread_id']
        r = self.client.post(f'/api/ai/threads-tools/{tid}/messages/', {'content': 'hola'}, format='json')
        self.assertEqual(r.status_code, 503, r.content)
        self.assertIn('no está configurado', r.json()['error'])
        self.assertNotIn('DefaultCredentialsError', r.content.decode())

    def test_proveedor_caido_502(self):
        self._con_fake([lc.LLMNoDisponible('ServerError 503')])
        tid = self._thread()['thread_id']
        r = self.client.post(f'/api/ai/threads-tools/{tid}/messages/', {'content': 'hola'}, format='json')
        self.assertEqual(r.status_code, 502, r.content)
        self.assertIn('no está disponible', r.json()['error'])

    def test_fallo_al_construir_cliente_503(self):
        with mock.patch('apps.ai_assistant.services.chat.get_llm_client',
                        side_effect=lc.LLMNoConfigurado('LLM_MODEL vacío')):
            tid = self._thread()['thread_id']
            r = self.client.post(f'/api/ai/threads-tools/{tid}/messages/', {'content': 'hola'}, format='json')
        self.assertEqual(r.status_code, 503)

    def test_error_inesperado_500_generico(self):
        self._con_fake([RuntimeError('detalle interno')])
        tid = self._thread()['thread_id']
        r = self.client.post(f'/api/ai/threads-tools/{tid}/messages/', {'content': 'hola'}, format='json')
        self.assertEqual(r.status_code, 500)
        self.assertNotIn('detalle interno', r.content.decode())


class TraduccionErroresTests(TestCase):
    """Mapeo de excepciones del SDK → errores con nombre (sin red)."""

    @staticmethod
    def _exc(nombre, modulo, **attrs):
        cls = type(nombre, (Exception,), {'__module__': modulo})
        e = cls(nombre)
        for k, v in attrs.items():
            setattr(e, k, v)
        return e

    def test_vertex(self):
        t = lc.VertexClient._traducir
        self.assertIsInstance(t(self._exc('DefaultCredentialsError', 'google.auth.exceptions')), lc.LLMNoConfigurado)
        self.assertIsInstance(t(self._exc('ClientError', 'google.genai.errors', code=403)), lc.LLMNoConfigurado)
        self.assertIsInstance(t(self._exc('ClientError', 'google.genai.errors', code=404)), lc.LLMNoConfigurado)
        self.assertIsInstance(t(self._exc('ClientError', 'google.genai.errors', code=429)), lc.LLMNoDisponible)
        self.assertIsInstance(t(self._exc('ServerError', 'google.genai.errors', code=503)), lc.LLMNoDisponible)
        self.assertIsInstance(t(self._exc('ReadTimeout', 'httpx')), lc.LLMNoDisponible)
        self.assertIsInstance(t(self._exc('ConnectError', 'httpx')), lc.LLMNoDisponible)
        malo = t(self._exc('ClientError', 'google.genai.errors', code=400))
        self.assertIsInstance(malo, lc.LLMError)
        self.assertNotIsInstance(malo, (lc.LLMNoConfigurado, lc.LLMNoDisponible))

    def test_openai_compat(self):
        t = lc.OpenAICompatClient._traducir
        self.assertIsInstance(t(self._exc('AuthenticationError', 'openai')), lc.LLMNoConfigurado)
        self.assertIsInstance(t(self._exc('PermissionDeniedError', 'openai')), lc.LLMNoConfigurado)
        self.assertIsInstance(t(self._exc('NotFoundError', 'openai')), lc.LLMNoConfigurado)
        self.assertIsInstance(t(self._exc('APITimeoutError', 'openai')), lc.LLMNoDisponible)
        self.assertIsInstance(t(self._exc('RateLimitError', 'openai')), lc.LLMNoDisponible)
        self.assertIsInstance(t(self._exc('InternalServerError', 'openai')), lc.LLMNoDisponible)

    def test_openai_sin_api_key_es_no_configurado(self):
        c = lc.OpenAICompatClient('m', 30, base_url=None, api_key=None)
        with self.assertRaises(lc.LLMNoConfigurado):
            c.chat('s', [], [])

    def test_vertex_sin_project_es_no_configurado(self):
        c = lc.VertexClient('m', 30, project='', location='global')
        with self.assertRaises(lc.LLMNoConfigurado):
            c.chat('s', [], [])

    @override_settings(LLM_PROVIDER='otro', LLM_MODEL='x')
    def test_proveedor_desconocido(self):
        with self.assertRaises(lc.LLMNoConfigurado):
            lc.get_llm_client()

    @override_settings(LLM_PROVIDER='vertex', LLM_MODEL='', LLM_PROJECT='p')
    def test_modelo_vacio(self):
        with self.assertRaises(lc.LLMNoConfigurado):
            lc.get_llm_client()

    def test_parseo_respuesta_vertex(self):
        fc = SimpleNamespace(name='analizar_ventas', args={'periodo': 'mes'}, id=None)
        partes = [SimpleNamespace(function_call=fc, text=None, thought=False),
                  SimpleNamespace(function_call=None, text='pensando', thought=True),
                  SimpleNamespace(function_call=None, text='Hola', thought=False)]
        resp = SimpleNamespace(
            candidates=[SimpleNamespace(content=SimpleNamespace(parts=partes))],
            usage_metadata=SimpleNamespace(prompt_token_count=100, candidates_token_count=20, thoughts_token_count=5))
        out = lc.VertexClient('m', 30, 'p', 'global')._de_respuesta(resp)
        self.assertEqual(out.text, 'Hola')
        self.assertEqual(out.tool_calls[0].name, 'analizar_ventas')
        self.assertEqual(out.tool_calls[0].arguments, {'periodo': 'mes'})
        self.assertEqual((out.tokens_entrada, out.tokens_salida), (100, 25))


class SchemaToolsTests(TestCase):
    def test_schema_sin_ref_title_default_y_con_nullable(self):
        from apps.ai_assistant.tools.ventas_tools import CrearVentaParams
        s = json.dumps(schema_de_pydantic(CrearVentaParams))
        for prohibido in ('$ref', '$defs', '"title"', '"default"'):
            self.assertNotIn(prohibido, s)
        props = schema_de_pydantic(CrearVentaParams)['properties']
        self.assertEqual(props['productos']['items']['properties']['cantidad']['type'], 'integer')
        self.assertTrue(props['notas'].get('nullable'))
        self.assertEqual(props['notas']['type'], 'string')

    def test_perfiles_no_exponen_empresa(self):
        from apps.ai_assistant.services.perfiles import PERFILES
        for perfil in PERFILES.values():
            for t in perfil.tools:
                self.assertNotIn('empresa', json.dumps(t.parameters).lower(), f'{perfil.clave}/{t.name}')


class AislamientoAsistenteTests(AsistenteBase):
    def setUp(self):
        super().setUp()
        self._con_fake([texto('x')] * 5)
        self.tid_a = self._thread()['thread_id']

    def test_otro_tenant_no_escribe_ni_lee_el_thread(self):
        self.client.force_authenticate(self.user_b)
        r = self.client.post(f'/api/ai/threads-tools/{self.tid_a}/messages/', {'content': 'intruso'}, format='json')
        self.assertEqual(r.status_code, 404, r.content)
        g = self.client.get(f'/api/ai/threads-tools/{self.tid_a}/messages/')
        self.assertEqual(g.status_code, 404)
        self.assertFalse(Message.objects.filter(conversation__thread_id=self.tid_a, content='intruso').exists())

    def test_mismo_tenant_otro_usuario_tampoco(self):
        self.client.force_authenticate(self.user_a2)
        r = self.client.post(f'/api/ai/threads-tools/{self.tid_a}/messages/', {'content': 'colega'}, format='json')
        self.assertEqual(r.status_code, 404, r.content)
        self.assertEqual(self.client.get(f'/api/ai/threads-tools/{self.tid_a}/messages/').status_code, 404)

    def test_mensajes_anidados_de_conversacion_ajena_404(self):
        conv_a = Conversation.objects.get(thread_id=self.tid_a)
        self.client.force_authenticate(self.user_b)
        self.assertEqual(self.client.get(f'/api/ai/conversations/{conv_a.pk}/messages/').status_code, 404)
        self.client.force_authenticate(self.user_a2)
        self.assertEqual(self.client.get(f'/api/ai/conversations/{conv_a.pk}/messages/').status_code, 404)
        self.client.force_authenticate(self.user_a)
        self.assertEqual(self.client.get(f'/api/ai/conversations/{conv_a.pk}/messages/').status_code, 200)

    def test_el_perfil_del_endpoint_debe_coincidir(self):
        # Un thread de Jorge no se puede usar desde el asistente de ventas (tools de escritura).
        r = self.client.post(f'/api/ai/ventas-assistant/{self.tid_a}/messages/', {'message': 'crea una venta'}, format='json')
        self.assertEqual(r.status_code, 404, r.content)

    def test_ventas_get_or_create_es_por_perfil_y_usuario(self):
        r1 = self.client.get('/api/ai/ventas-assistant/conversation/')
        self.assertEqual(r1.status_code, 200, r1.content)
        self.assertEqual(r1.json()['assistant'], 'ventas')
        self.assertNotEqual(r1.json()['thread_id'], self.tid_a)  # no reutiliza la de Jorge
        r2 = self.client.get('/api/ai/ventas-assistant/conversation/')
        self.assertEqual(r1.json()['thread_id'], r2.json()['thread_id'])
        self.client.force_authenticate(self.user_a2)
        r3 = self.client.get('/api/ai/ventas-assistant/conversation/')
        self.assertNotEqual(r3.json()['thread_id'], r1.json()['thread_id'])

    def test_sin_empresa_400(self):
        huerfano = User(email='h@h.pe', username='h@h.pe')
        huerfano.set_password('x')
        huerfano.save()
        # El signal post_save crea una empresa a todo usuario nuevo; la quitamos.
        User.objects.filter(pk=huerfano.pk).update(empresa=None)
        huerfano.refresh_from_db()
        self.client.force_authenticate(huerfano)
        r = self.client.post('/api/ai/threads-tools/')
        self.assertEqual(r.status_code, 400)

    def test_contrato_ventas_y_compras(self):
        v = self.client.post('/api/ai/ventas-assistant/')
        self.assertEqual(v.status_code, 200)
        self.assertEqual(set(v.json()), {'thread_id', 'conversation_id', 'assistant'})
        r = self.client.post(f"/api/ai/ventas-assistant/{v.json()['thread_id']}/messages/", {'message': 'hola'}, format='json')
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual(set(r.json()), {'response'})
        c = self.client.post('/api/ai/compras-assistant/')
        self.assertEqual(c.json()['assistant'], 'compras')
        self.assertEqual(Conversation.objects.get(thread_id=c.json()['thread_id']).perfil, 'compras')

    def test_threads_generico_201_y_mensaje(self):
        r = self.client.post('/api/ai/threads/')
        self.assertEqual(r.status_code, 201, r.content)
        self.assertEqual(set(r.json()), {'thread_id', 'conversation_id', 'message'})
        tid = r.json()['thread_id']
        m = self.client.post(f'/api/ai/threads/{tid}/messages/', {'content': 'hola'}, format='json')
        self.assertEqual(m.status_code, 200, m.content)
        self.assertEqual(set(m.json()), {'message'})
