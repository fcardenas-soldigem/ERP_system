"""C10 — webhook: secreto, idempotencia, vinculación, no vinculado, audio."""
from datetime import timedelta
from unittest import mock

from django.utils import timezone

from apps.canales.models import UpdateProcesado, VinculacionTelegram
from apps.canales.nucleo.orquestador import MSG_NO_VINCULADO

from .base import CanalTestCase


class WebhookSeguridadTests(CanalTestCase):
    def test_cabecera_invalida_403(self):
        r = self.post_update(self.update_texto(self.CHAT_A, 'hola'), secreto='equivocado')
        self.assertEqual(r.status_code, 403)
        self.assertEqual(UpdateProcesado.objects.count(), 0)
        self.assertEqual(self.respuestas_bot(), [])

    def test_sin_cabecera_403(self):
        r = self.post_update(self.update_texto(self.CHAT_A, 'hola'), secreto=None)
        self.assertEqual(r.status_code, 403)

    def test_idempotencia_por_update_id(self):
        upd = self.update_texto(self.CHAT_A, '/ayuda')
        r1 = self.post_update(upd)
        r2 = self.post_update(upd)  # Telegram reintenta el MISMO update
        self.assertEqual((r1.status_code, r2.status_code), (200, 200))
        self.assertTrue(r2.json().get('duplicado'))
        # se procesó UNA sola vez → una sola respuesta del bot
        self.assertEqual(len(self.respuestas_bot()), 1)

    def test_payload_sin_update_id_no_revienta(self):
        r = self.post_update({'otro': 1})
        self.assertEqual(r.status_code, 200)


class VinculacionTests(CanalTestCase):
    def _codigo_para(self, usuario):
        vinc = VinculacionTelegram.objects.create(
            usuario=usuario, codigo_expira=timezone.now() + timedelta(minutes=10))
        return vinc

    def test_no_vinculado_recibe_instrucciones_y_nada_mas(self):
        chat_desconocido = 999999
        self.post_update(self.update_texto(chat_desconocido, 'cotiza algo'))
        chat, texto, botones = self.ultima_respuesta()
        self.assertEqual(chat, str(chat_desconocido))
        self.assertIn('Vincular Telegram', texto)
        self.assertEqual(botones, [])

    def test_start_con_codigo_valido_vincula(self):
        from django.contrib.auth import get_user_model
        nuevo = get_user_model().objects.create_user(
            username='nuevo@a.pe', email='nuevo@a.pe', password='x',
            nombre='Nuevo', apellido='A', empresa=self.empresa_a, rol='operador')
        vinc = self._codigo_para(nuevo)
        self.post_update(self.update_texto(444444, f'/start {vinc.codigo}'))
        vinc.refresh_from_db()
        self.assertEqual(vinc.chat_id, 444444)
        self.assertIn('✅', self.ultima_respuesta()[1])

    def test_start_codigo_expirado_o_usado(self):
        from django.contrib.auth import get_user_model
        u = get_user_model().objects.create_user(
            username='exp@a.pe', email='exp@a.pe', password='x',
            nombre='Exp', apellido='A', empresa=self.empresa_a, rol='operador')
        vinc = self._codigo_para(u)
        VinculacionTelegram.objects.filter(pk=vinc.pk).update(codigo_expira=timezone.now() - timedelta(minutes=1))
        self.post_update(self.update_texto(555555, f'/start {vinc.codigo}'))
        self.assertIn('no es válido o ya venció', self.ultima_respuesta()[1])
        vinc.refresh_from_db()
        self.assertIsNone(vinc.chat_id)
        # usado: el del vendedor ya está vinculado → su código no canjea
        vinc_usado = VinculacionTelegram.objects.get(usuario=self.vendedor)
        self.post_update(self.update_texto(666666, f'/start {vinc_usado.codigo}'))
        self.assertIn('no es válido o ya venció', self.ultima_respuesta()[1])

    def test_desvincular(self):
        self.post_update(self.update_texto(self.CHAT_A, '/desvincular'))
        self.assertFalse(VinculacionTelegram.objects.filter(usuario=self.vendedor).exists())
        self.assertIn('desvinculé', self.ultima_respuesta()[1])

    def test_api_vincular_genera_codigo_y_link(self):
        self.client.force_authenticate(self.vendedor_b)
        VinculacionTelegram.objects.filter(usuario=self.vendedor_b).delete()
        r = self.client.post('/api/canales/telegram/vincular/')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.json()['codigo']), 8)
        self.assertIn('t.me/SoldigemPruebaBot?start=', r.json()['link'])


class AudioTests(CanalTestCase):
    def test_audio_se_transcribe_y_fluye_al_interprete(self):
        self.mock_llm('consultar_venta', {'cliente_query': 'Transportes Lima'})
        with mock.patch('apps.canales.telegram.TelegramCanal.descargar_archivo', return_value=b'OGG'), \
             mock.patch('apps.canales.transcripcion.transcribir', return_value='ya pagó transportes lima?') as m_tr:
            CanalTestCase._update_id += 1
            self.post_update({'update_id': CanalTestCase._update_id, 'message': {
                'chat': {'id': self.CHAT_A}, 'from': {'first_name': 'V'},
                'voice': {'file_id': 'voz1', 'duration': 3},
            }})
        m_tr.assert_called_once()
        texto = self.ultima_respuesta()[1]
        self.assertIn(self.venta.numero, texto)  # respondió la consulta de la venta

    def test_audio_ilegible_pide_texto(self):
        with mock.patch('apps.canales.telegram.TelegramCanal.descargar_archivo', return_value=b'OGG'), \
             mock.patch('apps.canales.transcripcion.transcribir', return_value=''):
            CanalTestCase._update_id += 1
            self.post_update({'update_id': CanalTestCase._update_id, 'message': {
                'chat': {'id': self.CHAT_A}, 'from': {'first_name': 'V'},
                'voice': {'file_id': 'voz2'},
            }})
        self.assertIn('audio', self.ultima_respuesta()[1].lower())


class TranscripcionConfigTests(CanalTestCase):
    """El audio usa la MISMA configuración LLM_* que el resto (sin red)."""

    def test_usa_proyecto_region_y_modelo_de_settings(self):
        from django.test import override_settings
        from apps.canales import transcripcion
        with override_settings(LLM_PROJECT='erp-system-468516', LLM_LOCATION='global',
                               LLM_MODEL='gemini-3.1-flash-lite'), \
             mock.patch('google.genai.Client') as cliente:
            cliente.return_value.models.generate_content.return_value.text = ' ya pagó acme? '
            texto = transcripcion.transcribir(b'OGG')
        self.assertEqual(texto, 'ya pagó acme?')
        kwargs = cliente.call_args.kwargs
        self.assertEqual((kwargs['vertexai'], kwargs['project'], kwargs['location']),
                         (True, 'erp-system-468516', 'global'))
        llamada = cliente.return_value.models.generate_content.call_args.kwargs
        self.assertEqual(llamada['model'], 'gemini-3.1-flash-lite')
