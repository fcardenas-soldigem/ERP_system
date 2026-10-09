import logging
from django.db import models
from django.conf import settings
from apps.empresas.models import Empresa
from apps.inventario.models.producto import Producto
from apps.inventario.models.stock import Stock
from apps.inventario.models.inventario_productos_terminados import InventarioProductosTerminados
from apps.inventario.models.inventario_materias_primas import InventarioMateriasPrimas
from apps.inventario.models.movimiento_inventario import MovimientoInventario
from apps.core.services.tipo_cambio import TipoCambioMixin
from decimal import Decimal
from django.db import transaction
from django.core.exceptions import ValidationError
from django.utils import timezone
import os
from django.core.validators import MinValueValidator
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

logger = logging.getLogger(__name__)

class Cliente(models.Model):
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='clientes')
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True)
    nombre = models.CharField(max_length=200, verbose_name='Nombre/Razón Social')
    documento = models.CharField(max_length=20, verbose_name='DNI/RUC')  # RUC o DNI
    direccion = models.TextField(blank=True, null=True, verbose_name='Dirección')
    telefono = models.CharField(max_length=20, blank=True, null=True, verbose_name='Teléfono')
    email = models.EmailField(blank=True, null=True, verbose_name='Email')
    activo = models.BooleanField(default=True)
    fecha_registro = models.DateTimeField(auto_now_add=True)
    ultima_actualizacion = models.DateTimeField(auto_now=True)
    TIPO_DOCUMENTO_CHOICES = [
        ('dni', 'DNI'),
        ('ruc', 'RUC'),
    ]
    tipo_documento = models.CharField(max_length=10, choices=TIPO_DOCUMENTO_CHOICES, default='dni')

    class Meta:
        verbose_name = 'Cliente'
        verbose_name_plural = 'Clientes'
        ordering = ['-fecha_registro']
        unique_together = ('empresa', 'documento')

    def __str__(self):
        return f"{self.nombre} - {self.documento}"

def comprobante_upload_to(instance, filename):
    # Generar la ruta para el archivo
    return f'ventas/comprobantes/{instance.venta.empresa.id}/{instance.venta.numero}/{filename}'

class ComprobantePago(models.Model):
    venta = models.OneToOneField('Venta', on_delete=models.CASCADE, related_name='comprobante_pago')
    archivo = models.FileField(upload_to=comprobante_upload_to)
    fecha_subida = models.DateTimeField(auto_now_add=True)
    tipo = models.CharField(max_length=50, choices=[
        ('boleta', 'Boleta'),
        ('factura', 'Factura'),
        ('ticket', 'Ticket'),
        ('otro', 'Otro')
    ])
    numero = models.CharField(max_length=50, blank=True, null=True)
    notas = models.TextField(blank=True)

    class Meta:
        verbose_name = 'Comprobante de Pago'
        verbose_name_plural = 'Comprobantes de Pago'

    def __str__(self):
        return f'Comprobante {self.tipo} - Venta {self.venta.numero}'

    def delete(self, *args, **kwargs):
        # Eliminar el archivo físico
        if self.archivo:
            if os.path.isfile(self.archivo.path):
                os.remove(self.archivo.path)
        super().delete(*args, **kwargs)

class Venta(TipoCambioMixin, models.Model):
    ESTADO_CHOICES = [
        ('borrador', 'Borrador'),
        ('pendiente', 'Pendiente'),
        ('pagado', 'Pagado'),
        ('anulado', 'Anulado')
    ]

    TIPO_VENTA_CHOICES = [
        ('contado', 'Contado'),
        ('credito_30', 'Crédito 30 días'),
        ('credito_60', 'Crédito 60 días')
    ]

    METODO_PAGO_CHOICES = [
        ('efectivo', 'Efectivo'),
        ('transferencia', 'Transferencia'),
        ('tarjeta', 'Tarjeta'),
        ('cheque', 'Cheque')
    ]
    
    MONEDA_CHOICES = [
        ('PEN', 'Sol Peruano (S/)'),
        ('USD', 'Dólar Americano ($)'),
    ]
    
    # Modo de venta: stock (descuenta PT) o pedido (descuenta MP directamente)
    MODO_VENTA_CHOICES = [
        ('stock', 'Desde Stock (Producto Terminado)'),
        ('pedido', 'A Pedido (Descontar Materias Primas)'),
    ]

    # F3 — Estado OPERATIVO (separado del estado de PAGO). Flujo back-to-back.
    ESTADO_OPERATIVO_CHOICES = [
        ('pendiente_compra', 'Pendiente de compra'),
        ('comprado', 'Comprado'),
        ('recibido', 'Recibido'),
        ('entregado', 'Entregado'),
        ('esperando_oc_nr', 'Esperando OC/NR del cliente'),
        ('facturado', 'Facturado'),
        ('cobrado', 'Cobrado'),
    ]
    # 'cobrado' es terminal y se sincroniza con el estado de PAGO (no se elige a mano).
    ESTADOS_OPERATIVOS_MANUALES = [
        'pendiente_compra', 'comprado', 'recibido', 'entregado',
        'esperando_oc_nr', 'facturado',
    ]
    # SLA por estado (días esperados). Valores pensados para back-to-back:
    # comprar rápido tras aceptar, lead time de proveedor, y cobranza.
    # 'cobrado' es terminal → sin SLA. Configurable por empresa en fase futura (D5).
    SLA_OPERATIVO_DIAS = {
        'pendiente_compra': 2,
        'comprado': 5,
        'recibido': 2,
        'entregado': 3,
        'esperando_oc_nr': 5,
        # B1 — 35 = crédito 30 días + tolerancia. En Fase 2 derivar de forma_pago.
        'facturado': 35,
    }

    id = models.BigAutoField(primary_key=True)
    numero = models.CharField(max_length=20)  # único POR EMPRESA (ver Meta)
    empresa = models.ForeignKey(Empresa, on_delete=models.PROTECT)
    cliente = models.ForeignKey('Cliente', on_delete=models.PROTECT)
    fecha_emision = models.DateField()
    fecha_vencimiento = models.DateField(null=True, blank=True)
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='borrador')
    tipo_venta = models.CharField(max_length=20, choices=TIPO_VENTA_CHOICES, default='contado')
    metodo_pago = models.CharField(max_length=20, choices=METODO_PAGO_CHOICES, null=True, blank=True)
    igv_incluido = models.BooleanField(default=True)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    igv = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    pagos_total = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    moneda = models.CharField(
        max_length=3,
        choices=MONEDA_CHOICES,
        default='PEN',
        verbose_name='Moneda'
    )
    tipo_cambio = models.DecimalField(
        max_digits=10, decimal_places=4, null=True, blank=True,
        verbose_name='Tipo de cambio',
        help_text='TC venta SBS de la fecha de emisión. PEN = 1.0. Se fija al emitir y no cambia.'
    )
    notas = models.TextField(blank=True)
    referencia = models.CharField(max_length=100, blank=True)
    comprobante = models.FileField(upload_to='comprobantes/', null=True, blank=True)
    # Modo de venta para ventas a pedido
    modo_venta = models.CharField(
        max_length=20,
        choices=MODO_VENTA_CHOICES,
        default='stock',
        verbose_name='Modo de Venta',
        help_text='Stock: descuenta productos terminados. Pedido: descuenta materias primas directamente.'
    )
    # F3 — estado operativo (timeline), independiente de `estado` (pago).
    estado_operativo = models.CharField(
        max_length=30,
        choices=ESTADO_OPERATIVO_CHOICES,
        default='pendiente_compra',
        verbose_name='Estado operativo',
    )
    estado_operativo_actualizado = models.DateTimeField(null=True, blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_modificacion = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-fecha_emision']
        verbose_name = 'Venta'
        verbose_name_plural = 'Ventas'
        constraints = [
            models.UniqueConstraint(
                fields=['empresa', 'numero'], name='uniq_venta_empresa_numero'
            ),
        ]

    def __str__(self):
        return f"Venta {self.numero} - {self.cliente.nombre}"

    def get_saldo_pendiente(self):
        # Solo considerar pagos que no estén en estado pendiente
        pagado = self.pagos.exclude(metodo_pago='pendiente').aggregate(
            total=models.Sum('monto')
        )['total'] or Decimal('0')
        # Asegurar tipos Decimal en la resta
        return (self.total or Decimal('0')) - pagado

    def get_simbolo_moneda(self):
        simbolos = {
            'PEN': 'S/',
            'USD': '$'
        }
        return simbolos.get(self.moneda, 'S/')

    def clean(self):
        if not self.empresa_id:
            raise ValidationError('La venta debe tener una empresa asignada')
        if not self.cliente_id:
            raise ValidationError('La venta debe tener un cliente asignado')
        super().clean()

    def save(self, *args, **kwargs):
        if not self.numero and not self.empresa:
            raise ValidationError('La venta debe tener una empresa asignada antes de generar el número')

        if self.tipo_venta.startswith('credito_'):
            dias = int(self.tipo_venta.split('_')[1])
            if not self.fecha_vencimiento:
                self.fecha_vencimiento = self.fecha_emision + timezone.timedelta(days=dias)

        self.asegurar_tipo_cambio()

        from apps.core.numbering import guardar_con_numero
        guardar_con_numero(
            self, self._siguiente_numero,
            lambda: super(Venta, self).save(*args, **kwargs),
        )

    def _siguiente_numero(self):
        """Siguiente número de venta POR EMPRESA (V-000001...). select_for_update."""
        ultima = (
            Venta.objects.select_for_update()
            .filter(empresa_id=self.empresa_id, numero__startswith='V-')
            .order_by('-numero').only('numero').first()
        )
        if ultima:
            try:
                siguiente = int(ultima.numero.split('-')[1]) + 1
            except (ValueError, IndexError):
                siguiente = Venta.objects.filter(empresa_id=self.empresa_id).count() + 1
        else:
            legacy = (
                Venta.objects.select_for_update()
                .filter(empresa_id=self.empresa_id, numero__regex=r'^\d+$')
                .order_by('-numero').only('numero').first()
            )
            siguiente = (int(legacy.numero) + 1) if legacy else 1
        return f"V-{str(siguiente).zfill(6)}"

    def actualizar_totales(self):
        detalles = self.detalles.all()
        subtotal = sum(detalle.cantidad * detalle.precio_unitario for detalle in detalles)
        
        if self.igv_incluido:
            self.total = subtotal
            self.subtotal = round(subtotal / Decimal('1.18'), 2)
            self.igv = self.total - self.subtotal
        else:
            self.subtotal = subtotal
            self.igv = round(subtotal * Decimal('0.18'), 2)
            self.total = self.subtotal + self.igv
        
        self.save()

    def _debe_mover_stock(self, detalle):
        """
        Regla ESTRICTA (H1, punto 7 — sin fail-open). Solo mueve stock si TODO
        se cumple:
        - la empresa controla inventario (modo_inventario == 'con_stock'), Y
        - la línea es de stock (origen == 'stock'), Y
        - la línea NO fue descontada aún (stock_descontado == False), Y
        - la línea tiene producto.

        origen == None ya NO se trata como movible: el backfill #8 fijó las
        líneas históricas y DetalleVenta.save() infiere el origen en las nuevas.
        """
        if getattr(self.empresa, 'modo_inventario', 'con_stock') != 'con_stock':
            return False
        if detalle.origen != 'stock':
            return False
        if detalle.stock_descontado:
            return False
        if detalle.producto_id is None:
            return False
        return True

    # ───────── F3: estado operativo, historial y SLA ─────────
    @property
    def tiene_historial_operativo(self):
        """True si la venta tiene historial operativo (ventas nuevas, no históricas)."""
        return self.historial_operativo.exists()

    @property
    def dias_en_estado_operativo(self):
        ref = self.estado_operativo_actualizado or self.fecha_creacion
        if ref is None:
            return None
        return (timezone.now() - ref).days

    @property
    def estado_sla_operativo(self):
        """ok / alerta / vencido / sin_sla (patrón servicios.estado_sla)."""
        if self.estado_operativo == 'cobrado':
            return 'ok'  # terminal
        limite = self.SLA_OPERATIVO_DIAS.get(self.estado_operativo)
        dias = self.dias_en_estado_operativo
        if limite is None or dias is None:
            return 'sin_sla'
        if dias > limite:
            return 'vencido'
        if dias >= limite - 1:
            return 'alerta'
        return 'ok'

    def _registrar_historial_operativo(self, anterior, nuevo, usuario=None, nota=''):
        HistorialEstadoVenta.objects.create(
            venta=self, estado_anterior=anterior or '', estado_nuevo=nuevo,
            usuario=usuario, nota=nota or '',
        )

    def cambiar_estado_operativo(self, nuevo_estado, usuario=None, nota=''):
        """
        F3/D3. Avanza o retrocede el estado operativo, escribe historial y
        dispara/reversa el descuento de stock al entrar/salir de 'entregado'.
        'cobrado' NO es elegible aquí: se sincroniza con el estado de pago.
        """
        if nuevo_estado not in dict(self.ESTADO_OPERATIVO_CHOICES):
            raise ValidationError(f'Estado operativo inválido: {nuevo_estado}')
        if nuevo_estado == 'cobrado':
            raise ValidationError(
                "'cobrado' se sincroniza con el estado de pago; no se asigna manualmente."
            )
        anterior = self.estado_operativo
        if anterior == nuevo_estado:
            return self
        with transaction.atomic():
            self.estado_operativo = nuevo_estado
            self.estado_operativo_actualizado = timezone.now()
            self.save(update_fields=['estado_operativo', 'estado_operativo_actualizado', 'fecha_modificacion'])
            self._registrar_historial_operativo(anterior, nuevo_estado, usuario, nota)
            if nuevo_estado == 'entregado':
                self.aplicar_entrega_stock()
            elif anterior == 'entregado':
                self.revertir_entrega_stock()
        return self

    def _sincronizar_estado_operativo_pago(self, usuario=None):
        """
        Fuente única cobrado↔pago (punto 3):
        - estado 'pagado'            → estado_operativo 'cobrado' (+historial).
        - estado deja de ser 'pagado' y estaba 'cobrado' → 'facturado' (+historial).
        """
        if self.estado == 'pagado' and self.estado_operativo != 'cobrado':
            anterior = self.estado_operativo
            self.estado_operativo = 'cobrado'
            self.estado_operativo_actualizado = timezone.now()
            self.save(update_fields=['estado_operativo', 'estado_operativo_actualizado'])
            self._registrar_historial_operativo(anterior, 'cobrado', usuario, 'Sincronizado con pago')
        elif self.estado != 'pagado' and self.estado_operativo == 'cobrado':
            self.estado_operativo = 'facturado'
            self.estado_operativo_actualizado = timezone.now()
            self.save(update_fields=['estado_operativo', 'estado_operativo_actualizado'])
            self._registrar_historial_operativo('cobrado', 'facturado', usuario, 'Pago revertido')

    def aplicar_entrega_stock(self):
        """§4.4 — Descuenta stock al entrar a 'entregado' (una sola vez por línea)."""
        from apps.inventario.models.inventario_productos_terminados import InventarioProductosTerminados
        for detalle in self.detalles.all():
            if not self._debe_mover_stock(detalle):
                continue
            producto = detalle.producto
            almacen = producto.almacen or self.empresa.almacenes.first()
            if not almacen:
                logger.warning("Entrega venta %s: sin almacén para %s; se omite", self.numero, producto.nombre)
                continue
            try:
                InventarioProductosTerminados.procesar_venta(
                    empresa=self.empresa, producto=producto, almacen=almacen,
                    cantidad=detalle.cantidad, desde_reserva=True,
                )
            except Exception:
                # OD-B degradación: sin reserva previa → descontar de disponible.
                try:
                    InventarioProductosTerminados.procesar_venta(
                        empresa=self.empresa, producto=producto, almacen=almacen,
                        cantidad=detalle.cantidad, desde_reserva=False,
                    )
                except Exception as e2:
                    logger.warning("Entrega venta %s: no se pudo descontar %s: %s", self.numero, producto.nombre, e2)
            detalle.stock_descontado = True
            detalle.save(update_fields=['stock_descontado'])
            producto.actualizar_stock_total()

    def revertir_entrega_stock(self):
        """§4.4 — Reversa simétrica al retroceder desde 'entregado'."""
        from apps.inventario.models.inventario_productos_terminados import InventarioProductosTerminados
        for detalle in self.detalles.all():
            if detalle.origen != 'stock' or not detalle.stock_descontado or detalle.producto_id is None:
                continue
            producto = detalle.producto
            almacen = producto.almacen or self.empresa.almacenes.first()
            if almacen:
                try:
                    inv = InventarioProductosTerminados.objects.select_for_update().get(
                        empresa=self.empresa, producto=producto, almacen=almacen)
                    inv.cantidad_disponible += detalle.cantidad
                    inv.save()
                except Exception as e:
                    logger.warning("Reversa entrega venta %s: no se reintegró %s: %s", self.numero, producto.nombre, e)
            detalle.stock_descontado = False
            detalle.save(update_fields=['stock_descontado'])
            producto.actualizar_stock_total()

    def actualizar_stock(self):
        """
        Actualiza el stock cuando se confirma una venta.
        
        Modos de venta:
        - 'stock': Descuenta productos terminados del inventario (modo normal)
        - 'pedido': Descuenta materias primas directamente según la receta del producto
                   (útil cuando no hay stock de PT y se produce bajo demanda)
        
        Registra movimientos de inventario con trazabilidad completa.
        """
        logger.info("Actualizando stock venta %s (modo: %s)", self.numero, self.modo_venta)

        for detalle in self.detalles.all():
            # H1 — Regla ESTRICTA. Esta vía (descuento al pagar) quedó
            # DESACTIVADA (§4.4): el descuento real ocurre al entrar a 'entregado'
            # vía aplicar_entrega_stock(). Se mantiene la guarda por seguridad.
            if not self._debe_mover_stock(detalle):
                continue

            producto = detalle.producto
            cantidad = detalle.cantidad

            almacen = producto.almacen
            if not almacen:
                almacen = self.empresa.almacenes.first()

            if not almacen:
                logger.error("No se encontró almacén para el producto %s", producto.nombre)
                continue
            
            # Variables para el costo
            costo_unitario = producto.precio_compra or Decimal('0')
            
            # Determinar qué modo de actualización usar
            if self.modo_venta == 'pedido' and producto.tipo_producto == 'FINISHED':
                # MODO PEDIDO: Descontar materias primas directamente
                self._descontar_materias_primas_por_receta(detalle, producto, cantidad, almacen)
            else:
                # MODO STOCK (normal): Descontar productos terminados
                self._descontar_producto_terminado(detalle, producto, cantidad, almacen, costo_unitario)
        
    def _descontar_producto_terminado(self, detalle, producto, cantidad, almacen, costo_unitario):
        """
        Modo normal: Descuenta del inventario de productos terminados.
        """
        # 1. Actualizar Stock legacy
        stock, created = Stock.objects.get_or_create(
            producto=producto,
            almacen=almacen,
            empresa=self.empresa,
            defaults={'cantidad': 0}
        )
        
        stock_anterior = stock.cantidad

        if stock.cantidad >= cantidad:
            stock.cantidad -= cantidad
            stock.save()
        else:
            logger.warning("Stock insuficiente para %s: disponible %s, solicitado %s", producto.nombre, stock.cantidad, cantidad)
            stock.cantidad = 0
            stock.save()

        if producto.tipo_producto == 'FINISHED':
            try:
                resultado = InventarioProductosTerminados.procesar_venta(
                    empresa=self.empresa,
                    producto=producto,
                    almacen=almacen,
                    cantidad=cantidad,
                    desde_reserva=False
                )
                costo_unitario = resultado['costo_unitario']
            except (InventarioProductosTerminados.DoesNotExist, ValidationError) as e:
                logger.warning("No se pudo descontar de InventarioPT: %s", e)

        try:
            MovimientoInventario.objects.create(
                empresa=self.empresa,
                producto=producto,
                almacen=almacen,
                fecha=timezone.now(),
                tipo_movimiento='salida_venta',
                tipo_documento='venta',
                tipo_inventario='producto_terminado' if producto.tipo_producto == 'FINISHED' else 'general',
                numero_documento=self.numero,
                cantidad_salida=cantidad,
                costo_unitario=costo_unitario,
                costo_total_salida=cantidad * costo_unitario,
                cantidad_saldo=stock.cantidad,
                inventario_anterior=float(stock_anterior),
                inventario_actual=float(stock.cantidad),
                venta_id=self.id,
                observaciones=f'Venta {self.numero} - Cliente: {self.cliente.nombre}',
                created_by=''
            )
        except Exception as e:
            logger.error("Error al registrar movimiento de inventario venta %s: %s", self.numero, e, exc_info=True)
        
        # Actualizar stock total del producto
        producto.actualizar_stock_total()
    
    def _descontar_materias_primas_por_receta(self, detalle, producto, cantidad, almacen):
        """
        Modo pedido: Descuenta materias primas directamente según la receta del producto.
        Útil para ventas a pedido donde no hay stock de productos terminados.
        """
        from apps.produccion.models import RecetaProducto, RecetaDetalle
        
        logger.info("Venta a pedido: descontando MP para %s x %s", producto.nombre, cantidad)

        try:
            receta = RecetaProducto.objects.filter(
                empresa=self.empresa,
                producto_terminado=producto,
                activa=True
            ).first()

            if not receta:
                logger.warning("No se encontró receta activa para %s, usando modo stock", producto.nombre)
                self._descontar_producto_terminado(detalle, producto, cantidad, almacen, producto.precio_compra or Decimal('0'))
                return

            rendimiento = Decimal(str(receta.cantidad_producida)) if receta.cantidad_producida else Decimal('1')
            factor = Decimal(str(cantidad)) / rendimiento
            costo_total_mp = Decimal('0')

            for ingrediente in receta.ingredientes.all():
                insumo = ingrediente.insumo
                cantidad_necesaria = Decimal(str(ingrediente.cantidad)) * factor
                almacen_insumos = almacen

                costo_unitario_mp = Decimal('0')
                try:
                    inv_mp = InventarioMateriasPrimas.objects.filter(
                        empresa=self.empresa,
                        producto=insumo,
                        almacen=almacen_insumos,
                        cantidad_disponible__gt=0
                    ).first()
                    if inv_mp:
                        costo_unitario_mp = inv_mp.costo_unitario_promedio
                except Exception:
                    costo_unitario_mp = insumo.precio_compra or Decimal('0')

                try:
                    resultado = InventarioMateriasPrimas.consumir_en_produccion(
                        empresa=self.empresa,
                        producto=insumo,
                        almacen=almacen_insumos,
                        cantidad=cantidad_necesaria,
                        desde_reserva=False
                    )
                    costo_unitario_mp = resultado['costo_unitario']
                except ValidationError as e:
                    logger.warning("Error al descontar MP %s: %s — usando Stock legacy", insumo.nombre, e)
                    try:
                        stock_mp, _ = Stock.objects.get_or_create(
                            producto=insumo,
                            almacen=almacen_insumos,
                            empresa=self.empresa,
                            defaults={'cantidad': 0}
                        )
                        if stock_mp.cantidad >= cantidad_necesaria:
                            stock_mp.cantidad -= cantidad_necesaria
                        else:
                            stock_mp.cantidad = 0
                        stock_mp.save()
                    except Exception as ex:
                        logger.error("Error en Stock legacy para %s: %s", insumo.nombre, ex, exc_info=True)

                try:
                    MovimientoInventario.objects.create(
                        empresa=self.empresa,
                        producto=insumo,
                        almacen=almacen_insumos,
                        fecha=timezone.now(),
                        tipo_movimiento='salida_venta',
                        tipo_documento='venta',
                        tipo_inventario='materia_prima',
                        numero_documento=self.numero,
                        cantidad_salida=cantidad_necesaria,
                        costo_unitario=costo_unitario_mp,
                        costo_total_salida=cantidad_necesaria * costo_unitario_mp,
                        venta_id=self.id,
                        observaciones=f'Venta a pedido {self.numero} - Para: {producto.nombre} x {cantidad}',
                        created_by=''
                    )
                except Exception as e:
                    logger.error("Error al registrar movimiento MP: %s", e, exc_info=True)

                insumo.actualizar_stock_total()
                costo_total_mp += cantidad_necesaria * costo_unitario_mp

            costo_unitario_pt = costo_total_mp / Decimal(str(cantidad)) if cantidad > 0 else Decimal('0')

            try:
                MovimientoInventario.objects.create(
                    empresa=self.empresa,
                    producto=producto,
                    almacen=almacen,
                    fecha=timezone.now(),
                    tipo_movimiento='salida_venta',
                    tipo_documento='venta',
                    tipo_inventario='producto_terminado',
                    numero_documento=self.numero,
                    cantidad_salida=cantidad,
                    costo_unitario=costo_unitario_pt,
                    costo_total_salida=costo_total_mp,
                    venta_id=self.id,
                    observaciones=f'Venta a pedido {self.numero} - Cliente: {self.cliente.nombre} (MP descontadas directamente)',
                    created_by=''
                )
            except Exception as e:
                logger.error("Error al registrar movimiento PT virtual: %s", e, exc_info=True)

        except Exception as e:
            logger.error("Error en venta a pedido %s: %s", self.numero, e, exc_info=True)
            self._descontar_producto_terminado(detalle, producto, cantidad, almacen, producto.precio_compra or Decimal('0'))

    def marcar_como_pagada(self):
        if self.estado == 'pagado':
            return

        with transaction.atomic():
            self.estado = 'pagado'
            self.save()
            # Fuente única cobrado↔pago (F3, punto 3).
            self._sincronizar_estado_operativo_pago()

    def anular_venta(self):
        if self.estado == 'pagado':
            for detalle in self.detalles.all():
                # D1/D6: líneas de texto libre (producto None) o productos que no
                # controlan stock no tienen inventario que revertir.
                if detalle.producto is None or not detalle.producto.controla_stock:
                    continue
                almacen = self.empresa.almacenes.first() if hasattr(self.empresa, 'almacenes') else None
                if almacen is None:
                    raise ValidationError('No se encontró un almacén para la empresa.')
                stock, created = Stock.objects.get_or_create(
                    producto=detalle.producto,
                    empresa=self.empresa,
                    almacen=almacen,
                    defaults={'cantidad': 0}
                )
                stock.cantidad += detalle.cantidad
                stock.save()
                detalle.producto.actualizar_stock_total()
        
        self.estado = 'anulado'
        self.save()

    def cancelar_venta(self):
        if self.estado == 'anulado':
            raise ValueError('La venta ya está anulada')
        
        self.estado = 'anulado'
        self.save()

    def actualizar_estado_pago(self):
        # Calcular el total pagado excluyendo los pagos pendientes
        total_pagado = self.pagos.exclude(metodo_pago='pendiente').aggregate(
            total=models.Sum('monto')
        )['total'] or Decimal('0')
        
        self.pagos_total = total_pagado
        
        if self.tipo_venta in ['credito_30', 'credito_60']:
            if total_pagado >= self.total:
                self.estado = 'pagado'
            else:
                self.estado = 'pendiente'
        else:
            if total_pagado >= self.total:
                self.estado = 'pagado'
            elif total_pagado > 0:
                self.estado = 'pendiente'
            else:
                self.estado = 'borrador'

        self.save()
        # Fuente única cobrado↔pago (F3, punto 3).
        self._sincronizar_estado_operativo_pago()
        return self.estado

class DetalleVenta(models.Model):
    ORIGEN_CHOICES = [
        ('stock', 'Desde stock (reserva/descuenta inventario)'),
        ('pedido_proveedor', 'A pedido de proveedor (nunca mueve inventario)'),
    ]

    venta = models.ForeignKey(
        Venta,
        on_delete=models.CASCADE,
        related_name='detalles'
    )
    # producto nullable (D1): se permiten líneas de texto libre.
    producto = models.ForeignKey(
        'inventario.Producto', on_delete=models.PROTECT, null=True, blank=True
    )
    # descripcion para líneas sin producto (D1).
    descripcion = models.CharField(max_length=500, null=True, blank=True)
    cantidad = models.DecimalField(max_digits=10, decimal_places=2)
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2)
    # D6 — origen. La conversión lo fija explícito; en ventas normales lo infiere
    # save() según el modo de inventario de la empresa (ya no hay fail-open).
    origen = models.CharField(
        max_length=20, choices=ORIGEN_CHOICES, null=True, blank=True
    )
    # Guarda de idempotencia del descuento de stock (§4.4): el descuento real
    # ocurre al entrar a 'entregado' y marca esta bandera.
    stock_descontado = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(default=timezone.now)

    class Meta:
        verbose_name = 'Detalle de venta'
        verbose_name_plural = 'Detalles de venta'

    def __str__(self):
        nombre = self.producto.nombre if self.producto_id else (self.descripcion or 'Ítem')
        return f"{nombre} - {self.cantidad} unidades"

    def clean(self):
        if self.cantidad <= 0:
            raise ValidationError('La cantidad debe ser mayor que cero')
        if self.precio_unitario <= 0:
            raise ValidationError('El precio unitario debe ser mayor que cero')

    def save(self, *args, **kwargs):
        # Inferir origen cuando no vino explícito (ventas normales). La conversión
        # ya lo fija. sin_stock → pedido_proveedor; con_stock → stock.
        if self.origen is None and self.venta_id:
            modo = getattr(self.venta.empresa, 'modo_inventario', 'con_stock')
            self.origen = 'pedido_proveedor' if modo == 'sin_stock' else 'stock'
        super().save(*args, **kwargs)
        if self.venta_id:
            self.venta.actualizar_totales()

class Factura(models.Model):
    venta = models.OneToOneField(
        Venta, 
        on_delete=models.CASCADE, 
        related_name='factura'
    )
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE, related_name='facturas')
    numero_factura = models.CharField(max_length=20)
    fecha = models.DateField(auto_now_add=True)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    igv = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.igv:
            self.igv = self.subtotal * Decimal('0.18')
        if not self.total:
            self.total = self.subtotal + self.igv
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = 'Factura'
        verbose_name_plural = 'Facturas'
        ordering = ['-fecha']
        unique_together = ('cliente', 'numero_factura')

    def __str__(self):
        return f"Factura {self.numero_factura} - {self.cliente.nombre}"

class OrdenVenta(models.Model):
    ESTADO_CHOICES = [
        ('pendiente', 'Pendiente'),
        ('aprobada', 'Aprobada'),
        ('rechazada', 'Rechazada'),
        ('completada', 'Completada'),
    ]

    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='ordenes_venta')
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE, related_name='ordenes_venta')
    numero_orden = models.CharField(max_length=20)
    fecha_orden = models.DateField()
    fecha_entrega = models.DateField()
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='pendiente')
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    igv = models.DecimalField(max_digits=10, decimal_places=2)
    total = models.DecimalField(max_digits=10, decimal_places=2)
    notas = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Orden de venta'
        verbose_name_plural = 'Órdenes de venta'
        ordering = ['-fecha_orden']
        unique_together = ('empresa', 'numero_orden')

    def __str__(self):
        return f"OV-{self.numero_orden} - {self.cliente.nombre}"

class PagoVenta(models.Model):
    METODO_PAGO_CHOICES = [
        ('pendiente', 'Pendiente'),
        ('efectivo', 'Efectivo'),
        ('transferencia', 'Transferencia'),
        ('tarjeta', 'Tarjeta'),
        ('cheque', 'Cheque')
    ]

    venta = models.ForeignKey(
        Venta, 
        on_delete=models.CASCADE, 
        related_name='pagos',
        verbose_name='Venta'
    )
    fecha = models.DateField(
        verbose_name='Fecha de Pago'
    )
    monto = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        verbose_name='Monto',
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    metodo_pago = models.CharField(
        max_length=20, 
        choices=METODO_PAGO_CHOICES,
        verbose_name='Método de Pago'
    )
    referencia = models.CharField(
        max_length=100, 
        blank=True,
        verbose_name='Referencia'
    )
    comprobante = models.FileField(
        upload_to='ventas/pagos/', 
        null=True, 
        blank=True,
        verbose_name='Comprobante'
    )
    notas = models.TextField(
        blank=True,
        verbose_name='Notas'
    )

    class Meta:
        verbose_name = 'Pago de Venta'
        verbose_name_plural = 'Pagos de Ventas'
        ordering = ['-fecha', '-id']

    def __str__(self):
        return f"Pago {self.id} - Venta {self.venta.numero}"

    def clean(self):
        if self.monto > self.venta.get_saldo_pendiente():
            raise ValidationError('El monto del pago excede el saldo pendiente de la venta')
        
        if self.fecha < self.venta.fecha_emision:
            raise ValidationError('La fecha del pago no puede ser anterior a la fecha de emisión de la venta')

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)
        
        self.venta.actualizar_estado_pago()

@receiver(post_save, sender=PagoVenta)
def actualizar_estado_pago_venta(sender, instance, **kwargs):
    instance.venta.actualizar_estado_pago()

@receiver(post_delete, sender=PagoVenta)
def actualizar_estado_pago_venta_delete(sender, instance, **kwargs):
    instance.venta.actualizar_estado_pago()


class HistorialEstadoVenta(models.Model):
    """
    F3 — Historial de cambios de estado OPERATIVO de la venta.
    Espejo de servicios.HistorialEstadoOS. Lo escribe Venta.cambiar_estado_operativo
    y la sincronización con el pago. NO se crea para ventas históricas (H3).
    """
    venta = models.ForeignKey(
        Venta, on_delete=models.CASCADE, related_name='historial_operativo'
    )
    estado_anterior = models.CharField(max_length=30, blank=True)
    estado_nuevo = models.CharField(max_length=30)
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='historial_estado_venta',
    )
    fecha = models.DateTimeField(auto_now_add=True)
    nota = models.CharField(max_length=500, blank=True)

    class Meta:
        verbose_name = 'Historial de Estado Operativo de Venta'
        verbose_name_plural = 'Historial de Estados Operativos de Venta'
        ordering = ['-fecha']

    def __str__(self):
        return f"{self.venta.numero}: {self.estado_anterior} → {self.estado_nuevo}"