"""Punto 3 — bucle de tools compartido por el bot y eval_agente."""
from unittest import mock

from apps.canales.models import BorradorAgente
from apps.canales.nucleo.interprete import resolver

from .base import CanalTestCase, respuesta_llm


class FakeLLM:
    """Devuelve las respuestas en orden y guarda lo que recibió en cada ronda."""

    def __init__(self, respuestas):
        self.respuestas = list(respuestas)
        self.vistos = []

    def chat(self, system, messages, tools, temperature=0.2):
        self.vistos.append(list(messages))
        return self.respuestas.pop(0) if self.respuestas else respuesta_llm(None, texto='...')


class BucleTests(CanalTestCase):
    def test_busca_y_luego_cotiza_en_dos_rondas(self):
        """Lo que hizo gemini en #1/#8/#13: buscar_producto y DESPUÉS cotizar.
        Antes el eval solo miraba la 1ª llamada; ahora gana la preparación."""
        llm = FakeLLM([
            respuesta_llm('buscar_producto', {'query': 'jabra 750'}),
            respuesta_llm('preparar_cotizacion', {'cliente': 'transportes lima',
                                                  'items': [{'producto': 'jabra 750', 'cantidad': 3}]}),
        ])
        r = resolver(self.vendedor, 'cotiza 3 jabra a transportes', cliente=llm)
        self.assertEqual((r.tipo, r.nombre, r.rondas), ('preparacion', 'preparar_cotizacion', 2))
        self.assertEqual(r.llamadas, [(1, 'buscar_producto'), (2, 'preparar_cotizacion')])
        self.assertEqual(r.tokens_entrada, 100)

    def test_al_modelo_no_le_llegan_costos_ni_proveedores(self):
        llm = FakeLLM([respuesta_llm('buscar_producto', {'query': 'jabra 750'})])
        resolver(self.vendedor, 'jabra?', cliente=llm)
        tool_msg = [m for m in llm.vistos[1] if m.role == 'tool'][0]
        self.assertIn('Jabra Evolve2 750', tool_msg.content)
        for prohibido in ('ultimo_costo', 'precio_venta', 'proveedor', 'stock', '300', '450'):
            self.assertNotIn(prohibido, tool_msg.content)

    def test_lectura_intermedia_que_es_la_respuesta(self):
        llm = FakeLLM([respuesta_llm('buscar_producto', {'query': 'jabra 750'}),
                       respuesta_llm(None, texto='Aquí tienes')])
        r = resolver(self.vendedor, 'precio del jabra', cliente=llm)
        self.assertEqual((r.tipo, r.nombre, r.rondas), ('lectura', 'buscar_producto', 2))
        self.assertEqual(r.resultado['productos'][0]['precio_venta'], '450.00')

    def test_lectura_terminal_corta_en_una_ronda(self):
        llm = FakeLLM([respuesta_llm('consultar_venta', {'venta_numero': self.venta.numero})])
        r = resolver(self.vendedor, 'ya pagó?', cliente=llm)
        self.assertEqual((r.tipo, r.rondas), ('lectura', 1))

    def test_tope_de_cinco_rondas(self):
        llm = FakeLLM([respuesta_llm('buscar_cliente', {'query': 'transportes'})] * 9)
        r = resolver(self.vendedor, 'x', cliente=llm)
        self.assertEqual(r.rondas, 5)
        self.assertEqual(r.tipo, 'lectura')   # se queda con la última lectura útil

    def test_argumentos_invalidos_se_devuelven_al_modelo_para_corregir(self):
        llm = FakeLLM([
            respuesta_llm('preparar_cotizacion', {'items': []}),          # inválido
            respuesta_llm('preparar_cotizacion', {'cliente': 'transportes lima',
                                                  'items': [{'producto': 'jabra 750', 'cantidad': 1}]}),
        ])
        r = resolver(self.vendedor, 'cotiza', cliente=llm)
        self.assertEqual((r.tipo, r.rondas), ('preparacion', 2))
        error = [m for m in llm.vistos[1] if m.role == 'tool'][0].content
        self.assertIn('argumentos inválidos', error)

    def test_solo_argumentos_invalidos_pide_datos(self):
        llm = FakeLLM([respuesta_llm('preparar_cotizacion', {'items': []}),
                       respuesta_llm(None, texto='?')])
        r = resolver(self.vendedor, 'cotiza', cliente=llm)
        self.assertEqual(r.tipo, 'faltan_datos')

    def test_bot_completo_con_dos_rondas(self):
        """De punta a punta por el webhook: buscar y cotizar → UN borrador."""
        with mock.patch('apps.canales.nucleo.interprete.get_llm_client') as m:
            m.return_value.chat.side_effect = [
                respuesta_llm('buscar_producto', {'query': 'jabra'}),
                respuesta_llm('preparar_cotizacion', {'cliente': 'transportes lima',
                                                      'items': [{'producto': 'jabra 750', 'cantidad': 2}]}),
            ]
            self.post_update(self.update_texto(self.CHAT_A, 'cotiza 2 jabra a transportes'))
        self.assertEqual(BorradorAgente.objects.filter(estado='pendiente').count(), 1)
        self.assertEqual(len(self.respuestas_bot()), 1)   # B7: un solo mensaje
