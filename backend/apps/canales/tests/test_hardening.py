"""Regresiones de REVIEW_BOT.md: #3 doble confirmación, #5 transición de
cot:enviada, #7 camino de la foto, #12 callbacks forjados, #13 HTML."""
from decimal import Decimal
from unittest import mock

from django.utils import timezone

from apps.canales.models import BorradorAgente
from apps.cotizaciones.models import Cotizacion
from apps.ventas.models import PagoVenta

from .base import CanalTestCase


class DobleConfirmacionTests(CanalTestCase):
    def test_segundo_toque_no_duplica_el_cobro(self):
        """#3 — el botón se puede tocar dos veces (dos update_id distintos):
        solo UN pago debe nacer."""
        self.mock_llm('preparar_cobro', {'venta_numero': self.venta.numero})
        self.post_update(self.update_texto(self.CHAT_A, 'cobra la venta'))
        borrador = BorradorAgente.objects.get(estado='pendiente')

        self.post_update(self.update_callback(self.CHAT_A, f'b:{borrador.id}:ok'))
        self.post_update(self.update_callback(self.CHAT_A, f'b:{borrador.id}:ok'))

        self.assertEqual(PagoVenta.objects.count(), 1)
        borrador.refresh_from_db()
        self.assertEqual(borrador.estado, 'confirmado')
        self.assertIn('ya está confirmado', self.ultima_respuesta()[1])


class TransicionEnviadaTests(CanalTestCase):
    def _cotizacion(self, estado):
        cot = Cotizacion.objects.create(
            empresa=self.empresa_a, cliente=self.cliente, usuario_creador=self.vendedor,
            asunto='X', fecha_vencimiento=timezone.localdate())
        Cotizacion.objects.filter(pk=cot.pk).update(estado=estado)
        cot.refresh_from_db()
        return cot

    def test_aceptada_no_retrocede_a_enviada(self):
        """#5 — callback_data forjado no puede retroceder estados."""
        cot = self._cotizacion('aceptada')
        self.post_update(self.update_callback(self.CHAT_A, f'cot:{cot.id}:enviada'))
        cot.refresh_from_db()
        self.assertEqual(cot.estado, 'aceptada')
        self.assertIn('no la muevo', self.ultima_respuesta()[1])

    def test_borrador_si_pasa_a_enviada(self):
        cot = self._cotizacion('borrador')
        self.post_update(self.update_callback(self.CHAT_A, f'cot:{cot.id}:enviada'))
        cot.refresh_from_db()
        self.assertEqual(cot.estado, 'enviada')

    def test_callback_con_id_basura_no_revienta(self):
        """#12 — ids no numéricos: respuesta fija, nunca silencio/500."""
        for data in ('cot:abc:enviada', 'b:x:ok', 'b::ok'):
            self.post_update(self.update_callback(self.CHAT_A, data))
            self.assertIn('Puedo ayudarte con', self.ultima_respuesta()[1])


class FotoComprobanteTests(CanalTestCase):
    def _foto(self, chat):
        CanalTestCase._update_id += 1
        return {'update_id': CanalTestCase._update_id, 'message': {
            'chat': {'id': chat}, 'from': {'first_name': 'V'},
            'photo': [{'file_id': 'chica'}, {'file_id': 'grande'}],
        }}

    def _cobro_confirmado(self):
        self.mock_llm('preparar_cobro', {'venta_numero': self.venta.numero})
        self.post_update(self.update_texto(self.CHAT_A, 'cobra todo'))
        borrador = BorradorAgente.objects.get(estado='pendiente')
        self.post_update(self.update_callback(self.CHAT_A, f'b:{borrador.id}:ok'))
        return borrador

    def test_foto_tras_cobro_que_saldo_la_venta(self):
        """#7 — el caso que antes moría en silencio: cobro COMPLETO (saldo 0)
        y después la foto del comprobante."""
        borrador = self._cobro_confirmado()
        self.venta.refresh_from_db()
        self.assertEqual(self.venta.estado, 'pagado')  # quedó saldada

        with mock.patch('apps.canales.telegram.TelegramCanal.descargar_archivo', return_value=b'JPG' * 10):
            self.post_update(self._foto(self.CHAT_A))

        pago = PagoVenta.objects.get()
        self.assertTrue(pago.comprobante.name.startswith(f'canales/empresa_{self.empresa_a.id}/'))
        self.assertIn('comprobante', self.ultima_respuesta()[1])

    def test_segunda_foto_no_pisa_el_comprobante(self):
        self._cobro_confirmado()
        with mock.patch('apps.canales.telegram.TelegramCanal.descargar_archivo', return_value=b'JPG'):
            self.post_update(self._foto(self.CHAT_A))
            primera = PagoVenta.objects.get().comprobante.name
            self.post_update(self._foto(self.CHAT_A))
        self.assertEqual(PagoVenta.objects.get().comprobante.name, primera)
        self.assertIn('ya tiene comprobante', self.ultima_respuesta()[1])

    def test_foto_sin_contexto_se_guarda_y_avisa(self):
        with mock.patch('apps.canales.telegram.TelegramCanal.descargar_archivo', return_value=b'JPG'):
            self.post_update(self._foto(self.CHAT_A))
        self.assertIn('no sé a qué cobro', self.ultima_respuesta()[1])


class EscapeHTMLTests(CanalTestCase):
    def test_nombre_de_cliente_con_html_no_rompe_el_mensaje(self):
        """#13 — «<b>Acme» en BD no debe viajar crudo con parse_mode=HTML."""
        self.cliente.nombre = '<b>Acme & Hijos'
        self.cliente.save(update_fields=['nombre'])
        self.mock_llm('buscar_cliente', {'query': 'acme'})
        self.post_update(self.update_texto(self.CHAT_A, 'busca acme'))
        texto = self.ultima_respuesta()[1]
        self.assertIn('&lt;b&gt;Acme &amp; Hijos', texto)
        self.assertNotIn('<b>Acme', texto)
