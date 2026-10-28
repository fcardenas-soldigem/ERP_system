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
    def _hasta_borrador_confirmable(self):
        """Mensaje real → borrador de VENTA con cliente nuevo verificado por DNI."""
        self.mock_llm('preparar_venta', ARGS_VENTA_BRUNO)
        self.post_update(self.update_texto(self.CHAT_A, MENSAJE_BRUNO))
        borrador = BorradorAgente.objects.get(estado='pendiente')
        self.assertEqual(borrador.tipo, 'venta')
        self.post_update(self.update_callback(self.CHAT_A, f'r:{borrador.id}:cn'))
        with mock.patch('apps.core.services.documento_service.DocumentoService.consultar_documento',
                        return_value=APIS_OK):
            self.post_update(self.update_texto(self.CHAT_A, '70771234'))
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
        self.assertIn('contado · efectivo', texto)
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
            'cliente': 'Transportes Lima', 'tipo_venta': 'credito_30',
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
            'cliente': 'Transportes Lima', 'tipo_venta': 'credito_30', 'moneda': 'PEN',
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
                     'tipo_venta': 'contado', 'metodo_pago': 'efectivo',
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
        self.assertIn('Convertir', self.ultima_respuesta()[1])

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
