from django.db import models, transaction
from django.core.exceptions import ValidationError
from decimal import Decimal
from apps.empresas.models import Empresa
from .producto import Producto
from .almacen import Almacen


class InventarioProductosTerminados(models.Model):
    """
    Inventario específico para productos terminados.
    Controla el stock disponible para venta, reservado para pedidos pendientes,
    y gestiona costos de producción.
    """
    
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE)
    producto = models.ForeignKey(
        Producto, 
        on_delete=models.CASCADE, 
        related_name='inventario_productos_terminados',
        limit_choices_to={'tipo_producto': 'FINISHED'}
    )
    almacen = models.ForeignKey(Almacen, on_delete=models.CASCADE)
    
    # Cantidades
    cantidad_disponible = models.DecimalField(
        max_digits=12, 
        decimal_places=4, 
        default=0,
        verbose_name='Cantidad Disponible',
        help_text='Stock disponible para venta'
    )
    cantidad_reservada = models.DecimalField(
        max_digits=12, 
        decimal_places=4, 
        default=0,
        verbose_name='Cantidad Reservada',
        help_text='Stock reservado para ventas pendientes'
    )
    
    # Costos
    costo_produccion_unitario = models.DecimalField(
        max_digits=12, 
        decimal_places=4, 
        default=0,
        verbose_name='Costo de Producción Unitario',
        help_text='Costo promedio de producción por unidad'
    )
    precio_venta_sugerido = models.DecimalField(
        max_digits=12, 
        decimal_places=4, 
        default=0,
        verbose_name='Precio de Venta Sugerido'
    )
    
    # Ubicación y control
    ubicacion_almacen = models.CharField(
        max_length=100, 
        blank=True,
        verbose_name='Ubicación en Almacén'
    )
    
    # Niveles de stock
    stock_minimo = models.DecimalField(
        max_digits=12, 
        decimal_places=4, 
        default=0,
        verbose_name='Stock Mínimo'
    )
    stock_maximo = models.DecimalField(
        max_digits=12, 
        decimal_places=4, 
        default=0,
        verbose_name='Stock Máximo'
    )
    
    # Control de lotes de producción
    lote_produccion = models.CharField(
        max_length=100, 
        blank=True,
        verbose_name='Lote de Producción'
    )
    fecha_produccion = models.DateField(
        null=True, 
        blank=True,
        verbose_name='Fecha de Producción'
    )
    fecha_vencimiento = models.DateField(
        null=True, 
        blank=True,
        verbose_name='Fecha de Vencimiento'
    )
    
    # Referencia a orden de producción
    orden_produccion_id = models.IntegerField(
        null=True, 
        blank=True,
        verbose_name='ID Orden de Producción'
    )
    
    # Metadatos
    ultima_actualizacion = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Inventario de Producto Terminado'
        verbose_name_plural = 'Inventarios de Productos Terminados'
        unique_together = ['empresa', 'producto', 'almacen', 'lote_produccion']
        ordering = ['producto__nombre']
        indexes = [
            models.Index(fields=['empresa', 'producto']),
            models.Index(fields=['empresa', 'almacen']),
            models.Index(fields=['fecha_produccion']),
            models.Index(fields=['fecha_vencimiento']),
        ]
    
    def __str__(self):
        return f"{self.producto.nombre} - {self.almacen.nombre}: {self.cantidad_disponible}"
    
    def clean(self):
        """Validaciones del modelo"""
        if self.cantidad_disponible < 0:
            raise ValidationError('La cantidad disponible no puede ser negativa')
        if self.cantidad_reservada < 0:
            raise ValidationError('La cantidad reservada no puede ser negativa')
        if self.stock_minimo < 0:
            raise ValidationError('El stock mínimo no puede ser negativo')
        if self.stock_maximo < 0:
            raise ValidationError('El stock máximo no puede ser negativo')
        if self.stock_minimo > self.stock_maximo and self.stock_maximo > 0:
            raise ValidationError('El stock mínimo no puede ser mayor al stock máximo')
        
        # Validar que el producto sea producto terminado
        if self.producto and self.producto.tipo_producto != 'FINISHED':
            raise ValidationError('Este inventario solo acepta productos terminados')
    
    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)
    
    @property
    def cantidad_total(self):
        """Cantidad total incluyendo reservada"""
        return self.cantidad_disponible + self.cantidad_reservada
    
    @property
    def valor_inventario(self):
        """Valor del inventario basado en costo de producción"""
        return self.cantidad_total * self.costo_produccion_unitario
    
    @property
    def valor_venta_potencial(self):
        """Valor potencial de venta"""
        return self.cantidad_disponible * self.precio_venta_sugerido
    
    @property
    def margen_utilidad(self):
        """Margen de utilidad en porcentaje"""
        if self.costo_produccion_unitario > 0:
            return ((self.precio_venta_sugerido - self.costo_produccion_unitario) / 
                    self.costo_produccion_unitario * 100)
        return Decimal('0')
    
    @property
    def estado_stock(self):
        """Estado del stock basado en niveles"""
        if self.cantidad_disponible <= 0:
            return 'sin_stock'
        elif self.cantidad_disponible <= self.stock_minimo:
            return 'stock_bajo'
        elif self.stock_maximo > 0 and self.cantidad_disponible >= self.stock_maximo:
            return 'stock_alto'
        return 'normal'
    
    @classmethod
    def registrar_entrada_produccion(cls, empresa, producto, almacen, cantidad, 
                                      costo_produccion, lote='', orden_produccion_id=None,
                                      fecha_produccion=None, fecha_vencimiento=None,
                                      ubicacion=''):
        """
        Registra entrada de productos terminados desde producción.
        Actualiza el costo de producción promedio.
        """
        with transaction.atomic():
            # Obtener o crear registro de inventario
            inventario, created = cls.objects.get_or_create(
                empresa=empresa,
                producto=producto,
                almacen=almacen,
                lote_produccion=lote or '',
                defaults={
                    'cantidad_disponible': Decimal('0'),
                    'cantidad_reservada': Decimal('0'),
                    'costo_produccion_unitario': costo_produccion,
                    'precio_venta_sugerido': producto.precio_venta or Decimal('0'),
                    'ubicacion_almacen': ubicacion,
                    'fecha_produccion': fecha_produccion,
                    'fecha_vencimiento': fecha_vencimiento,
                    'orden_produccion_id': orden_produccion_id,
                }
            )
            
            if not created:
                # Calcular nuevo costo promedio de producción
                cantidad_anterior = inventario.cantidad_disponible + inventario.cantidad_reservada
                costo_anterior = inventario.costo_produccion_unitario
                
                cantidad_total = cantidad_anterior + cantidad
                if cantidad_total > 0:
                    nuevo_costo = (
                        (cantidad_anterior * costo_anterior) + (cantidad * costo_produccion)
                    ) / cantidad_total
                    inventario.costo_produccion_unitario = nuevo_costo
            
            # Incrementar cantidad disponible
            inventario.cantidad_disponible += cantidad
            
            # Actualizar campos adicionales si se proporcionan
            if ubicacion:
                inventario.ubicacion_almacen = ubicacion
            if fecha_produccion:
                inventario.fecha_produccion = fecha_produccion
            if fecha_vencimiento:
                inventario.fecha_vencimiento = fecha_vencimiento
            if orden_produccion_id:
                inventario.orden_produccion_id = orden_produccion_id
            
            inventario.save()
            
            return inventario
    
    @classmethod
    def reservar_para_venta(cls, empresa, producto, almacen, cantidad):
        """
        Reserva productos para una venta pendiente.
        Mueve cantidad de disponible a reservada.
        """
        with transaction.atomic():
            try:
                inventario = cls.objects.select_for_update().get(
                    empresa=empresa,
                    producto=producto,
                    almacen=almacen
                )
            except cls.DoesNotExist:
                raise ValidationError(f'No existe inventario para {producto.nombre} en {almacen.nombre}')
            
            if inventario.cantidad_disponible < cantidad:
                raise ValidationError(
                    f'Stock insuficiente para {producto.nombre}. '
                    f'Disponible: {inventario.cantidad_disponible}, Solicitado: {cantidad}'
                )
            
            inventario.cantidad_disponible -= cantidad
            inventario.cantidad_reservada += cantidad
            inventario.save()
            
            return inventario
    
    @classmethod
    def liberar_reserva(cls, empresa, producto, almacen, cantidad):
        """
        Libera reserva (por cancelación de venta).
        Mueve cantidad de reservada a disponible.
        """
        with transaction.atomic():
            inventario = cls.objects.select_for_update().get(
                empresa=empresa,
                producto=producto,
                almacen=almacen
            )
            
            if inventario.cantidad_reservada < cantidad:
                raise ValidationError(
                    f'Cantidad reservada insuficiente para {producto.nombre}. '
                    f'Reservada: {inventario.cantidad_reservada}, Solicitado: {cantidad}'
                )
            
            inventario.cantidad_reservada -= cantidad
            inventario.cantidad_disponible += cantidad
            inventario.save()
            
            return inventario
    
    @classmethod
    def procesar_venta(cls, empresa, producto, almacen, cantidad, desde_reserva=True):
        """
        Procesa la salida por venta.
        Si desde_reserva=True, descuenta de cantidad_reservada.
        Si desde_reserva=False, descuenta directamente de cantidad_disponible.
        
        Retorna el costo de los productos vendidos (COGS).
        """
        with transaction.atomic():
            try:
                inventario = cls.objects.select_for_update().get(
                    empresa=empresa,
                    producto=producto,
                    almacen=almacen
                )
            except cls.DoesNotExist:
                raise ValidationError(f'No existe inventario para {producto.nombre} en {almacen.nombre}')
            
            if desde_reserva:
                if inventario.cantidad_reservada < cantidad:
                    raise ValidationError(
                        f'Cantidad reservada insuficiente para {producto.nombre}. '
                        f'Reservada: {inventario.cantidad_reservada}, A vender: {cantidad}'
                    )
                inventario.cantidad_reservada -= cantidad
            else:
                if inventario.cantidad_disponible < cantidad:
                    raise ValidationError(
                        f'Stock insuficiente para {producto.nombre}. '
                        f'Disponible: {inventario.cantidad_disponible}, A vender: {cantidad}'
                    )
                inventario.cantidad_disponible -= cantidad
            
            # Calcular costo de productos vendidos (COGS)
            costo_venta = cantidad * inventario.costo_produccion_unitario
            
            inventario.save()
            
            return {
                'inventario': inventario,
                'costo_venta': costo_venta,
                'costo_unitario': inventario.costo_produccion_unitario
            }
    
    @classmethod
    def ajustar_inventario(cls, empresa, producto, almacen, cantidad_ajuste, motivo=''):
        """
        Realiza un ajuste de inventario (positivo o negativo).
        """
        with transaction.atomic():
            inventario = cls.objects.select_for_update().get(
                empresa=empresa,
                producto=producto,
                almacen=almacen
            )
            
            nueva_cantidad = inventario.cantidad_disponible + cantidad_ajuste
            
            if nueva_cantidad < 0:
                raise ValidationError(
                    f'El ajuste resultaría en inventario negativo. '
                    f'Disponible: {inventario.cantidad_disponible}, Ajuste: {cantidad_ajuste}'
                )
            
            inventario.cantidad_disponible = nueva_cantidad
            inventario.save()
            
            return inventario
    
    @classmethod
    def obtener_alertas_stock(cls, empresa):
        """
        Obtiene todos los productos terminados con alertas de stock.
        """
        from django.db.models import F
        from django.utils import timezone
        from datetime import timedelta
        
        alertas = []
        
        # Stock bajo
        stock_bajo = cls.objects.filter(
            empresa=empresa,
            cantidad_disponible__lte=F('stock_minimo'),
            stock_minimo__gt=0
        ).select_related('producto', 'almacen')
        
        for inv in stock_bajo:
            alertas.append({
                'tipo': 'stock_bajo',
                'producto': inv.producto.nombre,
                'almacen': inv.almacen.nombre,
                'cantidad_disponible': inv.cantidad_disponible,
                'stock_minimo': inv.stock_minimo,
                'mensaje': f'Stock bajo para {inv.producto.nombre}: {inv.cantidad_disponible}/{inv.stock_minimo}'
            })
        
        # Productos por vencer (30 días)
        fecha_limite = timezone.now().date() + timedelta(days=30)
        por_vencer = cls.objects.filter(
            empresa=empresa,
            fecha_vencimiento__lte=fecha_limite,
            fecha_vencimiento__isnull=False,
            cantidad_disponible__gt=0
        ).select_related('producto', 'almacen')
        
        for inv in por_vencer:
            alertas.append({
                'tipo': 'por_vencer',
                'producto': inv.producto.nombre,
                'almacen': inv.almacen.nombre,
                'fecha_vencimiento': inv.fecha_vencimiento,
                'cantidad_disponible': inv.cantidad_disponible,
                'mensaje': f'{inv.producto.nombre} vence el {inv.fecha_vencimiento}'
            })
        
        return alertas
    
    @classmethod
    def obtener_stock_total_producto(cls, empresa, producto):
        """
        Obtiene el stock total de un producto terminado sumando todos los almacenes.
        """
        from django.db.models import Sum
        
        resultado = cls.objects.filter(
            empresa=empresa,
            producto=producto
        ).aggregate(
            total_disponible=Sum('cantidad_disponible'),
            total_reservado=Sum('cantidad_reservada'),
            costo_promedio=models.Avg('costo_produccion_unitario')
        )
        
        return {
            'cantidad_disponible': resultado['total_disponible'] or Decimal('0'),
            'cantidad_reservada': resultado['total_reservado'] or Decimal('0'),
            'cantidad_total': (resultado['total_disponible'] or Decimal('0')) + 
                             (resultado['total_reservado'] or Decimal('0')),
            'costo_promedio': resultado['costo_promedio'] or Decimal('0')
        }
