from django.db import models, transaction
from django.core.exceptions import ValidationError
from decimal import Decimal
from apps.empresas.models import Empresa
from .producto import Producto
from .almacen import Almacen


class InventarioMateriasPrimas(models.Model):
    """
    Inventario específico para materias primas e insumos.
    Controla el stock disponible, reservado y costos para la producción.
    """
    
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE)
    producto = models.ForeignKey(
        Producto, 
        on_delete=models.CASCADE, 
        related_name='inventario_materias_primas',
        limit_choices_to={'tipo_producto__in': ['RAW', 'SEMIFINISHED']}
    )
    almacen = models.ForeignKey(Almacen, on_delete=models.CASCADE)
    
    # Cantidades
    cantidad_disponible = models.DecimalField(
        max_digits=12, 
        decimal_places=4, 
        default=0,
        verbose_name='Cantidad Disponible',
        help_text='Stock disponible para uso'
    )
    cantidad_reservada = models.DecimalField(
        max_digits=12, 
        decimal_places=4, 
        default=0,
        verbose_name='Cantidad Reservada',
        help_text='Stock reservado para producción en proceso'
    )
    
    # Costos
    costo_unitario_promedio = models.DecimalField(
        max_digits=12, 
        decimal_places=4, 
        default=0,
        verbose_name='Costo Unitario Promedio',
        help_text='Costo promedio ponderado'
    )
    
    # Ubicación y control
    ubicacion_almacen = models.CharField(
        max_length=100, 
        blank=True,
        verbose_name='Ubicación en Almacén',
        help_text='Estante, pasillo, etc.'
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
    
    # Control de lotes (opcional)
    lote = models.CharField(
        max_length=100, 
        blank=True,
        verbose_name='Número de Lote'
    )
    fecha_vencimiento = models.DateField(
        null=True, 
        blank=True,
        verbose_name='Fecha de Vencimiento'
    )
    
    # Metadatos
    ultima_actualizacion = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Inventario de Materia Prima'
        verbose_name_plural = 'Inventarios de Materias Primas'
        unique_together = ['empresa', 'producto', 'almacen', 'lote']
        ordering = ['producto__nombre']
        indexes = [
            models.Index(fields=['empresa', 'producto']),
            models.Index(fields=['empresa', 'almacen']),
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
        
        # Validar que el producto sea materia prima o insumo
        if self.producto and self.producto.tipo_producto not in ['RAW', 'SEMIFINISHED']:
            raise ValidationError('Este inventario solo acepta materias primas o productos semi-terminados')
    
    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)
    
    @property
    def cantidad_total(self):
        """Cantidad total incluyendo reservada"""
        return self.cantidad_disponible + self.cantidad_reservada
    
    @property
    def valor_inventario(self):
        """Valor total del inventario (disponible + reservado)"""
        return self.cantidad_total * self.costo_unitario_promedio
    
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
    
    @property
    def esta_por_vencer(self):
        """Verifica si el producto está por vencer (30 días)"""
        if not self.fecha_vencimiento:
            return False
        from django.utils import timezone
        from datetime import timedelta
        return self.fecha_vencimiento <= (timezone.now().date() + timedelta(days=30))
    
    @classmethod
    def registrar_entrada_compra(cls, empresa, producto, almacen, cantidad, costo_unitario, 
                                  lote='', fecha_vencimiento=None, ubicacion=''):
        """
        Registra una entrada por compra y actualiza el costo promedio ponderado.
        
        Fórmula costo promedio:
        Nuevo costo = (Cantidad anterior × Costo anterior + Cantidad nueva × Costo nuevo) / Cantidad total
        """
        with transaction.atomic():
            # Obtener o crear registro de inventario
            inventario, created = cls.objects.get_or_create(
                empresa=empresa,
                producto=producto,
                almacen=almacen,
                lote=lote or '',
                defaults={
                    'cantidad_disponible': Decimal('0'),
                    'cantidad_reservada': Decimal('0'),
                    'costo_unitario_promedio': costo_unitario,
                    'ubicacion_almacen': ubicacion,
                    'fecha_vencimiento': fecha_vencimiento,
                }
            )
            
            if not created:
                # Calcular nuevo costo promedio ponderado
                cantidad_anterior = inventario.cantidad_disponible + inventario.cantidad_reservada
                costo_anterior = inventario.costo_unitario_promedio
                
                cantidad_total = cantidad_anterior + cantidad
                if cantidad_total > 0:
                    nuevo_costo = (
                        (cantidad_anterior * costo_anterior) + (cantidad * costo_unitario)
                    ) / cantidad_total
                    inventario.costo_unitario_promedio = nuevo_costo
            
            # Incrementar cantidad disponible
            inventario.cantidad_disponible += cantidad
            
            # Actualizar ubicación si se proporciona
            if ubicacion:
                inventario.ubicacion_almacen = ubicacion
            
            # Actualizar fecha de vencimiento si se proporciona
            if fecha_vencimiento:
                inventario.fecha_vencimiento = fecha_vencimiento
            
            inventario.save()
            
            return inventario
    
    @classmethod
    def reservar_para_produccion(cls, empresa, producto, almacen, cantidad):
        """
        Reserva materiales para una orden de producción.
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
        Libera reserva (por cancelación de orden de producción).
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
    def consumir_en_produccion(cls, empresa, producto, almacen, cantidad, desde_reserva=True):
        """
        Consume materiales para producción.
        Si desde_reserva=True, descuenta de cantidad_reservada.
        Si desde_reserva=False, descuenta directamente de cantidad_disponible.
        
        Retorna el costo total consumido.
        """
        with transaction.atomic():
            inventario = cls.objects.select_for_update().get(
                empresa=empresa,
                producto=producto,
                almacen=almacen
            )
            
            if desde_reserva:
                if inventario.cantidad_reservada < cantidad:
                    raise ValidationError(
                        f'Cantidad reservada insuficiente para {producto.nombre}. '
                        f'Reservada: {inventario.cantidad_reservada}, A consumir: {cantidad}'
                    )
                inventario.cantidad_reservada -= cantidad
            else:
                if inventario.cantidad_disponible < cantidad:
                    raise ValidationError(
                        f'Stock insuficiente para {producto.nombre}. '
                        f'Disponible: {inventario.cantidad_disponible}, A consumir: {cantidad}'
                    )
                inventario.cantidad_disponible -= cantidad
            
            # Calcular costo total consumido
            costo_consumido = cantidad * inventario.costo_unitario_promedio
            
            inventario.save()
            
            return {
                'inventario': inventario,
                'costo_consumido': costo_consumido,
                'costo_unitario': inventario.costo_unitario_promedio
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
        Obtiene todos los productos con alertas de stock.
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
