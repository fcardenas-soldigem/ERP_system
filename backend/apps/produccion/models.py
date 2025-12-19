from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone
from decimal import Decimal
from apps.empresas.models import Empresa
from apps.inventario.models import Producto, Almacen
from django.contrib.auth import get_user_model

User = get_user_model()


class RecetaProducto(models.Model):
    """
    Receta o BOM (Bill of Materials) para producir un producto terminado.
    Define qué insumos se necesitan y en qué cantidades.
    """
    empresa = models.ForeignKey(
        Empresa,
        on_delete=models.CASCADE,
        related_name='recetas_produccion'
    )
    producto_terminado = models.ForeignKey(
        Producto,
        on_delete=models.PROTECT,
        related_name='recetas',
        verbose_name='Producto Terminado',
        help_text='Producto que se obtiene al ejecutar esta receta'
    )
    nombre = models.CharField(
        max_length=200,
        verbose_name='Nombre de la Receta',
        help_text='Descripción de la receta'
    )
    cantidad_producida = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=1,
        verbose_name='Cantidad Producida',
        help_text='Cantidad de producto terminado que se obtiene con esta receta'
    )
    tiempo_estimado = models.IntegerField(
        default=0,
        verbose_name='Tiempo Estimado (minutos)',
        help_text='Tiempo estimado de producción en minutos'
    )
    costo_mano_obra = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name='Costo de Mano de Obra',
        help_text='Costo estimado de mano de obra directa'
    )
    costo_indirecto = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name='Costos Indirectos (CIF)',
        help_text='Costos indirectos de fabricación'
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name='Activa',
        help_text='Indica si esta receta está activa'
    )
    version = models.IntegerField(
        default=1,
        verbose_name='Versión',
        help_text='Número de versión de la receta'
    )
    notas = models.TextField(
        blank=True,
        verbose_name='Notas',
        help_text='Instrucciones adicionales para la producción'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Receta de Producción'
        verbose_name_plural = 'Recetas de Producción'
        ordering = ['-created_at']
        unique_together = ['empresa', 'producto_terminado', 'version']

    def __str__(self):
        return f"{self.nombre} - v{self.version}"

    def clean(self):
        """Validaciones personalizadas"""
        if self.cantidad_producida <= 0:
            raise ValidationError('La cantidad producida debe ser mayor a 0')
        
        # Validar que el producto terminado no esté como insumo en sus propios detalles
        if self.pk:
            insumos_ids = self.detalles.values_list('insumo_id', flat=True)
            if self.producto_terminado_id in insumos_ids:
                raise ValidationError(
                    'El producto terminado no puede ser usado como insumo en su propia receta'
                )

    def calcular_costo_teorico(self):
        """Calcula el costo teórico total de la receta"""
        costo_insumos = sum(
            detalle.cantidad * detalle.costo_unitario 
            for detalle in self.detalles.all()
        )
        costo_total = costo_insumos + self.costo_mano_obra + self.costo_indirecto
        return {
            'costo_insumos': costo_insumos,
            'costo_mano_obra': self.costo_mano_obra,
            'costo_indirecto': self.costo_indirecto,
            'costo_total': costo_total,
            'costo_unitario': costo_total / self.cantidad_producida if self.cantidad_producida > 0 else 0
        }


class RecetaDetalle(models.Model):
    """
    Detalle de los insumos necesarios para una receta.
    Cada registro representa un insumo con su cantidad requerida.
    """
    receta = models.ForeignKey(
        RecetaProducto,
        on_delete=models.CASCADE,
        related_name='detalles'
    )
    insumo = models.ForeignKey(
        Producto,
        on_delete=models.PROTECT,
        related_name='usado_en_recetas',
        verbose_name='Insumo'
    )
    cantidad = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name='Cantidad Necesaria'
    )
    unidad_medida = models.CharField(
        max_length=20,
        verbose_name='Unidad de Medida',
        help_text='Debe coincidir con la unidad del producto'
    )
    costo_unitario = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name='Costo Unitario',
        help_text='Costo unitario del insumo al momento de crear la receta (referencia)'
    )
    notas = models.TextField(
        blank=True,
        verbose_name='Notas',
        help_text='Notas adicionales sobre este insumo'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Detalle de Receta'
        verbose_name_plural = 'Detalles de Receta'
        unique_together = ['receta', 'insumo']

    def __str__(self):
        return f"{self.insumo.nombre} - {self.cantidad} {self.unidad_medida}"

    def clean(self):
        """Validaciones personalizadas"""
        if self.cantidad <= 0:
            raise ValidationError('La cantidad debe ser mayor a 0')
        
        # Validar que la unidad de medida coincida con la del producto
        if self.insumo and self.insumo.unidad_medida != self.unidad_medida:
            raise ValidationError(
                f'La unidad de medida debe ser {self.insumo.get_unidad_medida_display()}'
            )

    def save(self, *args, **kwargs):
        # Si no se especifica costo unitario, usar el del producto
        if not self.costo_unitario and self.insumo:
            self.costo_unitario = self.insumo.precio_compra
        
        # Si no se especifica unidad de medida, usar la del producto
        if not self.unidad_medida and self.insumo:
            self.unidad_medida = self.insumo.unidad_medida
        
        self.clean()
        super().save(*args, **kwargs)

    @property
    def costo_total(self):
        """Costo total del insumo (cantidad * costo unitario)"""
        return self.cantidad * self.costo_unitario


class OrdenProduccion(models.Model):
    """
    Orden de Producción - Representa una orden de trabajo para producir productos.
    Controla el flujo desde la planificación hasta la finalización.
    """
    ESTADO_CHOICES = [
        ('pendiente', 'Pendiente'),
        ('en_proceso', 'En Proceso'),
        ('finalizada', 'Finalizada'),
        ('cancelada', 'Cancelada'),
    ]

    empresa = models.ForeignKey(
        Empresa,
        on_delete=models.CASCADE,
        related_name='ordenes_produccion'
    )
    numero = models.CharField(
        max_length=20,
        unique=True,
        verbose_name='Número de Orden',
        help_text='Código único de la orden (auto-generado)'
    )
    receta = models.ForeignKey(
        RecetaProducto,
        on_delete=models.PROTECT,
        related_name='ordenes',
        verbose_name='Receta'
    )
    cantidad_planificada = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name='Cantidad Planificada',
        help_text='Cantidad que se planea producir'
    )
    cantidad_producida = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name='Cantidad Producida',
        help_text='Cantidad real producida'
    )
    fecha_programada = models.DateField(
        verbose_name='Fecha Programada',
        help_text='Fecha en que se debe producir'
    )
    fecha_inicio = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Fecha de Inicio',
        help_text='Fecha y hora en que se inició la producción'
    )
    fecha_fin = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Fecha de Finalización',
        help_text='Fecha y hora en que se finalizó la producción'
    )
    almacen_insumos = models.ForeignKey(
        Almacen,
        on_delete=models.PROTECT,
        related_name='ordenes_consumo',
        verbose_name='Almacén de Insumos',
        help_text='Almacén desde donde se consumen los insumos'
    )
    almacen_destino = models.ForeignKey(
        Almacen,
        on_delete=models.PROTECT,
        related_name='ordenes_destino',
        verbose_name='Almacén de Destino',
        help_text='Almacén donde ingresa el producto terminado'
    )
    estado = models.CharField(
        max_length=20,
        choices=ESTADO_CHOICES,
        default='pendiente',
        verbose_name='Estado'
    )
    costo_mano_obra_real = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name='Costo Mano de Obra Real',
        help_text='Costo real de mano de obra'
    )
    costo_indirecto_real = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name='Costo Indirecto Real',
        help_text='Costos indirectos reales (CIF)'
    )
    tiempo_real = models.IntegerField(
        default=0,
        verbose_name='Tiempo Real (minutos)',
        help_text='Tiempo real que tomó la producción en minutos'
    )
    observaciones = models.TextField(
        blank=True,
        verbose_name='Observaciones',
        help_text='Notas u observaciones del operador'
    )
    responsable = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='ordenes_responsable',
        verbose_name='Responsable',
        help_text='Usuario responsable de ejecutar la orden'
    )
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='ordenes_creadas',
        verbose_name='Creado por'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Orden de Producción'
        verbose_name_plural = 'Órdenes de Producción'
        ordering = ['-created_at']

    def __str__(self):
        return f"OP-{self.numero} - {self.receta.producto_terminado.nombre}"

    def clean(self):
        """Validaciones personalizadas"""
        if self.cantidad_planificada <= 0:
            raise ValidationError('La cantidad planificada debe ser mayor a 0')
        
        if self.cantidad_producida < 0:
            raise ValidationError('La cantidad producida no puede ser negativa')
        
        # Validar que los almacenes pertenezcan a la empresa
        if self.almacen_insumos and self.almacen_insumos.empresa_id != self.empresa_id:
            raise ValidationError('El almacén de insumos no pertenece a la empresa')
        
        if self.almacen_destino and self.almacen_destino.empresa_id != self.empresa_id:
            raise ValidationError('El almacén de destino no pertenece a la empresa')

    def save(self, *args, **kwargs):
        # Generar número de orden si no existe
        if not self.numero:
            ultimo = OrdenProduccion.objects.filter(
                empresa=self.empresa
            ).order_by('-id').first()
            
            if ultimo and ultimo.numero:
                try:
                    ultimo_num = int(ultimo.numero.split('-')[-1])
                    nuevo_num = ultimo_num + 1
                except (ValueError, IndexError):
                    nuevo_num = 1
            else:
                nuevo_num = 1
            
            self.numero = f"{nuevo_num:06d}"
        
        self.clean()
        super().save(*args, **kwargs)

    @property
    def esta_retrasada(self):
        """Verifica si la orden está retrasada"""
        if self.estado in ['finalizada', 'cancelada']:
            return False
        return self.fecha_programada < timezone.now().date()

    @property
    def eficiencia_produccion(self):
        """Calcula la eficiencia de producción (%)"""
        if self.cantidad_planificada > 0:
            return (self.cantidad_producida / self.cantidad_planificada) * 100
        return 0

    @property
    def eficiencia_tiempo(self):
        """Calcula la eficiencia de tiempo (%)"""
        if self.receta.tiempo_estimado > 0 and self.tiempo_real > 0:
            return (self.receta.tiempo_estimado / self.tiempo_real) * 100
        return 0

    def calcular_costo_real(self):
        """Calcula el costo real de la orden de producción"""
        costo_insumos = sum(
            consumo.costo_total for consumo in self.consumos.all()
        )
        costo_total = costo_insumos + self.costo_mano_obra_real + self.costo_indirecto_real
        costo_unitario = costo_total / self.cantidad_producida if self.cantidad_producida > 0 else 0
        
        return {
            'costo_insumos': costo_insumos,
            'costo_mano_obra': self.costo_mano_obra_real,
            'costo_indirecto': self.costo_indirecto_real,
            'costo_total': costo_total,
            'costo_unitario': costo_unitario
        }


class ConsumoReal(models.Model):
    """
    Consumo Real de Insumos - Registra el consumo real de cada insumo
    durante la ejecución de una orden de producción.
    """
    orden_produccion = models.ForeignKey(
        OrdenProduccion,
        on_delete=models.CASCADE,
        related_name='consumos'
    )
    insumo = models.ForeignKey(
        Producto,
        on_delete=models.PROTECT,
        related_name='consumos_produccion',
        verbose_name='Insumo'
    )
    cantidad_teorica = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name='Cantidad Teórica',
        help_text='Cantidad según la receta'
    )
    cantidad_real = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name='Cantidad Real',
        help_text='Cantidad realmente consumida'
    )
    merma = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name='Merma',
        help_text='Cantidad desperdiciada'
    )
    costo_unitario = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name='Costo Unitario',
        help_text='Precio del insumo al momento del consumo'
    )
    notas = models.TextField(
        blank=True,
        verbose_name='Notas',
        help_text='Observaciones sobre el consumo'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Consumo Real'
        verbose_name_plural = 'Consumos Reales'
        unique_together = ['orden_produccion', 'insumo']

    def __str__(self):
        return f"{self.insumo.nombre} - OP {self.orden_produccion.numero}"

    def clean(self):
        """Validaciones personalizadas"""
        if self.cantidad_teorica < 0:
            raise ValidationError('La cantidad teórica no puede ser negativa')
        
        if self.cantidad_real < 0:
            raise ValidationError('La cantidad real no puede ser negativa')
        
        if self.merma < 0:
            raise ValidationError('La merma no puede ser negativa')

    def save(self, *args, **kwargs):
        # Si no se especifica costo unitario, usar el del producto
        if not self.costo_unitario and self.insumo:
            self.costo_unitario = self.insumo.precio_compra
        
        self.clean()
        super().save(*args, **kwargs)

    @property
    def diferencia(self):
        """Diferencia entre consumo real y teórico"""
        return self.cantidad_real - self.cantidad_teorica

    @property
    def porcentaje_diferencia(self):
        """Porcentaje de diferencia respecto al teórico"""
        if self.cantidad_teorica > 0:
            return (self.diferencia / self.cantidad_teorica) * 100
        return 0

    @property
    def porcentaje_merma(self):
        """Porcentaje de merma respecto al consumo real"""
        if self.cantidad_real > 0:
            return (self.merma / self.cantidad_real) * 100
        return 0

    @property
    def costo_total(self):
        """Costo total del consumo (cantidad_real * costo_unitario)"""
        return self.cantidad_real * self.costo_unitario

    @property
    def costo_merma(self):
        """Costo de la merma"""
        return self.merma * self.costo_unitario


class ProductionOutput(models.Model):
    """
    Producción Parcial / Lotes
    Permite registrar cierres parciales de producción.
    """
    orden_produccion = models.ForeignKey(
        OrdenProduccion,
        on_delete=models.CASCADE,
        related_name='outputs',
        verbose_name='Orden de Producción'
    )
    cantidad_producida = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name='Cantidad Producida',
        help_text='Cantidad producida en este lote/cierre parcial'
    )
    numero_lote = models.CharField(
        max_length=50,
        blank=True,
        verbose_name='Número de Lote',
        help_text='Identificador del lote producido'
    )
    fecha_produccion = models.DateTimeField(
        default=timezone.now,
        verbose_name='Fecha de Producción'
    )
    notas = models.TextField(
        blank=True,
        verbose_name='Notas',
        help_text='Observaciones sobre este lote'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Producción Parcial'
        verbose_name_plural = 'Producciones Parciales'
        ordering = ['-created_at']

    def __str__(self):
        return f"Lote {self.numero_lote} - OP {self.orden_produccion.numero} - {self.cantidad_producida} unidades"


class ProductionWaste(models.Model):
    """
    Mermas y Desperdicios
    Registro detallado de mermas por razón.
    """
    MOTIVO_CHOICES = [
        ('PROCESS', 'Proceso Normal'),
        ('DAMAGED', 'Dañado/Defectuoso'),
        ('EXPIRED', 'Vencido/Caducado'),
        ('OTHER', 'Otro'),
    ]

    orden_produccion = models.ForeignKey(
        OrdenProduccion,
        on_delete=models.CASCADE,
        related_name='mermas',
        verbose_name='Orden de Producción'
    )
    producto = models.ForeignKey(
        'inventario.Producto',
        on_delete=models.PROTECT,
        related_name='mermas_produccion',
        verbose_name='Producto/Insumo'
    )
    cantidad_desperdiciada = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name='Cantidad Desperdiciada'
    )
    motivo = models.CharField(
        max_length=20,
        choices=MOTIVO_CHOICES,
        default='PROCESS',
        verbose_name='Motivo'
    )
    costo_unitario = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name='Costo Unitario'
    )
    descripcion = models.TextField(
        blank=True,
        verbose_name='Descripción',
        help_text='Detalles adicionales sobre la merma'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Merma/Desperdicio'
        verbose_name_plural = 'Mermas/Desperdicios'
        ordering = ['-created_at']

    def __str__(self):
        return f"Merma {self.producto.nombre} - OP {self.orden_produccion.numero} - {self.cantidad_desperdiciada}"

    @property
    def costo_total_merma(self):
        """Costo total de la merma"""
        return self.cantidad_desperdiciada * self.costo_unitario


class ProductionCost(models.Model):
    """
    Costeo de Producción
    Snapshot final del costo de una orden de producción.
    """
    orden_produccion = models.OneToOneField(
        OrdenProduccion,
        on_delete=models.CASCADE,
        related_name='costeo',
        verbose_name='Orden de Producción'
    )
    costo_materiales = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        verbose_name='Costo de Materiales',
        help_text='Costo total de insumos consumidos'
    )
    costo_mano_obra = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        verbose_name='Costo de Mano de Obra'
    )
    costo_indirecto = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        verbose_name='Costos Indirectos (CIF)'
    )
    costo_mermas = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        verbose_name='Costo de Mermas',
        help_text='Costo total de desperdicios'
    )
    costo_total = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        verbose_name='Costo Total'
    )
    costo_unitario = models.DecimalField(
        max_digits=12,
        decimal_places=4,
        default=0,
        verbose_name='Costo Unitario',
        help_text='Costo por unidad producida'
    )
    cantidad_producida = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name='Cantidad Producida',
        help_text='Snapshot de la cantidad producida'
    )
    notas = models.TextField(
        blank=True,
        verbose_name='Notas',
        help_text='Observaciones sobre el costeo'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Costeo de Producción'
        verbose_name_plural = 'Costeos de Producción'

    def __str__(self):
        return f"Costeo OP-{self.orden_produccion.numero} - Total: S/ {self.costo_total}"

    def calcular_costos(self):
        """
        Calcula todos los costos de la orden.
        Este método debe llamarse al finalizar la orden.
        """
        orden = self.orden_produccion

        # 1. Costo de materiales (insumos consumidos)
        self.costo_materiales = sum(
            consumo.costo_total for consumo in orden.consumos.all()
        )

        # 2. Costo de mano de obra
        self.costo_mano_obra = orden.costo_mano_obra_real or 0

        # 3. Costos indirectos
        self.costo_indirecto = orden.costo_indirecto_real or 0

        # 4. Costo de mermas
        self.costo_mermas = sum(
            merma.costo_total_merma for merma in orden.mermas.all()
        )

        # 5. Costo total
        self.costo_total = (
            self.costo_materiales +
            self.costo_mano_obra +
            self.costo_indirecto +
            self.costo_mermas
        )

        # 6. Costo unitario
        self.cantidad_producida = orden.cantidad_producida
        if self.cantidad_producida > 0:
            self.costo_unitario = self.costo_total / self.cantidad_producida
        else:
            self.costo_unitario = 0

        self.save()
        
        return {
            'costo_materiales': float(self.costo_materiales),
            'costo_mano_obra': float(self.costo_mano_obra),
            'costo_indirecto': float(self.costo_indirecto),
            'costo_mermas': float(self.costo_mermas),
            'costo_total': float(self.costo_total),
            'costo_unitario': float(self.costo_unitario),
            'cantidad_producida': float(self.cantidad_producida)
        }
