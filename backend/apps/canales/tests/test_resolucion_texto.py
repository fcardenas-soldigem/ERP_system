"""Punto 1 — preparar_cotizacion con cliente e ítems en TEXTO: el servidor
resuelve (búsqueda difusa); lo que no resuelve queda pendiente en el borrador
y se pregunta con botones (máx. 3 opciones + salida)."""
from decimal import Decimal

from apps.canales.models import BorradorAgente
from apps.canales.nucleo import busqueda
from apps.cotizaciones.models import Cotizacion
from apps.inventario.models.producto import Producto
from apps.ventas.models import Cliente

from .base import CanalTestCase


class BusquedaDifusaTests(CanalTestCase):
    def test_plural_tilde_y_tipeo(self):
        Producto.objects.create(empresa=self.empresa_a, sku='M170', nombre='Mouse inalámbrico Logitech M170',
                                precio_compra=Decimal('18'), precio_venta=Decimal('30'))
        for texto in ('mouse inalambrico', 'mouses logitec', 'MOUSE inalámbrico'):
            estado, encontrados = busqueda.resolver_producto(self.empresa_a, texto)
            self.assertEqual(estado, 'ok', texto)
            self.assertEqual(encontrados[0][2]['sku'], 'M170')

    def test_cliente_ignora_forma_societaria(self):
        estado, encontrados = busqueda.resolver_cliente(self.empresa_a, 'transportes lima sac')
        self.assertEqual((estado, encontrados[0][0]), ('ok', self.cliente.id))

    def test_otra_empresa_no_aparece(self):
        estado, _ = busqueda.resolver_cliente(self.empresa_b, 'transportes lima')
        self.assertEqual(estado, 'no_encontrado')


class CotizacionPorTextoTests(CanalTestCase):
    def _cotizar(self, args, chat=None):
        self.mock_llm('preparar_cotizacion', args)
        self.post_update(self.update_texto(chat or self.CHAT_A, 'cotiza'))
        return BorradorAgente.objects.filter(estado='pendiente').order_by('-id').first()

    def test_todo_resuelto_en_una_sola_llamada(self):
        b = self._cotizar({'cliente': 'transportes lima', 'items': [{'producto': 'jabra 750', 'cantidad': 3}]})
        self.assertEqual(b.payload['cliente'], self.cliente.id)
        d = b.payload['detalles'][0]
        self.assertEqual((d['estado'], d['producto'], d['precio_unitario']), ('ok', self.producto.id, '450.00'))
        chat, texto, botones = self.ultima_respuesta()
        self.assertIn(f'b:{b.id}:ok', botones)   # sin pendientes → Confirmar

    def test_producto_ambiguo_ofrece_opciones_y_se_resuelve(self):
        p2 = Producto.objects.create(empresa=self.empresa_a, sku='JB-650', nombre='Auricular Jabra Evolve2 650',
                                     precio_compra=Decimal('200'), precio_venta=Decimal('320'))
        b = self._cotizar({'cliente': 'transportes lima', 'items': [{'producto': 'auricular jabra', 'cantidad': 2}]})
        self.assertEqual(b.payload['detalles'][0]['estado'], 'ambiguo')
        _, texto, botones = self.ultima_respuesta()
        self.assertIn('¿Cuál producto', texto)
        self.assertIn(f'r:{b.id}:i0:{p2.id}', botones)
        self.assertIn(f'r:{b.id}:i0:libre', botones)
        self.assertNotIn(f'b:{b.id}:ok', botones)   # no se puede confirmar con pendientes

        self.post_update(self.update_callback(self.CHAT_A, f'r:{b.id}:i0:{p2.id}'))
        b.refresh_from_db()
        d = b.payload['detalles'][0]
        self.assertEqual((d['estado'], d['producto'], d['precio_unitario']), ('ok', p2.id, '320.00'))
        self.assertIn(f'b:{b.id}:ok', self.ultima_respuesta()[2])

    def test_opcion_forjada_se_rechaza(self):
        Producto.objects.create(empresa=self.empresa_a, sku='JB-650', nombre='Auricular Jabra Evolve2 650',
                                precio_compra=Decimal('200'), precio_venta=Decimal('320'))
        intruso = Producto.objects.create(empresa=self.empresa_b, sku='X', nombre='Producto de B',
                                          precio_compra=Decimal('1'), precio_venta=Decimal('1'))
        b = self._cotizar({'cliente': 'transportes lima', 'items': [{'producto': 'auricular jabra', 'cantidad': 1}]})
        self.post_update(self.update_callback(self.CHAT_A, f'r:{b.id}:i0:{intruso.id}'))
        self.assertIn('no es válida', self.ultima_respuesta()[1])
        b.refresh_from_db()
        self.assertEqual(b.payload['detalles'][0]['estado'], 'ambiguo')

    def test_confirmar_forjado_con_pendientes_no_crea_nada(self):
        b = self._cotizar({'cliente': 'transportes lima', 'items': [{'producto': 'xyzzy', 'cantidad': 1}]})
        self.post_update(self.update_callback(self.CHAT_A, f'b:{b.id}:ok'))
        self.assertIn('Faltan datos', self.ultima_respuesta()[1])
        self.assertEqual(Cotizacion.objects.count(), 0)

    def test_texto_libre(self):
        b = self._cotizar({'cliente': 'transportes lima',
                           'items': [{'producto': 'servicio de instalacion', 'cantidad': 1, 'precio_unitario': 80}]})
        self.assertEqual(b.payload['detalles'][0]['estado'], 'no_encontrado')
        self.post_update(self.update_callback(self.CHAT_A, f'r:{b.id}:i0:libre'))
        self.post_update(self.update_callback(self.CHAT_A, f'b:{b.id}:ok'))
        cot = Cotizacion.objects.get()
        det = cot.detalles.get()
        self.assertIsNone(det.producto)
        self.assertEqual((det.descripcion, det.precio_unitario), ('servicio de instalacion', Decimal('80')))

    def test_cliente_nuevo_pide_ruc_y_se_crea_al_confirmar(self):
        b = self._cotizar({'cliente': 'ferreteria el porvenir', 'items': [{'producto': 'jabra 750', 'cantidad': 1}]})
        self.assertIsNone(b.payload['cliente'])
        _, texto, botones = self.ultima_respuesta()
        self.assertIn('No encontré al cliente', texto)
        self.assertIn(f'r:{b.id}:cn', botones)

        self.post_update(self.update_callback(self.CHAT_A, f'r:{b.id}:cn'))
        self.assertIn('RUC', self.ultima_respuesta()[1])
        self.post_update(self.update_texto(self.CHAT_A, '20 4567 8901'))     # 10 dígitos: inválido
        self.assertIn('11 dígitos', self.ultima_respuesta()[1])
        self.post_update(self.update_texto(self.CHAT_A, '20456789012'))
        self.assertIn(f'b:{b.id}:ok', self.ultima_respuesta()[2])
        self.assertFalse(Cliente.objects.filter(documento='20456789012').exists())  # aún no

        self.post_update(self.update_callback(self.CHAT_A, f'b:{b.id}:ok'))
        nuevo = Cliente.objects.get(documento='20456789012')
        self.assertEqual((nuevo.empresa, nuevo.tipo_documento, nuevo.nombre),
                         (self.empresa_a, 'ruc', 'Ferreteria El Porvenir'))
        self.assertEqual(Cotizacion.objects.get().cliente, nuevo)

    def test_documento_existente_reutiliza_el_cliente(self):
        b = self._cotizar({'cliente': 'transportes del sur', 'items': [{'producto': 'jabra 750', 'cantidad': 1}]})
        self.post_update(self.update_callback(self.CHAT_A, f'r:{b.id}:cn'))
        self.post_update(self.update_texto(self.CHAT_A, self.cliente.documento))
        b.refresh_from_db()
        self.assertEqual(b.payload['cliente'], self.cliente.id)
        self.assertIn('ya es de', self.ultima_respuesta()[1])

    def test_html_en_texto_del_usuario_se_escapa(self):
        self._cotizar({'cliente': '<b>raro', 'items': [{'producto': 'jabra 750', 'cantidad': 1}]})
        texto = self.ultima_respuesta()[1]
        self.assertIn('&lt;b&gt;raro', texto)
