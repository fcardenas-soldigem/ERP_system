"""feat/bot-ventas — el caso real: «crea venta para bruno perez 10 headsets
jabra evolve 20 $39 la unidad mas igv» terminó como COT-00000107 sin aviso.
El bot nunca cambia en silencio el tipo de documento; las ventas se crean con
el MISMO servicio de la web (crear_venta) y la conversión con el de la web."""
import datetime
from decimal import Decimal
from unittest import mock

from django.core.cache import cache
from django.core.signing import TimestampSigner
from django.utils import timezone

from apps.canales.models import BorradorAgente
from apps.canales.nucleo import servicios
from apps.cotizaciones.models import Cotizacion
from apps.inventario.models.movimiento_inventario import MovimientoInventario
from apps.ventas.models import PagoVenta, Venta

from .base import CanalTestCase

MENSAJE_BRUNO = 'crea venta para bruno perez 10 headsets jabra evolve 20 $39 la unidad mas igv'
ARGS_VENTA_BRUNO = {
    'cliente': 'bruno perez', 'moneda': 'USD',
    'items': [{'descripcion': 'headsets jabra evolve 20', 'cantidad': 10,
               'precio_unitario': '39', 'precio_incluye_igv': False}],
}
APIS_OK = {'success': True, 'data': {'nombre_completo': 'BRUNO ALONSO PEREZ QUISPE',
                                     'nombres': 'BRUNO ALONSO', 'apellido_paterno': 'PEREZ',
                                     'apellido_materno': 'QUISPE', 'numero_documento': '70771234'}}


class BaseVentas(CanalTestCase):
    @classmethod
    def setUpTestData(cls):
        # TC sembrado ANTES del fixture (crea una venta USD): nada sale a la red
        cache.set(f'tc_venta_{datetime.date.today().isoformat()}', '3.80', 3600)
        super().setUpTestData()
        # el fixture base nace como materia prima (default RAW): para VENDERLO
        # directo debe ser producto terminado, como exige la web
        from apps.inventario.models.producto import Producto
        Producto.objects.filter(pk=cls.producto.pk).update(tipo_producto='FINISHED')
        cls.producto.refresh_from_db()

    def setUp(self):
        super().setUp()
        # setUp limpia la caché: re-sembrar para las ventas USD de cada test
        cache.set(f'tc_venta_{datetime.date.today().isoformat()}', '3.80', 3600)


class PrepararVentaTests(BaseVentas):
    def _hasta_borrador_confirmable(self, condicion='cont'):
        """Mensaje real → borrador de VENTA: cliente nuevo verificado por DNI
        y condición de pago elegida con botón (NUNCA se asume)."""
        self.mock_llm('preparar_venta', ARGS_VENTA_BRUNO)
        self.post_update(self.update_texto(self.CHAT_A, MENSAJE_BRUNO))
        borrador = BorradorAgente.objects.get(estado='pendiente')
        self.assertEqual(borrador.tipo, 'venta')
        self.post_update(self.update_callback(self.CHAT_A, f'r:{borrador.id}:cn'))
        with mock.patch('apps.core.services.documento_service.DocumentoService.consultar_documento',
                        return_value=APIS_OK):
            self.post_update(self.update_texto(self.CHAT_A, '70771234'))
        # sin condición dicha: el borrador la pregunta con botones
        chat, texto, botones = self.ultima_respuesta()
        self.assertIn('condición de pago por definir', texto)
        self.assertIn('¿Condición de pago?', texto)
        self.assertIn(f'r:{borrador.id}:cond:c30', botones)
        self.assertIn(f'r:{borrador.id}:cond:c15', botones)
        self.assertIn(f'r:{borrador.id}:cond:cont', botones)
        self.assertNotIn(f'b:{borrador.id}:ok', botones)     # sin Confirmar todavía
        self.post_update(self.update_callback(self.CHAT_A, f'r:{borrador.id}:cond:{condicion}'))
        borrador.refresh_from_db()
        return borrador

    def test_crea_venta_no_cotizacion_y_borrador_dice_venta(self):
        borrador = self._hasta_borrador_confirmable()
        payload = borrador.payload
        self.assertEqual(payload['moneda'], 'USD')
        self.assertFalse(payload['precios_incluyen_igv'])          # «mas igv» = base
        self.assertEqual(payload['detalles'][0]['estado'], 'libre')
        chat, texto, botones = self.ultima_respuesta()
        self.assertIn('<b>Venta</b>', texto)                       # dice VENTA, no cotización
        self.assertIn('contado · efectivo', texto)                 # condición SIEMPRE visible
        self.assertIn('Total: $ 460.20', texto)                    # 10×39 ×1.18

        self.post_update(self.update_callback(self.CHAT_A, f'b:{borrador.id}:ok'))
        self.assertEqual(Cotizacion.objects.count(), 0)            # NADA de cotización
        venta = Venta.objects.exclude(pk=self.venta.pk).get()
        self.assertTrue(venta.numero.startswith('V-'))
        self.assertEqual(venta.estado, 'pagado')                   # contado, como la web
        self.assertEqual(venta.moneda, 'USD')
        self.assertFalse(venta.igv_incluido)
        self.assertEqual(venta.total, Decimal('460.20'))
        det = venta.detalles.get()
        self.assertIsNone(det.producto)                            # línea libre
        self.assertEqual(det.descripcion, 'headsets jabra evolve 20')
        self.assertEqual(venta.cliente.nombre, 'BRUNO ALONSO PEREZ QUISPE')
        chat, texto, _ = self.ultima_respuesta()
        self.assertIn(f'Venta <b>{venta.numero}</b> creada', texto)

    def test_venta_a_credito_usa_el_flujo_de_la_web(self):
        """crédito_30 → pendiente + vencimiento + PagoVenta placeholder (el
        MISMO post-proceso que la web: completar_creacion_venta)."""
        self.mock_llm('preparar_venta', {
            'cliente': 'Transportes Lima', 'condicion_pago': 'credito', 'plazo_dias': 30,
            'items': [{'producto_id': self.producto.id, 'cantidad': 2, 'precio_unitario': '100'}],
        })
        self.post_update(self.update_texto(self.CHAT_A, 'venta al crédito 30 para transportes'))
        borrador = BorradorAgente.objects.get(estado='pendiente')
        self.post_update(self.update_callback(self.CHAT_A, f'b:{borrador.id}:ok'))
        venta = Venta.objects.exclude(pk=self.venta.pk).get()
        self.assertEqual(venta.estado, 'pendiente')
        self.assertEqual(venta.fecha_vencimiento, venta.fecha_emision + timezone.timedelta(days=30))
        placeholder = PagoVenta.objects.get(venta=venta)
        self.assertEqual((placeholder.metodo_pago, placeholder.monto), ('pendiente', venta.total))

    def test_linea_libre_de_venta_no_mueve_stock_ni_kardex_al_entregar(self):
        """Extiende el test de cotizaciones a VENTAS (punto 2)."""
        self.mock_llm('preparar_venta', {
            'cliente': 'Transportes Lima', 'condicion_pago': 'credito', 'plazo_dias': 30,
            'moneda': 'PEN',
            'items': [{'descripcion': 'pedestal especial fuera de catalogo', 'cantidad': 4,
                       'precio_unitario': '441', 'precio_incluye_igv': True}],
        })
        self.post_update(self.update_texto(self.CHAT_A, 'venta 4 pedestales a transportes'))
        borrador = BorradorAgente.objects.get(estado='pendiente')
        self.post_update(self.update_callback(self.CHAT_A, f'b:{borrador.id}:ok'))
        venta = Venta.objects.exclude(pk=self.venta.pk).get()
        self.assertEqual(venta.total, Decimal('1764.00'))          # 4×441 con IGV, al céntimo
        stock_antes = self.producto.stock_total
        venta.cambiar_estado_operativo('entregado', usuario=self.vendedor)
        det = venta.detalles.get()
        self.assertIsNone(det.producto)
        self.assertFalse(det.stock_descontado)
        self.producto.refresh_from_db()
        self.assertEqual(self.producto.stock_total, stock_antes)
        self.assertEqual(MovimientoInventario.objects.count(), 0)

    def test_solo_lectura_no_puede_confirmar_ni_siquiera_directo(self):
        """El rol se valida TAMBIÉN al confirmar (callback_data es forjable)."""
        borrador = BorradorAgente.objects.create(
            empresa=self.empresa_a, usuario=self.lector, tipo='venta',
            id_externo=str(self.CHAT_LECTOR),
            payload={'cliente': self.cliente.id, 'cliente_nombre': self.cliente.nombre,
                     'cliente_estado': 'ok', 'cliente_nuevo': None, 'moneda': 'PEN',
                     'condicion': 'contado', 'plazo_dias': None, 'metodo_pago': 'efectivo',
                     'precios_incluyen_igv': False,
                     'detalles': [{'estado': 'ok', 'producto': self.producto.id,
                                   'descripcion': self.producto.nombre, 'texto': 'jabra',
                                   'cantidad': '1', 'precio_unitario': '100',
                                   'opciones': [], 'aviso': ''}]})
        with self.assertRaises(ValueError):
            servicios.confirmar_borrador(borrador)
        self.assertEqual(Venta.objects.exclude(pk=self.venta.pk).count(), 0)


class ConversionTests(BaseVentas):
    def _cotizacion(self, estado='enviada'):
        cot = Cotizacion.objects.create(
            empresa=self.empresa_a, cliente=self.cliente, usuario_creador=self.vendedor,
            asunto='Equipos', fecha_vencimiento=timezone.localdate() + timezone.timedelta(days=15))
        cot.detalles.create(producto=self.producto, descripcion=self.producto.nombre,
                            cantidad=Decimal('3'), precio_unitario=Decimal('450'))
        Cotizacion.objects.filter(pk=cot.pk).update(estado=estado)
        cot.refresh_from_db()
        return cot

    def test_convierte_cotizacion_con_el_servicio_de_la_web(self):
        cot = self._cotizacion()
        self.mock_llm('convertir_cotizacion_en_venta', {'cotizacion_numero': cot.numero})
        self.post_update(self.update_texto(self.CHAT_A, f'convierte la {cot.numero} en venta'))
        borrador = BorradorAgente.objects.get(estado='pendiente')
        self.assertEqual(borrador.tipo, 'conversion_venta')
        chat, texto, botones = self.ultima_respuesta()
        self.assertIn('Convertir', texto)
        # la forma_pago «Contado» es el default del modelo, no una elección:
        # la conversión TAMBIÉN pregunta la condición (misma regla que la venta)
        self.assertIn('condición de pago por definir', texto)
        self.assertIn(f'r:{borrador.id}:cond:cont', botones)
        self.post_update(self.update_callback(self.CHAT_A, f'r:{borrador.id}:cond:cont'))

        self.post_update(self.update_callback(self.CHAT_A, f'b:{borrador.id}:ok'))
        cot.refresh_from_db()
        self.assertEqual(cot.estado, 'convertida')
        venta = cot.venta
        self.assertIsNotNone(venta)                     # convertir_cotizacion_a_venta (web)
        self.assertEqual(venta.detalles.count(), 1)
        chat, texto, _ = self.ultima_respuesta()
        self.assertIn('convertida', texto)
        self.assertIn(venta.numero, texto)

    def test_cotizacion_ya_convertida_avisa(self):
        cot = self._cotizacion()
        from apps.cotizaciones.services.conversion_service import convertir_cotizacion_a_venta
        convertir_cotizacion_a_venta(cot)
        res = servicios.convertir_cotizacion_en_venta(
            self.vendedor, servicios.E.ConvertirCotizacionEnVenta(cotizacion_numero=cot.numero))
        self.assertIn('ya fue convertida', res['error'])

    def test_acepta_numero_corto(self):
        cot = self._cotizacion()
        digitos = str(int(cot.numero.split('-')[1]))
        res = servicios.convertir_cotizacion_en_venta(
            self.vendedor, servicios.E.ConvertirCotizacionEnVenta(cotizacion_numero=f'COT-{digitos}'))
        self.assertEqual(res['borrador']['payload']['cotizacion'], cot.id)


class HonestidadTests(BaseVentas):
    def test_operacion_no_soportada_respuesta_honesta(self):
        """«anula la factura 5»: el bot dice que NO puede y ofrece lo que sí."""
        self.mock_llm(None, None)
        self.post_update(self.update_texto(self.CHAT_A, 'anula la factura 5'))
        chat, texto, _ = self.ultima_respuesta()
        self.assertIn('no puedo hacerlo', texto.lower())
        self.assertIn('Sí puedo', texto)
        self.assertEqual(BorradorAgente.objects.count(), 0)


class ClienteNuevoVerificadoTests(BaseVentas):
    def _hasta_pedir_dni(self):
        self.mock_llm('preparar_venta', ARGS_VENTA_BRUNO)
        self.post_update(self.update_texto(self.CHAT_A, MENSAJE_BRUNO))
        borrador = BorradorAgente.objects.get(estado='pendiente')
        self.post_update(self.update_callback(self.CHAT_A, f'r:{borrador.id}:cn'))
        self.assertIn('RUC', self.ultima_respuesta()[1])
        return borrador

    def test_apis_devuelve_el_nombre_oficial_y_el_borrador_lo_muestra(self):
        borrador = self._hasta_pedir_dni()
        with mock.patch('apps.core.services.documento_service.DocumentoService.consultar_documento',
                        return_value=APIS_OK) as consulta:
            self.post_update(self.update_texto(self.CHAT_A, '70771234'))
        consulta.assert_called_once_with('70771234', 'dni')        # el MISMO servicio de la web
        chat, texto, _ = self.ultima_respuesta()
        self.assertIn('DNI 70771234 →', texto)                     # «DNI xxxx → NOMBRE OFICIAL»
        self.assertIn('BRUNO ALONSO PEREZ QUISPE', texto)
        self.assertIn('escribiste «Bruno Perez»', texto)           # difiere de lo tipeado
        borrador.refresh_from_db()
        self.assertEqual(borrador.payload['cliente_nuevo']['nombre'], 'BRUNO ALONSO PEREZ QUISPE')

    def test_apis_caido_avisa_registra_error_y_usa_lo_escrito(self):
        borrador = self._hasta_pedir_dni()
        with mock.patch('apps.core.services.documento_service.DocumentoService.consultar_documento',
                        side_effect=RuntimeError('timeout APIS')):
            with self.assertLogs('apps.canales.nucleo.servicios', level='ERROR') as logs:
                self.post_update(self.update_texto(self.CHAT_A, '70771234'))
        self.assertTrue(any('APIS.NET.PE' in m for m in logs.output))
        chat, texto, _ = self.ultima_respuesta()
        self.assertIn('No pude verificar', texto)
        borrador.refresh_from_db()
        self.assertEqual(borrador.payload['cliente_nuevo']['nombre'], 'Bruno Perez')
        self.assertEqual(borrador.payload['cliente_nuevo']['documento'], '70771234')


class PDFFirmadoTests(BaseVentas):
    def _cot(self, empresa=None):
        return Cotizacion.objects.create(
            empresa=empresa or self.empresa_a, cliente=self.cliente if empresa is None else None,
            usuario_creador=self.vendedor, asunto='x',
            fecha_vencimiento=timezone.localdate()) if empresa is None else None

    def setUp(self):
        super().setUp()
        self.cot = Cotizacion.objects.create(
            empresa=self.empresa_a, cliente=self.cliente, usuario_creador=self.vendedor,
            asunto='PDF', fecha_vencimiento=timezone.localdate())
        self.cot.detalles.create(producto=self.producto, descripcion='x',
                                 cantidad=Decimal('1'), precio_unitario=Decimal('10'))

    def _firma(self, valor, hace_dias=0):
        import time as time_mod
        with mock.patch('django.core.signing.time.time',
                        return_value=time_mod.time() - hace_dias * 86400):
            return TimestampSigner(salt='canales.pdf').sign(valor)

    def test_token_vigente_da_el_pdf_y_a_los_7_dias_expira(self):
        valor = f'{self.cot.id}:{self.empresa_a.id}'
        r = self.client.get(f'/api/canales/pdf-cotizacion/?t={self._firma(valor, hace_dias=6)}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r['Content-Type'], 'application/pdf')
        r = self.client.get(f'/api/canales/pdf-cotizacion/?t={self._firma(valor, hace_dias=8)}')
        self.assertEqual(r.status_code, 410)                       # expirado (7 días)

    def test_token_manipulado_403(self):
        firma = self._firma(f'{self.cot.id}:{self.empresa_a.id}')
        otro_id = str(self.cot.id + 1)
        manipulado = otro_id + firma[firma.index(':'):]
        r = self.client.get(f'/api/canales/pdf-cotizacion/?t={manipulado}')
        self.assertEqual(r.status_code, 403)

    def test_token_atado_a_la_empresa_403(self):
        """Un token firmado para otra empresa no abre este documento."""
        firma = self._firma(f'{self.cot.id}:{self.empresa_b.id}')
        r = self.client.get(f'/api/canales/pdf-cotizacion/?t={firma}')
        self.assertEqual(r.status_code, 403)

    def test_formato_viejo_sin_empresa_403(self):
        firma = self._firma(str(self.cot.id))                      # formato pre-tanda
        r = self.client.get(f'/api/canales/pdf-cotizacion/?t={firma}')
        self.assertEqual(r.status_code, 403)


class CondicionDePagoTests(BaseVentas):
    """Ajuste pre-deploy: PROHIBIDO asumir contado."""

    def test_sin_condicion_no_se_puede_confirmar(self):
        """Ni siquiera forjando el callback de Confirmar."""
        self.mock_llm('preparar_venta', {
            'cliente': 'Transportes Lima',
            'items': [{'producto_id': self.producto.id, 'cantidad': 1, 'precio_unitario': '100'}],
        })
        self.post_update(self.update_texto(self.CHAT_A, 'crea venta 1 jabra a transportes'))
        borrador = BorradorAgente.objects.get(estado='pendiente')
        self.assertIsNone(borrador.payload['condicion'])
        # el botón Confirmar no se ofrece; forjarlo tampoco crea nada
        self.post_update(self.update_callback(self.CHAT_A, f'b:{borrador.id}:ok'))
        self.assertIn('condición de pago', self.ultima_respuesta()[1])
        self.assertEqual(Venta.objects.exclude(pk=self.venta.pk).count(), 0)
        borrador.refresh_from_db()
        self.assertEqual(borrador.estado, 'pendiente')

    def test_credito_15_aparece_en_cxc_con_vencimiento_correcto(self):
        self.mock_llm('preparar_venta', {
            'cliente': 'Transportes Lima',
            'items': [{'producto_id': self.producto.id, 'cantidad': 1, 'precio_unitario': '200'}],
        })
        self.post_update(self.update_texto(self.CHAT_A, 'crea venta 1 jabra a transportes'))
        borrador = BorradorAgente.objects.get(estado='pendiente')
        self.post_update(self.update_callback(self.CHAT_A, f'r:{borrador.id}:cond:c15'))
        chat, texto, _ = self.ultima_respuesta()
        vence = timezone.localdate() + timezone.timedelta(days=15)
        self.assertIn(f'crédito 15 días · vence {vence.strftime("%d/%m/%Y")}', texto)

        self.post_update(self.update_callback(self.CHAT_A, f'b:{borrador.id}:ok'))
        venta = Venta.objects.exclude(pk=self.venta.pk).get()
        self.assertEqual(venta.estado, 'pendiente')               # CxC
        self.assertEqual(venta.tipo_venta, 'credito_30')          # el tipo web más cercano
        self.assertEqual(venta.fecha_vencimiento, venta.fecha_emision + timezone.timedelta(days=15))
        placeholder = PagoVenta.objects.get(venta=venta)          # aparece en por-cobrar
        self.assertEqual((placeholder.metodo_pago, placeholder.monto), ('pendiente', venta.total))
        self.assertIn('15 días', placeholder.notas)

    def test_contado_explicito_no_pregunta_y_nace_pagada(self):
        self.mock_llm('preparar_venta', {
            'cliente': 'Transportes Lima', 'condicion_pago': 'contado', 'metodo_pago': 'transferencia',
            'items': [{'producto_id': self.producto.id, 'cantidad': 1, 'precio_unitario': '100'}],
        })
        self.post_update(self.update_texto(self.CHAT_A, 'venta al contado por transferencia, 1 jabra a transportes'))
        borrador = BorradorAgente.objects.get(estado='pendiente')
        chat, texto, botones = self.ultima_respuesta()
        self.assertIn('contado · transferencia', texto)
        self.assertIn(f'b:{borrador.id}:ok', botones)             # directo a confirmar
        self.post_update(self.update_callback(self.CHAT_A, f'b:{borrador.id}:ok'))
        venta = Venta.objects.exclude(pk=self.venta.pk).get()
        self.assertEqual((venta.estado, venta.tipo_venta, venta.metodo_pago),
                         ('pagado', 'contado', 'transferencia'))
        self.assertEqual(PagoVenta.objects.filter(venta=venta).count(), 0)  # sin cobro inventado

    def test_conversion_credito_15_respeta_el_plazo(self):
        cot = Cotizacion.objects.create(
            empresa=self.empresa_a, cliente=self.cliente, usuario_creador=self.vendedor,
            asunto='x', fecha_vencimiento=timezone.localdate())
        cot.detalles.create(producto=self.producto, descripcion='x',
                            cantidad=Decimal('1'), precio_unitario=Decimal('100'))
        Cotizacion.objects.filter(pk=cot.pk).update(estado='enviada')
        self.mock_llm('convertir_cotizacion_en_venta', {'cotizacion_numero': cot.numero})
        self.post_update(self.update_texto(self.CHAT_A, f'convierte la {cot.numero}'))
        borrador = BorradorAgente.objects.get(estado='pendiente')
        self.post_update(self.update_callback(self.CHAT_A, f'r:{borrador.id}:cond:c15'))
        self.post_update(self.update_callback(self.CHAT_A, f'b:{borrador.id}:ok'))
        cot.refresh_from_db()
        venta = cot.venta
        self.assertEqual(venta.tipo_venta, 'credito_30')
        self.assertEqual(venta.fecha_vencimiento, venta.fecha_emision + timezone.timedelta(days=15))

    def test_conversion_con_credito_explicito_en_la_cotizacion_no_pregunta(self):
        cot = Cotizacion.objects.create(
            empresa=self.empresa_a, cliente=self.cliente, usuario_creador=self.vendedor,
            asunto='x', fecha_vencimiento=timezone.localdate(), forma_pago='CREDITO 30 DIAS')
        cot.detalles.create(producto=self.producto, descripcion='x',
                            cantidad=Decimal('1'), precio_unitario=Decimal('100'))
        Cotizacion.objects.filter(pk=cot.pk).update(estado='enviada')
        self.mock_llm('convertir_cotizacion_en_venta', {'cotizacion_numero': cot.numero})
        self.post_update(self.update_texto(self.CHAT_A, f'convierte la {cot.numero}'))
        borrador = BorradorAgente.objects.get(estado='pendiente')
        chat, texto, botones = self.ultima_respuesta()
        self.assertIn('crédito 30 días', texto)                   # prellenada de la ficha
        self.assertIn(f'b:{borrador.id}:ok', botones)             # sin pregunta


class MonedaEInsumoTests(BaseVentas):
    """fix/bot-ventas-errores — caso real 29/10: catálogo en USD 39 como
    materia prima → venta en S/ 39 + error crudo del serializer."""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        from apps.inventario.models.producto import Producto
        cls.insumo_usd = Producto.objects.create(
            empresa=cls.empresa_a, sku='JB-E20', nombre='Headset Jabra Evolve 20',
            precio_compra=Decimal('25'), precio_venta=Decimal('39'),
            moneda='USD', tipo_producto='RAW')

    def _preparar_bruno(self):
        """El mensaje real: producto de catálogo USD + materia prima, sin precio
        ni moneda del usuario."""
        self.mock_llm('preparar_venta', {
            'cliente': 'Transportes Lima',
            'items': [{'descripcion': 'headsets jabra evolve 20', 'cantidad': 2}],
        })
        self.post_update(self.update_texto(
            self.CHAT_A, 'Crea venta para Bruno tudela ferrando 2 headsets jabra evolve 20'))
        return BorradorAgente.objects.get(estado='pendiente')

    def test_caso_bruno_borrador_en_usd_con_linea_libre_y_aviso(self):
        borrador = self._preparar_bruno()
        payload = borrador.payload
        self.assertEqual(payload['moneda'], 'USD')             # adopta la del catálogo
        d = payload['detalles'][0]
        self.assertEqual(d['estado'], 'libre')                 # insumo → línea libre
        self.assertIsNone(d['producto'])
        self.assertEqual(d['precio_unitario'], '39.00')        # USD 39, nunca S/ 39
        self.assertIn('insumo', d['aviso'])
        chat, texto, _ = self.ultima_respuesta()
        self.assertIn('registrado como insumo', texto)
        self.assertIn('$ 39.00', texto)
        self.assertNotIn('S/ 39', texto)

    def test_caso_bruno_confirma_y_crea_la_venta(self):
        borrador = self._preparar_bruno()
        self.post_update(self.update_callback(self.CHAT_A, f'r:{borrador.id}:cond:cont'))
        self.post_update(self.update_callback(self.CHAT_A, f'b:{borrador.id}:ok'))
        venta = Venta.objects.exclude(pk=self.venta.pk).get()
        self.assertEqual(venta.moneda, 'USD')
        self.assertEqual(venta.total, Decimal('92.04'))        # 2×39 ×1.18
        det = venta.detalles.get()
        self.assertIsNone(det.producto)                        # línea libre: sin stock
        self.assertIn('Jabra Evolve 20', det.descripcion)

    def test_conflicto_usuario_soles_catalogo_usd_pregunta_moneda(self):
        self.mock_llm('preparar_venta', {
            'cliente': 'Transportes Lima', 'moneda': 'PEN',
            'items': [{'descripcion': 'headsets jabra evolve 20', 'cantidad': 2}],
        })
        self.post_update(self.update_texto(self.CHAT_A, 'venta en soles de 2 headsets jabra evolve 20'))
        borrador = BorradorAgente.objects.get(estado='pendiente')
        self.assertIsNone(borrador.payload['moneda'])          # conflicto → se pregunta
        chat, texto, botones = self.ultima_respuesta()
        self.assertIn('¿En qué moneda va', texto)
        self.assertIn(f'r:{borrador.id}:mon:PEN', botones)
        self.assertIn(f'r:{borrador.id}:mon:USD', botones)
        self.assertNotIn(f'b:{borrador.id}:ok', botones)       # sin Confirmar aún

        # elige SOLES: el número de catálogo (USD 39) NO se copia → pide precio
        self.post_update(self.update_callback(self.CHAT_A, f'r:{borrador.id}:mon:PEN'))
        borrador.refresh_from_db()
        self.assertEqual(borrador.payload['moneda'], 'PEN')
        d = borrador.payload['detalles'][0]
        self.assertIsNone(d['precio_unitario'])
        self.assertIn('dime el precio en PEN', d['aviso'])

    def test_precio_explicito_del_usuario_manda(self):
        """«$39» → USD del usuario; el catálogo no interviene."""
        self.mock_llm('preparar_venta', {
            'cliente': 'Transportes Lima', 'moneda': 'USD',
            'items': [{'descripcion': 'headsets jabra evolve 20', 'cantidad': 2,
                       'precio_unitario': '39'}],
        })
        self.post_update(self.update_texto(self.CHAT_A, 'venta 2 headsets jabra evolve 20 $39'))
        payload = BorradorAgente.objects.get(estado='pendiente').payload
        self.assertEqual(payload['moneda'], 'USD')
        self.assertEqual(payload['detalles'][0]['precio_unitario'], '39')

    def test_cotizacion_tambien_adopta_la_moneda_del_catalogo(self):
        res = servicios.preparar_cotizacion(self.vendedor, servicios.E.PrepararCotizacion(
            cliente='Transportes Lima',
            items=[{'descripcion': 'headsets jabra evolve 20', 'cantidad': 1}]))
        self.assertEqual(res['borrador']['payload']['moneda'], 'USD')


class ErroresAlConfirmarTests(BaseVentas):
    def _borrador_confirmable(self):
        self.mock_llm('preparar_venta', {
            'cliente': 'Transportes Lima', 'condicion_pago': 'contado',
            'items': [{'producto_id': self.producto.id, 'cantidad': 1, 'precio_unitario': '100'}],
        })
        self.post_update(self.update_texto(self.CHAT_A, 'venta al contado 1 jabra a transportes'))
        return BorradorAgente.objects.get(estado='pendiente')

    def test_error_desconocido_mensaje_interno_log_y_borrador_pendiente(self):
        borrador = self._borrador_confirmable()
        from rest_framework.exceptions import ValidationError as DRFValidationError
        with mock.patch('apps.ventas.services.creacion_venta.crear_venta',
                        side_effect=DRFValidationError({'detalles': ['algo rarísimo del serializer']})):
            with self.assertLogs('apps.canales.nucleo.orquestador', level='ERROR'):
                self.post_update(self.update_callback(self.CHAT_A, f'b:{borrador.id}:ok'))
        chat, texto, _ = self.ultima_respuesta()
        self.assertIn('error interno', texto)
        self.assertNotIn('ErrorDetail', texto)                 # nada crudo al usuario
        borrador.refresh_from_db()
        self.assertEqual(borrador.estado, 'pendiente')         # queda para reintentar

        # reintento sin el error: la venta sale (el borrador no se perdió)
        self.post_update(self.update_callback(self.CHAT_A, f'b:{borrador.id}:ok'))
        borrador.refresh_from_db()
        self.assertEqual(borrador.estado, 'confirmado')
        self.assertEqual(Venta.objects.exclude(pk=self.venta.pk).count(), 1)

    def test_error_conocido_se_traduce(self):
        borrador = self._borrador_confirmable()
        from rest_framework.exceptions import ValidationError as DRFValidationError
        detalle_crudo = {'detalles': [{'producto': [
            "ERROR: 'X' es una materia prima/insumo y no puede venderse directamente."]}]}
        with mock.patch('apps.ventas.services.creacion_venta.crear_venta',
                        side_effect=DRFValidationError(detalle_crudo)):
            self.post_update(self.update_callback(self.CHAT_A, f'b:{borrador.id}:ok'))
        chat, texto, _ = self.ultima_respuesta()
        self.assertIn('insumo', texto)
        self.assertIn('línea libre', texto)
        self.assertNotIn('ErrorDetail', texto)
