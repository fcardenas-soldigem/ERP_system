"""Bucle de tools compartido por el bot y eval_agente.

Reglas (tras el eval real: #5, #7 y #11 agotaban 5 rondas repitiendo buscar_*):
- toda lectura o preparación corta el bucle en SU ronda;
- solo se sigue para que el modelo corrija argumentos inválidos;
- una llamada repetida (misma tool, mismos argumentos) no se ejecuta otra vez;
- tope: 3 rondas.
"""
from unittest import mock

from apps.canales.models import BorradorAgente
from apps.canales.nucleo.interprete import MAX_RONDAS, resolver

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
    def test_tope_es_3(self):
        self.assertEqual(MAX_RONDAS, 3)

    def test_consulta_de_producto_cuesta_una_ronda(self):
        """#5/#11: antes 5 rondas (el modelo repetía buscar_producto)."""
        llm = FakeLLM([respuesta_llm('buscar_producto', {'query': 'jabra 750'})] * 5)
        r = resolver(self.vendedor, 'precio y stock del jabra 750?', cliente=llm)
        self.assertEqual((r.tipo, r.nombre, r.rondas), ('lectura', 'buscar_producto', 1))
        self.assertEqual(len(llm.vistos), 1)                       # una sola llamada al modelo
        self.assertEqual(r.resultado['productos'][0]['precio_venta'], '450.00')

    def test_consulta_de_cliente_cuesta_una_ronda(self):
        """#7: antes 5 rondas (el modelo repetía buscar_cliente)."""
        llm = FakeLLM([respuesta_llm('buscar_cliente', {'query': 'transportes'})] * 5)
        r = resolver(self.vendedor, 'ruc de transportes lima', cliente=llm)
        self.assertEqual((r.tipo, r.nombre, r.rondas), ('lectura', 'buscar_cliente', 1))
        self.assertEqual(r.resultado['clientes'][0]['documento'], self.cliente.documento)

    def test_el_resultado_de_una_lectura_nunca_va_al_modelo(self):
        llm = FakeLLM([respuesta_llm('buscar_producto', {'query': 'jabra 750'})])
        resolver(self.vendedor, 'jabra?', cliente=llm)
        roles = [m.role for ronda in llm.vistos for m in ronda]
        self.assertNotIn('tool', roles)

    def test_buscar_antes_de_cotizar_responde_la_busqueda(self):
        """Trade-off asumido: si el modelo busca ANTES de cotizar, el bot responde
        con la búsqueda (no cotiza). Con preparar_cotizacion recibiendo texto el
        modelo ya no lo hace (eval real 20/20); si volviera a pasar, eval_agente
        lo marca como incorrecto en los casos de cotizar."""
        llm = FakeLLM([
            respuesta_llm('buscar_producto', {'query': 'jabra 750'}),
            respuesta_llm('preparar_cotizacion', {'cliente': 'transportes lima',
                                                  'items': [{'producto': 'jabra 750', 'cantidad': 3}]}),
        ])
        r = resolver(self.vendedor, 'cotiza 3 jabra a transportes', cliente=llm)
        self.assertEqual((r.tipo, r.nombre, r.rondas), ('lectura', 'buscar_producto', 1))

    def test_lectura_terminal_corta_en_una_ronda(self):
        llm = FakeLLM([respuesta_llm('consultar_venta', {'venta_numero': self.venta.numero})])
        r = resolver(self.vendedor, 'ya pagó?', cliente=llm)
        self.assertEqual((r.tipo, r.rondas), ('lectura', 1))

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

    def test_llamada_repetida_no_se_reintenta(self):
        """Deduplicación: el mismo pedido inválido dos veces corta en la ronda 2
        (no gasta la 3.ª ni vuelve a procesarlo)."""
        invalido = respuesta_llm('preparar_cotizacion', {'items': []})
        llm = FakeLLM([invalido, invalido, invalido])
        r = resolver(self.vendedor, 'cotiza', cliente=llm)
        self.assertEqual((r.tipo, r.rondas), ('faltan_datos', 2))
        self.assertEqual(len(llm.vistos), 2)

    def test_tope_de_tres_rondas(self):
        """Correcciones distintas y todas inválidas: se corta en la 3.ª."""
        llm = FakeLLM([respuesta_llm('preparar_cotizacion', {'items': [], 'asunto': str(i)})
                       for i in range(9)])
        r = resolver(self.vendedor, 'cotiza', cliente=llm)
        self.assertEqual((r.tipo, r.rondas), ('faltan_datos', 3))
        self.assertEqual(len(llm.vistos), 3)

    def test_solo_argumentos_invalidos_pide_datos(self):
        llm = FakeLLM([respuesta_llm('preparar_cotizacion', {'items': []}),
                       respuesta_llm(None, texto='?')])
        r = resolver(self.vendedor, 'cotiza', cliente=llm)
        self.assertEqual(r.tipo, 'faltan_datos')

    def test_bot_por_webhook_consulta_en_una_llamada(self):
        with mock.patch('apps.canales.nucleo.interprete.get_llm_client') as m:
            m.return_value.chat.side_effect = [respuesta_llm('buscar_producto', {'query': 'jabra'})] * 5
            self.post_update(self.update_texto(self.CHAT_A, 'precio del jabra'))
        self.assertEqual(m.return_value.chat.call_count, 1)
        self.assertIn('Jabra Evolve2 750', self.ultima_respuesta()[1])
        self.assertEqual(len(self.respuestas_bot()), 1)   # B7: un solo mensaje

    def test_bot_por_webhook_cotiza_y_deja_un_borrador(self):
        with mock.patch('apps.canales.nucleo.interprete.get_llm_client') as m:
            m.return_value.chat.side_effect = [respuesta_llm(
                'preparar_cotizacion', {'cliente': 'transportes lima',
                                        'items': [{'producto': 'jabra 750', 'cantidad': 2}]})]
            self.post_update(self.update_texto(self.CHAT_A, 'cotiza 2 jabra a transportes'))
        self.assertEqual(BorradorAgente.objects.filter(estado='pendiente').count(), 1)
        self.assertEqual(len(self.respuestas_bot()), 1)
