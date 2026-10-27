"""C10 — flujo de borradores: cotización completa, edición, expiración,
aislamiento entre empresas, solo_lectura y límites."""
from datetime import timedelta
from decimal import Decimal
from unittest import mock

from django.utils import timezone

from apps.canales.models import BorradorAgente
from apps.canales.nucleo.orquestador import MSG_SOLO_LECTURA
from apps.cotizaciones.models import Cotizacion
from apps.ventas.models import PagoVenta

from .base import CanalTestCase, respuesta_llm


def _args_cotizacion():
    return {
        'cliente_query': 'Transportes Lima',
        'items': [{'producto_id': None, 'descripcion': None, 'cantidad': 3, 'precio_unitario': None}],
        'moneda': 'PEN',
    }


class CotizacionCompletaTests(CanalTestCase):
    def test_flujo_completo_con_confirmacion(self):
        # el intérprete resuelve el producto con producto_id
        self.mock_llm('preparar_cotizacion', {
            'cliente_query': 'Transportes Lima',
            'items': [{'producto_id': self.producto.id, 'cantidad': 3}],
            'moneda': 'PEN',
        })
        self.post_update(self.update_texto(self.CHAT_A, 'cotízale 3 jabra 750 a transportes lima'))

        borrador = BorradorAgente.objects.get(usuario=self.vendedor, estado='pendiente')
        self.assertEqual(borrador.tipo, 'cotizacion')
        chat, texto, botones = self.ultima_respuesta()
        self.assertIn('Cotización', texto)
        self.assertIn('Transportes Lima', texto)
        self.assertIn(f'b:{borrador.id}:ok', botones)
        self.assertEqual(Cotizacion.objects.count(), 0)  # NUNCA sin confirmación

        # confirmar con el botón
        self.post_update(self.update_callback(self.CHAT_A, f'b:{borrador.id}:ok'))
        borrador.refresh_from_db()
        self.assertEqual(borrador.estado, 'confirmado')
        cot = Cotizacion.objects.get()
        self.assertEqual(cot.empresa, self.empresa_a)
        self.assertEqual(cot.cliente, self.cliente)
        self.assertEqual(cot.detalles.count(), 1)
        self.assertEqual(cot.detalles.first().cantidad, Decimal('3'))

        chat, texto, botones = self.ultima_respuesta()
        self.assertIn(cot.numero, texto)
        self.assertIn('/api/canales/pdf-cotizacion/?t=', texto)       # link firmado
        self.assertIn(f'cot:{cot.id}:enviada', botones)               # marcar enviada

        # el link firmado del PDF responde sin sesión
        firma = texto.split('?t=')[1].split()[0]
        r = self.client.get(f'/api/canales/pdf-cotizacion/?t={firma}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r['Content-Type'], 'application/pdf')

        # botón "Marcar como enviada"
        self.post_update(self.update_callback(self.CHAT_A, f'cot:{cot.id}:enviada'))
        cot.refresh_from_db()
        self.assertEqual(cot.estado, 'enviada')

    def test_pdf_con_firma_invalida_403(self):
        r = self.client.get('/api/canales/pdf-cotizacion/?t=1:falsa')
        self.assertEqual(r.status_code, 403)

    def test_cancelar_no_crea_nada(self):
        self.mock_llm('preparar_cotizacion', {
            'cliente_query': 'Transportes Lima',
            'items': [{'producto_id': self.producto.id, 'cantidad': 1}],
        })
        self.post_update(self.update_texto(self.CHAT_A, 'cotiza 1 jabra'))
        borrador = BorradorAgente.objects.get(estado='pendiente')
        self.post_update(self.update_callback(self.CHAT_A, f'b:{borrador.id}:no'))
        borrador.refresh_from_db()
        self.assertEqual(borrador.estado, 'cancelado')
        self.assertEqual(Cotizacion.objects.count(), 0)


class EdicionYExpiracionTests(CanalTestCase):
    def test_editar_acepta_correccion_en_lenguaje_natural(self):
        m = self.mock_llm('preparar_cotizacion', {
            'cliente_query': 'Transportes Lima',
            'items': [{'producto_id': self.producto.id, 'cantidad': 3}],
        })
        self.post_update(self.update_texto(self.CHAT_A, 'cotiza 3 jabra a transportes'))
        b1 = BorradorAgente.objects.get(estado='pendiente')

        self.post_update(self.update_callback(self.CHAT_A, f'b:{b1.id}:editar'))
        self.assertIn('qué corrijo', self.ultima_respuesta()[1])

        # la corrección vuelve a llamar la tool con los datos corregidos
        m.return_value.chat.return_value = respuesta_llm('preparar_cotizacion', {
            'cliente_query': 'Transportes Lima',
            'items': [{'producto_id': self.producto.id, 'cantidad': 5}],
        })
        self.post_update(self.update_texto(self.CHAT_A, 'que sean 5'))
        # el contexto de edición llegó al LLM
        historial = m.return_value.chat.call_args.kwargs.get('messages') or m.return_value.chat.call_args[1].get('messages')
        self.assertTrue(any('corrige' in (msg.content or '') for msg in historial))

        b1.refresh_from_db()
        self.assertEqual(b1.estado, 'cancelado')  # el anterior quedó cancelado
        b2 = BorradorAgente.objects.get(estado='pendiente')
        self.assertIn("'cantidad': '5'", str(b2.payload))

    def test_borrador_expirado_no_se_confirma(self):
        self.mock_llm('preparar_cobro', {'venta_numero': self.venta.numero})
        self.post_update(self.update_texto(self.CHAT_A, 'cobra la venta'))
        borrador = BorradorAgente.objects.get(estado='pendiente')
        BorradorAgente.objects.filter(pk=borrador.pk).update(
            created_at=timezone.now() - timedelta(minutes=31))
        self.post_update(self.update_callback(self.CHAT_A, f'b:{borrador.id}:ok'))
        borrador.refresh_from_db()
        self.assertEqual(borrador.estado, 'expirado')
        self.assertIn('expiró', self.ultima_respuesta()[1])
        self.assertEqual(PagoVenta.objects.count(), 0)


class CobroTests(CanalTestCase):
    def test_cobro_hereda_moneda_y_precarga_saldo(self):
        self.mock_llm('preparar_cobro', {'venta_numero': self.venta.numero})
        self.post_update(self.update_texto(self.CHAT_A, 'ya me pagó transportes, registra el cobro'))
        borrador = BorradorAgente.objects.get(estado='pendiente', tipo='cobro')
        self.assertEqual(borrador.payload['monto'], '1000.00')  # saldo completo
        self.assertIn('$', self.ultima_respuesta()[1])           # moneda de la venta (USD)

        self.post_update(self.update_callback(self.CHAT_A, f'b:{borrador.id}:ok'))
        pago = PagoVenta.objects.get()
        self.assertEqual(pago.monto, Decimal('1000.00'))
        self.venta.refresh_from_db()
        self.assertEqual(self.venta.estado, 'pagado')


class AislamientoYRolesTests(CanalTestCase):
    def test_empresa_b_no_ve_ventas_de_a(self):
        self.mock_llm('consultar_venta', {'venta_numero': self.venta.numero})
        self.post_update(self.update_texto(self.CHAT_B, f'cómo va la {self.venta.numero}'))
        self.assertIn('No encontré', self.ultima_respuesta()[1])

    def test_empresa_b_no_puede_confirmar_borrador_de_a(self):
        self.mock_llm('preparar_cobro', {'venta_numero': self.venta.numero})
        self.post_update(self.update_texto(self.CHAT_A, 'cobra la venta'))
        borrador = BorradorAgente.objects.get(estado='pendiente')
        self.post_update(self.update_callback(self.CHAT_B, f'b:{borrador.id}:ok'))
        self.assertIn('ya no existe', self.ultima_respuesta()[1])
        borrador.refresh_from_db()
        self.assertEqual(borrador.estado, 'pendiente')
        self.assertEqual(PagoVenta.objects.count(), 0)

    def test_solo_lectura_consulta_pero_no_prepara(self):
        self.mock_llm('consultar_venta', {'venta_numero': self.venta.numero})
        self.post_update(self.update_texto(self.CHAT_LECTOR, 'cómo va la venta'))
        self.assertIn(self.venta.numero, self.ultima_respuesta()[1])

        self.mock_llm('preparar_cobro', {'venta_numero': self.venta.numero})
        self.post_update(self.update_texto(self.CHAT_LECTOR, 'registra el cobro'))
        self.assertEqual(self.ultima_respuesta()[1], MSG_SOLO_LECTURA)
        self.assertEqual(BorradorAgente.objects.count(), 0)

    def test_solo_lectura_no_confirma_borrador_ajeno_de_escritura(self):
        self.mock_llm('preparar_cobro', {'venta_numero': self.venta.numero})
        self.post_update(self.update_texto(self.CHAT_A, 'cobra'))
        borrador = BorradorAgente.objects.get(estado='pendiente')
        # aunque le llegue el id del borrador, no es suyo → no existe para él
        self.post_update(self.update_callback(self.CHAT_LECTOR, f'b:{borrador.id}:ok'))
        self.assertIn('ya no existe', self.ultima_respuesta()[1])
        self.assertEqual(PagoVenta.objects.count(), 0)


class LimitesTests(CanalTestCase):
    def test_limite_60_mensajes_usuario_hora(self):
        from django.core.cache import cache
        from django.utils import timezone as tz
        hora = tz.now().strftime('%Y%m%d%H')
        cache.set(f'canales:msj:u{self.vendedor.id}:{hora}', 60, 3600)
        self.post_update(self.update_texto(self.CHAT_A, '/ayuda'))
        self.assertIn('límite de 60 mensajes', self.ultima_respuesta()[1])

    def test_fuera_de_alcance_respuesta_fija(self):
        self.mock_llm(None, None)  # el modelo no elige herramienta
        self.post_update(self.update_texto(self.CHAT_A, 'cuéntame un chiste'))
        self.assertIn('Puedo ayudarte con', self.ultima_respuesta()[1])
