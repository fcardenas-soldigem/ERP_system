from django.db import models, transaction
from django.core.exceptions import ValidationError
from decimal import Decimal
from apps.empresas.models import Empresa
from .producto import Producto
from .almacen import Almacen

class MovimientoInventario(models.Model):
    """
    Modelo para registrar todos los movimientos de inventario
    Implementa el sistema Kardex con método FIFO
    Soporta trazabilidad completa entre módulos (compras, producción, ventas)
    """
    
    TIPO_MOVIMIENTO_CHOICES = [
        ('entrada', 'Entrada'),
        ('salida', 'Salida'),
        ('ajuste_entrada', 'Ajuste - Entrada'),
        ('ajuste_salida', 'Ajuste - Salida'),
        ('devolucion_compra', 'Devolución Compra'),
        ('devolucion_venta', 'Devolución Venta'),
        ('transferencia_entrada', 'Transferencia - Entrada'),
        ('transferencia_salida', 'Transferencia - Salida'),
        # Nuevos tipos para producción
        ('entrada_compra', 'Entrada por Compra'),
        ('salida_produccion', 'Salida a Producción'),
        ('entrada_produccion', 'Entrada por Producción'),
        ('salida_venta', 'Salida por Venta'),
        ('reserva_produccion', 'Reserva para Producción'),
        ('liberacion_reserva', 'Liberación de Reserva'),
        ('reserva_venta', 'Reserva para Venta'),
    ]
    
    TIPO_DOCUMENTO_CHOICES = [
        ('compra', 'Compra'),
        ('venta', 'Venta'),
        ('ajuste', 'Ajuste de Inventario'),
        ('devolucion_compra', 'Devolución de Compra'),
        ('devolucion_venta', 'Devolución de Venta'),
        ('transferencia', 'Transferencia'),
        ('inventario_inicial', 'Inventario Inicial'),
        ('orden_produccion', 'Orden de Producción'),
        ('recepcion_produccion', 'Recepción de Producción'),
    ]
    
    TIPO_INVENTARIO_CHOICES = [
        ('materia_prima', 'Materia Prima'),
        ('producto_terminado', 'Producto Terminado'),
        ('general', 'General'),
    ]
    
    # Relaciones básicas
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE)
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE, related_name='movimientos')
    almacen = models.ForeignKey(Almacen, on_delete=models.CASCADE)
    
    # Información del movimiento
    fecha = models.DateTimeField()
    tipo_movimiento = models.CharField(max_length=30, choices=TIPO_MOVIMIENTO_CHOICES)
    tipo_documento = models.CharField(max_length=30, choices=TIPO_DOCUMENTO_CHOICES)
    numero_documento = models.CharField(max_length=50, blank=True)
    
    # Tipo de inventario afectado
    tipo_inventario = models.CharField(
        max_length=30, 
        choices=TIPO_INVENTARIO_CHOICES, 
        default='general',
        verbose_name='Tipo de Inventario'
    )
    
    # Cantidades
    cantidad_entrada = models.DecimalField(max_digits=12, decimal_places=4, default=0)
    cantidad_salida = models.DecimalField(max_digits=12, decimal_places=4, default=0)
    cantidad_saldo = models.DecimalField(max_digits=12, decimal_places=4, default=0)
    
    # Costos
    costo_unitario = models.DecimalField(max_digits=12, decimal_places=4, default=0)
    costo_total_entrada = models.DecimalField(max_digits=15, decimal_places=4, default=0)
    costo_total_salida = models.DecimalField(max_digits=15, decimal_places=4, default=0)
    costo_saldo = models.DecimalField(max_digits=15, decimal_places=4, default=0)
    
    # Inventarios anterior y actual (para trazabilidad)
    inventario_anterior = models.DecimalField(
        max_digits=12, 
        decimal_places=4, 
        default=0,
        verbose_name='Inventario Anterior'
    )
    inventario_actual = models.DecimalField(
        max_digits=12, 
        decimal_places=4, 
        default=0,
        verbose_name='Inventario Actual'
    )
    
    # Referencias a documentos originales
    compra_id = models.IntegerField(null=True, blank=True)
    venta_id = models.IntegerField(null=True, blank=True)
    ajuste_id = models.IntegerField(null=True, blank=True)
    orden_produccion_id = models.IntegerField(null=True, blank=True, verbose_name='ID Orden Producción')
    
    # Almacenes para transferencias
    almacen_origen = models.ForeignKey(
        Almacen, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='movimientos_origen',
        verbose_name='Almacén Origen'
    )
    almacen_destino = models.ForeignKey(
        Almacen, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='movimientos_destino',
        verbose_name='Almacén Destino'
    )
    
    # Metadatos
    observaciones = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.CharField(max_length=100, blank=True)  # Usuario que hizo el movimiento
    
    # Campos para control FIFO
    lote_referencia = models.CharField(max_length=100, blank=True)  # Para identificar lotes
    costo_promedio = models.DecimalField(max_digits=12, decimal_places=4, default=0)
    
    class Meta:
        verbose_name = 'Movimiento de Inventario'
        verbose_name_plural = 'Movimientos de Inventario'
        ordering = ['-fecha', '-id']
        indexes = [
            models.Index(fields=['empresa', 'producto', 'fecha']),
            models.Index(fields=['empresa', 'producto', 'tipo_movimiento']),
            models.Index(fields=['fecha']),
        ]
    
    def __str__(self):
        return f"{self.producto.sku} - {self.get_tipo_movimiento_display()} - {self.fecha.strftime('%Y-%m-%d')}"
    
    def clean(self):
        """Validaciones del modelo"""
        if self.cantidad_entrada > 0 and self.cantidad_salida > 0:
            raise ValidationError("Un movimiento no puede tener entrada y salida al mismo tiempo")
        
        if self.cantidad_entrada == 0 and self.cantidad_salida == 0:
            raise ValidationError("El movimiento debe tener cantidad de entrada o salida")
        
        if self.tipo_movimiento in ['entrada', 'ajuste_entrada', 'devolucion_venta', 'transferencia_entrada']:
            if self.cantidad_entrada <= 0:
                raise ValidationError(f"Los movimientos de tipo {self.tipo_movimiento} deben tener cantidad de entrada")
        
        if self.tipo_movimiento in ['salida', 'ajuste_salida', 'devolucion_compra', 'transferencia_salida']:
            if self.cantidad_salida <= 0:
                raise ValidationError(f"Los movimientos de tipo {self.tipo_movimiento} deben tener cantidad de salida")
    
    @classmethod
    def registrar_entrada(cls, empresa, producto, almacen, cantidad, costo_unitario, 
                         tipo_documento, numero_documento, fecha, observaciones="", 
                         documento_id=None, usuario=""):
        """
        Registra una entrada de inventario
        """
        with transaction.atomic():
            # Obtener saldo actual
            ultimo_movimiento = cls.objects.filter(
                empresa=empresa,
                producto=producto,
                almacen=almacen
            ).first()
            
            saldo_anterior = ultimo_movimiento.cantidad_saldo if ultimo_movimiento else Decimal('0')
            costo_saldo_anterior = ultimo_movimiento.costo_saldo if ultimo_movimiento else Decimal('0')
            
            # Calcular nuevos valores
            nuevo_saldo = saldo_anterior + cantidad
            costo_total_entrada = cantidad * costo_unitario
            nuevo_costo_saldo = costo_saldo_anterior + costo_total_entrada
            
            # Calcular costo promedio
            costo_promedio = nuevo_costo_saldo / nuevo_saldo if nuevo_saldo > 0 else Decimal('0')
            
            # Crear el movimiento
            movimiento = cls.objects.create(
                empresa=empresa,
                producto=producto,
                almacen=almacen,
                fecha=fecha,
                tipo_movimiento='entrada',
                tipo_documento=tipo_documento,
                numero_documento=numero_documento,
                cantidad_entrada=cantidad,
                cantidad_saldo=nuevo_saldo,
                costo_unitario=costo_unitario,
                costo_total_entrada=costo_total_entrada,
                costo_saldo=nuevo_costo_saldo,
                costo_promedio=costo_promedio,
                observaciones=observaciones,
                created_by=usuario,
                compra_id=documento_id if tipo_documento == 'compra' else None,
                venta_id=documento_id if tipo_documento == 'devolucion_venta' else None,
                ajuste_id=documento_id if tipo_documento == 'ajuste' else None,
            )
            
            # Actualizar stock del producto
            producto.actualizar_stock_total()
            
            return movimiento
    
    @classmethod
    def registrar_salida(cls, empresa, producto, almacen, cantidad, 
                        tipo_documento, numero_documento, fecha, observaciones="", 
                        documento_id=None, usuario=""):
        """
        Registra una salida de inventario aplicando método FIFO
        """
        with transaction.atomic():
            # Obtener saldo actual
            ultimo_movimiento = cls.objects.filter(
                empresa=empresa,
                producto=producto,
                almacen=almacen
            ).first()
            
            if not ultimo_movimiento or ultimo_movimiento.cantidad_saldo < cantidad:
                raise ValidationError(f"Stock insuficiente. Disponible: {ultimo_movimiento.cantidad_saldo if ultimo_movimiento else 0}")
            
            saldo_anterior = ultimo_movimiento.cantidad_saldo
            costo_saldo_anterior = ultimo_movimiento.costo_saldo
            
            # Aplicar FIFO para calcular costo de salida
            costo_total_salida = cls._calcular_costo_fifo(empresa, producto, almacen, cantidad)
            
            # Calcular nuevos valores
            nuevo_saldo = saldo_anterior - cantidad
            nuevo_costo_saldo = costo_saldo_anterior - costo_total_salida
            
            # Calcular costo promedio
            costo_promedio = nuevo_costo_saldo / nuevo_saldo if nuevo_saldo > 0 else Decimal('0')
            costo_unitario_promedio = costo_total_salida / cantidad if cantidad > 0 else Decimal('0')
            
            # Crear el movimiento
            movimiento = cls.objects.create(
                empresa=empresa,
                producto=producto,
                almacen=almacen,
                fecha=fecha,
                tipo_movimiento='salida',
                tipo_documento=tipo_documento,
                numero_documento=numero_documento,
                cantidad_salida=cantidad,
                cantidad_saldo=nuevo_saldo,
                costo_unitario=costo_unitario_promedio,
                costo_total_salida=costo_total_salida,
                costo_saldo=nuevo_costo_saldo,
                costo_promedio=costo_promedio,
                observaciones=observaciones,
                created_by=usuario,
                compra_id=documento_id if tipo_documento == 'devolucion_compra' else None,
                venta_id=documento_id if tipo_documento == 'venta' else None,
                ajuste_id=documento_id if tipo_documento == 'ajuste' else None,
            )
            
            # Actualizar stock del producto
            producto.actualizar_stock_total()
            
            return movimiento
    
    @classmethod
    def _calcular_costo_fifo(cls, empresa, producto, almacen, cantidad_salida):
        """
        Calcula el costo de salida aplicando método FIFO
        """
        # Obtener todas las entradas pendientes ordenadas por fecha (FIFO)
        entradas = cls.objects.filter(
            empresa=empresa,
            producto=producto,
            almacen=almacen,
            tipo_movimiento__in=['entrada', 'ajuste_entrada', 'devolucion_venta', 'transferencia_entrada']
        ).order_by('fecha', 'id')
        
        # Obtener todas las salidas para calcular cuánto queda de cada entrada
        salidas = cls.objects.filter(
            empresa=empresa,
            producto=producto,
            almacen=almacen,
            tipo_movimiento__in=['salida', 'ajuste_salida', 'devolucion_compra', 'transferencia_salida']
        ).order_by('fecha', 'id')
        
        # Calcular disponible por entrada aplicando FIFO
        entradas_disponibles = []
        cantidad_total_entradas = Decimal('0')
        cantidad_total_salidas = Decimal('0')
        
        for entrada in entradas:
            cantidad_total_entradas += entrada.cantidad_entrada
            entradas_disponibles.append({
                'fecha': entrada.fecha,
                'cantidad_original': entrada.cantidad_entrada,
                'costo_unitario': entrada.costo_unitario,
                'cantidad_disponible': entrada.cantidad_entrada
            })
        
        # Aplicar salidas anteriores
        for salida in salidas:
            cantidad_a_descontar = salida.cantidad_salida
            cantidad_total_salidas += cantidad_a_descontar
            
            for entrada_disp in entradas_disponibles:
                if cantidad_a_descontar <= 0:
                    break
                
                if entrada_disp['cantidad_disponible'] > 0:
                    descontar = min(entrada_disp['cantidad_disponible'], cantidad_a_descontar)
                    entrada_disp['cantidad_disponible'] -= descontar
                    cantidad_a_descontar -= descontar
        
        # Calcular costo de la nueva salida aplicando FIFO
        costo_total_salida = Decimal('0')
        cantidad_restante = cantidad_salida
        
        for entrada_disp in entradas_disponibles:
            if cantidad_restante <= 0:
                break
            
            if entrada_disp['cantidad_disponible'] > 0:
                tomar = min(entrada_disp['cantidad_disponible'], cantidad_restante)
                costo_total_salida += tomar * entrada_disp['costo_unitario']
                cantidad_restante -= tomar
        
        if cantidad_restante > 0:
            raise ValidationError(f"No hay suficiente stock para la salida. Faltante: {cantidad_restante}")
        
        return costo_total_salida
    
    @classmethod
    def obtener_kardex(cls, empresa, producto=None, almacen=None, fecha_inicio=None, fecha_fin=None):
        """
        Obtiene el kardex filtrado por los parámetros dados
        """
        queryset = cls.objects.filter(empresa=empresa)
        
        if producto:
            queryset = queryset.filter(producto=producto)
        
        if almacen:
            queryset = queryset.filter(almacen=almacen)
        
        if fecha_inicio:
            queryset = queryset.filter(fecha__gte=fecha_inicio)
        
        if fecha_fin:
            queryset = queryset.filter(fecha__lte=fecha_fin)
        
        return queryset.order_by('fecha', 'id')
    
    @classmethod
    def obtener_stock_actual(cls, empresa, producto, almacen):
        """
        Obtiene el stock actual de un producto en un almacén
        """
        ultimo_movimiento = cls.objects.filter(
            empresa=empresa,
            producto=producto,
            almacen=almacen
        ).first()
        
        return {
            'cantidad': ultimo_movimiento.cantidad_saldo if ultimo_movimiento else Decimal('0'),
            'costo_total': ultimo_movimiento.costo_saldo if ultimo_movimiento else Decimal('0'),
            'costo_promedio': ultimo_movimiento.costo_promedio if ultimo_movimiento else Decimal('0')
        } 