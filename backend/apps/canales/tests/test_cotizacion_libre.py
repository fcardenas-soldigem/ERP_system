"""Fix V2 del bot — el caso real del piloto: cotización con productos FUERA de
catálogo (la empresa no maneja stock de eso), precios con IGV incluido, cliente
que llega en un mensaje posterior, borradores duplicados y «cuánto voy en
ventas». Reproduce cada falla antes de validar la corrección."""
from datetime import timedelta
from decimal import Decimal
from unittest import mock

from django.utils import timezone

from apps.canales.models import BorradorAgente, MensajeConversacion
from apps.canales.nucleo import contexto, servicios
from apps.canales.nucleo import esquemas as E
from apps.cotizaciones.models import Cotizacion
from apps.inventario.models.movimiento_inventario import MovimientoInventario
from apps.ventas.models import Venta

from .base import CanalTestCase, respuesta_llm

# El mensaje 1 REAL del piloto, multilínea, con IGV incluido y sin cliente.
MENSAJE_PILOTO = (
    'Crea una cotización de 4 PEDESTAL CON INCLINACIÓN 90° TV 32 A 75 PULG / VESA MAX\n'
    '600X400MM / CARGA 75KG  precio S/. 441.00 incluido IGV\n\n'
    '1 Gabinete de Piso para Servidores / 32 RU / 60x80x150 cm (AnchoxProf.xAlt.) /\n'
    'Puerta Frontal Microperforadas y Posterior doble Microperforadas  precio S/. 1750 incluido IGV'
)
PEDESTAL = ('PEDESTAL CON INCLINACIÓN 90° TV 32 A 75 PULG / VESA MAX 600X400MM / CARGA 75KG')
GABINETE = ('Gabinete de Piso para Servidores / 32 RU / 60x80x150 cm / '
            'Puerta Frontal Microperforadas y Posterior doble Microperforadas')

ARGS_PILOTO_SIN_CLIENTE = {
    'items': [
        {'descripcion': PEDESTAL, 'cantidad': 4, 'precio_unitario': '441.00',
         'precio_incluye_igv': True},
        {'descripcion': GABINETE, 'cantidad': 1, 'precio_unitario': '1750',
         'precio_incluye_igv': True},
    ],
    'moneda': 'PEN',
}
ARGS_PILOTO_CON_CLIENTE = {**ARGS_PILOTO_SIN_CLIENTE, 'cliente': 'Uhman Perú sac'}


class LineasLibresTests(CanalTestCase):
    """Punto 1 — productos fuera de catálogo con precio → línea libre directa."""

    def test_mensaje_piloto_crea_borrador_con_dos_lineas_libres_y_pregunta_cliente(self):
        self.mock_llm('preparar_cotizacion', ARGS_PILOTO_SIN_CLIENTE)
        self.post_update(self.update_texto(self.CHAT_A, MENSAJE_PILOTO))

        borrador = BorradorAgente.objects.get(usuario=self.vendedor, estado='pendiente')
        detalles = borrador.payload['detalles']
        self.assertEqual([d['estado'] for d in detalles], ['libre', 'libre'])
        self.assertEqual([d['producto'] for d in detalles], [None, None])
        self.assertEqual(detalles[0]['cantidad'], '4')
        self.assertEqual(detalles[0]['precio_unitario'], '441.00')
        self.assertTrue(borrador.payload['precios_incluyen_igv'])
        self.assertEqual(borrador.payload['cliente_estado'], 'falta')

        chat, texto, botones = self.ultima_respuesta()
        # los ítems NUNCA se descartan: el bot pregunta SOLO por el cliente
        self.assertIn('PEDESTAL', texto)
        self.assertIn('¿Para qué cliente', texto)
        # total con IGV exacto: 4×441 + 1750 = 3,514.00, sin «+ IGV» ambiguo
        self.assertIn('Total: S/ 3,514.00', texto)
        self.assertIn('IGV (18%): S/ 536.03', texto)
        self.assertIn('Subtotal: S/ 2,977.97', texto)
        self.assertNotIn('+ IGV', texto)

    def test_producto_de_catalogo_gana_a_linea_libre(self):
        self.mock_llm('preparar_cotizacion', {
            'cliente': 'Transportes Lima',
            'items': [{'descripcion': 'jabra 750', 'cantidad': 2, 'precio_unitario': '400'}],
        })
        self.post_update(self.update_texto(self.CHAT_A, 'cotiza 2 jabra 750 a 400 a transportes lima'))
        d = BorradorAgente.objects.get(estado='pendiente').payload['detalles'][0]
        self.assertEqual(d['estado'], 'ok')
        self.assertEqual(d['producto'], self.producto.id)
        self.assertEqual(d['precio_unitario'], '400')   # el precio del usuario manda

    def test_match_dudoso_pregunta_con_boton_texto_libre(self):
        """ambiguo → botones; «usar como texto» sigue siendo la salida manual."""
        entrada = E.PrepararCotizacion(cliente='Transportes Lima', items=[
            {'descripcion': 'auricular jabra', 'cantidad': 1, 'precio_unitario': '100'}])
        # 'auricular jabra' matchea completo el único producto → forzar ambigüedad
        from apps.inventario.models.producto import Producto
        Producto.objects.create(empresa=self.empresa_a, sku='JB-20', precio_compra=1,
                                precio_venta=2, nombre='Auricular Jabra Evolve2 20')
        res = servicios.preparar_cotizacion(self.vendedor, entrada)
        d = res['borrador']['payload']['detalles'][0]
        self.assertEqual(d['estado'], 'ambiguo')
        pregunta = servicios.pregunta_pendiente(res['borrador']['payload'], 1)
        self.assertTrue(any('texto libre' in t for t, _ in pregunta[1]))

    def test_sin_precio_y_sin_match_no_crea_linea_libre_automatica(self):
        entrada = E.PrepararCotizacion(cliente='Transportes Lima', items=[
            {'descripcion': 'cosa rarisima inexistente', 'cantidad': 1}])
        res = servicios.preparar_cotizacion(self.vendedor, entrada)
        self.assertEqual(res['borrador']['payload']['detalles'][0]['estado'], 'no_encontrado')

    def test_meta_frase_pide_aclaracion_y_no_crea_item_basura(self):
        """El caso real: «productos y cantidades» NUNCA debe ser un ítem."""
        for frase in ('productos y cantidades', 'ya te di los productos',
                      'lo que te dije', 'los mismos de antes',
                      'productos pendientes', 'los artículos del pedido'):
            entrada = E.PrepararCotizacion(cliente='Uhman', items=[
                {'descripcion': frase, 'cantidad': 1}])
            res = servicios.preparar_cotizacion(self.vendedor, entrada)
            self.assertIn('error', res, frase)
        self.assertEqual(BorradorAgente.objects.count(), 0)

    def test_confirmar_crea_cotizacion_con_igv_incluido_que_cuadra_al_centimo(self):
        self.mock_llm('preparar_cotizacion', ARGS_PILOTO_CON_CLIENTE)
        self.post_update(self.update_texto(self.CHAT_A, MENSAJE_PILOTO))
        borrador = BorradorAgente.objects.get(estado='pendiente')
        # cliente nuevo: se resuelve con el flujo existente (documento)
        payload = borrador.payload
        self.assertEqual(payload['cliente_estado'], 'no_encontrado')
        payload, _ = servicios.aplicar_resolucion(self.vendedor, payload, 'cn', '')
        payload, aviso = servicios.aplicar_documento(self.vendedor, payload, '20612345678')
        self.assertIsNone(aviso)
        borrador.payload = payload
        borrador.save(update_fields=['payload'])

        self.post_update(self.update_callback(self.CHAT_A, f'b:{borrador.id}:ok'))
        cot = Cotizacion.objects.get()
        self.assertTrue(cot.precios_incluyen_igv)
        self.assertEqual(cot.total, Decimal('3514.00'))   # 4×441 + 1750, al céntimo
        self.assertEqual(cot.igv, Decimal('536.03'))
        self.assertEqual(cot.detalles.count(), 2)
        self.assertIsNone(cot.detalles.first().producto)

    def test_igv_mezclado_convierte_a_base(self):
        """Un precio con IGV junto a uno de catálogo (base): el que incluía IGV
        se pasa a base ÷1.18 y el flag queda en False."""
        entrada = E.PrepararCotizacion(cliente='Transportes Lima', items=[
            {'descripcion': 'jabra 750', 'cantidad': 1},                       # catálogo, base
            {'descripcion': 'soporte articulado especial', 'cantidad': 2,
             'precio_unitario': '118', 'precio_incluye_igv': True},            # libre, con IGV
        ])
        payload = servicios.preparar_cotizacion(self.vendedor, entrada)['borrador']['payload']
        self.assertFalse(payload['precios_incluyen_igv'])
        libre = payload['detalles'][1]
        self.assertEqual(libre['precio_unitario'], '100.00')   # 118 ÷ 1.18
        self.assertIn('IGV', libre['aviso'])

    def test_linea_libre_no_mueve_stock_ni_kardex_al_convertir_a_venta(self):
        """Las líneas sin producto NUNCA tocan inventario, ni al entregar."""
        from apps.cotizaciones.services.conversion_service import convertir_cotizacion_a_venta
        cot = Cotizacion.objects.create(
            empresa=self.empresa_a, cliente=self.cliente, usuario_creador=self.vendedor,
            asunto='Pedestales', fecha_vencimiento=timezone.localdate() + timedelta(days=15),
            precios_incluyen_igv=True)
        cot.detalles.create(producto=None, descripcion=PEDESTAL,
                            cantidad=Decimal('4'), precio_unitario=Decimal('441.00'))
        stock_antes = self.producto.stock_total
        venta = convertir_cotizacion_a_venta(cot)

        detalle = venta.detalles.get()
        self.assertIsNone(detalle.producto)
        self.assertEqual(detalle.origen, 'pedido_proveedor')
        self.assertFalse(detalle.stock_descontado)

        # entregar la venta tampoco descuenta nada (no hay producto)
        venta.cambiar_estado_operativo('entregado', usuario=self.vendedor)
        detalle.refresh_from_db()
        self.assertFalse(detalle.stock_descontado)
        self.producto.refresh_from_db()
        self.assertEqual(self.producto.stock_total, stock_antes)
        self.assertEqual(MovimientoInventario.objects.count(), 0)
        self.assertEqual(Venta.objects.get(pk=venta.pk).total, Decimal('1764.00'))


class ContextoConversacionalTests(CanalTestCase):
    """Punto 3 — historial + borrador pendiente como contexto del agente."""

    def test_seguimiento_completa_el_mismo_borrador_sin_duplicar(self):
        m = self.mock_llm('preparar_cotizacion', ARGS_PILOTO_SIN_CLIENTE)
        self.post_update(self.update_texto(self.CHAT_A, MENSAJE_PILOTO))
        primero = BorradorAgente.objects.get(estado='pendiente')

        # mensaje 2: solo el cliente; el modelo (con contexto) re-llama completo
        self.programar_llm(m, 'preparar_cotizacion', ARGS_PILOTO_CON_CLIENTE)
        self.post_update(self.update_texto(self.CHAT_A, 'Cliente Uhman Perú sac\nYa te di los productos y cantidades'))

        primero.refresh_from_db()
        self.assertEqual(primero.estado, 'reemplazado')
        pendientes = BorradorAgente.objects.filter(estado='pendiente')
        self.assertEqual(pendientes.count(), 1)   # UN solo borrador pendiente por chat
        payload = pendientes.get().payload
        self.assertEqual(len(payload['detalles']), 2)   # los ítems del mensaje 1 siguen ahí
        self.assertEqual(payload['cliente_texto'], 'Uhman Perú sac')

    def test_el_modelo_recibe_historial_y_borrador_pendiente(self):
        m = self.mock_llm('preparar_cotizacion', ARGS_PILOTO_SIN_CLIENTE)
        self.post_update(self.update_texto(self.CHAT_A, MENSAJE_PILOTO))

        capturado = {}

        def chat(system, messages, tools, temperature=0.0):
            capturado['messages'] = list(messages)
            return respuesta_llm('preparar_cotizacion', ARGS_PILOTO_CON_CLIENTE)

        m.return_value.chat.side_effect = chat
        self.post_update(self.update_texto(self.CHAT_A, 'Cliente Uhman Perú sac'))

        contenidos = [str(x.content) for x in capturado['messages']]
        self.assertTrue(any(MENSAJE_PILOTO[:30] in c for c in contenidos))      # historial user
        self.assertTrue(any('¿Para qué cliente' in c for c in contenidos))      # historial bot
        self.assertTrue(any('borrador pendiente' in c.lower() for c in contenidos))
        self.assertEqual(capturado['messages'][-1].content, 'Cliente Uhman Perú sac')

    def test_historial_respeta_el_tope_de_mensajes(self):
        for i in range(15):
            contexto.guardar_mensaje(self.vendedor, 'telegram', str(self.CHAT_A), 'user', f'm{i}')
        historial = contexto.historial_chat(self.vendedor, str(self.CHAT_A))
        self.assertEqual(len(historial), 10)                       # N por defecto
        self.assertEqual(historial[-1].content, 'm14')             # los más recientes
        self.assertEqual(historial[0].content, 'm5')

    def test_historial_no_cruza_chats_ni_usuarios(self):
        contexto.guardar_mensaje(self.vendedor_b, 'telegram', str(self.CHAT_B), 'user', 'secreto de B')
        historial = contexto.historial_chat(self.vendedor, str(self.CHAT_A))
        self.assertEqual(historial, [])

    def test_mensajes_se_guardan_de_ambos_lados(self):
        self.mock_llm('preparar_cotizacion', ARGS_PILOTO_SIN_CLIENTE)
        self.post_update(self.update_texto(self.CHAT_A, MENSAJE_PILOTO))
        roles = list(MensajeConversacion.objects.order_by('created_at').values_list('rol', flat=True))
        self.assertEqual(roles, ['user', 'assistant'])


class BorradoresDuplicadosTests(CanalTestCase):
    """Punto 4 — un solo pendiente por chat; ediciones y reintentos no duplican."""

    def test_mensaje_editado_no_se_procesa(self):
        """Causa raíz: un mensaje editado llega con update_id NUEVO, así que la
        idempotencia por update_id no lo frena. Antes se reinterpretaba el texto
        completo y nacía un segundo borrador idéntico."""
        self.mock_llm('preparar_cotizacion', ARGS_PILOTO_CON_CLIENTE)
        CanalTestCase._update_id += 1
        r = self.post_update({'update_id': CanalTestCase._update_id,
                              'edited_message': {'chat': {'id': self.CHAT_A},
                                                 'from': {'first_name': 'Test'},
                                                 'text': MENSAJE_PILOTO}})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(BorradorAgente.objects.count(), 0)
        self.assertEqual(self.respuestas_bot(), [])

    def test_update_repetido_no_duplica(self):
        self.mock_llm('preparar_cotizacion', ARGS_PILOTO_CON_CLIENTE)
        update = self.update_texto(self.CHAT_A, MENSAJE_PILOTO)
        self.post_update(update)
        r = self.post_update(update)   # reintento de Telegram: mismo update_id
        self.assertTrue(r.json().get('duplicado'))
        self.assertEqual(BorradorAgente.objects.count(), 1)

    def test_callback_repetido_es_idempotente(self):
        self.mock_llm('preparar_cotizacion', {
            'cliente': 'Transportes Lima',
            'items': [{'producto_id': self.producto.id, 'cantidad': 1}],
        })
        self.post_update(self.update_texto(self.CHAT_A, 'cotiza 1 jabra'))
        borrador = BorradorAgente.objects.get(estado='pendiente')
        self.post_update(self.update_callback(self.CHAT_A, f'b:{borrador.id}:ok', callback_id='mismo'))
        n = len(self.respuestas_bot())
        # el proveedor reenvía el MISMO callback_query.id en otro update
        self.post_update(self.update_callback(self.CHAT_A, f'b:{borrador.id}:ok', callback_id='mismo'))
        self.assertEqual(Cotizacion.objects.count(), 1)
        self.assertEqual(len(self.respuestas_bot()), n)   # ni siquiera responde otra vez

    def test_nuevo_borrador_desactiva_botones_del_anterior(self):
        m = self.mock_llm('preparar_cotizacion', ARGS_PILOTO_CON_CLIENTE)
        # el mock de sendMessage devuelve un message_id real
        self.tg_requests.post.return_value.json.return_value = {'result': {'message_id': 77}}
        self.post_update(self.update_texto(self.CHAT_A, MENSAJE_PILOTO))
        primero = BorradorAgente.objects.get(estado='pendiente')
        self.assertEqual(primero.payload['mensaje_bot_id'], 77)

        self.programar_llm(m, 'preparar_cotizacion', ARGS_PILOTO_CON_CLIENTE)
        self.post_update(self.update_texto(self.CHAT_A, 'mejor hazla de nuevo'))
        primero.refresh_from_db()
        self.assertEqual(primero.estado, 'reemplazado')
        ediciones = [c for c in self.tg_requests.post.call_args_list
                     if 'editMessageReplyMarkup' in (c.args[0] if c.args else '')]
        self.assertEqual(len(ediciones), 1)
        self.assertEqual(ediciones[0].kwargs['json']['message_id'], 77)
        self.assertEqual(ediciones[0].kwargs['json']['reply_markup'], {'inline_keyboard': []})

    def test_cobro_pendiente_tambien_se_reemplaza(self):
        m = self.mock_llm('preparar_cobro', {'venta_numero': self.venta.numero})
        self.post_update(self.update_texto(self.CHAT_A, 'me pagaron lo de transportes'))
        cobro = BorradorAgente.objects.get(estado='pendiente', tipo='cobro')
        self.programar_llm(m, 'preparar_cotizacion', ARGS_PILOTO_CON_CLIENTE)
        self.post_update(self.update_texto(self.CHAT_A, MENSAJE_PILOTO))
        cobro.refresh_from_db()
        self.assertEqual(cobro.estado, 'reemplazado')
        self.assertEqual(BorradorAgente.objects.filter(estado='pendiente').count(), 1)


class CierreA1Tests(CanalTestCase):
    """Tanda 2 A1 — UsoLLM, typing y fallbacks con causa en el log."""

    def test_el_bot_registra_uso_llm_como_el_asistente_web(self):
        from apps.ai_assistant.models import UsoLLM
        self.mock_llm('preparar_cotizacion', ARGS_PILOTO_CON_CLIENTE)
        self.post_update(self.update_texto(self.CHAT_A, MENSAJE_PILOTO))
        uso = UsoLLM.objects.get(empresa=self.empresa_a)
        self.assertEqual((uso.tokens_entrada, uso.tokens_salida, uso.llamadas), (50, 20, 1))
        self.assertEqual(uso.modelo, 'fake')

    def test_typing_mientras_el_llm_procesa(self):
        self.mock_llm('preparar_cotizacion', ARGS_PILOTO_CON_CLIENTE)
        self.post_update(self.update_texto(self.CHAT_A, MENSAJE_PILOTO))
        acciones = [c for c in self.tg_requests.post.call_args_list
                    if 'sendChatAction' in (c.args[0] if c.args else '')]
        self.assertGreaterEqual(len(acciones), 1)
        self.assertEqual(acciones[0].kwargs['json']['action'], 'typing')

    def test_fallback_de_ayuda_se_loguea_con_warning_y_causa(self):
        self.mock_llm(None, None)   # el modelo no elige herramienta
        with self.assertLogs('apps.canales.nucleo.orquestador', level='WARNING') as logs:
            self.post_update(self.update_texto(self.CHAT_A, 'hola, qué tal'))
        self.assertTrue(any('fallback ayuda' in m and 'herramienta' in m for m in logs.output))

    def test_faltan_datos_se_loguea_con_warning_y_causa(self):
        # argumentos inválidos sostenidos: cantidad imposible
        self.mock_llm('preparar_cotizacion', {'items': [{'descripcion': 'algo', 'cantidad': -1}]})
        with self.assertLogs('apps.canales.nucleo.orquestador', level='WARNING') as logs:
            self.post_update(self.update_texto(self.CHAT_A, 'cotiza algo'))
        self.assertTrue(any('faltan_datos' in m and 'preparar_cotizacion' in m for m in logs.output))


class ResumenVentasTests(CanalTestCase):
    """Punto 5 — «cuánto voy en ventas» ya no cae al mensaje de ayuda."""

    def setUp(self):
        super().setUp()
        # TC de fallback sembrado en caché: el test nunca sale a la red (SBS).
        # get_tc_venta parte de date.today(), así que la clave usa esa fecha.
        import datetime
        from django.core.cache import cache
        cache.set(f'tc_venta_{datetime.date.today().isoformat()}', '3.80', 3600)

    def test_resumen_ventas_del_mes(self):
        hoy = timezone.localdate()
        v2 = Venta.objects.create(
            empresa=self.empresa_a, cliente=self.cliente, tipo_venta='contado',
            fecha_emision=hoy, metodo_pago='efectivo', moneda='PEN')
        Venta.objects.filter(pk=v2.pk).update(
            total=Decimal('500'), subtotal=Decimal('423.73'), estado='pagado',
            pagos_total=Decimal('500'), tipo_cambio=Decimal('1'))
        # la venta USD del fixture es de este mes: TC fijado para no salir a la red
        Venta.objects.filter(pk=self.venta.pk).update(tipo_cambio=Decimal('3.50'))

        res = servicios.resumen_ventas(self.vendedor, E.ResumenVentas())
        self.assertEqual(res['n_ventas'], 2)
        self.assertEqual(res['total_mes'], '4000.00')        # 1000×3.5 + 500
        self.assertEqual(res['por_cobrar'], '3500.00')       # solo la pendiente
        self.assertEqual(res['top_clientes'][0]['nombre'], self.cliente.nombre)

    def test_resumen_no_cruza_empresas(self):
        Venta.objects.filter(pk=self.venta.pk).update(tipo_cambio=Decimal('3.50'))
        res = servicios.resumen_ventas(self.vendedor_b, E.ResumenVentas())
        self.assertEqual(res['n_ventas'], 0)
        self.assertEqual(res['total_mes'], '0.00')

    def test_bot_responde_resumen_y_no_el_mensaje_de_ayuda(self):
        Venta.objects.filter(pk=self.venta.pk).update(tipo_cambio=Decimal('3.50'))
        self.mock_llm('resumen_ventas', {'periodo': 'mes'})
        self.post_update(self.update_texto(self.CHAT_A, 'Cuánto voy en ventas este mes'))
        chat, texto, _ = self.ultima_respuesta()
        self.assertIn('Ventas de', texto)
        self.assertIn('S/ 3,500.00', texto)   # 1000 USD × 3.5
        self.assertIn('Por cobrar', texto)
        self.assertNotIn('Puedo ayudarte con', texto)

    def test_error_tecnico_no_es_mensaje_de_ayuda(self):
        parche = mock.patch('apps.canales.nucleo.interprete.get_llm_client')
        m = parche.start()
        self.addCleanup(parche.stop)
        m.return_value.chat.side_effect = RuntimeError('vertex caído')
        with self.assertLogs('apps.canales.nucleo.orquestador', level='ERROR'):
            self.post_update(self.update_texto(self.CHAT_A, 'Cuánto voy en ventas este mes'))
        chat, texto, _ = self.ultima_respuesta()
        self.assertIn('tuvo un problema', texto)
        self.assertNotIn('Puedo ayudarte con', texto)
