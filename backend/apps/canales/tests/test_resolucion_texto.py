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

    def test_texto_libre_con_precio_es_directo(self):
        """V2: sin match en catálogo y CON precio → línea libre automática,
        sin botón intermedio."""
        b = self._cotizar({'cliente': 'transportes lima',
                           'items': [{'producto': 'servicio de instalacion', 'cantidad': 1, 'precio_unitario': 80}]})
        self.assertEqual(b.payload['detalles'][0]['estado'], 'libre')
        self.post_update(self.update_callback(self.CHAT_A, f'b:{b.id}:ok'))
        cot = Cotizacion.objects.get()
        det = cot.detalles.get()
        self.assertIsNone(det.producto)
        self.assertEqual((det.descripcion, det.precio_unitario), ('servicio de instalacion', Decimal('80')))

    def test_texto_libre_sin_precio_usa_el_boton(self):
        """Sin precio el botón «usar como texto libre» sigue siendo la salida."""
        b = self._cotizar({'cliente': 'transportes lima',
                           'items': [{'producto': 'servicio de instalacion', 'cantidad': 1}]})
        self.assertEqual(b.payload['detalles'][0]['estado'], 'no_encontrado')
        self.post_update(self.update_callback(self.CHAT_A, f'r:{b.id}:i0:libre'))
        b.refresh_from_db()
        self.assertEqual(b.payload['detalles'][0]['estado'], 'libre')

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


class BuscarProductoTests(CanalTestCase):
    """Punto 2 — una tool por intención: buscar_producto lo trae todo."""

    def test_devuelve_precio_stock_costo_y_proveedor(self):
        from apps.canales.nucleo import esquemas as E, servicios
        Producto.objects.filter(pk=self.producto.pk).update(stock_total=Decimal('15'))
        res = servicios.buscar_producto(self.vendedor, E.BuscarProducto(query='jabra 750'))
        p = res['productos'][0]
        self.assertEqual((p['nombre'], p['sku'], p['precio_venta'], p['stock']),
                         ('Auricular Jabra Evolve2 750', 'JB-750', '450.00', '15.00'))
        # sin compras registradas: último costo = precio de compra del catálogo
        self.assertEqual(p['ultimo_costo'], '300.00')
        self.assertFalse(res['aproximado'])

    def test_consultar_stock_ya_no_existe(self):
        from apps.canales.nucleo.interprete import CATALOGO
        self.assertNotIn('consultar_stock', CATALOGO)

    def test_respuesta_del_bot_muestra_todo(self):
        self.mock_llm('buscar_producto', {'query': 'jabra 750'})
        self.post_update(self.update_texto(self.CHAT_A, 'precio y stock del jabra 750?'))
        texto = self.ultima_respuesta()[1]
        for dato in ('Jabra Evolve2 750', 'JB-750', '450.00', 'stock', 'últ. costo'):
            self.assertIn(dato, texto)

    def test_estado_por_cliente(self):
        """«ya se entregó lo de transportes lima»: sin número de venta."""
        from apps.canales.nucleo import esquemas as E, servicios
        res = servicios.cambiar_estado_operativo(self.vendedor, E.CambiarEstadoOperativo(
            cliente_query='transportes lima', nuevo_estado='entregado'))
        self.assertEqual(res['borrador']['payload']['venta'], self.venta.id)


class UltimoCostoTests(CanalTestCase):
    def _compra(self, proveedor, fecha, precio, estado='pendiente'):
        from apps.compras.models import Compra, CompraDetalle
        from apps.inventario.models.almacen import Almacen
        almacen, _ = Almacen.objects.get_or_create(empresa=self.empresa_a, nombre='Central',
                                                   defaults={'direccion': 'x'})
        c = Compra.objects.create(empresa=self.empresa_a, proveedor=proveedor, fecha_emision=fecha,
                                  almacen=almacen)
        CompraDetalle.objects.create(compra=c, producto=self.producto, cantidad=Decimal('1'),
                                     precio_unitario=Decimal(precio))
        # save() de compra y de detalle recalculan el estado (contado → pagada):
        # se fija al final, como lo hace anular()
        Compra.objects.filter(pk=c.pk).update(estado=estado)
        return c

    def test_ultimo_costo_y_proveedor_de_la_ultima_compra_valida(self):
        import datetime as dt
        from apps.canales.nucleo import esquemas as E, servicios
        from apps.compras.models import Proveedor
        viejo = Proveedor.objects.create(empresa=self.empresa_a, razon_social='Proveedor Viejo SAC', ruc='20100000001')
        nuevo = Proveedor.objects.create(empresa=self.empresa_a, razon_social='Proveedor Nuevo SAC', ruc='20100000002')
        hoy = dt.date.today()
        self._compra(viejo, hoy - dt.timedelta(days=30), '280')
        self._compra(nuevo, hoy - dt.timedelta(days=5), '295')
        self._compra(viejo, hoy, '999', estado='anulada')        # no cuenta
        p = servicios.buscar_producto(self.vendedor, E.BuscarProducto(query='jabra 750'))['productos'][0]
        self.assertEqual((p['ultimo_costo'], p['proveedor']), ('295.00', 'Proveedor Nuevo SAC'))
